import copy
import json
from pathlib import Path

import pytest
from adp_da.experiment_02 import (
    Experiment02Error,
    build_operational_metrics_contract,
    build_internal_control_roles,
    build_rag_top1_analysis,
    validate_evidence,
    validate_e2_to_e3_handoff,
    validate_operational_metrics_contract,
    validate_internal_control_roles,
    validate_rag_top1_analysis,
    validate_synthetic_egress_evidence,
    validate_temporal_provenance,
)

ARTIFACT = Path(__file__).parents[1] / "artifacts/experiment_02/FINANCIAL_AI_REGULATORY_EVIDENCE_V2.json"
EGRESS_ARTIFACT = Path(__file__).parents[1] / "artifacts/experiment_02/NVIDIA_API_TRIAL_SYNTHETIC_EGRESS_EVIDENCE_V1.json"
TEMPORAL_ARTIFACT = Path(__file__).parents[1] / "artifacts/experiment_02/E2_SYNTHETIC_TEMPORAL_PROVENANCE_V1.json"
REEVALUATION_V2 = Path(__file__).parents[1] / "artifacts/experiment_02/NVIDIA_API_TRIAL_SYNTHETIC_EGRESS_REEVALUATION_V2.json"
CANONICAL_DOC = Path(__file__).parents[1] / "docs/EXPERIMENT_02_REGULATORY_RUNTIME_VALIDATION.md"
OPERATIONAL_CONTRACT = Path(__file__).parents[1] / "artifacts/experiment_02/E2_CROSS_MODEL_OPERATIONAL_METRICS_CONTRACT_V1.json"
RAG_TOP1_ANALYSIS = Path(__file__).parents[1] / "artifacts/experiment_02/E2_RAG_TOP1_MISS_ANALYSIS_V1.json"
CONTROL_ROLES = Path(__file__).parents[1] / "artifacts/experiment_02/E2_INTERNAL_CONTROL_ROLE_CLASSIFICATION_V1.json"
CONTROL_CATALOG = Path(__file__).parents[1] / "gateway_rules/processed/controls.json"
E2_TO_E3_HANDOFF = Path(__file__).parents[1] / "artifacts/experiment_03/E2_TO_E3_TRANSFORM_REQUIREMENTS.json"


def test_regulatory_evidence_and_rag_are_deterministic() -> None:
    result = validate_evidence(json.loads(ARTIFACT.read_text(encoding="utf-8")))
    assert result["status"] == "PASS"
    assert result["source_count"] == 10
    assert result["requirement_count"] == 39
    assert result["runtime_mapped"] == 39
    assert result["unmapped"] == 0
    assert result["hit_at_1"] == 1.0
    assert (result["hit_at_3"], result["hit_at_5"]) == (1.0, 1.0)


def test_top1_misses_are_explicitly_analyzed_and_resolved() -> None:
    evidence = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    analysis = build_rag_top1_analysis(evidence)
    assert json.loads(RAG_TOP1_ANALYSIS.read_text(encoding="utf-8")) == analysis
    assert validate_rag_top1_analysis(analysis, evidence)["resolved_miss_count"] == 2
    assert {row["query_id"] for row in analysis["misses"]} == {"Q04", "Q06"}


def test_all_19_internal_controls_have_explained_roles() -> None:
    controls = json.loads(CONTROL_CATALOG.read_text(encoding="utf-8"))
    roles = build_internal_control_roles(controls)
    assert json.loads(CONTROL_ROLES.read_text(encoding="utf-8")) == roles
    result = validate_internal_control_roles(roles)
    assert result["role_family_counts"] == {"DIRECT": 6, "INDIRECT": 5, "GOVERNANCE": 8}


def test_negative_case_provider_call_must_remain_zero() -> None:
    value = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    changed = copy.deepcopy(value)
    changed["negative_cases"][0]["provider_calls"] = 1
    with pytest.raises(Experiment02Error, match="provider-call-zero"):
        validate_evidence(changed)


def test_unresolved_applicability_fails_closed() -> None:
    value = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    changed = copy.deepcopy(value)
    changed["requirements"][0]["applicability"] = "UNRESOLVED"
    with pytest.raises(Experiment02Error, match="unresolved applicability"):
        validate_evidence(changed)


def test_unmapped_requirement_fails_closed() -> None:
    value = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    changed = copy.deepcopy(value)
    changed["requirements"][0]["fpg_control_id"] = "UNMAPPED"
    with pytest.raises(Experiment02Error, match="unmapped requirement"):
        validate_evidence(changed)


def test_hit_metrics_are_not_runtime_compliance() -> None:
    value = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    changed = copy.deepcopy(value)
    changed["verification_layers"]["runtime_enforcement"] = "PASS"
    with pytest.raises(Experiment02Error, match="requires execution evidence"):
        validate_evidence(changed)


def test_nvidia_trial_uses_only_fail_closed_synthetic_resolution() -> None:
    result = validate_synthetic_egress_evidence(json.loads(EGRESS_ARTIFACT.read_text(encoding="utf-8")))
    assert result["status"] == "PASS"
    assert result["provider_call_authorized"] is False


def test_nvidia_trial_provider_uncertainty_cannot_be_hidden() -> None:
    value = json.loads(EGRESS_ARTIFACT.read_text(encoding="utf-8"))
    changed = copy.deepcopy(value)
    changed["provider_terms"]["processing_region"] = "US"
    with pytest.raises(Experiment02Error, match="region must not be inferred"):
        validate_synthetic_egress_evidence(changed)


def test_nvidia_trial_extra_released_field_fails_closed() -> None:
    value = json.loads(EGRESS_ARTIFACT.read_text(encoding="utf-8"))
    changed = copy.deepcopy(value)
    changed["payload_minimization"]["retrieved_and_released_field_paths"].append("customer.email")
    with pytest.raises(Experiment02Error, match="released field allowlist"):
        validate_synthetic_egress_evidence(changed)


def test_e2_synthetic_timestamps_are_inside_frozen_retrieval_window() -> None:
    result = validate_temporal_provenance(json.loads(TEMPORAL_ARTIFACT.read_text(encoding="utf-8")))
    assert result["status"] == "PASS"
    assert result["transaction_count"] == 6


def test_e2_synthetic_timestamp_outside_window_fails_closed() -> None:
    value = json.loads(TEMPORAL_ARTIFACT.read_text(encoding="utf-8"))
    changed = copy.deepcopy(value)
    changed["transactions"][0]["normalized_synthetic_timestamp"] = "2022-06-14T08:00:00"
    with pytest.raises(Experiment02Error, match="outside retrieval window"):
        validate_temporal_provenance(changed)


def test_temporally_consistent_cases_reach_outbound_without_provider_call() -> None:
    value = json.loads(REEVALUATION_V2.read_text(encoding="utf-8"))
    assert value["temporal_consistency_status"] == "VERIFIED"
    assert len(value["results"]) == 3
    assert all(row["retrieval_transaction_count"] == 2 for row in value["results"])
    assert all(row["transform_status"] == "APPLIED" for row in value["results"])
    assert all(row["outbound_guard_status"] == "PASSED" for row in value["results"])
    assert all(row["provider_status"] == "NOT_SENT" for row in value["results"])
    assert set(value["provider_baseline"].values()) == {0}
    assert value["destination_risk"]["decision"] == "REVIEW_REQUIRED"
    assert value["destination_risk"]["provider_call_authorized"] is False


def test_canonical_doc_preserves_e1_depth_and_truthful_e2_execution_boundary() -> None:
    document = CANONICAL_DOC.read_text(encoding="utf-8")
    required_sections = (
        "## 1. Objective", "## 2. E1 Baseline", "## 3. E1 → E2 Expansion",
        "## 4. Regulatory Evidence", "## 5. Internal Policy / Control",
        "## 6. Workload / Purpose", "## 7. RAG Validation", "## 8. Applicability",
        "## 9. Field Requirement", "## 10. Positive Runtime",
        "## 11. Negative Runtime N1~N4", "## 12. Provider Governance",
        "## 13. Model별 Validation Contract", "### 13.1 Nemotron 3.5 Lightning",
        "### 13.2 Muse Glimmer 30B", "### 13.3 Gemma 4 31B IT",
        "## 14. Cross-Model Metrics Contract", "## 15. E1 ↔ E2 Comparison",
        "## 16. FE Controller Contract", "## 17. E3 Handoff",
        "## 18. Limitations / Remaining Gap",
    )
    assert all(section in document for section in required_sections)
    assert "Status: `OPEN / PRE_PROVIDER_VALIDATED / PROVIDER_GOVERNANCE_BLOCKED`" in document
    assert "Provider baseline은 request `0`, connector execution `0`, AI model execution evidence `0`" in document
    assert "| P1 | NOT_EXECUTED | NOT_EXECUTED | NOT_EXECUTED |" in document
    assert "| P2 | NOT_EXECUTED | NOT_EXECUTED | NOT_EXECUTED |" in document
    assert "| P3 | NOT_EXECUTED | NOT_EXECUTED | NOT_EXECUTED |" in document
    assert "E2-FIELD-REQ-REV-001" in document
    assert "NOT_IMPLEMENTED_AS_NATIVE_BE_FINDING" in document


def test_e2_owned_e3_input_handoff_is_frozen_without_running_e3() -> None:
    result = validate_e2_to_e3_handoff(json.loads(E2_TO_E3_HANDOFF.read_text(encoding="utf-8")))
    assert result == {
        "status": "PASS",
        "contract_version": "1.1.1",
        "contract_digest": "sha256:899cf31a920c1363cfb21b9c7d6f3204819222935bcbb9008a01ccbf9a8ba73e",
        "requirement_count": 60,
    }


def test_cross_model_operational_metrics_are_frozen_without_fabricated_values() -> None:
    contract = build_operational_metrics_contract()
    assert json.loads(OPERATIONAL_CONTRACT.read_text(encoding="utf-8")) == contract
    result = validate_operational_metrics_contract(contract)
    assert result["status"] == "PASS"
    assert result["execution_contract_count"] == 9
    assert all(row["provider_latency_ms"] is None for row in contract["executions"])
    assert all(row["total_tokens"] is None for row in contract["executions"])
    assert all(row["response_finding_types"] is None for row in contract["executions"])
