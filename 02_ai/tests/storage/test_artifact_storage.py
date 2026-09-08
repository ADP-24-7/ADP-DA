from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from typing import Any

import pytest
from adp_da import artifact_storage_cli, ncp_storage_e2e
from adp_da.storage import (
    ArtifactIntegrityError,
    ArtifactNotFoundError,
    ArtifactStorageError,
    LocalArtifactStore,
    NcpObjectStorageStore,
    build_object_key,
    load_published_artifact,
    publish_artifact,
    sha256_digest,
)
from botocore.exceptions import ClientError


class Body:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.closed = False

    def read(self, size: int) -> bytes:
        return self.data[:size]

    def close(self) -> None:
        self.closed = True


class FakeS3:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}
        self.put_calls: list[dict[str, Any]] = []
        self.deleted: list[tuple[str, str]] = []
        self.last_body: Body | None = None
        self.fail_manifest_put = False

    def head_object(self, **kwargs: Any) -> dict[str, Any]:
        identity = (kwargs["Bucket"], kwargs["Key"])
        if identity not in self.objects:
            raise ClientError({"Error": {"Code": "NoSuchKey", "Message": "missing"}}, "HeadObject")
        return {"ContentLength": len(self.objects[identity])}

    def put_object(self, **kwargs: Any) -> None:
        if self.fail_manifest_put and kwargs["Key"].endswith("/manifest.json"):
            raise ClientError(
                {"Error": {"Code": "RequestTimeout", "Message": "timeout"}}, "PutObject"
            )
        self.put_calls.append(kwargs)
        self.objects[(kwargs["Bucket"], kwargs["Key"])] = kwargs["Body"]

    def get_object(self, **kwargs: Any) -> dict[str, Body]:
        identity = (kwargs["Bucket"], kwargs["Key"])
        if identity not in self.objects:
            raise ClientError({"Error": {"Code": "NoSuchKey", "Message": "missing"}}, "GetObject")
        self.last_body = Body(self.objects[identity])
        return {"Body": self.last_body}

    def delete_object(self, **kwargs: Any) -> None:
        identity = (kwargs["Bucket"], kwargs["Key"])
        self.deleted.append(identity)
        self.objects.pop(identity, None)


def test_local_publish_load_and_canonical_manifest(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path, bucket="adp-qa-data-artifacts")
    data = b'{"validated":true}'
    published = publish_artifact(
        store,
        data,
        prefix="artifacts/validation",
        artifact_id="validation-001",
        artifact_version="2026.09-v1",
        filename="result.json",
        code_git_sha="abcdef1234567",
        classification="SYNTHETIC_OR_PSEUDONYMIZED",
        source_ids=("execution-1",),
        content_type="application/json",
    )

    manifest, downloaded = load_published_artifact(
        store,
        manifest_object_key=published.manifest_object_key,
        manifest_digest=published.manifest_digest,
    )

    assert downloaded == data
    assert manifest.digest == sha256_digest(data)
    assert published.reference()["bucket"] == "adp-qa-data-artifacts"
    stored_manifest = json.loads((tmp_path / published.manifest_object_key).read_text())
    assert stored_manifest == manifest.as_dict()


@pytest.mark.parametrize(
    "key",
    [
        "../artifacts/evaluation/a",
        "/artifacts/evaluation/a",
        "artifacts/evaluation/../policy/a",
        "artifacts//evaluation/a",
        "artifacts/evaluation\\a",
        "unknown/a",
    ],
)
def test_object_key_rejects_escape_and_unapproved_prefix(key: str) -> None:
    from adp_da.storage import validate_object_key

    with pytest.raises(ValueError):
        validate_object_key(key)


def test_object_key_builder_rejects_unsafe_identity() -> None:
    with pytest.raises(ValueError, match="artifact_id"):
        build_object_key("artifacts/evaluation", "../secret", "v1", "data.json")


def test_local_store_fails_closed_for_tamper_and_collision(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path)
    key = "artifacts/evaluation/eval-1/v1/data.json"
    original = b"original"
    store.put(key, original, digest=sha256_digest(original), content_type="application/json")

    with pytest.raises(ArtifactIntegrityError, match="other bytes"):
        store.put(
            key, b"changed", digest=sha256_digest(b"changed"), content_type="application/json"
        )

    (tmp_path / key).write_bytes(b"tampered")
    with pytest.raises(ArtifactIntegrityError, match="SHA-256"):
        store.get(key, expected_digest=sha256_digest(original))


def test_local_store_missing_object_is_explicit(tmp_path: Path) -> None:
    with pytest.raises(ArtifactNotFoundError):
        LocalArtifactStore(tmp_path).get(
            "artifacts/evaluation/missing/v1/data.json",
            expected_digest=sha256_digest(b"missing"),
        )


def test_ncp_store_upload_download_has_no_public_acl() -> None:
    client = FakeS3()
    store = NcpObjectStorageStore(client, bucket="adp-qa-data-artifacts")
    key = "handoff/validated/artifact-1/v1/data.json"
    data = b"validated"
    digest = sha256_digest(data)

    store.put(key, data, digest=digest, content_type="application/json")
    downloaded = store.get(key, expected_digest=digest)

    assert downloaded == data
    assert "ACL" not in client.put_calls[0]
    assert client.put_calls[0]["Metadata"] == {"sha256": digest.removeprefix("sha256:")}
    assert client.last_body is not None and client.last_body.closed


def test_ncp_store_same_key_is_idempotent_and_different_bytes_fail() -> None:
    client = FakeS3()
    store = NcpObjectStorageStore(client, bucket="adp-qa-data-artifacts")
    key = "artifacts/evaluation/eval-1/v1/result.json"
    original = b"original"

    assert store.put(key, original, digest=sha256_digest(original), content_type="application/json")
    assert not store.put(
        key, original, digest=sha256_digest(original), content_type="application/json"
    )
    with pytest.raises(ArtifactIntegrityError, match="immutable NCP"):
        store.put(
            key,
            b"different",
            digest=sha256_digest(b"different"),
            content_type="application/json",
        )

    assert len(client.put_calls) == 1


def test_ncp_store_maps_missing_object() -> None:
    store = NcpObjectStorageStore(FakeS3(), bucket="adp-qa-data-artifacts")
    with pytest.raises(ArtifactNotFoundError):
        store.get(
            "handoff/validated/missing/v1/data.json",
            expected_digest=sha256_digest(b"missing"),
        )


def test_ncp_configuration_requires_credentials_and_ncp_https_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="NCLOUD_ACCESS_KEY"):
        NcpObjectStorageStore.from_env({})

    environment = {
        "NCLOUD_ACCESS_KEY": "access",
        "NCLOUD_SECRET_KEY": "secret",
        "ADP_NCP_OBJECT_STORAGE_ENDPOINT": "https://example.invalid",
    }
    with pytest.raises(ValueError, match="NCP HTTPS origin"):
        NcpObjectStorageStore.from_env(environment)

    captured: dict[str, Any] = {}

    def fake_client(service: str, **kwargs: Any) -> FakeS3:
        captured.update({"service": service, **kwargs})
        return FakeS3()

    monkeypatch.setattr("adp_da.storage.ncp.boto3.client", fake_client)
    store = NcpObjectStorageStore.from_env(
        {
            "NCLOUD_ACCESS_KEY": "access",
            "NCLOUD_SECRET_KEY": "secret",
            "NCLOUD_REGION": "KR",
            "ADP_NCP_ARTIFACT_BUCKET": "adp-qa-data-artifacts",
        }
    )
    assert store.bucket == "adp-qa-data-artifacts"
    assert captured["service"] == "s3"
    assert captured["endpoint_url"] == "https://kr.object.ncloudstorage.com"
    assert captured["region_name"] == "KR"


@pytest.mark.parametrize("bucket", ["adp-qa-tfstate", "unapproved-artifacts"])
def test_ncp_store_rejects_state_and_non_allowlisted_bucket(bucket: str) -> None:
    with pytest.raises(ValueError, match="bucket"):
        NcpObjectStorageStore(FakeS3(), bucket=bucket)


def test_ncp_e2e_preflight_never_records_credentials() -> None:
    report = ncp_storage_e2e.preflight(
        {
            "NCLOUD_ACCESS_KEY": "must-not-appear",
            "NCLOUD_SECRET_KEY": "must-not-appear-either",
        }
    )
    serialized = json.dumps(report)
    assert report["access_key_present"] is True
    assert report["secret_key_present"] is True
    assert "must-not-appear" not in serialized
    assert report["credential_values_recorded"] is False


def test_ncp_e2e_requires_explicit_external_write_confirmation() -> None:
    with pytest.raises(RuntimeError, match="explicit YES"):
        ncp_storage_e2e.execute(
            {
                "NCLOUD_ACCESS_KEY": "access",
                "NCLOUD_SECRET_KEY": "secret",
                "ADP_CODE_GIT_SHA": "abcdef1",
                "ADP_NCP_STORAGE_E2E_CONFIRM": "NO",
            }
        )


def test_ncp_e2e_uploads_verifies_and_cleans_up(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeS3()
    store = NcpObjectStorageStore(client, bucket="adp-qa-data-artifacts")
    monkeypatch.setattr(
        ncp_storage_e2e.NcpObjectStorageStore,
        "from_env",
        lambda environment: store,
    )

    result = ncp_storage_e2e.execute(
        {
            "NCLOUD_ACCESS_KEY": "access",
            "NCLOUD_SECRET_KEY": "secret",
            "ADP_CODE_GIT_SHA": "abcdef1",
            "ADP_NCP_STORAGE_E2E_CONFIRM": "YES",
        }
    )

    assert result["status"] == "PASS"
    assert result["run_type"] == "NCP_STORAGE_E2E"
    assert result["adapter_git_sha"] == "abcdef1"
    assert result["upload_digest"] == result["download_digest"]
    assert result["match"] is True
    assert result["download_matches_upload"] is True
    assert result["cleanup_completed"] is True
    assert client.objects == {}
    assert len(client.deleted) == 2


def test_publish_failure_cleans_only_new_orphan_objects() -> None:
    client = FakeS3()
    client.fail_manifest_put = True
    store = NcpObjectStorageStore(client, bucket="adp-qa-data-artifacts")

    with pytest.raises(ArtifactStorageError, match="upload failed"):
        publish_artifact(
            store,
            b"artifact",
            prefix="artifacts/validation",
            artifact_id="VAL-ORPHAN-TEST",
            artifact_version="v1",
            filename="result.json",
            code_git_sha="abcdef1",
            classification="SYNTHETIC",
        )

    assert client.objects == {}
    assert client.deleted == [
        ("adp-qa-data-artifacts", "artifacts/validation/VAL-ORPHAN-TEST/v1/result.json")
    ]


def test_artifact_cli_publishes_and_downloads_persistent_reference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = FakeS3()
    store = NcpObjectStorageStore(client, bucket="adp-qa-data-artifacts")
    monkeypatch.setattr(
        artifact_storage_cli.NcpObjectStorageStore,
        "from_env",
        lambda environment: store,
    )
    source = tmp_path / "validated.json"
    source.write_bytes(b'{"status":"PASS"}')
    reference = tmp_path / "reference.json"
    environment = {"ADP_NCP_ARTIFACT_PUBLISH_CONFIRM": "YES"}

    published = artifact_storage_cli.publish(
        Namespace(
            source=source,
            prefix="handoff/validated",
            artifact_id="VAL-TEST",
            artifact_version="v1",
            filename=None,
            code_git_sha="abcdef1",
            classification="SYNTHETIC",
            source_id=["source-1"],
            content_type="application/json",
            reference_output=reference,
        ),
        environment,
    )
    output = tmp_path / "downloaded.json"
    downloaded = artifact_storage_cli.download(
        Namespace(reference=reference, output=output), environment
    )

    assert published["artifact_id"] == "VAL-TEST"
    assert downloaded["status"] == "PASS"
    assert output.read_bytes() == source.read_bytes()


def test_artifact_cli_requires_explicit_publish_confirmation(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="PUBLISH_CONFIRM"):
        artifact_storage_cli.publish(
            Namespace(source=tmp_path / "unused"),
            {},
        )
