from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from adp_da import ai_handoff_vnext as handoff

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def contract() -> dict[str, Any]:
    return handoff.build_runtime_contract()


def field_for(contract: dict[str, Any], field: str) -> dict[str, Any]:
    return next(row for row in contract["fields"] if row["field"] == field)


@pytest.mark.parametrize(
    ("field", "phase", "source_type"),
    [
        ("caller", "PRE_EXECUTION", "CALLER_CONTEXT"),
        ("role", "PRE_EXECUTION", "ROLE_BINDING"),
        ("model_or_tool_request_payload", "PRE_EXECUTION", "REQUESTED_FIELD"),
        ("request_id", "TRACE", "RUNTIME_TRACE_IDENTIFIER"),
        ("internal_policy_evidence", "TRACE", "POLICY_EVALUATION_REFERENCE"),
        ("model_output", "POST_EXECUTION", "AI_RESPONSE"),
        ("response_metadata", "POST_EXECUTION", "AI_RESPONSE_METADATA"),
    ],
)
def test_source_phase_routing(
    contract: dict[str, Any], field: str, phase: str, source_type: str
) -> None:
    row = field_for(contract, field)

    assert row["source_phase"] == phase
    assert row["source_type"] == source_type


@pytest.mark.parametrize(
    "field",
    [
        "caller",
        "role",
        "workload",
        "purpose",
        "requested_field_scope",
        "model_identifier",
        "tool_action_identifier",
        "request_id",
    ],
)
def test_exact_required_transform_whitelist(contract: dict[str, Any], field: str) -> None:
    row = field_for(contract, field)

    assert row["field_requirement"] == "EXACT_REQUIRED"
    assert row["transform_method"] == "PASS_THROUGH"


def test_internal_only_externalization_block(contract: dict[str, Any]) -> None:
    invalid = copy.deepcopy(contract)
    field_for(invalid, "internal_policy_evidence")["destination"].append("MODEL_PROVIDER")

    validation = handoff.validate_runtime_contract(invalid)

    assert validation["status"] == "FAIL"
    assert any(
        error["field"] == "internal_policy_evidence"
        and error["rule"] == "INTERNAL_ONLY_NO_EXTERNAL_DESTINATION"
        for error in validation["validation_errors"]
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"binding_match": False},
        {"field_scope_match": False},
        {"destination_authorized": False},
        {"model_authorized": False},
        {"tool_authorized": False},
        {"policy_evaluation_ref_present": False},
        {"trace_ref_present": False},
    ],
)
def test_policy_mismatch_cases_block(kwargs: dict[str, bool]) -> None:
    baseline = {
        "destination_authorized": True,
        "model_authorized": True,
        "tool_authorized": True,
        "binding_match": True,
        "field_scope_match": True,
        "exact_match": True,
        "forbidden_externalization": False,
        "policy_evaluation_ref_present": True,
        "trace_ref_present": True,
        "transform_resolved": True,
        "thresholds_resolved": True,
    }
    baseline.update(kwargs)

    decision = handoff.evaluate_runtime_decision(**baseline)

    assert decision["decision"] == "BLOCK"


def test_allowed_field_scope_pass() -> None:
    decision = handoff.evaluate_runtime_decision(
        destination_authorized=True,
        model_authorized=True,
        tool_authorized=True,
        binding_match=True,
        field_scope_match=True,
        exact_match=True,
        forbidden_externalization=False,
        policy_evaluation_ref_present=True,
        trace_ref_present=True,
        transform_resolved=True,
        thresholds_resolved=True,
    )

    assert decision["decision"] == "PASS"


@pytest.mark.parametrize("missing", ["transform_resolved", "thresholds_resolved"])
def test_unresolved_transform_or_threshold_review(missing: str) -> None:
    inputs = {
        "destination_authorized": True,
        "model_authorized": True,
        "tool_authorized": True,
        "binding_match": True,
        "field_scope_match": True,
        "exact_match": True,
        "forbidden_externalization": False,
        "policy_evaluation_ref_present": True,
        "trace_ref_present": True,
        "transform_resolved": True,
        "thresholds_resolved": True,
    }
    inputs[missing] = False

    decision = handoff.evaluate_runtime_decision(**inputs)

    assert decision["decision"] == "REVIEW"


def test_missing_trace_reference_validation(contract: dict[str, Any]) -> None:
    invalid = copy.deepcopy(contract)
    field_for(invalid, "request_id")["trace_binding"] = "MISSING"

    validation = handoff.validate_runtime_contract(invalid)

    assert validation["status"] == "FAIL"
    assert any(
        error["field"] == "request_id" and error["rule"] == "TRACE_REFERENCE_REQUIRED"
        for error in validation["validation_errors"]
    )


def test_policy_evaluation_reference_validation(contract: dict[str, Any]) -> None:
    invalid = copy.deepcopy(contract)
    field_for(invalid, "internal_policy_evidence")["classification_basis"] = []

    validation = handoff.validate_runtime_contract(invalid)

    assert validation["status"] == "FAIL"
    assert any(
        error["field"] == "internal_policy_evidence"
        and error["rule"] == "VALIDATION_ARTIFACT_REFERENCE_REQUIRED"
        for error in validation["validation_errors"]
    )


def test_artifact_schema_validation(contract: dict[str, Any]) -> None:
    validation = handoff.validate_runtime_contract(contract)

    jsonschema.validate(contract, handoff.runtime_contract_schema())
    jsonschema.validate(validation, handoff.validation_schema())


def test_artifact_generation_reproducibility() -> None:
    first = json.dumps(handoff.build_runtime_contract(), ensure_ascii=False, sort_keys=True)
    second = json.dumps(handoff.build_runtime_contract(), ensure_ascii=False, sort_keys=True)

    assert hashlib.sha256(first.encode("utf-8")).hexdigest() == hashlib.sha256(
        second.encode("utf-8")
    ).hexdigest()


def test_cross_domain_common_runtime_contract_consistency(contract: dict[str, Any]) -> None:
    da_matrix_path = (
        ROOT / "03_digital_asset" / "artifacts" / "outbound_design_vNext"
        / "outbound_requirement_matrix.json"
    )
    da_matrix = json.loads(da_matrix_path.read_text(encoding="utf-8"))

    da_common_fields = {
        "source_phase",
        "field_requirement",
        "transform_intent",
        "destination",
        "decision",
        "trace_binding",
        "validation_errors",
    }
    ai_common_fields = set(contract["common_contract_fields"])

    assert da_common_fields <= ai_common_fields
    assert "source_phase" in da_matrix["requirements"][0]
    assert "destination" in da_matrix["requirements"][0]
