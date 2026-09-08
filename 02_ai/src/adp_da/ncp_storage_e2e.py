"""Credential-safe, explicit NCP Object Storage upload/download integrity drill."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from adp_da.storage.ncp import DEFAULT_BUCKET, DEFAULT_ENDPOINT, NcpObjectStorageStore
from adp_da.storage.publisher import (
    delete_published_artifact,
    load_published_artifact,
    publish_artifact,
)

CONFIRM_ENV = "ADP_NCP_STORAGE_E2E_CONFIRM"
CODE_SHA_ENV = "ADP_CODE_GIT_SHA"


def preflight(environment: dict[str, str]) -> dict[str, Any]:
    return {
        "endpoint": environment.get("ADP_NCP_OBJECT_STORAGE_ENDPOINT", DEFAULT_ENDPOINT),
        "bucket": environment.get("ADP_NCP_ARTIFACT_BUCKET", DEFAULT_BUCKET),
        "region": environment.get("NCLOUD_REGION", "KR"),
        "access_key_present": bool(environment.get("NCLOUD_ACCESS_KEY")),
        "secret_key_present": bool(environment.get("NCLOUD_SECRET_KEY")),
        "code_git_sha_present": bool(environment.get(CODE_SHA_ENV)),
        "external_write_confirmed": environment.get(CONFIRM_ENV) == "YES",
        "credential_values_recorded": False,
    }


def execute(environment: dict[str, str]) -> dict[str, Any]:
    report = preflight(environment)
    if not all(
        (
            report["access_key_present"],
            report["secret_key_present"],
            report["code_git_sha_present"],
            report["external_write_confirmed"],
        )
    ):
        raise RuntimeError("NCP storage E2E requires credentials, code SHA and explicit YES")
    store = NcpObjectStorageStore.from_env(environment)
    session = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    data = json.dumps(
        {"kind": "adp-da-ncp-storage-e2e", "session": session},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    published = publish_artifact(
        store,
        data,
        prefix="replay",
        artifact_id="ncp-storage-e2e",
        artifact_version=session,
        filename="probe.json",
        code_git_sha=environment[CODE_SHA_ENV],
        classification="SYNTHETIC",
        content_type="application/json",
    )
    result: dict[str, Any]
    try:
        manifest, downloaded = load_published_artifact(
            store,
            manifest_object_key=published.manifest_object_key,
            manifest_digest=published.manifest_digest,
        )
        result = {
            **report,
            "run_type": "NCP_STORAGE_E2E",
            "adapter_git_sha": environment[CODE_SHA_ENV],
            "status": "PASS",
            "artifact_id": manifest.artifact_id,
            "artifact_version": manifest.artifact_version,
            "object_key": manifest.object_key,
            "manifest_object_key": published.manifest_object_key,
            "digest": manifest.digest,
            "upload_digest": manifest.digest,
            "download_digest": manifest.digest,
            "match": downloaded == data,
            "download_matches_upload": downloaded == data,
        }
    finally:
        delete_published_artifact(store, published)
    result["cleanup_completed"] = True
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--evidence-output", type=Path)
    args = parser.parse_args()
    environment = dict(os.environ)
    result = execute(environment) if args.execute else preflight(environment)
    if args.evidence_output:
        if not args.execute:
            raise RuntimeError("evidence output is only available with --execute")
        args.evidence_output.parent.mkdir(parents=True, exist_ok=True)
        args.evidence_output.write_text(
            json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
