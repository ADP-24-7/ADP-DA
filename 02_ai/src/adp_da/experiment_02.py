"""Fail-closed validation for Experiment 02 regulatory and runtime evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


class Experiment02Error(ValueError):
    pass


SCHEMA = "adp-ai-financial-regulatory-evidence/v2"
SOURCE_TYPES = {"LAW", "REGULATION", "SUPERVISORY_GUIDELINE", "SECURITY_GUIDANCE"}
APPLICABILITY = {"APPLICABLE", "CONDITIONAL", "NOT_APPLICABLE", "UNRESOLVED"}
RUNTIME_STAGES = {
    "Authentication",
    "Authorization",
    "WorkloadPurposeSubjectActionBinding",
    "Policy",
    "Retrieval",
    "Transform",
    "OutboundGuard",
    "Provider",
    "ResponseGuard",
    "ControlledDelivery",
    "ContractEvaluationBundle",
    "StageTimingTrace",
}
EGRESS_SCHEMA = "adp-ai-provider-egress-evidence/v1"
E2_DATASET_DIGEST = "sha256:9afdc4bf89c0047a5e90f21e6f8eaffb4f6c148998f1740f30baf666bdae0a44"
E2_RELEASED_FIELDS = {
    "input.prompt",
    "customer.customer_id",
    "customer.segment",
    "account.account_id",
    "account.account_type",
    "account.balance",
    "transaction.transaction_id",
    "transaction.posted_at",
    "transaction.merchant_category",
    "transaction.amount",
}
OPERATIONAL_METRICS_SCHEMA = "adp-ai-e2-cross-model-operational-metrics/v1"
RAG_TOP1_ANALYSIS_SCHEMA = "adp-ai-e2-rag-top1-miss-analysis/v1"
INTERNAL_CONTROL_ROLE_SCHEMA = "adp-ai-e2-internal-control-role-classification/v1"
E2_TO_E3_HANDOFF_SCHEMA = "adp-ai-e2-to-e3-transform-requirements/v1"
E2_CASES = (
    "financial-regulatory-p1-customer-10861",
    "financial-regulatory-p2-customer-10832",
    "financial-regulatory-p3-customer-10202",
)
E2_MODELS = (
    "Nemotron 3.5 Lightning",
    "Muse Glimmer 30B",
    "Gemma 4 31B IT",
)
REQUIRED_REQUIREMENT_FIELDS = {
    "source_id",
    "source_title",
    "source_type",
    "authority",
    "effective_date",
    "article_or_section",
    "requirement_id",
    "requirement_text",
    "applicability_condition",
    "applicability",
    "workload_scope",
    "data_scope",
    "provider_scope",
    "destination_scope",
    "fpg_control_id",
    "runtime_stage",
    "expected_decision",
    "evidence_field",
    "citation",
    "content_digest",
}
REQUIRED_HANDOFF_ROW_FIELDS = {
    "case_id",
    "workload_id",
    "purpose_code",
    "field_name",
    "business_need",
    "regulatory_requirement_ids",
    "internal_policy_ids",
    "applicability",
    "field_requirement",
    "transform_intent",
    "utility_requirement",
    "candidate_transform_methods",
    "prohibited_transform_methods",
    "required_exact",
    "relation_preservation_required",
    "reversibility_allowed",
    "external_release_allowed",
    "runtime_control_id",
    "decision_reason",
    "evidence_digest",
}


def digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def requirement_digest(item: dict[str, Any]) -> str:
    return digest({key: value for key, value in item.items() if key != "content_digest"})


def _fail(condition: bool, message: str) -> None:
    if condition:
        raise Experiment02Error(message)


def validate_e2_to_e3_handoff(value: dict[str, Any]) -> dict[str, Any]:
    """Validate the frozen E2-owned input contract without running Experiment 03."""
    _fail(value.get("schema_version") != E2_TO_E3_HANDOFF_SCHEMA, "handoff schema mismatch")
    _fail(value.get("contract_version") != "1.1.1", "handoff version mismatch")
    _fail(value.get("status") != "FROZEN", "handoff is not frozen")
    _fail(
        value.get("provider_call_authorized") is not False,
        "handoff provider authorization must be false",
    )
    expected_digest = digest({key: item for key, item in value.items() if key != "contract_digest"})
    _fail(value.get("contract_digest") != expected_digest, "handoff contract digest mismatch")

    rows = value.get("requirements", [])
    pairs = {(row.get("case_id"), row.get("field_name")) for row in rows}
    _fail(len(rows) != 60 or len(pairs) != 60, "handoff field cardinality mismatch")
    _fail({row.get("case_id") for row in rows} != set(E2_CASES), "handoff case binding mismatch")
    _fail(
        any(not REQUIRED_HANDOFF_ROW_FIELDS <= row.keys() for row in rows),
        "handoff row field missing",
    )
    _fail(
        any(
            row.get("workload_id") != "customer_summary"
            or row.get("purpose_code") != "CUSTOMER_SUPPORT"
            for row in rows
        ),
        "handoff workload/purpose mismatch",
    )

    exact_amount_rows = [
        row for row in rows if row.get("field_name") in {"account.balance", "transaction.amount"}
    ]
    _fail(len(exact_amount_rows) != 6, "handoff exact amount cardinality mismatch")
    _fail(
        any(
            row.get("field_requirement") != "REQUIRED_EXACT"
            or row.get("required_exact") is not True
            or row.get("candidate_transform_methods") != ["KEEP"]
            or "GENERALIZE" not in row.get("prohibited_transform_methods", [])
            for row in exact_amount_rows
        ),
        "handoff KEEP_ONLY requirement mismatch",
    )
    return {
        "status": "PASS",
        "contract_version": value["contract_version"],
        "contract_digest": expected_digest,
        "requirement_count": len(rows),
    }


def validate_evidence(value: dict[str, Any]) -> dict[str, Any]:
    _fail(value.get("schema_version") != SCHEMA, "schema version mismatch")
    sources = value.get("sources", [])
    requirements = value.get("requirements", [])
    cases = value.get("positive_cases", [])
    _fail(
        not sources or not requirements or len(cases) != 3,
        "source/requirement/positive-case cardinality mismatch",
    )

    source_ids = {item.get("source_id") for item in sources}
    _fail(None in source_ids or len(source_ids) != len(sources), "source identity mismatch")
    _fail(
        any(item.get("source_type") not in SOURCE_TYPES for item in sources), "source type mismatch"
    )

    requirement_ids: set[str] = set()
    for item in requirements:
        _fail(not REQUIRED_REQUIREMENT_FIELDS <= item.keys(), "requirement field missing")
        _fail(item["requirement_id"] in requirement_ids, "duplicate requirement id")
        requirement_ids.add(item["requirement_id"])
        _fail(item["source_id"] not in source_ids, "requirement source binding mismatch")
        _fail(item["source_type"] not in SOURCE_TYPES, "requirement source type mismatch")
        _fail(item["applicability"] not in APPLICABILITY, "applicability enum mismatch")
        _fail(item["applicability"] == "UNRESOLVED", "unresolved applicability cannot pass")
        stages = set(item["runtime_stage"])
        _fail(not stages or not stages <= RUNTIME_STAGES, "runtime stage mapping mismatch")
        _fail(item["fpg_control_id"] == "UNMAPPED", "unmapped requirement cannot pass")
        _fail(item["content_digest"] != requirement_digest(item), "requirement digest mismatch")

    queries = value.get("rag", {}).get("queries", [])
    _fail(not queries, "RAG query cardinality mismatch")
    for query in queries:
        _fail(query.get("gold") not in requirement_ids, "RAG gold binding mismatch")
        _fail(
            any(item not in requirement_ids for item in query.get("ranked", [])),
            "RAG ranked binding mismatch",
        )
    hits = {k: sum(q["gold"] in q["ranked"][:k] for q in queries) / len(queries) for k in (1, 3, 5)}
    expected = value["rag"]["metrics"]
    _fail(
        any(abs(hits[k] - expected[f"hit_at_{k}"]) > 1e-12 for k in (1, 3, 5)),
        "RAG metric mismatch",
    )

    layers = value.get("verification_layers", {})
    _fail(
        set(layers)
        != {
            "source_coverage",
            "retrieval_correctness",
            "runtime_enforcement",
            "execution_evidence",
        },
        "four-layer verification mismatch",
    )
    _fail(
        layers["source_coverage"] != "PASS" or layers["retrieval_correctness"] != "PASS",
        "corpus verification layer mismatch",
    )
    _fail(
        layers["runtime_enforcement"] not in {"PASS", "PENDING"}
        or layers["execution_evidence"] not in {"PASS", "PENDING"},
        "runtime verification layer mismatch",
    )
    _fail(
        layers["runtime_enforcement"] == "PASS" and layers["execution_evidence"] != "PASS",
        "runtime enforcement requires execution evidence",
    )

    negatives = value.get("negative_cases", [])
    _fail(
        len(negatives) != 4 or any(item.get("provider_calls") != 0 for item in negatives),
        "negative provider-call-zero mismatch",
    )
    _fail(
        any(key in json.dumps(value).lower() for key in ('"raw_value"', '"raw_text"', '"offset"')),
        "raw or offset evidence is forbidden",
    )

    applicability = Counter(item["applicability"] for item in requirements)
    source_types = Counter(item["source_type"] for item in sources)
    return {
        "status": "PASS",
        "source_count": len(sources),
        "requirement_count": len(requirements),
        "runtime_mapped": len(requirements),
        "unmapped": 0,
        "source_type_distribution": dict(sorted(source_types.items())),
        "applicability_distribution": dict(sorted(applicability.items())),
        "hit_at_1": hits[1],
        "hit_at_3": hits[3],
        "hit_at_5": hits[5],
        "evidence_digest": digest(value),
    }


def build_rag_top1_analysis(value: dict[str, Any]) -> dict[str, Any]:
    """Record the two corrected pre-freeze Top1 misses without hiding their semantics."""
    requirement_index = {row["requirement_id"]: row for row in value["requirements"]}
    query_index = {row["query_id"]: row for row in value["rag"]["queries"]}
    misses = []
    definitions = (
        (
            "Q04",
            "EFSR-CLOUD-IMPORTANCE",
            "PIPA-OVERSEAS-TRANSFER",
            "INCORRECT_TOP1_DIFFERENT_REQUIREMENT",
            "Cloud service importance assessment is adjacent destination governance, "
            "but it does not answer the overseas-transfer legal-condition query.",
        ),
        (
            "Q06",
            "AI-ACT-HIGH-IMPACT-CHECK",
            "CREDIT-AUTOMATED-EVALUATION",
            "INCORRECT_TOP1_DIFFERENT_REQUIREMENT",
            "High-impact AI classification is adjacent applicability context, but it does "
            "not answer the Credit Information Act automated-evaluation rights query.",
        ),
    )
    for query_id, previous_top1, gold, assessment, reason in definitions:
        query = query_index[query_id]
        gold_row = requirement_index[gold]
        previous_row = requirement_index[previous_top1]
        misses.append(
            {
                "query_id": query_id,
                "query_text": query["text"],
                "expected_gold_requirement": gold,
                "previous_actual_top1": previous_top1,
                "previous_correct_gold_rank": 2,
                "source": gold_row["source_id"],
                "requirement": gold_row["requirement_text"],
                "applicability": gold_row["applicability"],
                "previous_top1_source": previous_row["source_id"],
                "previous_top1_applicability": previous_row["applicability"],
                "semantic_assessment": assessment,
                "analysis": reason,
                "runtime_decision_impact": (
                    "NONE; both queries remain evidence retrieval inputs and applicability "
                    "is evaluated independently."
                ),
                "resolution": "RANKING_METADATA_CORRECTED_TO_REQUIREMENT_SPECIFIC_GOLD",
                "resolved_top1": query["ranked"][0],
                "resolved_gold_rank": query["ranked"].index(gold) + 1,
            }
        )
    payload = {
        "schema_version": RAG_TOP1_ANALYSIS_SCHEMA,
        "status": "RESOLVED",
        "corpus_id": value["corpus_id"],
        "analysis_scope": ["Q04", "Q06"],
        "before_metrics": {"hit_at_1": 11 / 13, "hit_at_3": 1.0, "hit_at_5": 1.0},
        "after_metrics": value["rag"]["metrics"],
        "misses": misses,
    }
    payload["analysis_digest"] = digest(payload)
    return payload


def validate_rag_top1_analysis(value: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    _fail(
        value.get("schema_version") != RAG_TOP1_ANALYSIS_SCHEMA, "RAG Top1 analysis schema mismatch"
    )
    expected = digest({k: v for k, v in value.items() if k != "analysis_digest"})
    _fail(value.get("analysis_digest") != expected, "RAG Top1 analysis digest mismatch")
    _fail(
        value.get("status") != "RESOLVED" or len(value.get("misses", [])) != 2,
        "RAG Top1 misses are not resolved",
    )
    ranked = {row["query_id"]: row for row in evidence["rag"]["queries"]}
    _fail(
        any(
            ranked[row["query_id"]]["ranked"][0] != row["expected_gold_requirement"]
            or row["resolved_gold_rank"] != 1
            for row in value["misses"]
        ),
        "RAG Top1 resolution does not match frozen rankings",
    )
    _fail(
        value.get("after_metrics") != {"hit_at_1": 1.0, "hit_at_3": 1.0, "hit_at_5": 1.0},
        "RAG Top1 post-resolution metrics mismatch",
    )
    return {"status": "PASS", "resolved_miss_count": 2, "analysis_digest": expected}


def build_internal_control_roles(controls: list[dict[str, Any]]) -> dict[str, Any]:
    direct = {
        "CTRL-EVAL-001",
        "CTRL-RUNTIME-001",
        "CTRL-RUNTIME-003",
        "CTRL-RUNTIME-008",
        "CTRL-GOV-003",
        "CTRL-RUNTIME-009",
    }
    policy_input = {
        "CTRL-RUNTIME-002",
        "CTRL-RUNTIME-004",
        "CTRL-RUNTIME-005",
        "CTRL-RUNTIME-006",
        "CTRL-RUNTIME-007",
    }
    explicit_roles = {
        "CTRL-GOV-001": "AUDIT_ONLY",
        "CTRL-GOV-002": "HUMAN_REVIEW",
        "CTRL-REF-001": "HUMAN_REVIEW",
        "CTRL-REF-002": "AUDIT_ONLY",
        "CTRL-GOV-004": "GOVERNANCE_ONLY",
        "CTRL-REF-003": "HUMAN_REVIEW",
        "CTRL-GOV-005": "GOVERNANCE_ONLY",
        "CTRL-GOV-006": "PROVIDER_GOVERNANCE",
    }
    runtime_locations = {
        "CTRL-EVAL-001": "E2 field requirement / E3 method evidence and validation profile",
        "CTRL-RUNTIME-001": "Policy -> OutboundGuard -> outbound decision evidence",
        "CTRL-RUNTIME-003": "Transform -> field treatment / mapping separation evidence",
        "CTRL-RUNTIME-008": "Transform -> OutboundGuard sensitive-data release evidence",
        "CTRL-GOV-003": "Applicability / destination profile -> provider governance gate",
        "CTRL-RUNTIME-009": "Policy -> destination reuse-risk decision -> provider NOT_CALLED",
    }
    rows = []
    for control in controls:
        control_id = control["control_id"]
        if control_id in direct:
            role, family = "DIRECT_RUNTIME_CONTROL", "DIRECT"
            location = runtime_locations[control_id]
        elif control_id in policy_input:
            role, family = "POLICY_INPUT", "INDIRECT"
            location = (
                "Policy/applicability input; no independent final Runtime allow/block binding in E2"
            )
        else:
            role, family = explicit_roles[control_id], "GOVERNANCE"
            location = ", ".join(control.get("enforcement_point", []))
        rows.append(
            {
                "internal_control": control_id,
                "control_name": control["control_name"],
                "role": role,
                "role_family": family,
                "runtime_api_trace_location": location,
                "evidence": {
                    "catalog_ref": f"gateway_rules/processed/controls.json#{control_id}",
                    "requirement_ids": control.get("requirement_ids", []),
                    "validation_requirement": control.get("validation_requirement"),
                    "implementation_boundary": control.get("implementation_boundary"),
                },
            }
        )
    counts = Counter(row["role_family"] for row in rows)
    payload = {
        "schema_version": INTERNAL_CONTROL_ROLE_SCHEMA,
        "status": "CLASSIFIED",
        "control_count": len(rows),
        "unmapped_count": 0,
        "role_family_counts": {key: counts[key] for key in ("DIRECT", "INDIRECT", "GOVERNANCE")},
        "controls": rows,
    }
    payload["classification_digest"] = digest(payload)
    return payload


def validate_internal_control_roles(value: dict[str, Any]) -> dict[str, Any]:
    _fail(
        value.get("schema_version") != INTERNAL_CONTROL_ROLE_SCHEMA,
        "internal control role schema mismatch",
    )
    expected = digest({k: v for k, v in value.items() if k != "classification_digest"})
    _fail(value.get("classification_digest") != expected, "internal control role digest mismatch")
    rows = value.get("controls", [])
    _fail(
        len(rows) != 19 or len({row.get("internal_control") for row in rows}) != 19,
        "internal control catalog cardinality mismatch",
    )
    _fail(value.get("unmapped_count") != 0, "internal control role remains unmapped")
    counts = Counter(row.get("role_family") for row in rows)
    _fail(
        dict(counts) != {"DIRECT": 6, "INDIRECT": 5, "GOVERNANCE": 8},
        "internal control role-family counts mismatch",
    )
    _fail(
        any(not row.get("runtime_api_trace_location") or not row.get("evidence") for row in rows),
        "internal control role explanation missing",
    )
    return {
        "status": "PASS",
        "control_count": 19,
        "role_family_counts": value["role_family_counts"],
        "classification_digest": expected,
    }


def validate_runtime(bundle: dict[str, Any], traces: list[dict[str, Any]]) -> dict[str, Any]:
    results = bundle.get("case_results", [])
    pairs = {(row["eval_case_id"], row["model_profile_id"]) for row in results}
    _fail(len(results) != 9 or len(pairs) != 9, "3 case x 3 model completeness mismatch")
    by_case: dict[str, set[str]] = {}
    for row in results:
        by_case.setdefault(row["eval_case_id"], set()).add(row["semantic_provider_input_digest"])
    _fail(
        any(len(values) != 1 for values in by_case.values()),
        "semantic provider input differs by model",
    )

    trace_ids = {trace["executionId"] for trace in traces}
    result_ids = {row["execution_id"] for row in results}
    _fail(trace_ids != result_ids, "bundle/trace execution identity mismatch")
    for trace in traces:
        evidence = trace.get("evidence", {})
        authorization = evidence.get("authorizationResult")
        policy = evidence.get("policyAction") or evidence.get("finalAction")
        outbound = evidence.get("outboundGuardStatus")
        provider = evidence.get("providerStatus")
        response_guard = evidence.get("responseGuardStatus")
        delivery = evidence.get("controlledDeliveryStatus")
        _fail(
            authorization == "DENIED" and provider != "NOT_CALLED",
            "provider called after authorization deny",
        )
        _fail(policy == "BLOCK" and provider != "NOT_CALLED", "provider called after policy block")
        _fail(
            outbound == "BLOCKED" and provider != "NOT_CALLED",
            "provider called after outbound block",
        )
        _fail(
            response_guard == "REJECTED" and delivery == "DELIVERED", "rejected response delivered"
        )
        _fail(
            delivery == "WITHHELD" and bool(evidence.get("deliveredResponseDigest")),
            "withheld response exposed",
        )
        _fail(
            not evidence.get("regulatoryEvidenceDigest") or not evidence.get("ragEvidenceDigest"),
            "regulatory/RAG evidence binding missing",
        )
        timings = trace.get("stageTimings", [])
        _fail(not timings, "stage timing evidence missing")
        for timing in timings:
            _fail(
                timing["endedAt"] < timing["startedAt"] or timing["durationMillis"] < 0,
                "stage timing ordering mismatch",
            )
        model = evidence.get("aiModel") or {}
        tokens = [model.get("inputTokens"), model.get("outputTokens"), model.get("totalTokens")]
        measured_tokens = [item for item in tokens if isinstance(item, int)]
        if len(measured_tokens) == 3:
            _fail(
                measured_tokens[0] + measured_tokens[1] != measured_tokens[2], "token sum mismatch"
            )
    return {"status": "PASS", "execution_count": len(pairs)}


def validate_synthetic_egress_evidence(value: dict[str, Any]) -> dict[str, Any]:
    """Validate option-2 safety evidence without creating a provider request."""
    _fail(value.get("schema_version") != EGRESS_SCHEMA, "egress evidence schema mismatch")
    terms = value.get("provider_terms", {})
    _fail(terms.get("processing_region") != "UNRESOLVED", "provider region must not be inferred")
    _fail(
        "DURATION_UNSPECIFIED" not in terms.get("retention", ""),
        "provider retention uncertainty missing",
    )
    _fail(
        "AI_MODEL_IMPROVEMENT" not in terms.get("training_or_reuse", ""),
        "provider reuse disclosure missing",
    )

    resolution = value.get("resolution", {})
    _fail(
        resolution.get("path") != "FULLY_SYNTHETIC_NON_LINKABLE_MINIMIZED_PAYLOAD",
        "synthetic resolution path mismatch",
    )
    _fail(
        resolution.get("provider_conditions_treated_as_resolved") is not False,
        "provider uncertainty must remain explicit",
    )
    _fail(
        "MUST_NOT_CALL_PROVIDER" not in resolution.get("fail_closed_condition", ""),
        "synthetic evidence is not fail-closed",
    )

    provenance = value.get("dataset_provenance", {})
    _fail(
        provenance.get("dataset_digest") != E2_DATASET_DIGEST, "synthetic dataset digest mismatch"
    )
    _fail(
        provenance.get("source_type") != "SYNTHETIC"
        or provenance.get("real_person_linkage") != "NONE",
        "dataset is not proven synthetic and non-linkable",
    )
    _fail(len(set(provenance.get("case_row_refs", []))) != 3, "synthetic case binding mismatch")

    payload = value.get("payload_minimization", {})
    _fail(
        set(payload.get("retrieved_and_released_field_paths", [])) != E2_RELEASED_FIELDS,
        "released field allowlist mismatch",
    )
    _fail(
        set(payload.get("transform_treatments", {})) != E2_RELEASED_FIELDS,
        "released field transform coverage mismatch",
    )
    _fail(
        any(
            payload.get(flag) is not False
            for flag in (
                "raw_personal_data_present",
                "raw_credit_information_present",
                "confidential_fpg_data_present",
                "linkable_to_real_person",
            )
        ),
        "unsafe outbound data classification",
    )

    reevaluation = value.get("reevaluation", {})
    _fail(
        reevaluation.get("applicability", {}).get("on_mismatch")
        != "UNRESOLVED_MUST_NOT_CALL_PROVIDER",
        "applicability mismatch is not fail-closed",
    )
    _fail(
        reevaluation.get("policy", {}).get("decision") != "TRANSFORM"
        or reevaluation.get("policy", {}).get("manual_override") is not False
        or reevaluation.get("policy", {}).get("production_semantics_changed") is not False,
        "policy reevaluation mismatch",
    )
    guard = reevaluation.get("outbound_guard", {})
    _fail(
        guard.get("decision") != "PASS_ELIGIBLE_NOT_EXECUTED"
        or guard.get("provider_call_authorized") is not False,
        "outbound guard reevaluation mismatch",
    )
    baseline = value.get("provider_baseline", {})
    _fail(
        any(
            baseline.get(key) != 0
            for key in (
                "provider_request",
                "connector_execution",
                "ai_model_execution_evidence",
            )
        ),
        "provider baseline is not zero",
    )
    return {"status": "PASS", "evidence_digest": digest(value), "provider_call_authorized": False}


def validate_temporal_provenance(value: dict[str, Any]) -> dict[str, Any]:
    _fail(
        value.get("schema_version") != "adp-ai-synthetic-temporal-provenance/v1",
        "temporal provenance schema mismatch",
    )
    _fail(
        value.get("temporal_consistency_status") != "VERIFIED",
        "temporal consistency is not verified",
    )
    reference = date.fromisoformat(value["evaluation_reference_date"])
    window = value.get("retrieval_window_days")
    _fail(window != 90, "retrieval window mismatch")
    window_days = 90
    rows = value.get("transactions", [])
    _fail(
        len(rows) != 6 or len({row.get("transaction_id") for row in rows}) != 6,
        "temporal transaction set mismatch",
    )
    lower = reference - timedelta(days=window_days)
    for row in rows:
        original = datetime.fromisoformat(row["original_synthetic_timestamp"])
        normalized = datetime.fromisoformat(row["normalized_synthetic_timestamp"])
        _fail(original == normalized, "timestamp was not normalized")
        _fail(
            not lower <= normalized.date() <= reference,
            "normalized timestamp outside retrieval window",
        )
        _fail(
            not row.get("customer_id")
            or not row.get("account_id")
            or not row.get("transaction_type")
            or not row.get("amount"),
            "preserved transaction semantics missing",
        )
    required = {
        "customer_account_relationship",
        "transaction_amount",
        "transaction_type",
        "balance_relationship",
        "regulatory_trigger",
        "workload_purpose",
        "transform_obligation",
        "destination_contract",
    }
    _fail(set(value.get("preserved_semantics", [])) != required, "preserved semantics mismatch")
    return {"status": "PASS", "transaction_count": 6, "evidence_digest": digest(value)}


def build_operational_metrics_contract() -> dict[str, Any]:
    pre_provider_ids = {
        E2_CASES[0]: "exec_6ecfbcda-6e7d-4eba-a778-cae92571e850",
        E2_CASES[1]: "exec_de6a4ea9-b08f-4b84-899b-7ee1f2042f68",
        E2_CASES[2]: "exec_08d6c0b0-158a-42c3-a15f-3046f3f810c9",
    }
    executions = []
    for case_id in E2_CASES:
        for model in E2_MODELS:
            is_pre_provider = model == E2_MODELS[0]
            executions.append(
                {
                    "case_id": case_id,
                    "model": model,
                    "pre_provider_execution_id": pre_provider_ids[case_id]
                    if is_pre_provider
                    else None,
                    "execution_status": "PRE_PROVIDER_ONLY" if is_pre_provider else "NOT_EXECUTED",
                    "provider_latency_ms": None,
                    "response_guard_latency_ms": None,
                    "runtime_end_to_end_latency_ms": None,
                    "total_execution_latency_ms": None,
                    "input_tokens": None,
                    "output_tokens": None,
                    "total_tokens": None,
                    "response_finding_types": None,
                    "response_finding_status": "NOT_AVAILABLE",
                    "provider_execution_status": "NOT_EXECUTED",
                    "evidence_status": "NOT_AVAILABLE",
                }
            )
    payload = {
        "schema_version": OPERATIONAL_METRICS_SCHEMA,
        "contract_id": "e2-cross-model-operational-metrics/v1",
        "status": "FROZEN_PRE_PROVIDER",
        "evaluation_run_id": "ai-experiment-02-financial-regulatory-v5",
        "fixed_conditions": [
            "CASE",
            "WORKLOAD",
            "PURPOSE",
            "REGULATORY_RAG",
            "INTERNAL_POLICY",
            "PROMPT",
            "RUNTIME_CONTRACT",
            "DESTINATION",
            "GENERATION_CONDITION",
        ],
        "measurement_sources": {
            "provider_latency_ms": "bundle.runtime_metrics.full_response_latency_millis",
            "response_guard_latency_ms": "trace.stage_timings[RESPONSE_GUARD].duration_millis",
            "runtime_end_to_end_latency_ms": "sum(trace stage durations excluding PROVIDER)",
            "total_execution_latency_ms": "trace.updated_at - trace.created_at",
            "input_tokens": "bundle.runtime_metrics.input_tokens",
            "output_tokens": "bundle.runtime_metrics.output_tokens",
            "total_tokens": "bundle.runtime_metrics.total_tokens",
        },
        "null_semantics": "NULL_MEANS_NOT_EXECUTED_OR_NOT_AVAILABLE; ZERO_IS_A_MEASURED_VALUE",
        "token_interpretation": (
            "TOKEN_COUNTS_ARE_MODEL_TOKENIZER_SPECIFIC_AND_NOT_A_GLOBAL_EFFICIENCY_SCORE"
        ),
        "response_finding_contract": {
            "native_source": "BE responseFindingTypes and calibration-evidence finding_type",
            "native_types": [
                "RAW_VALUE_REFLECTION",
                "EMAIL",
                "PHONE_NUMBER",
                "ACCOUNT_NUMBER",
                "RESIDENT_REGISTRATION_NUMBER",
                "PRIVATE_KEY",
                "ACCESS_TOKEN",
                "REFRESH_TOKEN",
                "CREDENTIAL",
                "SECRET",
                "SEED",
            ],
            "analysis_mapping": {
                "SENSITIVE_DATA_EXPOSURE": (
                    "native sensitive finding types including RAW_VALUE_REFLECTION"
                ),
                "RESPONSE_GUARD_REJECTED": (
                    "response_guard_status/reason code; not a duplicate finding enum"
                ),
                "UNSUPPORTED_CLAIM": "NOT_IMPLEMENTED_AS_NATIVE_BE_FINDING",
                "REGULATORY_GROUNDING_MISSING": "NOT_IMPLEMENTED_AS_NATIVE_BE_FINDING",
                "REQUIRED_EVIDENCE_MISSING": "NOT_IMPLEMENTED_AS_NATIVE_BE_FINDING",
                "POLICY_CONFLICT": "NOT_IMPLEMENTED_AS_NATIVE_BE_FINDING",
                "INCOMPLETE_RESPONSE": "NOT_IMPLEMENTED_AS_NATIVE_BE_FINDING",
            },
        },
        "provider_baseline": {
            "provider_request": 0,
            "connector_execution": 0,
            "ai_model_execution_evidence": 0,
        },
        "executions": executions,
    }
    payload["contract_digest"] = digest(payload)
    return payload


def validate_operational_metrics_contract(value: dict[str, Any]) -> dict[str, Any]:
    _fail(
        value.get("schema_version") != OPERATIONAL_METRICS_SCHEMA,
        "operational metrics schema mismatch",
    )
    expected = digest({key: item for key, item in value.items() if key != "contract_digest"})
    _fail(value.get("contract_digest") != expected, "operational metrics digest mismatch")
    rows = value.get("executions", [])
    pairs = {(row.get("case_id"), row.get("model")) for row in rows}
    _fail(
        len(rows) != 9 or pairs != {(case, model) for case in E2_CASES for model in E2_MODELS},
        "operational metrics Cartesian contract mismatch",
    )
    metric_fields = {
        "provider_latency_ms",
        "response_guard_latency_ms",
        "runtime_end_to_end_latency_ms",
        "total_execution_latency_ms",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "response_finding_types",
    }
    _fail(
        any(row.get(field) is not None for row in rows for field in metric_fields),
        "unexecuted metric must remain null",
    )
    _fail(
        any(row.get("provider_execution_status") != "NOT_EXECUTED" for row in rows),
        "provider status must remain NOT_EXECUTED",
    )
    _fail(set(value.get("provider_baseline", {}).values()) != {0}, "provider baseline is not zero")
    mappings = value.get("response_finding_contract", {}).get("analysis_mapping", {})
    _fail(
        mappings.get("UNSUPPORTED_CLAIM") != "NOT_IMPLEMENTED_AS_NATIVE_BE_FINDING",
        "unsupported-claim mapping must remain an explicit gap",
    )
    return {"status": "PASS", "execution_contract_count": 9, "contract_digest": expected}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path, nargs="?")
    parser.add_argument("--write-operational-contract", type=Path)
    parser.add_argument("--write-rag-top1-analysis", type=Path)
    parser.add_argument("--controls", type=Path)
    parser.add_argument("--write-internal-control-roles", type=Path)
    args = parser.parse_args()
    if args.write_operational_contract:
        value = build_operational_metrics_contract()
        validate_operational_metrics_contract(value)
        args.write_operational_contract.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "status": "PASS",
                    "output": str(args.write_operational_contract),
                    "contract_digest": value["contract_digest"],
                },
                indent=2,
            )
        )
        return
    if args.write_rag_top1_analysis:
        if args.evidence is None:
            parser.error("evidence is required for --write-rag-top1-analysis")
        evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
        value = build_rag_top1_analysis(evidence)
        result = validate_rag_top1_analysis(value, evidence)
        args.write_rag_top1_analysis.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps({**result, "output": str(args.write_rag_top1_analysis)}, indent=2))
        return
    if args.write_internal_control_roles:
        if args.controls is None:
            parser.error("--controls is required for --write-internal-control-roles")
        controls = json.loads(args.controls.read_text(encoding="utf-8"))
        value = build_internal_control_roles(controls)
        result = validate_internal_control_roles(value)
        args.write_internal_control_roles.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps({**result, "output": str(args.write_internal_control_roles)}, indent=2))
        return
    if args.evidence is None:
        parser.error("evidence or --write-operational-contract is required")
    print(
        json.dumps(
            validate_evidence(json.loads(args.evidence.read_text(encoding="utf-8"))), indent=2
        )
    )


if __name__ == "__main__":
    main()
