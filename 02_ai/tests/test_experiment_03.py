import copy
import json
from pathlib import Path

import pytest
from adp_da.experiment_03 import (
    REQUIRED_HANDOFF_FIELDS,
    Experiment03Error,
    build_case_reevaluation,
    build_integrated_validation_profile,
    build_method_matrix,
    build_results,
    build_selective_rerun,
    build_validated_profile,
    canonical_digest,
    load_handoff,
    validate_handoff,
    validate_integrated_validation_profile,
    validate_method_matrix,
    validate_profile,
    validate_results,
    validate_selective_rerun,
)

DATA_DIR = Path(__file__).parents[1] / "data/processed/financial_synthetic"
ARTIFACT_DIR = Path(__file__).parents[1] / "artifacts/experiment_03"


@pytest.fixture(scope="module")
def built_artifacts():
    handoff = load_handoff(ARTIFACT_DIR / "E2_TO_E3_TRANSFORM_REQUIREMENTS.json")
    matrix = build_method_matrix(handoff["contract_digest"])
    results = build_results(DATA_DIR, handoff, matrix)
    return handoff, matrix, results


def test_e2_handoff_is_frozen_complete_and_content_addressed() -> None:
    handoff = load_handoff(ARTIFACT_DIR / "E2_TO_E3_TRANSFORM_REQUIREMENTS.json")
    validation = validate_handoff(handoff)
    assert validation["status"] == "PASS"
    assert validation["field_count"] == 20
    assert validation["requirement_count"] == 60
    assert handoff["provider_call_authorized"] is False
    assert all(REQUIRED_HANDOFF_FIELDS <= row.keys() for row in handoff["requirements"])


def test_silent_e3_requirement_change_fails_digest_validation() -> None:
    handoff = load_handoff(ARTIFACT_DIR / "E2_TO_E3_TRANSFORM_REQUIREMENTS.json")
    changed = copy.deepcopy(handoff)
    changed["requirements"][0]["required_exact"] = False
    with pytest.raises(Experiment03Error, match="contract digest"):
        validate_handoff(changed)


def test_method_matrix_is_frozen_before_results_and_source_bound() -> None:
    handoff = load_handoff(ARTIFACT_DIR / "E2_TO_E3_TRANSFORM_REQUIREMENTS.json")
    matrix = build_method_matrix(handoff["contract_digest"])
    validation = validate_method_matrix(matrix, handoff["contract_digest"])
    assert validation["status"] == "PASS"
    assert validation["row_count"] >= 9
    source_types = {row["source_type"] for row in matrix["sources"]}
    assert source_types >= {
        "OFFICIAL_GUIDANCE",
        "FINANCIAL_OPERATION_REFERENCE",
        "SECURITY_STANDARD",
        "PEER_REVIEWED",
    }
    assert {row["method"] for row in matrix["rows"]} == {
        "KEEP",
        "REMOVE",
        "MASK",
        "HMAC_PSEUDO",
        "VAULT_TOKEN",
        "STANDARD_ENCRYPTION",
        "FPE",
        "OPE_ORE",
        "GENERALIZE",
        "AGGREGATE",
        "NOISE_RANDOMIZATION",
    }


def test_all_e2_case_lenses_keep_provider_baseline_zero() -> None:
    handoff = load_handoff(ARTIFACT_DIR / "E2_TO_E3_TRANSFORM_REQUIREMENTS.json")
    reevaluation = build_case_reevaluation(handoff)
    assert len(reevaluation["cases"]) == 11
    assert set(reevaluation["provider_baseline"].values()) == {0}
    assert all(row["provider"] in {"NOT_SENT", "NOT_CALLED"} for row in reevaluation["cases"])


def test_e3_is_workload_bound_and_fail_closed(built_artifacts) -> None:
    handoff, matrix, results = built_artifacts
    validation = validate_results(results, handoff, matrix)
    assert validation["status"] == "PASS"
    assert results["provider_calls"] == 0
    assert validation["field_count"] == 20
    assert all(
        set(row["operational_metrics"])
        == {
            "transform_latency_ms",
            "payload_size_before",
            "payload_size_after",
            "schema_validity",
            "deterministic_consistency",
            "transform_failure",
            "retrieval_compatibility",
            "outbound_compatibility",
        }
        for row in results["results"]
    )


def test_current_workload_mask_variants_fail_combined_privacy_and_relation_fit(
    built_artifacts,
) -> None:
    handoff, matrix, results = built_artifacts
    masks = [row for row in results["results"] if row["method"].startswith("MASK_")]
    assert masks
    assert all(row["privacy_pass"] is False for row in masks)
    assert all(row["overall_fit"] == "NOT_FIT" for row in masks)
    validate_results(results, handoff, matrix)


def test_hmac_and_token_preserve_scoped_identifier_relations(built_artifacts) -> None:
    handoff, matrix, results = built_artifacts
    rows = [row for row in results["results"] if row["method"] in {"HMAC_PSEUDO", "VAULT_TOKEN"}]
    assert len(rows) == 6
    assert all(row["privacy_pass"] is True for row in rows)
    assert all(row["relation_pass"] is True for row in rows)
    assert all(row["overall_fit"] == "FIT" for row in rows)


def test_required_exact_amount_rejects_generalization(built_artifacts) -> None:
    handoff, matrix, results = built_artifacts
    generalized = [row for row in results["results"] if row["method"] == "GENERALIZE"]
    assert len(generalized) == 2
    assert all(row["exact_pass"] is False for row in generalized)
    assert all(row["utility_pass"] is False for row in generalized)
    assert all(row["overall_fit"] == "NOT_FIT" for row in generalized)


def test_e2_revision_keeps_only_exact_preserving_amount_candidate() -> None:
    handoff = load_handoff(ARTIFACT_DIR / "E2_TO_E3_TRANSFORM_REQUIREMENTS.json")
    rows = [
        row
        for row in handoff["requirements"]
        if row["field_name"] in {"account.balance", "transaction.amount"}
    ]
    assert len(rows) == 6
    assert all(row["candidate_transform_methods"] == ["KEEP"] for row in rows)
    assert all("GENERALIZE" in row["prohibited_transform_methods"] for row in rows)
    assert handoff["revision"]["revision_id"] == "E2-FIELD-REQ-REV-001"
    assert handoff["revision"]["approval_status"] == "APPROVED"
    assert len(handoff["revision"]["field_revisions"]) == 2
    assert all(
        row["approved_requirement"] == "KEEP_ONLY" for row in handoff["revision"]["field_revisions"]
    )
    assert handoff["revision"]["activation_effect"].startswith("NONE")


def test_overall_fit_cannot_override_failed_required_gate(built_artifacts) -> None:
    handoff, matrix, results = built_artifacts
    changed = copy.deepcopy(results)
    row = next(item for item in changed["results"] if item["method"] == "GENERALIZE")
    row["overall_fit"] = "FIT"
    row["evidence_digest"] = canonical_digest(
        {key: value for key, value in row.items() if key != "evidence_digest"}
    )
    changed["bundle_digest"] = canonical_digest(
        {key: value for key, value in changed.items() if key != "bundle_digest"}
    )
    with pytest.raises(Experiment03Error, match="not fail-closed"):
        validate_results(changed, handoff, matrix)


def test_validated_profile_activates_exact_value_runtime_contract(built_artifacts) -> None:
    handoff, _, results = built_artifacts
    profile = build_validated_profile(handoff, results)
    validation = validate_profile(profile, handoff, results)
    assert validation["status"] == "PASS"
    assert validation["profile_count"] == 20
    assert validation["runtime_gap_count"] == 0
    assert validation["contradiction_count"] == 0
    assert profile["status"] == "VALIDATED_ACTIVATED"
    assert profile["profile_version"] == "1.2.0"
    assert profile["activation_status"] == "ACTIVATED"
    assert all(row["activation_status"] == "ACTIVATED" for row in profile["profiles"])
    exact = [
        row
        for row in profile["profiles"]
        if row["field_name"] in {"account.balance", "transaction.amount"}
    ]
    assert all(row["current_runtime_method"] == "KEEP" for row in exact)
    assert all(row["exact_result"] == "PASS" for row in exact)


def test_only_two_revised_exact_fields_are_selectively_rerun(built_artifacts) -> None:
    handoff, _, results = built_artifacts
    rerun = build_selective_rerun(DATA_DIR, handoff, results)
    validation = validate_selective_rerun(rerun, handoff, results)
    assert validation["rerun_field_count"] == 2
    assert validation["contradiction_count"] == 0
    assert all(row["method"] == "KEEP" and row["overall_fit"] == "FIT" for row in rerun["results"])


def test_integrated_profile_keeps_external_execution_pending(built_artifacts) -> None:
    handoff, _, results = built_artifacts
    rerun = build_selective_rerun(DATA_DIR, handoff, results)
    profile = build_validated_profile(handoff, results, rerun)
    integrated = build_integrated_validation_profile(
        handoff, profile, rerun, "sha256:rag", "sha256:controls"
    )
    assert validate_integrated_validation_profile(integrated)["status"] == "PASS"
    assert (
        integrated["components"]["e2_policy_requirement_validation"]["external_model_execution"]
        == "PENDING_EXTERNAL_EXECUTION"
    )


def test_da_be_fe_governance_contract_uses_same_digests_and_fields(built_artifacts) -> None:
    artifact_dir = Path(__file__).parents[1] / "artifacts/experiment_03"
    handoff = json.loads(
        (artifact_dir / "E2_TO_E3_TRANSFORM_REQUIREMENTS.json").read_text(encoding="utf-8")
    )
    profile = json.loads(
        (artifact_dir / "E3_VALIDATED_TRANSFORM_PROFILE.json").read_text(encoding="utf-8")
    )
    workspace = Path(__file__).parents[3]
    be_projection = (
        workspace / "ADP-BE/src/main/java/com/adp/gateway/ai/application/"
        "AiTransformGovernanceProfileService.java"
    ).read_text(encoding="utf-8")
    fe_projection = (workspace / "ADP-FE/src/features/ai-evaluation/mocks/handlers.ts").read_text(
        encoding="utf-8"
    )

    assert handoff["contract_digest"] in be_projection
    assert profile["profile_digest"] in be_projection
    assert profile["profile_digest"] in fe_projection
    for field_name in {row["field_name"] for row in handoff["requirements"]}:
        assert field_name in be_projection
        assert field_name in fe_projection


def test_provider_governance_baseline_is_active_fail_closed_and_cross_repo_bound() -> None:
    governance = json.loads(
        (ARTIFACT_DIR / "E2_PROVIDER_GOVERNANCE_BASELINE.json").read_text(encoding="utf-8")
    )
    workspace = Path(__file__).parents[3]
    be_contract = (
        workspace / "ADP-BE/src/main/java/com/adp/gateway/ai/application/"
        "AiEvaluationContractService.java"
    ).read_text(encoding="utf-8")
    fe_projection = (workspace / "ADP-FE/src/features/ai-evaluation/mocks/handlers.ts").read_text(
        encoding="utf-8"
    )

    assert governance["activation_status"] == "ACTIVE_FAIL_CLOSED"
    assert governance["governance_decision"] == "BLOCK"
    assert governance["provider_actual_calls"] == 0
    assert governance["reason_codes"] == [
        "PROVIDER_REGION_REQUIRED",
        "RETENTION_UNVERIFIED",
        "MODEL_TRAINING_NOT_ALLOWED",
    ]
    mapping = {
        row["model_profile_id"]: row["destination_digest"]
        for row in governance["destination_contract_mapping"]
    }
    assert mapping == {
        "google-gemma-4-31b-it": (
            "sha256:824292c9ad5bdcd8cd1c502997053243f179782e18402ca380b4c54a0c76f991"
        ),
        "meta-muse-glimmer-30b": (
            "sha256:35827b9982c8813acef21a321d0bde08d856039a882c09cbf764d72d1cc3b607"
        ),
        "nvidia-nemotron-3.5-lightning-30b-a3b": (
            "sha256:a6d7fb15ca4da646ca16fb92eb2a7c39327be9cdff21a130012f564749bc922e"
        ),
    }
    assert governance["contract_version"] in be_contract
    assert governance["contract_digest"] in fe_projection


def test_holdout_baseline_digest_and_readiness_are_fail_closed() -> None:
    baseline = json.loads(
        (ARTIFACT_DIR / "AI_E1_E2_E3_HOLDOUT_BASELINE.json").read_text(encoding="utf-8")
    )
    integrated = json.loads(
        (ARTIFACT_DIR / "AI_INTEGRATED_VALIDATION_PROFILE.json").read_text(encoding="utf-8")
    )

    assert baseline["baseline_digest"] == canonical_digest(
        {key: value for key, value in baseline.items() if key != "baseline_digest"}
    )
    assert integrated["integrated_profile_digest"] == canonical_digest(
        {key: value for key, value in integrated.items() if key != "integrated_profile_digest"}
    )
    assert baseline["holdout_readiness"]["holdout_ready"] == "BLOCKED"
    assert baseline["provider_actual_calls"] == 0
    assert integrated["provider_calls"] == 0
