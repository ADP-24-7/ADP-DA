"""Filesystem implementation of the artifact storage port."""

from __future__ import annotations

from pathlib import Path

from adp_da.storage.core import (
    MAX_ARTIFACT_BYTES,
    ArtifactIntegrityError,
    ArtifactNotFoundError,
    validate_object_key,
    verify_bytes,
)


class LocalArtifactStore:
    def __init__(self, root: Path, *, bucket: str = "local-artifacts") -> None:
        self.root = root.resolve()
        self.bucket = bucket

    def _path(self, object_key: str) -> Path:
        key = validate_object_key(object_key)
        target = (self.root / key).resolve()
        if not target.is_relative_to(self.root):
            raise ValueError("object key escapes local artifact root")
        return target

    def put(self, object_key: str, data: bytes, *, digest: str, content_type: str) -> bool:
        del content_type
        verify_bytes(data, digest, MAX_ARTIFACT_BYTES)
        target = self._path(object_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if target.read_bytes() != data:
                raise ArtifactIntegrityError("immutable artifact key already contains other bytes")
            return False
        target.write_bytes(data)
        return True

    def get(
        self, object_key: str, *, expected_digest: str, max_bytes: int = MAX_ARTIFACT_BYTES
    ) -> bytes:
        target = self._path(object_key)
        if not target.is_file():
            raise ArtifactNotFoundError(f"artifact not found: {object_key}")
        with target.open("rb") as file:
            data = file.read(max_bytes + 1)
        verify_bytes(data, expected_digest, max_bytes)
        return data

    def delete(self, object_key: str) -> None:
        target = self._path(object_key)
        if target.exists():
            target.unlink()
