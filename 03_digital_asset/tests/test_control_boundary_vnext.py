from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]
BUILDER_PATH = ROOT / "03_digital_asset" / "src" / "build_control_boundary_v2.py"


def load_builder() -> Any:
    spec = importlib.util.spec_from_file_location("build_control_boundary_v2", BUILDER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def builder() -> Any:
    return load_builder()


@pytest.fixture()
def matrix(builder: Any) -> dict[str, Any]:
    return builder.build_matrix_v2()


@pytest.fixture()
def pipeline(builder: Any) -> dict[str, Any]:
    return builder.runtime_pipeline_v2()


def row_for(matrix: dict[str, Any], field: str) -> dict[str, Any]:
    return next(row for row in matrix["requirements"] if row["required_fields"] == [field])


@pytest.mark.parametrize("field", ["tx_hash", "execution_status", "timestamp"])
def test_execution_result_source_routing(matrix: dict[str, Any], field: str) -> None:
    row = row_for(matrix, field)

    assert set(row["field_roles"]) == {"TRACE_FIELD", "EXECUTION_RESULT_FIELD"}
    assert row["source_phase"] == "POST_EXECUTION"
    assert row["source_type"] == "EXTERNAL_EXECUTION_RESPONSE"
    assert row["requested_source"] == "NOT_PRE_EXECUTION_INPUT"
    assert row["pre_execution_required"] is False
    assert row["post_execution_binding"] is True


def test_pre_post_execution_field_separation(matrix: dict[str, Any]) -> None:
    transaction_id = row_for(matrix, "transaction_id")
    execution_result_fields = [
        row_for(matrix, field) for field in ["tx_hash", "execution_status", "timestamp"]
    ]

    assert transaction_id["source_type"] == "APPROVED_TRANSACTION_TRACE_INPUT"
    assert transaction_id["pre_execution_required"] is True
    assert all(
        row["source_type"] == "EXTERNAL_EXECUTION_RESPONSE" for row in execution_result_fields
    )
    assert all(not row["pre_execution_required"] for row in execution_result_fields)


@pytest.mark.parametrize(
    "field",
    [
        "amount",
        "asset",
        "originator_address",
        "beneficiary_address",
        "transaction_id",
        "tx_hash",
        "timestamp",
        "execution_status",
    ],
)
def test_exact_required_transform_whitelist(matrix: dict[str, Any], field: str) -> None:
    row = row_for(matrix, field)

    assert row["required_exact"] == "EXACT_REQUIRED"
    assert row["transform"] == ["PASS_THROUGH"]
    assert set(row["outbound_transform_by_destination"].values()) == {"PASS_THROUGH"}
    assert row["comparison_canonicalization"] == "NONE_CONTRACTED"


def test_internal_only_externalization_blocked(
    builder: Any, matrix: dict[str, Any], pipeline: dict[str, Any]
) -> None:
    invalid = copy.deepcopy(matrix)
    row_for(invalid, "kyc_status")["destination"].append("EXTERNAL_VASP")

    validation = builder.validate_boundary(invalid, pipeline)

    assert validation["status"] == "FAIL"
    assert any(
        failure["field"] == "kyc_status"
        and failure["rule"] == "INTERNAL_ONLY_NO_EXTERNAL_DESTINATION"
        for failure in validation["failures"]
    )


def test_destination_specific_transform_compatibility(
    builder: Any, matrix: dict[str, Any], pipeline: dict[str, Any]
) -> None:
    invalid = copy.deepcopy(matrix)
    row_for(invalid, "originator_identity")["outbound_transform_by_destination"][
        "TRAVEL_RULE_PROVIDER"
    ] = "PASS_THROUGH"

    validation = builder.validate_boundary(invalid, pipeline)

    assert validation["status"] == "FAIL"
    assert any(
        failure["field"] == "originator_identity"
        and failure["destination"] == "TRAVEL_RULE_PROVIDER"
        and failure["rule"] == "DESTINATION_TRANSFORM_CLASS_COMPATIBILITY"
        for failure in validation["failures"]
    )


def test_schema_validation(builder: Any, matrix: dict[str, Any], pipeline: dict[str, Any]) -> None:
    builder.schema_files()
    validation = builder.validate_boundary(matrix, pipeline)

    jsonschema.validate(
        matrix, builder.read_json(builder.CONTRACTS / "outbound_requirement_matrix_v2.schema.json")
    )
    jsonschema.validate(
        pipeline, builder.read_json(builder.CONTRACTS / "runtime_pipeline.schema.json")
    )
    jsonschema.validate(
        validation, builder.read_json(builder.CONTRACTS / "control_boundary_validation.schema.json")
    )


def test_artifact_generation_reproducibility(builder: Any) -> None:
    first = json.dumps(builder.build_matrix_v2(), ensure_ascii=False, sort_keys=True)
    second = json.dumps(builder.build_matrix_v2(), ensure_ascii=False, sort_keys=True)

    assert hashlib.sha256(first.encode("utf-8")).hexdigest() == hashlib.sha256(
        second.encode("utf-8")
    ).hexdigest()


def test_positive_pass_case(builder: Any, matrix: dict[str, Any], pipeline: dict[str, Any]) -> None:
    validation = builder.validate_boundary(matrix, pipeline)
    decision = builder.evaluate_handoff_decision(
        approved_requested_match=True,
        required_fields_resolved=True,
        mapping_resolved=True,
    )

    assert validation["status"] == "PASS"
    assert decision["decision"] == "PASS"


def test_mismatch_block_case(builder: Any) -> None:
    decision = builder.evaluate_handoff_decision(
        approved_requested_match=False,
        required_fields_resolved=True,
        mapping_resolved=True,
    )

    assert decision["decision"] == "BLOCK"
    assert decision["reason"] == "APPROVED_REQUESTED_MISMATCH"


def test_unresolved_mapping_review_case(builder: Any) -> None:
    decision = builder.evaluate_handoff_decision(
        approved_requested_match=True,
        required_fields_resolved=True,
        mapping_resolved=False,
    )

    assert decision["decision"] == "REVIEW"
    assert decision["reason"] == "UNRESOLVED_MAPPING_OR_FIELD"


def test_forbidden_runtime_control_negative_case(
    builder: Any, matrix: dict[str, Any], pipeline: dict[str, Any]
) -> None:
    invalid = copy.deepcopy(matrix)
    row_for(invalid, "kyc_status")["runtime_control"] = "KYC_STATUS_CHECK"

    validation = builder.validate_boundary(invalid, pipeline)
    decision = builder.evaluate_handoff_decision(
        approved_requested_match=True,
        required_fields_resolved=True,
        mapping_resolved=True,
        forbidden_runtime_control="KYC_STATUS_CHECK",
    )

    assert validation["status"] == "FAIL"
    assert decision["decision"] == "REVIEW"
    assert any(failure["rule"] == "FORBIDDEN_RUNTIME_CONTROL" for failure in validation["failures"])
