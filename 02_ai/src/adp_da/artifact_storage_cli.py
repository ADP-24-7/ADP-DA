"""Publish or download a digest-bound artifact through NCP Object Storage."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from adp_da.storage.core import MAX_ARTIFACT_BYTES, ArtifactIntegrityError
from adp_da.storage.ncp import NcpObjectStorageStore
from adp_da.storage.publisher import load_published_artifact, publish_artifact

PUBLISH_CONFIRM_ENV = "ADP_NCP_ARTIFACT_PUBLISH_CONFIRM"
CLASSIFICATIONS = ("SYNTHETIC", "PSEUDONYMIZED", "SYNTHETIC_OR_PSEUDONYMIZED")


def _read_bounded(path: Path, max_bytes: int = MAX_ARTIFACT_BYTES) -> bytes:
    with path.open("rb") as file:
        data = file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ArtifactIntegrityError("artifact exceeds byte limit")
    return data


def publish(args: argparse.Namespace, environment: dict[str, str]) -> dict[str, str]:
    if environment.get(PUBLISH_CONFIRM_ENV) != "YES":
        raise RuntimeError(f"NCP artifact publish requires {PUBLISH_CONFIRM_ENV}=YES")
    data = _read_bounded(args.source)
    store = NcpObjectStorageStore.from_env(environment)
    published = publish_artifact(
        store,
        data,
        prefix=args.prefix,
        artifact_id=args.artifact_id,
        artifact_version=args.artifact_version,
        filename=args.filename or args.source.name,
        code_git_sha=args.code_git_sha,
        classification=args.classification,
        source_ids=tuple(args.source_id),
        content_type=args.content_type,
    )
    reference = {"schema_version": "1.0.0", **published.reference()}
    args.reference_output.parent.mkdir(parents=True, exist_ok=True)
    args.reference_output.write_text(
        json.dumps(reference, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return reference


def download(args: argparse.Namespace, environment: dict[str, str]) -> dict[str, Any]:
    reference = json.loads(_read_bounded(args.reference, 1_000_000))
    if not isinstance(reference, dict):
        raise ArtifactIntegrityError("artifact reference must be a JSON object")
    store = NcpObjectStorageStore.from_env(environment)
    manifest, data = load_published_artifact(
        store,
        manifest_object_key=str(reference["manifest_object_key"]),
        manifest_digest=str(reference["manifest_digest"]),
    )
    expected = {
        "bucket": manifest.bucket,
        "artifact_id": manifest.artifact_id,
        "artifact_version": manifest.artifact_version,
        "artifact_digest": manifest.digest,
    }
    if any(reference.get(key) != value for key, value in expected.items()):
        raise ArtifactIntegrityError("artifact reference does not match downloaded manifest")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise FileExistsError(f"output already exists: {args.output}")
    args.output.write_bytes(data)
    return {**expected, "status": "PASS", "output": str(args.output)}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    publish_parser = commands.add_parser("publish")
    publish_parser.add_argument("--source", type=Path, required=True)
    publish_parser.add_argument("--prefix", required=True)
    publish_parser.add_argument("--artifact-id", required=True)
    publish_parser.add_argument("--artifact-version", required=True)
    publish_parser.add_argument("--filename")
    publish_parser.add_argument("--code-git-sha", required=True)
    publish_parser.add_argument("--classification", choices=CLASSIFICATIONS, required=True)
    publish_parser.add_argument("--source-id", action="append", default=[])
    publish_parser.add_argument("--content-type", default="application/octet-stream")
    publish_parser.add_argument("--reference-output", type=Path, required=True)

    download_parser = commands.add_parser("download")
    download_parser.add_argument("--reference", type=Path, required=True)
    download_parser.add_argument("--output", type=Path, required=True)
    return root


def main() -> None:
    args = parser().parse_args()
    environment = dict(os.environ)
    result = (
        publish(args, environment) if args.command == "publish" else download(args, environment)
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
