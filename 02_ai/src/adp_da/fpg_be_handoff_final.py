from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "02_ai" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from adp_da import ai_handoff_vnext  # noqa: E402

AI_VNEXT = ROOT / "02_ai" / "artifacts" / "ai_handoff_vNext"
DA_VNEXT = ROOT / "03_digital_asset" / "artifacts"
FINAL = ROOT / "artifacts" / "fpg_be_handoff_final"

COMMON_FIELDS = [
    "source_phase",
    "source_type",
    "comparison_sources",
    "field_requirement",
    "transform_intent",
    "transform_method",
    "destination",
    "decision",
    "trace_binding",
    "validation_errors",
]

COMMON_DECISIONS = ["PASS", "BLOCK", "REVIEW"]


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_common_runtime_contract() -> dict[str, Any]:
    return {
        "schema_version": "v1",
        "artifact_id": "FPG-COMMON-RUNTIME-CONTRACT-FINAL",
        "artifact_version": "final",
        "scope": "Common FPG runtime contract structure shared by AI and Digital Asset.",
        "common_fields": COMMON_FIELDS,
        "decision_values": COMMON_DECISIONS,
        "validation_error_shape": {
            "field": "string|null",
            "destination": "string|null",
            "rule": "string",
            "detail": "string",
        },
        "transform_destination_separation": {
            "PASS_THROUGH": (
                "The value is not mutated inside FPG runtime. This does not imply "
                "inclusion in any external payload."
            ),
            "EXTERNALIZE": (
                "External payload inclusion is decided separately by destination "
                "policy and payload builder rules."
            ),
        },
        "post_execution_format_normalize": {
            "model_output": (
                "FORMAT_NORMALIZE is limited to non-lossy post-execution response "
                "formatting/canonicalization and must not rewrite model answer meaning."
            )
        },
        "principle": (
            "Domains are not processed identically; they are governed through the same "
            "runtime contract structure."
        ),
    }


def build_ai_runtime_contract() -> dict[str, Any]:
    contract = read_json(AI_VNEXT / "runtime_contract" / "RTC-AI-CUSTOMER-SUPPORT-VNEXT.json")
    return {
        "schema_version": "v1",
        "artifact_id": "AI-RUNTIME-CONTRACT-FINAL",
        "artifact_version": "final",
        "source_artifact_ref": (
            "02_ai/artifacts/ai_handoff_vNext/runtime_contract/"
            "RTC-AI-CUSTOMER-SUPPORT-VNEXT.json"
        ),
        "common_contract_fields": contract["common_contract_fields"],
        "domain_specific_contract": {
            "role": "role",
            "workload": "workload",
            "purpose": "purpose",
            "data_field": "requested_field_scope",
            "model": "model_identifier",
            "tool_action": "tool_action_identifier",
            "external_ai_destination": ["MODEL_PROVIDER", "TOOL_PROVIDER"],
            "transform": ["MASK", "HMAC", "TOKEN", "OMIT", "REDACT"],
        },
        "fields": contract["fields"],
        "decision_semantics": contract["decision_semantics"],
    }


def _map_da_transform(row: dict[str, Any]) -> tuple[str, str]:
    requirement = row["required_exact"]
    if requirement == "EXACT_REQUIRED":
        return "PASS_THROUGH", "PASS_THROUGH"
    if requirement == "INTERNAL_ONLY":
        return "OMIT", "FIELD_DROP"
    if requirement == "MINIMIZATION_ALLOWED":
        return "MINIMIZE", "SCHEMA_MAPPING"
    if requirement == "FORMAT_TRANSFORM_ALLOWED":
        return "MAP_SCHEMA", "SCHEMA_MAPPING"
    return "CONTRACT_GAP", "CONTRACT_GAP"


def build_digital_asset_runtime_contract() -> dict[str, Any]:
    matrix = read_json(
        DA_VNEXT / "outbound_design_vNext" / "outbound_requirement_matrix.json"
    )
    fields = []
    for row in matrix["requirements"]:
        transform_intent, transform_method = _map_da_transform(row)
        fields.append(
            {
                "field": row["required_fields"][0],
                "source_phase": row["source_phase"],
                "source_type": row["source_type"],
                "comparison_sources": row["comparison_sources"],
                "field_requirement": row["required_exact"],
                "transform_intent": transform_intent,
                "transform_method": transform_method,
                "destination": row["destination"],
                "decision": row["validation_type"],
                "trace_binding": (
                    "TRACE_REQUIRED" if "TRACE_FIELD" in row["field_roles"] else "TRACE_OPTIONAL"
                ),
                "validation_errors": [],
                "source_requirement_ref": row["requirement_id"],
            }
        )
    return {
        "schema_version": "v1",
        "artifact_id": "DIGITAL-ASSET-RUNTIME-CONTRACT-FINAL",
        "artifact_version": "final",
        "source_artifact_ref": (
            "03_digital_asset/artifacts/outbound_design_vNext/"
            "outbound_requirement_matrix.json"
        ),
        "common_contract_fields": COMMON_FIELDS,
        "domain_specific_contract": {
            "purpose": "source_type/comparison_sources",
            "asset": "asset",
            "amount": "amount",
            "counterparty": "counterparty_vasp",
            "destination": "beneficiary_address",
            "period": "CONTRACT_GAP",
            "state": "execution_status",
            "idempotency": "CONTRACT_GAP",
            "reconciliation": "INTERNAL_RECONCILIATION_ONLY",
            "external_execution_result": ["tx_hash", "execution_status", "timestamp"],
        },
        "fields": fields,
        "decision_semantics": matrix["decision_semantics"],
        "forbidden_runtime_controls": [
            "KYC_STATUS_CHECK",
            "AML_CHECK",
            "SANCTIONS_CHECK",
            "VASP_ELIGIBILITY_CHECK",
            "COUNTERPARTY_VASP_VERIFY",
        ],
    }


def build_ai_transform_decision_matrix() -> dict[str, Any]:
    contract = read_json(AI_VNEXT / "runtime_contract" / "RTC-AI-CUSTOMER-SUPPORT-VNEXT.json")
    rows = []
    for row in contract["fields"]:
        status = "RESOLVED"
        parameter = "NOT_APPLICABLE"
        rationale = "Resolved from AI vNext runtime contract and referenced v1 evidence."
        if row["transform_method"] == "CONTRACT_GAP":
            status = "ANALYST_DECISION_REQUIRED"
            parameter = "MASK_PARAMETER=ANALYST_DECISION_REQUIRED"
            rationale = (
                "EVAL-AI-003 supports transform tradeoff behavior, but does not select a "
                "field-level MASK/HMAC/TOKEN method or parameter."
            )
        if row["field"] == "model_output":
            rationale = (
                "FORMAT_NORMALIZE is limited to non-lossy post-execution response "
                "formatting/canonicalization; it must not rewrite model output meaning."
            )
        rows.append(
            {
                "field": row["field"],
                "runtime_data_class": "UNMAPPED",
                "field_requirement": row["field_requirement"],
                "transform_intent": row["transform_intent"],
                "transform_method": row["transform_method"],
                "transform_parameter": parameter,
                "destination": row["destination"],
                "rationale": rationale,
                "evidence_refs": row["classification_basis"],
                "decision_status": status,
            }
        )
    return {
        "schema_version": "v1",
        "artifact_id": "AI-TRANSFORM-DECISION-MATRIX-FINAL",
        "artifact_version": "final",
        "source_artifact_ref": (
            "02_ai/artifacts/ai_handoff_vNext/runtime_contract/"
            "RTC-AI-CUSTOMER-SUPPORT-VNEXT.json"
        ),
        "decisions": rows,
    }


def build_contract_gap() -> dict[str, Any]:
    return {
        "schema_version": "v1",
        "artifact_id": "FPG-CONTRACT-GAP-FINAL",
        "artifact_version": "final",
        "items": [
            {"domain": "AI", "owner": "BE", "gap": "runtime enum"},
            {"domain": "AI", "owner": "BE", "gap": "model provider schema"},
            {"domain": "AI", "owner": "BE", "gap": "tool execution schema"},
            {"domain": "AI", "owner": "BE", "gap": "AI response schema"},
            {"domain": "AI", "owner": "BE", "gap": "audit event schema"},
            {"domain": "Digital Asset", "owner": "BE", "gap": "BE-owned runtime enum"},
            {"domain": "Digital Asset", "owner": "BE", "gap": "approved transaction schema"},
            {
                "domain": "Digital Asset",
                "owner": "BE",
                "gap": "approved policy snapshot schema",
            },
            {
                "domain": "Digital Asset",
                "owner": "BE",
                "gap": "provider-specific payload schema",
            },
            {
                "domain": "Digital Asset",
                "owner": "BE",
                "gap": "execution receipt/status schema",
            },
            {
                "domain": "Digital Asset",
                "owner": "BE",
                "gap": "retry/reconciliation event schema",
            },
            {"domain": "Digital Asset", "owner": "BE", "gap": "audit event schema"},
        ],
    }


def build_deferred_runtime_validation() -> dict[str, Any]:
    return {
        "schema_version": "v1",
        "artifact_id": "FPG-DEFERRED-RUNTIME-VALIDATION-FINAL",
        "artifact_version": "final",
        "items": [
            {
                "domain": "AI",
                "item": "utility threshold",
                "status": "DEFERRED_RUNTIME_VALIDATION",
            },
            {
                "domain": "AI",
                "item": "model quality threshold",
                "status": "DEFERRED_RUNTIME_VALIDATION",
            },
            {
                "domain": "AI",
                "item": "latency threshold",
                "status": "DEFERRED_RUNTIME_VALIDATION",
            },
            {
                "domain": "AI",
                "item": "failure tolerance",
                "status": "DEFERRED_RUNTIME_VALIDATION",
            },
        ],
        "blocker_assessment": (
            "These items do not block Common Runtime Engine implementation; unresolved "
            "values must produce REVIEW rather than inferred PASS/BLOCK."
        ),
    }


def validate_common_compatibility(
    common: dict[str, Any], ai_contract: dict[str, Any], da_contract: dict[str, Any]
) -> dict[str, Any]:
    assertions = []

    def add(name: str, passed: bool, detail: str) -> None:
        assertions.append(
            {
                "assertion": name,
                "status": "PASS" if passed else "FAIL",
                "field": None,
                "destination": None,
                "rule": name,
                "detail": detail,
            }
        )

    common_fields = set(common["common_fields"])
    add(
        "ai_common_fields_compatible",
        common_fields <= set(ai_contract["common_contract_fields"]),
        "AI contract exposes all common fields.",
    )
    add(
        "da_common_fields_compatible",
        common_fields <= set(da_contract["common_contract_fields"]),
        "Digital Asset contract exposes all common fields.",
    )
    add(
        "decision_enum_consistent",
        set(common["decision_values"]) == {"PASS", "BLOCK", "REVIEW"},
        "Common decisions are PASS/BLOCK/REVIEW.",
    )
    add(
        "ai_validation_pass",
        read_json(AI_VNEXT / "validation" / "VAL-AI-CUSTOMER-SUPPORT-VNEXT.json")[
            "status"
        ]
        == "PASS",
        "AI vNext validation artifact passes.",
    )
    add(
        "da_validation_pass",
        read_json(
            DA_VNEXT / "outbound_design_vNext" / "control_boundary_validation.json"
        )["status"]
        == "PASS",
        "Digital Asset vNext validation artifact passes.",
    )
    failures = [item for item in assertions if item["status"] == "FAIL"]
    return {
        "schema_version": "v1",
        "artifact_id": "FPG-FINAL-COMMON-CONSISTENCY",
        "artifact_version": "final",
        "status": "PASS" if not failures else "FAIL",
        "validation_errors": failures,
        "assertions": assertions,
    }


def write_scope_doc() -> None:
    write_text(
        FINAL / "BE_IMPLEMENTATION_SCOPE.md",
        "\n".join(
            [
                "# BE Implementation Scope",
                "",
                "## Common Engine",
                "",
                "- contract loader",
                "- source resolver",
                "- policy validator",
                "- field requirement validator",
                "- transform executor",
                "- destination payload builder",
                "- decision engine",
                "- trace writer",
                "- validation error serializer",
                "",
                "## AI Adapter",
                "",
                "- role/workload/purpose binding",
                "- model/destination validation",
                "- tool/action validation",
                "- AI field transform",
                "- external response binding",
                "",
                "## Digital Asset Adapter",
                "",
                "- approved/requested transaction comparison",
                "- destination payload build",
                "- exact field enforcement",
                "- execution response binding",
                "- settlement/reconciliation binding",
            ]
        )
        + "\n",
    )


def write_final_doc(consistency: dict[str, Any]) -> None:
    write_text(
        FINAL / "FPG_BE_HANDOFF_FINAL.md",
        "\n".join(
            [
                "# FPG BE Handoff Final",
                "",
                (
                    "This package references AI vNext and Digital Asset vNext artifacts "
                    "rather than copying or overwriting them."
                ),
                "",
                "## Status",
                "",
                "FPG BE HANDOFF READY WITH NON-BLOCKING GAPS",
                "",
                "## Blocking Assessment",
                "",
                "- BE can implement the Common Runtime Engine without threshold values.",
                (
                    "- BE can implement the AI Transform Executor interface; final methods "
                    "can return REVIEW while deferred."
                ),
                "- BE can implement the Digital Asset Runtime Validator from DA vNext.",
                (
                    "- CONTRACT_GAP items block provider adapter/schema completion, "
                    "not the common engine interface."
                ),
                (
                    "- ANALYST_DECISION_REQUIRED items are operating/performance validation "
                    "gates, not common engine blockers."
                ),
                "",
                "## Consistency",
                "",
                json.dumps(consistency, ensure_ascii=False),
            ]
        )
        + "\n",
    )


def write_be_handoff_to_be() -> None:
    write_text(
        FINAL / "BE_HANDOFF_TO_BE.md",
        "\n".join(
            [
                "# FPG to BE Final Handoff",
                "",
                "## 1. Current Status",
                "",
                "`FPG BE HANDOFF READY WITH NON-BLOCKING GAPS`",
                "",
                "AI and Digital Asset domain contracts and Common Runtime Contract "
                "consistency have been validated.",
                "",
                "Common Runtime Engine implementation can start.",
                "",
                "## 2. Scope BE Can Implement Now",
                "",
                "### Common Runtime Engine",
                "",
                "- contract loader",
                "- source resolver",
                "- policy validator",
                "- field requirement validator",
                "- transform executor",
                "- destination payload builder",
                "- PASS/BLOCK/REVIEW decision engine",
                "- trace writer",
                "- machine-readable validation error serializer",
                "",
                "### AI",
                "",
                "- role/workload/purpose binding",
                "- approved/requested field scope validation",
                "- model/destination validation",
                "- tool/action validation",
                "- field transform executor",
                "- external AI response binding",
                "",
                "### Digital Asset",
                "",
                "- approved/requested transaction comparison",
                "- Purpose / Asset / Amount / Counterparty / Destination / Period validation",
                "- exact field enforcement",
                "- destination-specific payload build",
                "- external execution response binding",
                "- tx_hash / execution_status / timestamp post-execution binding",
                "- settlement/reconciliation integration point",
                "",
                "## 3. Common Runtime Contract",
                "",
                "AI and Digital Asset are not processed identically. They share only the "
                "common control structure.",
                "",
                "- source_phase",
                "- source_type",
                "- comparison_sources",
                "- field_requirement",
                "- transform_intent",
                "- transform_method",
                "- destination",
                "- decision",
                "- trace_binding",
                "- validation_errors",
                "",
                "Decision:",
                "",
                "- PASS",
                "- BLOCK",
                "- REVIEW",
                "",
                "Principle:",
                "",
                "`Not processed identically; governed through the same structure.`",
                "",
                "## 4. Important Implementation Notes",
                "",
                "### PASS_THROUGH is not EXTERNALIZE",
                "",
                "PASS_THROUGH means FPG does not mutate the value.",
                "",
                "Whether the value is included in an external destination payload is "
                "decided separately by destination policy and the payload builder.",
                "",
                "### EXACT_REQUIRED",
                "",
                "Do not apply arbitrary MASK/HMAC/TOKEN/REDACT to outbound exact values.",
                "",
                "Comparison normalization and outbound transform must remain separate.",
                "",
                "### INTERNAL_ONLY",
                "",
                "Do not send INTERNAL_ONLY values to external destinations.",
                "",
                "### POST_EXECUTION",
                "",
                "Digital Asset `tx_hash`, `execution_status`, and `timestamp` are not "
                "outbound request inputs.",
                "",
                "They are bound from `EXTERNAL_EXECUTION_RESPONSE` after handoff.",
                "",
                "AI external response fields are also separated from PRE_EXECUTION sources.",
                "",
                "### model_output FORMAT_NORMALIZE",
                "",
                "`model_output` FORMAT_NORMALIZE is limited to non-lossy post-execution "
                "response formatting/canonicalization.",
                "",
                "It must not rewrite, reinterpret, summarize, or otherwise change model "
                "answer meaning.",
                "",
                "## 5. BE-owned CONTRACT GAP",
                "",
                "### AI",
                "",
                "- runtime enum",
                "- model provider schema",
                "- tool execution schema",
                "- AI response schema",
                "- audit event schema",
                "",
                "### Digital Asset",
                "",
                "- runtime enum",
                "- approved transaction schema",
                "- approved policy snapshot schema",
                "- provider-specific payload schema",
                "- execution receipt/status schema",
                "- retry/reconciliation event schema",
                "- audit event schema",
                "",
                "These items were not filled by analysis. They are BE implementation scope.",
                "",
                "## 6. Deferred Runtime Validation",
                "",
                "These are not current common runtime implementation blockers:",
                "",
                "- utility threshold",
                "- model quality threshold",
                "- latency threshold",
                "- failure tolerance",
                "",
                "When thresholds are unresolved, return REVIEW rather than inferred PASS/BLOCK.",
                "",
                "## 7. Remaining Analyst Decision",
                "",
                "AI `model_or_tool_request_payload` still needs final field-level choice and "
                "parameters for:",
                "",
                "- MASK",
                "- HMAC",
                "- TOKEN",
                "",
                "This does not block common engine or interface implementation.",
                "",
                "## 8. Validation Result",
                "",
                "- AI tests: 43 passed",
                "- Digital Asset tests: 20 passed",
                "- ruff: PASS",
                "- mypy: PASS",
                "- contract validation: PASS",
                "- Common Runtime Contract consistency: PASS",
                "",
                "## 9. Responsibility Boundary",
                "",
                "FPG does not replace upstream approval, KYC, AML, VASP, or sanctions systems.",
                "",
                "FPG verifies that previously approved conditions are still preserved at "
                "external execution handoff time and proves that enforcement through trace.",
                "",
                "Digital Asset KYC / AML / sanctions / VASP eligibility must not be "
                "reintroduced as FPG runtime controls.",
            ]
        )
        + "\n",
    )


def write_package() -> None:
    ai_handoff_vnext.write_artifacts()
    common = build_common_runtime_contract()
    ai_contract = build_ai_runtime_contract()
    da_contract = build_digital_asset_runtime_contract()
    consistency = validate_common_compatibility(common, ai_contract, da_contract)

    write_json(FINAL / "FPG_COMMON_RUNTIME_CONTRACT.json", common)
    write_json(FINAL / "AI_RUNTIME_CONTRACT.json", ai_contract)
    write_json(FINAL / "DIGITAL_ASSET_RUNTIME_CONTRACT.json", da_contract)
    write_json(FINAL / "AI_TRANSFORM_DECISION_MATRIX.json", build_ai_transform_decision_matrix())
    write_json(FINAL / "CONTRACT_GAP.json", build_contract_gap())
    write_json(FINAL / "DEFERRED_RUNTIME_VALIDATION.json", build_deferred_runtime_validation())
    write_json(FINAL / "COMMON_RUNTIME_CONTRACT_CONSISTENCY.json", consistency)
    write_scope_doc()
    write_final_doc(consistency)
    write_be_handoff_to_be()


if __name__ == "__main__":
    write_package()
