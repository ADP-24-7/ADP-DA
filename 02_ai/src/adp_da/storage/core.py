"""Storage-neutral artifact identity, integrity and object-key contract."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Protocol

from jsonschema import Draft202012Validator

MAX_ARTIFACT_BYTES = 50_000_000
ALLOWED_PREFIXES = frozenset(
    {
        "datasets/raw",
        "datasets/curated",
        "datasets/published",
        "artifacts/evaluation",
        "artifacts/validation",
        "artifacts/policy",
        "handoff/validated",
        "replay",
        "manifests/datasets",
        "manifests/artifacts",
    }
)
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
SCHEMA_PATH = Path(__file__).parents[3] / "contracts" / "artifact_storage_manifest.schema.json"


class ArtifactStorageError(RuntimeError):
    """Base error for fail-closed artifact storage operations."""


class ArtifactNotFoundError(ArtifactStorageError):
    """The requested object does not exist."""


class ArtifactIntegrityError(ArtifactStorageError):
    """Stored bytes do not match the expected digest or size contract."""


class ArtifactStore(Protocol):
    """Port shared by local and NCP artifact storage."""

    bucket: str

    def put(self, object_key: str, data: bytes, *, digest: str, content_type: str) -> bool:
        """Store immutable bytes and return True only when a new object was created."""
        ...

    def get(
        self, object_key: str, *, expected_digest: str, max_bytes: int = MAX_ARTIFACT_BYTES
    ) -> bytes: ...

    def delete(self, object_key: str) -> None: ...


@dataclass(frozen=True)
class ArtifactManifest:
    schema_version: str
    artifact_id: str
    artifact_version: str
    bucket: str
    object_key: str
    digest: str
    size_bytes: int
    code_git_sha: str
    classification: str
    source_ids: tuple[str, ...] = ()
    content_type: str = "application/octet-stream"

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_ids"] = list(self.source_ids)
        return payload

    def canonical_bytes(self) -> bytes:
        validate_manifest(self.as_dict())
        return json.dumps(
            self.as_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")


def sha256_digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def validate_digest(value: str) -> None:
    if not DIGEST.fullmatch(value):
        raise ArtifactIntegrityError("digest must use canonical sha256:<lowercase-hex> format")


def _validate_identifier(name: str, value: str) -> None:
    if not IDENTIFIER.fullmatch(value):
        raise ValueError(f"{name} contains unsupported characters")


def validate_object_key(object_key: str) -> str:
    if not object_key or len(object_key) > 1024 or "\\" in object_key:
        raise ValueError("invalid object key")
    path = PurePosixPath(object_key)
    if path.is_absolute() or object_key != path.as_posix():
        raise ValueError("object key must be a normalized relative POSIX path")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("object key contains an unsafe path segment")
    if not any(object_key.startswith(prefix + "/") for prefix in ALLOWED_PREFIXES):
        raise ValueError("object key prefix is not allowed")
    return object_key


def build_object_key(prefix: str, artifact_id: str, artifact_version: str, filename: str) -> str:
    if prefix not in ALLOWED_PREFIXES:
        raise ValueError("object key prefix is not allowed")
    _validate_identifier("artifact_id", artifact_id)
    _validate_identifier("artifact_version", artifact_version)
    _validate_identifier("filename", filename)
    return validate_object_key(f"{prefix}/{artifact_id}/{artifact_version}/{filename}")


def validate_manifest(payload: dict[str, Any]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(payload), key=lambda item: list(item.path)
    )
    if errors:
        raise ArtifactIntegrityError(f"invalid artifact storage manifest: {errors[0].message}")
    validate_object_key(str(payload["object_key"]))
    validate_digest(str(payload["digest"]))


def verify_bytes(data: bytes, expected_digest: str, max_bytes: int) -> None:
    validate_digest(expected_digest)
    if len(data) > max_bytes:
        raise ArtifactIntegrityError("artifact exceeds byte limit")
    if sha256_digest(data) != expected_digest:
        raise ArtifactIntegrityError("artifact SHA-256 mismatch")
