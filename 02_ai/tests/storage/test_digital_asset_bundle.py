from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from adp_da.digital_asset_bundle import (
    BuiltDigitalAssetBundle,
    build_digital_asset_bundle,
    canonical_digest,
    publish_digital_asset_bundle,
    verify_published_digital_asset_bundle,
)
from adp_da.storage import ArtifactIntegrityError, LocalArtifactStore

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "03_digital_asset" / "artifacts" / "be_loader_v1"
SCHEMAS = ROOT / "03_digital_asset" / "contracts" / "be_loader_v1"
SCHEMA_RAW_DIGESTS = {
    "digital-asset-artifact-bundle-v1.schema.json": (
        "89d5e9efcf4d3e7961473c56be889848762632a5ecd3bbfdee8d023cd6c4aac8"
    ),
    "binding-v1.schema.json": ("95b302b6c32237592b206b3f2705b0fba5c12f3fa3e8dc809f2d4504ee176365"),
    "outbound-requirement-matrix-v1.schema.json": (
        "81b433829161fdfd5359726025a4cbd5a53f681aa9e2676280cbec468a5425a5"
    ),
    "policy-evaluation-v1.schema.json": (
        "e47ffa9e6c486f4343c0d4f26b4a82c7d42520199cf1a07bd64e45eff0d1b002"
    ),
    "runtime-data-crosswalk-v1.schema.json": (
        "27ee9cf189d9fc721aa7d5f5f80091d46f620b59860fea0285f54d9abefd980a"
    ),
    "runtime-pipeline-v1.schema.json": (
        "9d7ab3bf9660cfad60f380b2250fa5c8770558b136d2736ef28d357db6e8fae4"
    ),
}


def build_bundle() -> BuiltDigitalAssetBundle:
    return build_digital_asset_bundle(
        source_dir=SOURCE,
        schema_dir=SCHEMAS,
        artifact_id="DA-DIGITAL-ASSET-RUNTIME-CANDIDATE-001",
        artifact_version="1.0.0",
        institution_id="institution_local",
        destination_profile_id="dest_mock_asset_platform_v1",
    )


def test_be_p0_5_schemas_are_exactly_frozen() -> None:
    for filename, expected in SCHEMA_RAW_DIGESTS.items():
        assert hashlib.sha256((SCHEMAS / filename).read_bytes()).hexdigest() == expected


def test_builds_exact_be_p0_5_manifest_contract() -> None:
    bundle = build_bundle()
    manifest = bundle.manifest
    without_digest = {key: value for key, value in manifest.items() if key != "content_digest"}

    assert manifest["schema_version"] == "adp-digital-asset-artifact-bundle/v1"
    assert manifest["content_digest"] == canonical_digest(without_digest)
    assert {entry["role"] for entry in manifest["files"]} == {
        "OUTBOUND_REQUIREMENT_MATRIX",
        "POLICY_EVALUATION",
        "BINDING",
        "RUNTIME_DATA_CROSSWALK",
        "RUNTIME_PIPELINE",
    }
    assert all(entry["reference"].startswith("handoff/validated/") for entry in manifest["files"])
    expected_schema_digests = {
        entry["role"]: entry["schema_digest"]
        for entry in json.loads((SOURCE / "manifest.json").read_text())["files"]
    }
    assert {
        entry["role"]: entry["schema_digest"] for entry in manifest["files"]
    } == expected_schema_digests


def test_local_and_ncp_port_semantics_support_idempotent_bundle_publish(tmp_path: Path) -> None:
    bundle = build_bundle()
    store = LocalArtifactStore(tmp_path, bucket="adp-qa-data-artifacts")

    first = publish_digital_asset_bundle(store, bundle)
    replay = publish_digital_asset_bundle(store, bundle)

    assert len(first.created_object_keys) == 6
    assert replay.created_object_keys == ()
    assert first.ingest_request() == {
        "manifestReference": (
            "handoff/validated/DA-DIGITAL-ASSET-RUNTIME-CANDIDATE-001/1.0.0/manifest.json"
        ),
        "expectedContentDigest": bundle.manifest["content_digest"],
    }
    verified = verify_published_digital_asset_bundle(
        store,
        manifest_reference=first.manifest_reference,
        expected_content_digest=first.expected_content_digest,
        storage_manifest_digest=first.storage_manifest_digest,
        schema_dir=SCHEMAS,
    )
    assert verified["status"] == "PASS"
    assert verified["run_type"] == "NCP_DIGITAL_ASSET_BUNDLE_VERIFY"
    assert verified["bucket"] == "adp-qa-data-artifacts"
    assert verified["credentialValuesRecorded"] is False
    assert set(verified["verifiedRoles"]) == set(
        entry["role"] for entry in bundle.manifest["files"]
    )


def test_bundle_publish_rejects_same_identity_with_different_bytes(tmp_path: Path) -> None:
    first = build_bundle()
    store = LocalArtifactStore(tmp_path, bucket="adp-qa-data-artifacts")
    publish_digital_asset_bundle(store, first)
    changed = build_bundle()
    first_reference = next(iter(changed.files))
    changed.files[first_reference] = b'{"changed":true}'

    with pytest.raises(ArtifactIntegrityError, match="immutable"):
        publish_digital_asset_bundle(store, changed)
