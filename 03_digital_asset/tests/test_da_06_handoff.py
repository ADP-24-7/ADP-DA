from __future__ import annotations

import copy
import importlib
import json
import re
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "03_digital_asset/src"))
da06 = importlib.import_module("build_da_06_handoff")


@pytest.fixture(scope="module")
def artifacts():
    return da06.build(check=True)


def test_original_sources_and_saved_outputs_preserved(artifacts):
    assert len(artifacts) == 5
    for path, digest in da06.ORIGINAL_HASHES.items():
        assert da06.sha256(ROOT / path) == digest


def test_observed_and_counterfactual_are_separate(artifacts):
    observed = artifacts["analysis_summary"]
    simulated = artifacts["validation_metrics"]
    assert observed["evidence_kind"] == "OBSERVED_EVIDENCE"
    assert simulated["evidence_kind"] == "COUNTERFACTUAL_EXPERIMENT"
    assert observed["metrics"]["receipt_success"] + observed["metrics"]["receipt_failed"] == 73410
    assert simulated["scenario"] == "SENT_UNKNOWN_WITH_REFERENCE"
    assert simulated["paired_comparison"]["recomputed"] is False
    assert all(value["live_be_evaluation"] is False for value in artifacts.values())


@pytest.mark.parametrize(
    "mutation",
    [
        "immediate_retry",
        "finalized_resend",
        "no_audit",
        "no_terminal_evidence",
        "no_policy",
        "no_finality",
        "no_field_match",
        "missing_invariant",
        "missing_prohibition",
    ],
)
def test_weakened_runtime_contract_rejected(artifacts, mutation):
    value = copy.deepcopy(artifacts["runtime_requirements"])
    if mutation == "immediate_retry":
        value["transitions"][1]["to"] = "RETRY"
    elif mutation == "finalized_resend":
        value["transitions"].append({"from": "FINALIZED", "to": "SUBMITTED", "requires": []})
    elif mutation == "no_audit":
        value["transitions"][0]["requires"].remove("audit_trace")
    elif mutation == "no_terminal_evidence":
        value["transitions"][5]["requires"].remove("terminal_failure_confirmed")
    elif mutation == "no_policy":
        value["transitions"][5]["requires"].remove("retry_policy_allows")
    elif mutation == "no_finality":
        value["transitions"][2]["requires"].remove("finality_confirmed")
    elif mutation == "no_field_match":
        value["transitions"][2]["requires"].remove("field_match")
    elif mutation == "missing_invariant":
        value["invariants"].pop()
    else:
        value["prohibited"].clear()
    with pytest.raises(ValueError):
        da06.validate_contract(value)


@pytest.mark.parametrize(
    "name",
    [
        "analysis_summary",
        "validation_metrics",
        "runtime_requirements",
        "runtime_architecture",
        "contract_gaps",
    ],
)
def test_schema_rejects_false_live_claim(artifacts, name):
    schema = json.loads((ROOT / da06.SCHEMA).read_text(encoding="utf-8"))
    value = copy.deepcopy(artifacts[name])
    value["live_be_evaluation"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(value, schema)


def test_existing_field_names_and_gaps(artifacts):
    fields = {r["semantic"]: r for r in artifacts["runtime_architecture"]["fields"]}
    assert len(fields) == 10
    assert fields["last_checked_at"]["existing"].endswith("last_status_queried_at")
    assert fields["retry_count"]["existing"] is None
    assert fields["parent_request_id"]["existing"] is None
    assert "receipt_status" not in fields["execution_status"]["existing"]


def test_provenance_and_local_document_links(artifacts):
    for artifact in artifacts.values():
        for ref in artifact["evidence_refs"]:
            path = (ROOT / ref["path"]).resolve()
            assert path.is_relative_to(ROOT.resolve())
            assert da06.sha256(path) == ref["sha256"]
    doc = ROOT / "03_digital_asset/docs/DA_06_RECOVERY_IDEMPOTENCY_BE_HANDOFF.md"
    for link in re.findall(r"\]\(([^)]+)\)", doc.read_text(encoding="utf-8")):
        assert (doc.parent / link).is_file(), link


def test_artifact_drift_fails_check(tmp_path):
    # Redirect only generated artifacts; sources retain their real immutable location.
    class RootView:
        def __truediv__(self, path):
            return tmp_path / path if str(path).startswith(str(da06.ART)) else ROOT / path

    view = RootView()
    da06.build(root=view)
    path = tmp_path / da06.ART / "analysis_summary.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["metrics"]["receipt_success"] = 0
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="Artifact drift"):
        da06.build(root=view, check=True)
