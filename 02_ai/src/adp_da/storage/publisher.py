"""Publish and load content-addressed artifacts through an ArtifactStore."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from adp_da.storage.core import (
    ArtifactIntegrityError,
    ArtifactManifest,
    ArtifactStore,
    build_object_key,
    sha256_digest,
    validate_manifest,
)

MANIFEST_MAX_BYTES = 1_000_000


@dataclass(frozen=True)
class PublishedArtifact:
    manifest: ArtifactManifest
    manifest_object_key: str
    manifest_digest: str

    def reference(self) -> dict[str, str]:
        return {
            "bucket": self.manifest.bucket,
            "manifest_object_key": self.manifest_object_key,
            "manifest_digest": self.manifest_digest,
            "artifact_id": self.manifest.artifact_id,
            "artifact_version": self.manifest.artifact_version,
            "artifact_digest": self.manifest.digest,
        }


def publish_artifact(
    store: ArtifactStore,
    data: bytes,
    *,
    prefix: str,
    artifact_id: str,
    artifact_version: str,
    filename: str,
    code_git_sha: str,
    classification: str,
    source_ids: tuple[str, ...] = (),
    content_type: str = "application/octet-stream",
) -> PublishedArtifact:
    object_key = build_object_key(prefix, artifact_id, artifact_version, filename)
    digest = sha256_digest(data)
    manifest = ArtifactManifest(
        schema_version="1.0.0",
        artifact_id=artifact_id,
        artifact_version=artifact_version,
        bucket=store.bucket,
        object_key=object_key,
        digest=digest,
        size_bytes=len(data),
        code_git_sha=code_git_sha,
        classification=classification,
        source_ids=source_ids,
        content_type=content_type,
    )
    manifest_bytes = manifest.canonical_bytes()
    manifest_key = build_object_key(
        "manifests/artifacts", artifact_id, artifact_version, "manifest.json"
    )
    manifest_digest = sha256_digest(manifest_bytes)
    store.put(object_key, data, digest=digest, content_type=content_type)
    store.get(object_key, expected_digest=digest)
    store.put(
        manifest_key,
        manifest_bytes,
        digest=manifest_digest,
        content_type="application/json",
    )
    store.get(
        manifest_key,
        expected_digest=manifest_digest,
        max_bytes=MANIFEST_MAX_BYTES,
    )
    return PublishedArtifact(manifest, manifest_key, manifest_digest)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ArtifactIntegrityError("duplicate JSON key in artifact manifest")
        result[key] = value
    return result


def load_published_artifact(
    store: ArtifactStore, *, manifest_object_key: str, manifest_digest: str
) -> tuple[ArtifactManifest, bytes]:
    manifest_bytes = store.get(
        manifest_object_key,
        expected_digest=manifest_digest,
        max_bytes=MANIFEST_MAX_BYTES,
    )
    try:
        payload = json.loads(manifest_bytes, object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ArtifactIntegrityError("artifact manifest is not valid UTF-8 JSON") from error
    if not isinstance(payload, dict):
        raise ArtifactIntegrityError("artifact manifest must be a JSON object")
    validate_manifest(payload)
    if payload["bucket"] != store.bucket:
        raise ArtifactIntegrityError("artifact manifest bucket does not match configured store")
    manifest = ArtifactManifest(
        schema_version=str(payload["schema_version"]),
        artifact_id=str(payload["artifact_id"]),
        artifact_version=str(payload["artifact_version"]),
        bucket=str(payload["bucket"]),
        object_key=str(payload["object_key"]),
        digest=str(payload["digest"]),
        size_bytes=int(payload["size_bytes"]),
        code_git_sha=str(payload["code_git_sha"]),
        classification=str(payload["classification"]),
        source_ids=tuple(str(value) for value in payload.get("source_ids", [])),
        content_type=str(payload.get("content_type", "application/octet-stream")),
    )
    data = store.get(manifest.object_key, expected_digest=manifest.digest)
    if len(data) != manifest.size_bytes:
        raise ArtifactIntegrityError("artifact size does not match manifest")
    return manifest, data


def delete_published_artifact(store: ArtifactStore, published: PublishedArtifact) -> None:
    store.delete(published.manifest_object_key)
    store.delete(published.manifest.object_key)
