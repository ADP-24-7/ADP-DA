"""Verify an NCP Digital Asset Bundle using the exact BE P0-5 contract."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from adp_da.digital_asset_bundle import verify_published_digital_asset_bundle
from adp_da.storage import NcpObjectStorageStore


def _read_reference(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Digital Asset ingest reference must be a JSON object")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--schema-dir", type=Path, required=True)
    parser.add_argument("--evidence-output", type=Path)
    args = parser.parse_args()
    reference = _read_reference(args.reference)
    result = verify_published_digital_asset_bundle(
        NcpObjectStorageStore.from_env(dict(os.environ)),
        manifest_reference=str(reference["manifestReference"]),
        expected_content_digest=str(reference["expectedContentDigest"]),
        storage_manifest_digest=str(reference["storageManifestDigest"]),
        schema_dir=args.schema_dir,
    )
    result["adapterGitSha"] = str(reference["adapterGitSha"])
    if args.evidence_output:
        args.evidence_output.parent.mkdir(parents=True, exist_ok=True)
        args.evidence_output.write_text(
            json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
