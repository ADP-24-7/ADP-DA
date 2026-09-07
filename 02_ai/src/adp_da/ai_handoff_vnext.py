from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
AI = ROOT / "02_ai"
DA = ROOT / "03_digital_asset"
V1 = AI / "artifacts" / "ai_handoff_v1"
VNEXT = AI / "artifacts" / "ai_handoff_vNext"
CONTRACTS = AI / "contracts"
DOC = AI / "docs" / "BE_HANDOFF_AI_VNEXT.md"

EXTERNAL_DESTINATIONS = {"MODEL_PROVIDER", "TOOL_PROVIDER", "EXTERNAL_AI_DESTINATION"}
INTERNAL_DESTINATIONS = {"FPG_TRACE", "FPG_POLICY_ENGINE", "INTERNAL_AUDIT_ONLY"}
LOSSY_METHODS = {"MASK", "TOKEN", "HMAC", "REDACT", "FIELD_DROP"}
ALLOWED_METHODS_BY_REQUIREMENT = {
    "EXACT_REQUIRED": {"PASS_THROUGH", "SCHEMA_MAPPING"},
    "MINIMIZATION_ALLOWED": {"MASK", "TOKEN", "HMAC", "OMIT", "REDACT", "PASS_THROUGH"},
    "INTERNAL_ONLY": {"FIELD_DROP"},
    "FORMAT_TRANSFORM_ALLOWED": {"FORMAT_NORMALIZE", "SCHEMA_MAPPING", "PASS_THROUGH"},
}

FIELD_CONTRACTS: list[dict[str, Any]] = [
    {
        "field": "caller",
        "source_phase": "PRE_EXECUTION",
        "source_type": "CALLER_CONTEXT",
        "comparison_sources": [],
        "field_requirement": "EXACT_REQUIRED",
        "transform_intent": "PASS_THROUGH",
        "transform_method": "PASS_THROUGH",
        "destination": ["FPG_POLICY_ENGINE", "FPG_TRACE"],
        "decision": "BLOCK_ON_MISSING_OR_MISMATCH",
        "trace_binding": "TRACE_REQUIRED",
        "classification_basis": ["EVAL-AI-001"],
    },
    {
        "field": "role",
        "source_phase": "PRE_EXECUTION",
        "source_type": "ROLE_BINDING",
        "comparison_sources": ["APPROVED_POLICY_SCOPE", "REQUEST_CONTEXT"],
        "field_requirement": "EXACT_REQUIRED",
        "transform_intent": "PASS_THROUGH",
        "transform_method": "PASS_THROUGH",
        "destination": ["FPG_POLICY_ENGINE", "FPG_TRACE"],
        "decision": "BLOCK_ON_SCOPE_MISMATCH",
        "trace_binding": "TRACE_REQUIRED",
        "classification_basis": ["EVAL-AI-001"],
    },
    {
        "field": "workload",
        "source_phase": "PRE_EXECUTION",
        "source_type": "WORKLOAD_BINDING",
        "comparison_sources": ["APPROVED_POLICY_SCOPE", "REQUEST_CONTEXT"],
        "field_requirement": "EXACT_REQUIRED",
        "transform_intent": "PASS_THROUGH",
        "transform_method": "PASS_THROUGH",
        "destination": ["FPG_POLICY_ENGINE", "FPG_TRACE"],
        "decision": "BLOCK_ON_SCOPE_MISMATCH",
        "trace_binding": "TRACE_REQUIRED",
        "classification_basis": ["EVAL-AI-001"],
    },
    {
        "field": "purpose",
        "source_phase": "PRE_EXECUTION",
        "source_type": "PURPOSE_BINDING",
        "comparison_sources": ["APPROVED_POLICY_SCOPE", "REQUEST_CONTEXT"],
        "field_requirement": "EXACT_REQUIRED",
        "transform_intent": "PASS_THROUGH",
        "transform_method": "PASS_THROUGH",
        "destination": ["FPG_POLICY_ENGINE", "FPG_TRACE"],
        "decision": "BLOCK_ON_SCOPE_MISMATCH",
        "trace_binding": "TRACE_REQUIRED",
        "classification_basis": ["EVAL-AI-001", "EVAL-AI-004"],
    },
    {
        "field": "requested_field_scope",
        "source_phase": "PRE_EXECUTION",
        "source_type": "REQUESTED_FIELD_SCOPE",
        "comparison_sources": ["APPROVED_DATA_SCOPE", "REQUESTED_FIELD_SCOPE"],
        "field_requirement": "EXACT_REQUIRED",
        "transform_intent": "PASS_THROUGH",
        "transform_method": "PASS_THROUGH",
        "destination": ["FPG_POLICY_ENGINE", "FPG_TRACE"],
        "decision": "BLOCK_ON_SCOPE_MISMATCH",
        "trace_binding": "TRACE_REQUIRED",
        "classification_basis": ["EVAL-AI-002", "EVAL-AI-004"],
    },
    {
        "field": "model_identifier",
        "source_phase": "PRE_EXECUTION",
        "source_type": "MODEL_REQUEST",
        "comparison_sources": ["APPROVED_POLICY_SCOPE", "REQUEST_CONTEXT"],
        "field_requirement": "EXACT_REQUIRED",
        "transform_intent": "PASS_THROUGH",
        "transform_method": "PASS_THROUGH",
        "destination": ["MODEL_PROVIDER", "FPG_TRACE"],
        "decision": "BLOCK_ON_UNAUTHORIZED_MODEL",
        "trace_binding": "TRACE_REQUIRED",
        "classification_basis": ["EVAL-AI-001"],
    },
    {
        "field": "tool_action_identifier",
        "source_phase": "PRE_EXECUTION",
        "source_type": "TOOL_OR_ACTION_REQUEST",
        "comparison_sources": ["APPROVED_POLICY_SCOPE", "REQUEST_CONTEXT"],
        "field_requirement": "EXACT_REQUIRED",
        "transform_intent": "PASS_THROUGH",
        "transform_method": "PASS_THROUGH",
        "destination": ["TOOL_PROVIDER", "FPG_TRACE"],
        "decision": "BLOCK_ON_UNAUTHORIZED_TOOL_OR_ACTION",
        "trace_binding": "TRACE_REQUIRED",
        "classification_basis": ["EVAL-AI-001"],
    },
    {
        "field": "model_or_tool_request_payload",
        "source_phase": "PRE_EXECUTION",
        "source_type": "REQUESTED_FIELD",
        "comparison_sources": ["APPROVED_DATA_SCOPE", "REQUESTED_FIELD_SCOPE"],
        "field_requirement": "MINIMIZATION_ALLOWED",
        "transform_intent": "MINIMIZE",
        "transform_method": "CONTRACT_GAP",
        "destination": ["MODEL_PROVIDER", "TOOL_PROVIDER"],
        "decision": "REVIEW_UNTIL_METHOD_SELECTED",
        "trace_binding": "TRACE_REQUIRED",
        "classification_basis": ["EVAL-AI-002", "EVAL-AI-003", "EVAL-AI-004"],
    },
    {
        "field": "internal_policy_evidence",
        "source_phase": "TRACE",
        "source_type": "POLICY_EVALUATION_REFERENCE",
        "comparison_sources": [],
        "field_requirement": "INTERNAL_ONLY",
        "transform_intent": "OMIT",
        "transform_method": "FIELD_DROP",
        "destination": ["FPG_TRACE", "INTERNAL_AUDIT_ONLY"],
        "decision": "BLOCK_ON_MISSING_REFERENCE",
        "trace_binding": "TRACE_REQUIRED",
        "classification_basis": ["EVAL-AI-004"],
    },
    {
        "field": "request_id",
        "source_phase": "TRACE",
        "source_type": "RUNTIME_TRACE_IDENTIFIER",
        "comparison_sources": [],
        "field_requirement": "EXACT_REQUIRED",
        "transform_intent": "PASS_THROUGH",
        "transform_method": "PASS_THROUGH",
        "destination": ["FPG_TRACE", "INTERNAL_AUDIT_ONLY"],
        "decision": "BLOCK_ON_MISSING_REFERENCE",
        "trace_binding": "TRACE_REQUIRED",
        "classification_basis": ["EVAL-AI-001"],
    },
    {
        "field": "model_output",
        "source_phase": "POST_EXECUTION",
        "source_type": "AI_RESPONSE",
        "comparison_sources": [],
        "field_requirement": "FORMAT_TRANSFORM_ALLOWED",
        "transform_intent": "CANONICALIZE",
        "transform_method": "FORMAT_NORMALIZE",
        "destination": ["FPG_TRACE", "INTERNAL_AUDIT_ONLY"],
        "decision": "REVIEW_IF_RESPONSE_SCHEMA_UNRESOLVED",
        "trace_binding": "TRACE_REQUIRED",
        "classification_basis": ["EVAL-AI-002", "EVAL-AI-004"],
    },
    {
        "field": "response_metadata",
        "source_phase": "POST_EXECUTION",
        "source_type": "AI_RESPONSE_METADATA",
        "comparison_sources": [],
        "field_requirement": "FORMAT_TRANSFORM_ALLOWED",
        "transform_intent": "MAP_SCHEMA",
        "transform_method": "SCHEMA_MAPPING",
        "destination": ["FPG_TRACE", "INTERNAL_AUDIT_ONLY"],
        "decision": "REVIEW_IF_RESPONSE_SCHEMA_UNRESOLVED",
        "trace_binding": "TRACE_REQUIRED",
        "classification_basis": ["EVAL-AI-004"],
    },
]


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(payload: dict[str, Any]) -> dict[str, str]:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return {"algorithm": "sha256", "value": hashlib.sha256(encoded).hexdigest()}


def build_runtime_contract() -> dict[str, Any]:
    return {
        "schema_version": "vNext",
        "artifact_id": "RTC-AI-CUSTOMER-SUPPORT-VNEXT",
        "artifact_version": "vNext",
        "domain": "AI",
        "common_contract_fields": [
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
        ],
        "decision_semantics": {
            "PASS": (
                "Approved/requested binding, field scope, transform, destination, "
                "and trace requirements are satisfied."
            ),
            "BLOCK": "A clear policy mismatch or forbidden externalization exists.",
            "REVIEW": "A required method, threshold, schema, or mapping remains unresolved.",
        },
        "transform_semantics": {
            "transform_intent": [
                "PASS_THROUGH",
                "CANONICALIZE",
                "MINIMIZE",
                "PSEUDONYMIZE",
                "OMIT",
                "MAP_SCHEMA",
            ],
            "transform_method": [
                "PASS_THROUGH",
                "MASK",
                "HMAC",
                "TOKEN",
                "REDACT",
                "FORMAT_NORMALIZE",
                "FIELD_DROP",
                "SCHEMA_MAPPING",
                "CONTRACT_GAP",
            ],
        },
        "fields": FIELD_CONTRACTS,
        "contract_gap": [
            "runtime enum",
            "model provider schema",
            "tool execution schema",
            "AI response schema",
            "audit event schema",
        ],
        "analyst_decision_required": [
            "final field-level MASK/HMAC/TOKEN selection",
            "utility threshold",
            "model quality threshold",
            "latency threshold",
            "failure tolerance",
        ],
    }


def build_policy_evaluation(runtime_contract: dict[str, Any]) -> dict[str, Any]:
    v1 = read_json(V1 / "policy_evaluations" / "PE-AI-CUSTOMER-SUPPORT-001.json")
    return {
        **v1,
        "artifact_id": "PE-AI-CUSTOMER-SUPPORT-VNEXT",
        "artifact_version": "vNext",
        "policy_action": "candidate_handoff",
        "applicability": {
            "status": "candidate",
            "scope": (
                "AI customer support vNext runtime contract handoff. "
                "Does not promote a Runtime Policy."
            ),
            "limitations": [
                "BE-owned workload_id remains UNMAPPED.",
                "BE-owned purpose remains UNMAPPED.",
                "BE-owned runtime_data_class remains UNMAPPED.",
                "Final field-level Transform remains ANALYST_DECISION_REQUIRED.",
                (
                    "Final utility, latency, model quality, and failure tolerance "
                    "thresholds remain ANALYST_DECISION_REQUIRED."
                ),
            ],
        },
        "runtime_binding": {
            "mapping_status": "unmapped",
            "runtime_data_class": "UNMAPPED",
            "workload_id": "UNMAPPED",
            "purpose": "UNMAPPED",
            "binding_ref": "WPB-AI-CUSTOMER-SUPPORT-VNEXT",
        },
        "digest": digest(runtime_contract),
    }


def build_binding() -> dict[str, Any]:
    return {
        "schema_version": "v1",
        "binding_version": "vNext",
        "bindings": [
            {
                "workload_id": "UNMAPPED",
                "purpose": "UNMAPPED",
                "processing_context": "AI_USE",
                "runtime_data_class": "UNMAPPED",
                "binding_status": "unresolved",
                "notes": (
                    "EVAL-AI-001 supports Role + Purpose + Action as binding basis; "
                    "BE enum values remain CONTRACT_GAP."
                ),
            }
        ],
    }


def build_crosswalk() -> dict[str, Any]:
    v1 = read_json(V1 / "crosswalks" / "RDC-AI-CUSTOMER-SUPPORT-001.json")
    return {**v1, "crosswalk_version": "vNext"}


def validate_runtime_contract(contract: dict[str, Any]) -> dict[str, Any]:
    assertions: list[dict[str, Any]] = []

    def add(
        assertion: str,
        passed: bool,
        rule: str,
        *,
        field: str | None = None,
        destination: str | None = None,
        detail: str = "",
    ) -> None:
        assertions.append(
            {
                "assertion": assertion,
                "status": "PASS" if passed else "FAIL",
                "field": field,
                "destination": destination,
                "rule": rule,
                "detail": detail,
            }
        )

    for row in contract["fields"]:
        field = row["field"]
        requirement = row["field_requirement"]
        method = row["transform_method"]
        destinations = set(row["destination"])
        external_destinations = destinations & EXTERNAL_DESTINATIONS

        add(
            "exact_required_transform_whitelist",
            requirement != "EXACT_REQUIRED" or method not in LOSSY_METHODS,
            "EXACT_REQUIRED_NO_LOSSY_TRANSFORM",
            field=field,
            detail=f"method={method}",
        )
        add(
            "internal_only_external_destination_blocked",
            requirement != "INTERNAL_ONLY" or not external_destinations,
            "INTERNAL_ONLY_NO_EXTERNAL_DESTINATION",
            field=field,
            detail=f"external_destinations={sorted(external_destinations)}",
        )
        add(
            "transform_method_allowed_for_requirement",
            method == "CONTRACT_GAP" or method in ALLOWED_METHODS_BY_REQUIREMENT[requirement],
            "TRANSFORM_METHOD_REQUIREMENT_COMPATIBILITY",
            field=field,
            detail=f"method={method} requirement={requirement}",
        )
        add(
            "minimization_has_explicit_method_or_gap",
            requirement != "MINIMIZATION_ALLOWED"
            or method in ALLOWED_METHODS_BY_REQUIREMENT[requirement]
            or method == "CONTRACT_GAP",
            "MINIMIZATION_REQUIRES_EXPLICIT_METHOD_OR_CONTRACT_GAP",
            field=field,
            detail=f"method={method}",
        )
        add(
            "external_response_not_pre_execution_request",
            row["source_type"] not in {"AI_RESPONSE", "AI_RESPONSE_METADATA"}
            or row["source_phase"] == "POST_EXECUTION",
            "SOURCE_PHASE_RESPONSE_SEPARATION",
            field=field,
            detail=f"source_phase={row['source_phase']} source_type={row['source_type']}",
        )
        add(
            "trace_reference_present",
            row["trace_binding"] == "TRACE_REQUIRED",
            "TRACE_REFERENCE_REQUIRED",
            field=field,
        )
        add(
            "classification_basis_present",
            bool(row["classification_basis"]),
            "VALIDATION_ARTIFACT_REFERENCE_REQUIRED",
            field=field,
            detail=f"basis={row['classification_basis']}",
        )

    failures = [assertion for assertion in assertions if assertion["status"] == "FAIL"]
    return {
        "schema_version": "vNext",
        "artifact_id": "VAL-AI-CUSTOMER-SUPPORT-VNEXT",
        "artifact_version": "vNext",
        "status": "PASS" if not failures else "FAIL",
        "validation_errors": failures,
        "assertions": assertions,
    }


def evaluate_runtime_decision(
    *,
    destination_authorized: bool,
    model_authorized: bool,
    tool_authorized: bool,
    binding_match: bool,
    field_scope_match: bool,
    exact_match: bool,
    forbidden_externalization: bool,
    policy_evaluation_ref_present: bool,
    trace_ref_present: bool,
    transform_resolved: bool,
    thresholds_resolved: bool,
) -> dict[str, str]:
    if (
        not destination_authorized
        or not model_authorized
        or not tool_authorized
        or not binding_match
        or not field_scope_match
        or not exact_match
        or forbidden_externalization
        or not policy_evaluation_ref_present
        or not trace_ref_present
    ):
        return {"decision": "BLOCK", "reason": "POLICY_MISMATCH_OR_REQUIRED_REFERENCE_MISSING"}
    if not transform_resolved or not thresholds_resolved:
        return {"decision": "REVIEW", "reason": "UNRESOLVED_METHOD_OR_THRESHOLD"}
    return {"decision": "PASS", "reason": "RUNTIME_CONTRACT_SATISFIED"}


def runtime_contract_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://github.com/ADP-24-7/ADP-DA/contracts/ai_runtime_contract_vnext.schema.json",
        "title": "AI Runtime Contract vNext",
        "type": "object",
        "required": [
            "schema_version",
            "artifact_id",
            "artifact_version",
            "domain",
            "common_contract_fields",
            "decision_semantics",
            "transform_semantics",
            "fields",
            "contract_gap",
            "analyst_decision_required",
        ],
        "properties": {
            "schema_version": {"type": "string", "const": "vNext"},
            "artifact_id": {"type": "string"},
            "artifact_version": {"type": "string"},
            "domain": {"type": "string", "const": "AI"},
            "common_contract_fields": {"type": "array", "items": {"type": "string"}},
            "decision_semantics": {"type": "object"},
            "transform_semantics": {"type": "object"},
            "fields": {"type": "array", "items": {"type": "object"}},
            "contract_gap": {"type": "array", "items": {"type": "string"}},
            "analyst_decision_required": {"type": "array", "items": {"type": "string"}},
        },
        "additionalProperties": False,
    }


def validation_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://github.com/ADP-24-7/ADP-DA/contracts/ai_runtime_validation_vnext.schema.json",
        "title": "AI Runtime Validation vNext",
        "type": "object",
        "required": [
            "schema_version",
            "artifact_id",
            "artifact_version",
            "status",
            "validation_errors",
            "assertions",
        ],
        "properties": {
            "schema_version": {"type": "string", "const": "vNext"},
            "artifact_id": {"type": "string"},
            "artifact_version": {"type": "string"},
            "status": {"type": "string"},
            "validation_errors": {"type": "array", "items": {"type": "object"}},
            "assertions": {"type": "array", "items": {"type": "object"}},
        },
        "additionalProperties": False,
    }


def write_docs(contract: dict[str, Any]) -> None:
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text(
        "\n".join(
            [
                "# BE Handoff AI vNext",
                "",
                "## A. AI에서 확정된 것",
                "",
                (
                    "- Runtime responsibility: FPG validates approved/requested AI handoff "
                    "readiness; it does not define final business approval or legal judgment."
                ),
                (
                    "- Role/workload/purpose binding: EVAL-AI-001 supports Role + Purpose "
                    "+ Action as the binding basis; BE enum values remain CONTRACT_GAP."
                ),
                (
                    "- Field requirement: EXACT_REQUIRED, MINIMIZATION_ALLOWED, "
                    "INTERNAL_ONLY, FORMAT_TRANSFORM_ALLOWED are mapped."
                ),
                (
                    "- Transform semantics: intent and method are separate; CONTRACT_GAP "
                    "is used where final method evidence is insufficient."
                ),
                (
                    "- Destination control: model/tool/external destinations are checked "
                    "separately from FPG trace and audit destinations."
                ),
                (
                    "- PASS/BLOCK/REVIEW: PASS means contract satisfied, BLOCK means clear "
                    "mismatch, REVIEW means unresolved method, threshold, schema, or mapping."
                ),
                (
                    "- Trace binding: request, policy evaluation, validation artifact, and "
                    "response references are required."
                ),
                (
                    "- Validation rule: failures are machine-readable with field, "
                    "destination, rule, and detail."
                ),
                "",
                "## B. BE가 구현할 것",
                "",
                "- Runtime contract loader",
                "- Policy binding validator",
                "- Transform executor",
                "- Destination payload builder",
                "- Response binding",
                "- Trace writer",
                "- Decision engine",
                "",
                "## C. CONTRACT_GAP",
                "",
                "\n".join(f"- {item}" for item in contract["contract_gap"]),
                "",
                "## D. ANALYST_DECISION_REQUIRED",
                "",
                "\n".join(f"- {item}" for item in contract["analyst_decision_required"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def write_gap_files(contract: dict[str, Any]) -> None:
    (VNEXT / "CONTRACT_GAP.md").write_text(
        "# AI Handoff vNext Contract Gap\n\n"
        + "\n".join(f"- {item}" for item in contract["contract_gap"])
        + "\n",
        encoding="utf-8",
    )
    (VNEXT / "ANALYST_DECISION_REQUIRED.md").write_text(
        "# AI Handoff vNext Analyst Decision Required\n\n"
        + "\n".join(f"- {item}" for item in contract["analyst_decision_required"])
        + "\n",
        encoding="utf-8",
    )


def copy_evaluations() -> None:
    target = VNEXT / "evaluations"
    target.mkdir(parents=True, exist_ok=True)
    for path in sorted((V1 / "evaluations").glob("*.json")):
        shutil.copyfile(path, target / path.name)


def write_artifacts() -> None:
    contract = build_runtime_contract()
    validation = validate_runtime_contract(contract)
    write_json(CONTRACTS / "ai_runtime_contract_vnext.schema.json", runtime_contract_schema())
    write_json(CONTRACTS / "ai_runtime_validation_vnext.schema.json", validation_schema())
    copy_evaluations()
    write_json(VNEXT / "runtime_contract" / "RTC-AI-CUSTOMER-SUPPORT-VNEXT.json", contract)
    write_json(VNEXT / "validation" / "VAL-AI-CUSTOMER-SUPPORT-VNEXT.json", validation)
    write_json(
        VNEXT / "policy_evaluations" / "PE-AI-CUSTOMER-SUPPORT-VNEXT.json",
        build_policy_evaluation(contract),
    )
    write_json(VNEXT / "bindings" / "WPB-AI-CUSTOMER-SUPPORT-VNEXT.json", build_binding())
    write_json(VNEXT / "crosswalks" / "RDC-AI-CUSTOMER-SUPPORT-VNEXT.json", build_crosswalk())
    write_gap_files(contract)
    write_docs(contract)


if __name__ == "__main__":
    write_artifacts()
