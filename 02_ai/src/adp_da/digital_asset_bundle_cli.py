"""Build and publish the BE P0-5 Digital Asset Bundle Manifest to NCP."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from adp_da.digital_asset_bundle import build_digital_asset_bundle, publish_digital_asset_bundle
from adp_da.storage import NcpObjectStorageStore

CONFIRM_ENV = "ADP_NCP_DIGITAL_ASSET_BUNDLE_PUBLISH_CONFIRM"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--schema-dir", type=Path, required=True)
    parser.add_argument("--artifact-id", required=True)
    parser.add_argument("--artifact-version", required=True)
    parser.add_argument("--institution-id", required=True)
    parser.add_argument("--destination-profile-id", required=True)
    parser.add_argument("--reference-output", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get(CONFIRM_ENV) != "YES":
        raise RuntimeError(f"NCP Digital Asset Bundle publish requires {CONFIRM_ENV}=YES")
    bundle = build_digital_asset_bundle(
        source_dir=args.source_dir,
        schema_dir=args.schema_dir,
        artifact_id=args.artifact_id,
        artifact_version=args.artifact_version,
        institution_id=args.institution_id,
        destination_profile_id=args.destination_profile_id,
    )
    published = publish_digital_asset_bundle(NcpObjectStorageStore.from_env(), bundle)
    reference = {
        "schema_version": "adp-digital-asset-artifact-ingest-request/v1",
        **published.ingest_request(),
        "storageManifestDigest": published.storage_manifest_digest,
    }
    args.reference_output.parent.mkdir(parents=True, exist_ok=True)
    args.reference_output.write_text(
        json.dumps(reference, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(reference, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
