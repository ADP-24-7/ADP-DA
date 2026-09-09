from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from adp_da.reference_evidence import (
    ReferenceEvidenceError,
    build_reference_evidence_bundle,
    validate_reference_evidence_bundle,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "02_ai/reference_evidence/reference_evidence_source_v1.json"
SCHEMA = ROOT / "02_ai/contracts/reference-evidence-bundle-v1.schema.json"


def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def built() -> tuple[dict[str, object], dict[str, object]]:
    schema = load(SCHEMA)
    return build_reference_evidence_bundle(load(SOURCE), schema), schema


def test_builds_deterministic_reference_only_bundle() -> None:
    first, schema = built()
    second = build_reference_evidence_bundle(load(SOURCE), schema)

    assert first == second
    assert first["evidence_count"] == 4
    assert str(first["content_digest"]).startswith("sha256:")
    assert {item["status"] for item in first["evidence"]} == {"REFERENCE_ONLY"}
    assert all(not item["policy_artifact_refs"] for item in first["evidence"])


def test_rejects_tampered_evidence_with_stale_digest() -> None:
    bundle, schema = built()
    tampered = deepcopy(bundle)
    tampered["evidence"][0]["claim_summary"] = "tampered"

    with pytest.raises(ReferenceEvidenceError, match="evidence content_digest mismatch"):
        validate_reference_evidence_bundle(tampered, schema)


def test_rejects_tampered_bundle_manifest() -> None:
    bundle, schema = built()
    tampered = deepcopy(bundle)
    tampered["analysis_version"] = "unknown"

    with pytest.raises(ReferenceEvidenceError, match="bundle content_digest mismatch"):
        validate_reference_evidence_bundle(tampered, schema)


def test_rejects_reference_only_runtime_policy_binding() -> None:
    source = load(SOURCE)
    source["evidence"][0]["policy_artifact_refs"] = ["runtime-policy-1"]

    with pytest.raises(ReferenceEvidenceError, match="cannot bind a Runtime policy"):
        build_reference_evidence_bundle(source, load(SCHEMA))


def test_rejects_unknown_contract_field() -> None:
    source = load(SOURCE)
    source["evidence"][0]["runtime_action"] = "ALLOW"

    with pytest.raises(ReferenceEvidenceError, match="schema mismatch"):
        build_reference_evidence_bundle(source, load(SCHEMA))
