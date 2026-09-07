from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from adp_da import fpg_be_handoff_final as final

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def package_contracts() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    common = final.build_common_runtime_contract()
    ai_contract = final.build_ai_runtime_contract()
    da_contract = final.build_digital_asset_runtime_contract()
    return common, ai_contract, da_contract


def test_common_contract_schema_compatibility(
    package_contracts: tuple[dict[str, Any], dict[str, Any], dict[str, Any]],
) -> None:
    common, ai_contract, da_contract = package_contracts
    consistency = final.validate_common_compatibility(common, ai_contract, da_contract)

    assert consistency["status"] == "PASS"
    assert consistency["validation_errors"] == []


@pytest.mark.parametrize("index", [1, 2])
def test_domain_contract_common_fields(index: int) -> None:
    common, *contracts = (
        final.build_common_runtime_contract(),
        final.build_ai_runtime_contract(),
        final.build_digital_asset_runtime_contract(),
    )

    assert set(common["common_fields"]) <= set(contracts[index - 1]["common_contract_fields"])


def test_pass_block_review_enum_consistency() -> None:
    common = final.build_common_runtime_contract()

    assert common["decision_values"] == ["PASS", "BLOCK", "REVIEW"]


def test_transform_intent_method_compatibility() -> None:
    matrix = final.build_ai_transform_decision_matrix()
    exact_rows = [
        row for row in matrix["decisions"] if row["field_requirement"] == "EXACT_REQUIRED"
    ]
    internal_rows = [
        row for row in matrix["decisions"] if row["field_requirement"] == "INTERNAL_ONLY"
    ]

    assert exact_rows
    assert all(row["transform_method"] == "PASS_THROUGH" for row in exact_rows)
    assert all(row["transform_method"] == "FIELD_DROP" for row in internal_rows)


def test_pass_through_does_not_imply_externalize() -> None:
    common = final.build_common_runtime_contract()

    assert "does not imply" in common["transform_destination_separation"]["PASS_THROUGH"]
    assert "destination policy" in common["transform_destination_separation"]["EXTERNALIZE"]


def test_model_output_format_normalize_is_non_lossy_response_formatting() -> None:
    common = final.build_common_runtime_contract()
    matrix = final.build_ai_transform_decision_matrix()
    row = next(item for item in matrix["decisions"] if item["field"] == "model_output")

    assert "non-lossy" in common["post_execution_format_normalize"]["model_output"]
    assert "must not rewrite" in row["rationale"]
    assert row["transform_method"] == "FORMAT_NORMALIZE"


def test_unresolved_ai_payload_transform_is_analyst_decision() -> None:
    matrix = final.build_ai_transform_decision_matrix()
    row = next(
        item for item in matrix["decisions"] if item["field"] == "model_or_tool_request_payload"
    )

    assert row["decision_status"] == "ANALYST_DECISION_REQUIRED"
    assert row["transform_parameter"] == "MASK_PARAMETER=ANALYST_DECISION_REQUIRED"


def test_contract_gap_owner_is_be() -> None:
    gap = final.build_contract_gap()

    assert gap["items"]
    assert all(item["owner"] == "BE" for item in gap["items"])


def test_deferred_thresholds_are_non_blocking() -> None:
    deferred = final.build_deferred_runtime_validation()

    assert all(item["status"] == "DEFERRED_RUNTIME_VALIDATION" for item in deferred["items"])
    assert "do not block" in deferred["blocker_assessment"]


def test_common_compatibility_failure_is_machine_readable(
    package_contracts: tuple[dict[str, Any], dict[str, Any], dict[str, Any]],
) -> None:
    common, ai_contract, da_contract = package_contracts
    broken_ai = copy.deepcopy(ai_contract)
    broken_ai["common_contract_fields"] = ["source_phase"]

    consistency = final.validate_common_compatibility(common, broken_ai, da_contract)

    assert consistency["status"] == "FAIL"
    assert {"field", "destination", "rule", "detail"} <= set(
        consistency["validation_errors"][0]
    )


def test_final_package_references_existing_vnext_artifacts() -> None:
    ai_contract = final.build_ai_runtime_contract()
    da_contract = final.build_digital_asset_runtime_contract()

    assert (ROOT / ai_contract["source_artifact_ref"]).exists()
    assert (ROOT / da_contract["source_artifact_ref"]).exists()


def test_final_package_generation_reproducibility() -> None:
    first = json.dumps(final.build_ai_transform_decision_matrix(), sort_keys=True)
    second = json.dumps(final.build_ai_transform_decision_matrix(), sort_keys=True)

    assert first == second
