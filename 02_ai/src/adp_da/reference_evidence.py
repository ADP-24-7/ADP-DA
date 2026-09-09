"""Build and validate the DA Reference Evidence Bundle consumed by ADP-BE."""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_VERSION = "adp-reference-evidence-bundle/v1"
DIGEST_PREFIX = "sha256:"


class ReferenceEvidenceError(ValueError):
    """Raised when a Reference Evidence handoff violates the frozen contract."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def canonical_digest(value: Any) -> str:
    return DIGEST_PREFIX + hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReferenceEvidenceError(f"invalid JSON: {path}") from error
    if not isinstance(value, dict):
        raise ReferenceEvidenceError(f"JSON root must be an object: {path}")
    return value


def _schema_errors(schema: dict[str, Any], value: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        error.message
        for error in sorted(validator.iter_errors(value), key=lambda item: list(item.path))
    ]


def build_reference_evidence_bundle(
    source: dict[str, Any], schema: dict[str, Any]
) -> dict[str, Any]:
    expected_keys = {
        "bundle_id",
        "bundle_version",
        "snapshot_at",
        "analysis_version",
        "evidence",
    }
    if set(source) != expected_keys or not isinstance(source.get("evidence"), list):
        raise ReferenceEvidenceError("reference evidence source shape is invalid")

    evidence: list[dict[str, Any]] = []
    for item in source["evidence"]:
        if not isinstance(item, dict) or "content_digest" in item:
            raise ReferenceEvidenceError("source evidence must be an object without content_digest")
        evidence.append({**deepcopy(item), "content_digest": canonical_digest(item)})

    without_digest = {
        "schema_version": SCHEMA_VERSION,
        "bundle_id": source["bundle_id"],
        "bundle_version": source["bundle_version"],
        "snapshot_at": source["snapshot_at"],
        "analysis_version": source["analysis_version"],
        "evidence_count": len(evidence),
        "evidence": evidence,
    }
    bundle = {**without_digest, "content_digest": canonical_digest(without_digest)}
    validate_reference_evidence_bundle(bundle, schema)
    return bundle


def validate_reference_evidence_bundle(
    bundle: dict[str, Any], schema: dict[str, Any]
) -> None:
    errors = _schema_errors(schema, bundle)
    if errors:
        raise ReferenceEvidenceError(f"reference evidence schema mismatch: {errors[0]}")

    evidence = bundle["evidence"]
    identities = [(item["evidence_id"], item["evidence_version"]) for item in evidence]
    if len(identities) != len(set(identities)):
        raise ReferenceEvidenceError("duplicate evidence identity")
    if bundle["evidence_count"] != len(evidence):
        raise ReferenceEvidenceError("evidence_count does not match evidence")

    for item in evidence:
        received = item["content_digest"]
        content = {key: value for key, value in item.items() if key != "content_digest"}
        if received != canonical_digest(content):
            raise ReferenceEvidenceError("evidence content_digest mismatch")
        if item["status"] == "REFERENCE_ONLY" and item["policy_artifact_refs"]:
            raise ReferenceEvidenceError("REFERENCE_ONLY evidence cannot bind a Runtime policy")
        if item["effective_from"] and item["effective_to"]:
            if item["effective_from"] > item["effective_to"]:
                raise ReferenceEvidenceError("invalid evidence effective period")

    received_bundle_digest = bundle["content_digest"]
    content = {key: value for key, value in bundle.items() if key != "content_digest"}
    if received_bundle_digest != canonical_digest(content):
        raise ReferenceEvidenceError("bundle content_digest mismatch")


def build_file(source_path: Path, schema_path: Path, output_path: Path) -> None:
    bundle = build_reference_evidence_bundle(
        _read_object(source_path), _read_object(schema_path)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_file(args.source, args.schema, args.output)


if __name__ == "__main__":
    main()
