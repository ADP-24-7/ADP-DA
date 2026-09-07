# ruff: noqa: E501, E701, E702, I001

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import jsonschema
import nbformat as nbf


ROOT = Path(__file__).resolve().parents[2]
DA = ROOT / "03_digital_asset"
PROCESSED = DA / "data" / "processed"
CONTRACTS = DA / "contracts"
OUTBOUND_V1 = DA / "artifacts" / "outbound_design_v1"
OUTBOUND_V2 = DA / "artifacts" / "outbound_design_v2"
BE_V3 = DA / "artifacts" / "be_handoff_v3"
DOC = DA / "docs" / "BE_HANDOFF_DIGITAL_ASSET_V3.md"
NOTEBOOK = DA / "notebooks" / "05_fpg_control_boundary_validation.ipynb"

FORBIDDEN_RUNTIME_CONTROLS = {
    "KYC_STATUS_CHECK",
    "AML_CHECK",
    "VASP_ELIGIBILITY_CHECK",
    "COUNTERPARTY_VASP_VERIFY",
    "CUSTOMER_RISK_CHECK",
    "SANCTIONS_CHECK",
}

UPSTREAM_BY_FIELD = {
    "kyc_status": "KYC/AML status must be produced by upstream approval, KYC/AML, or compliance systems. FPG consumes the result as input only.",
    "counterparty_vasp": "Counterparty VASP status or reference must be produced by upstream VASP directory, Travel Rule, or compliance systems. FPG does not determine eligibility.",
    "originator_identity": "Customer identity is upstream/customer-master data. FPG checks presence and maps it to outbound requirement only.",
    "beneficiary_identity": "Beneficiary identity is upstream/customer-master or Travel Rule data. FPG checks presence and maps it to outbound requirement only.",
}

RUNTIME_CONTROL_BY_FIELD = {
    "originator_identity": "REQUIRED_OUTBOUND_FIELD_PRESENCE",
    "beneficiary_identity": "REQUIRED_OUTBOUND_FIELD_PRESENCE",
    "originator_address": "APPROVED_VS_REQUESTED_MATCH",
    "beneficiary_address": "APPROVED_VS_REQUESTED_MATCH",
    "amount": "APPROVED_VS_REQUESTED_MATCH",
    "asset": "APPROVED_VS_REQUESTED_MATCH",
    "counterparty_vasp": "REQUIRED_OUTBOUND_FIELD_PRESENCE",
    "kyc_status": "REQUIRED_OUTBOUND_FIELD_PRESENCE",
    "transaction_id": "TRACE_BINDING",
    "tx_hash": "TRACE_BINDING",
    "execution_status": "TRACE_BINDING",
    "timestamp": "TRACE_BINDING",
}

VALIDATION_BY_CONTROL = {
    "APPROVED_VS_REQUESTED_MATCH": "MATCH_APPROVED_VALUE",
    "REQUIRED_OUTBOUND_FIELD_PRESENCE": "REQUIRED_FIELD_PRESENT",
    "REQUIRED_EXACT_PRESERVATION": "REQUIRED_EXACT_PRESERVED",
    "TRANSFORM_FIELD_SEPARATION": "TRANSFORM_VALID",
    "DESTINATION_SPECIFIC_PAYLOAD": "DESTINATION_MAPPING_VALID",
    "TRACE_BINDING": "TRACE_BINDING_VALID",
}

EXACT_CLASS_BY_FIELD = {
    "amount": "EXACT_REQUIRED",
    "asset": "EXACT_REQUIRED",
    "originator_address": "EXACT_REQUIRED",
    "beneficiary_address": "EXACT_REQUIRED",
    "transaction_id": "EXACT_REQUIRED",
    "tx_hash": "EXACT_REQUIRED",
    "timestamp": "EXACT_REQUIRED",
    "execution_status": "EXACT_REQUIRED",
    "originator_identity": "MINIMIZATION_ALLOWED",
    "beneficiary_identity": "MINIMIZATION_ALLOWED",
    "counterparty_vasp": "FORMAT_TRANSFORM_ALLOWED",
    "kyc_status": "INTERNAL_ONLY",
}

TRANSFORM_BY_EXACT_CLASS = {
    "EXACT_REQUIRED": ["PASS_THROUGH", "FORMAT_NORMALIZE"],
    "FORMAT_TRANSFORM_ALLOWED": ["MAP_TO_EXTERNAL_SCHEMA", "FORMAT_NORMALIZE"],
    "MINIMIZATION_ALLOWED": ["MINIMIZE", "MAP_TO_EXTERNAL_SCHEMA"],
    "INTERNAL_ONLY": ["OMIT"],
}

DESTINATION_BY_FIELD = {
    "amount": ["BLOCKCHAIN_EXECUTION_SYSTEM", "INTERNAL_RECONCILIATION_ONLY"],
    "asset": ["BLOCKCHAIN_EXECUTION_SYSTEM", "TRAVEL_RULE_PROVIDER"],
    "originator_address": ["BLOCKCHAIN_EXECUTION_SYSTEM", "INTERNAL_RECONCILIATION_ONLY"],
    "beneficiary_address": ["BLOCKCHAIN_EXECUTION_SYSTEM", "INTERNAL_RECONCILIATION_ONLY"],
    "originator_identity": ["TRAVEL_RULE_PROVIDER", "EXTERNAL_VASP"],
    "beneficiary_identity": ["TRAVEL_RULE_PROVIDER", "EXTERNAL_VASP"],
    "counterparty_vasp": ["TRAVEL_RULE_PROVIDER", "INTERNAL_AUDIT_ONLY"],
    "kyc_status": ["NOT_EXTERNALIZED", "INTERNAL_AUDIT_ONLY"],
    "transaction_id": ["TRAVEL_RULE_PROVIDER", "INTERNAL_RECONCILIATION_ONLY"],
    "tx_hash": ["INTERNAL_RECONCILIATION_ONLY"],
    "execution_status": ["INTERNAL_RECONCILIATION_ONLY", "INTERNAL_AUDIT_ONLY"],
    "timestamp": ["INTERNAL_RECONCILIATION_ONLY", "INTERNAL_AUDIT_ONLY"],
}

ROLE_BY_FIELD = {
    "amount": ["PRE_APPROVED_VALUE", "REQUEST_VALUE", "OUTBOUND_PAYLOAD_FIELD", "TRACE_FIELD"],
    "asset": ["PRE_APPROVED_VALUE", "REQUEST_VALUE", "OUTBOUND_PAYLOAD_FIELD"],
    "originator_address": ["REQUEST_VALUE", "OUTBOUND_PAYLOAD_FIELD", "TRACE_FIELD"],
    "beneficiary_address": ["REQUEST_VALUE", "DESTINATION_ATTRIBUTE", "OUTBOUND_PAYLOAD_FIELD", "TRACE_FIELD"],
    "originator_identity": ["REGULATORY_ATTRIBUTE", "OUTBOUND_PAYLOAD_FIELD"],
    "beneficiary_identity": ["REGULATORY_ATTRIBUTE", "OUTBOUND_PAYLOAD_FIELD"],
    "counterparty_vasp": ["REGULATORY_ATTRIBUTE", "DESTINATION_ATTRIBUTE"],
    "kyc_status": ["REGULATORY_ATTRIBUTE", "TRANSFORM_INPUT"],
    "transaction_id": ["TRACE_FIELD", "OUTBOUND_PAYLOAD_FIELD"],
    "tx_hash": ["TRACE_FIELD", "EXECUTION_RESULT_FIELD"],
    "execution_status": ["EXECUTION_RESULT_FIELD", "TRACE_FIELD"],
    "timestamp": ["TRACE_FIELD", "EXECUTION_RESULT_FIELD"],
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as fp:
        return list(csv.DictReader(fp))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def digest(payload: Any) -> dict[str, str]:
    value = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return {"algorithm": "sha256", "value": hashlib.sha256(value).hexdigest()}


def normalize_source(source: str, field: str) -> tuple[str, str, str]:
    if field in UPSTREAM_BY_FIELD:
        return "UPSTREAM_PRODUCED_DATA", "REQUIRED_OUTBOUND_FIELD_PRESENCE", UPSTREAM_BY_FIELD[field]
    return "FPG_ENFORCEMENT_INPUT", RUNTIME_CONTROL_BY_FIELD[field], "FPG validates outbound handoff readiness only."


def build_matrix_v2() -> dict[str, Any]:
    v1 = read_json(OUTBOUND_V1 / "outbound_requirement_matrix.json")
    requirements = []
    for item in v1["requirements"]:
        field = item["required_fields"][0]
        responsibility_layer, runtime_control, boundary_note = normalize_source(item["source"], field)
        exact_class = EXACT_CLASS_BY_FIELD[field]
        transforms = TRANSFORM_BY_EXACT_CLASS[exact_class]
        requirement_type = "REQUIRED_FIELD_PRESENCE" if field in UPSTREAM_BY_FIELD else item["evidence_type"]
        if runtime_control == "APPROVED_VS_REQUESTED_MATCH":
            validation_type = "MATCH_APPROVED_VALUE"
        elif runtime_control == "TRACE_BINDING":
            validation_type = "TRACE_BINDING_VALID"
        else:
            validation_type = "REQUIRED_FIELD_PRESENT"
        requirements.append(
            {
                "requirement_id": item["requirement_id"],
                "requirement_type": requirement_type,
                "evidence_type": item["evidence_type"],
                "responsibility_layer": responsibility_layer,
                "runtime_control": runtime_control,
                "legal_basis": item["legal_basis"],
                "approved_source": "APPROVED_TRANSACTION|APPROVED_POLICY_SNAPSHOT" if runtime_control == "APPROVED_VS_REQUESTED_MATCH" else "UPSTREAM_SYSTEM_OR_PROVIDER",
                "requested_source": "OUTBOUND_REQUEST",
                "required_fields": item["required_fields"],
                "field_roles": ROLE_BY_FIELD[field],
                "transform": transforms,
                "destination": DESTINATION_BY_FIELD[field],
                "required_exact": exact_class,
                "validation_type": validation_type,
                "on_missing": "REVIEW" if field in UPSTREAM_BY_FIELD else item["on_missing"],
                "on_mismatch": "BLOCK only for approved/requested value mismatch or payload schema mismatch; not approval cancellation.",
                "audit_requirement": item["audit"],
                "effective_status": item["effective_status"],
                "fpg_boundary_note": boundary_note,
            }
        )
    return {
        "schema_version": "v2",
        "artifact_id": "ORM-DA-REGULATED-TRANSFER-002",
        "artifact_version": "v2",
        "scope": "Control-boundary-corrected Digital Asset outbound handoff requirement matrix.",
        "fpg_boundary": {
            "role": "Policy Enforcement Gateway for already-approved transactions before external execution handoff.",
            "not_responsible_for": sorted(FORBIDDEN_RUNTIME_CONTROLS | {"WALLET_SIGNING_CUSTODY", "SETTLEMENT_FINALITY"}),
            "runtime_controls": [
                "APPROVED_VS_REQUESTED_MATCH",
                "REQUIRED_OUTBOUND_FIELD_PRESENCE",
                "REQUIRED_EXACT_PRESERVATION",
                "TRANSFORM_FIELD_SEPARATION",
                "DESTINATION_SPECIFIC_PAYLOAD",
                "TRACE_BINDING",
            ],
        },
        "decision_semantics": {
            "PASS": "Current outbound handoff requirements are satisfied. This is not transaction approval.",
            "BLOCK": "The transaction may already be approved, but the current outbound request does not satisfy approved values or mandatory outbound handoff conditions.",
            "REVIEW": "Information required to construct outbound handoff is unresolved, unmapped, pending, or ambiguous. Do not use KYC/AML/VASP risk judgment as FPG runtime control.",
        },
        "requirements": requirements,
    }


def runtime_pipeline_v2() -> dict[str, Any]:
    names = [
        ("Approved Transaction Load", "approved transaction record", "approved transaction context", "BE_APPROVAL_SYSTEM", "missing approved transaction", "load existing approval; do not approve transactions"),
        ("Approved Policy Snapshot Load", "approved policy snapshot id", "approved constraints", "BE_POLICY_STORE", "missing approved policy snapshot", "load snapshot; do not invent policy"),
        ("Regulatory Outbound Requirement Load", "outbound matrix", "applicable requirement list", "FPG", "missing outbound matrix", "load handoff requirements"),
        ("Required Field Resolution", "approved transaction plus upstream-produced fields", "resolved field set", "FPG", "required source unresolved", "consume upstream data; do not determine KYC/AML/VASP eligibility"),
        ("Approved Value vs Requested Value Match", "approved/requested asset amount destination beneficiary period", "match result", "FPG", "approved/requested mismatch", "compare values"),
        ("Required Field Presence Check", "resolved field set", "presence result", "FPG", "required outbound field missing", "check required outbound information exists"),
        ("Required Exact Validation", "exact-class fields", "exactness result", "FPG", "lossy transform or altered exact value", "verify exact fields are not lossy-transformed"),
        ("Transform / Field Separation", "resolved field set", "destination partitions", "FPG", "unsafe field externalization", "normalize, minimize, omit, split, and map fields"),
        ("Destination-specific Payload Build", "field partitions", "payloads per destination", "FPG", "destination schema unmapped", "build execution, Travel Rule, VASP, audit, reconciliation payloads"),
        ("Outbound Handoff Decision", "validation results", "PASS/BLOCK/REVIEW", "FPG", "unresolved handoff readiness", "decide handoff readiness only"),
        ("External Execution Handoff", "destination payload", "outbound handoff id", "EXTERNAL_EXECUTION_SYSTEM", "handoff rejected or unavailable", "forward payload; no wallet/signing/custody responsibility"),
        ("Execution Result Binding", "external response", "tx hash/status binding", "EXTERNAL_EXECUTION_SYSTEM", "execution response missing", "bind returned execution references only"),
        ("Audit / Reconciliation Trace", "handoff ids and decision refs", "audit trace", "FPG", "trace binding incomplete", "retain lineage for audit and reconciliation"),
    ]
    return {
        "schema_version": "v1",
        "artifact_id": "RTP-DA-REGULATED-TRANSFER-002",
        "artifact_version": "v2",
        "steps": [
            {
                "step_number": i,
                "name": name,
                "input": inp,
                "output": out,
                "responsible_system": system,
                "failure_mode": failure,
                "fpg_responsibility": responsibility,
            }
            for i, (name, inp, out, system, failure, responsibility) in enumerate(names, start=1)
        ],
    }


def schema_files() -> None:
    write_json(
        CONTRACTS / "outbound_requirement_matrix_v2.schema.json",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Digital Asset Outbound Requirement Matrix v2",
            "type": "object",
            "required": ["schema_version", "artifact_id", "artifact_version", "fpg_boundary", "decision_semantics", "requirements"],
            "properties": {
                "schema_version": {"type": "string", "const": "v2"},
                "artifact_id": {"type": "string"},
                "artifact_version": {"type": "string"},
                "scope": {"type": "string"},
                "fpg_boundary": {"type": "object"},
                "decision_semantics": {"type": "object"},
                "requirements": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": [
                            "requirement_id",
                            "requirement_type",
                            "evidence_type",
                            "responsibility_layer",
                            "runtime_control",
                            "legal_basis",
                            "approved_source",
                            "requested_source",
                            "required_fields",
                            "field_roles",
                            "transform",
                            "destination",
                            "required_exact",
                            "validation_type",
                            "on_missing",
                            "on_mismatch",
                            "audit_requirement",
                            "effective_status",
                            "fpg_boundary_note",
                        ],
                        "properties": {
                            "requirement_id": {"type": "string"},
                            "requirement_type": {"type": "string"},
                            "evidence_type": {"type": "string"},
                            "responsibility_layer": {"type": "string"},
                            "runtime_control": {"type": "string"},
                            "legal_basis": {"type": "string"},
                            "approved_source": {"type": "string"},
                            "requested_source": {"type": "string"},
                            "required_fields": {"type": "array", "items": {"type": "string"}},
                            "field_roles": {"type": "array", "items": {"type": "string"}},
                            "transform": {"type": "array", "items": {"type": "string"}},
                            "destination": {"type": "array", "items": {"type": "string"}},
                            "required_exact": {"type": "string"},
                            "validation_type": {"type": "string"},
                            "on_missing": {"type": "string"},
                            "on_mismatch": {"type": "string"},
                            "audit_requirement": {"type": "string"},
                            "effective_status": {"type": "string"},
                            "fpg_boundary_note": {"type": "string"},
                        },
                        "additionalProperties": False,
                    },
                },
            },
            "additionalProperties": False,
        },
    )
    write_json(
        CONTRACTS / "control_boundary_validation.schema.json",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Digital Asset Control Boundary Validation",
            "type": "object",
            "required": ["schema_version", "artifact_id", "artifact_version", "assertions"],
            "properties": {
                "schema_version": {"type": "string", "const": "v1"},
                "artifact_id": {"type": "string"},
                "artifact_version": {"type": "string"},
                "assertions": {"type": "array", "items": {"type": "object"}},
            },
            "additionalProperties": False,
        },
    )


def be_handoff_v3(matrix: dict[str, Any], pipeline: dict[str, Any]) -> None:
    requirements = matrix["requirements"]
    policy_eval = {
        "schema_version": "v1",
        "artifact_id": "PE-DA-REGULATED-TRANSFER-003",
        "artifact_version": "v3",
        "analysis_status": "candidate",
        "policy_action": "candidate_handoff",
        "approved_policy_ref": "DA-CANDIDATE-POLICY-REGULATED-TRANSFER-003",
        "execution_request_ref": "APPROVED_TRANSACTION_RUNTIME_INPUT",
        "policy_rule_refs": [{"ref_id": row["requirement_id"], "ref_type": "outbound_requirement", "version": "v2"} for row in requirements],
        "required_input_fields": sorted({field for row in requirements for field in row["required_fields"]}),
        "decision_values": ["PASS", "BLOCK", "REVIEW"],
        "handoff_chain": [
            "Approved Transaction",
            "FPG",
            "Regulatory Outbound Requirement Enforcement",
            "Destination-specific Payload",
            "External Execution System",
            "Execution Result Binding",
            "Audit / Reconciliation Trace",
        ],
        "limitations": [
            "This Policy Evaluation artifact is an Outbound Handoff Evaluation, not transaction approval evaluation.",
            "KYC/AML/VASP eligibility/risk/sanctions decisions are upstream or external responsibilities.",
            "Synthetic policy simulations are not used as BE runtime control evidence.",
            "BE-owned runtime enums and provider payload schemas remain CONTRACT_GAP.",
        ],
        "digest": digest(matrix),
    }
    binding = {
        "schema_version": "v1",
        "binding_version": "v3",
        "bindings": [
            {
                "digital_asset_runtime": "REGULATED_VIRTUAL_ASSET_TRANSFER_OUTBOUND_HANDOFF",
                "evaluation_kind": "OUTBOUND_HANDOFF_EVALUATION",
                "approved_transaction_identifier": "CONTRACT_GAP",
                "approved_policy_snapshot_identifier": "CONTRACT_GAP",
                "workload_id": "UNMAPPED",
                "purpose": "UNMAPPED",
                "runtime_data_class": "UNMAPPED",
                "destination_profile": "CONTRACT_GAP",
                "binding_status": "candidate_contract_gap",
                "boundary_note": "Binding does not grant FPG responsibility for KYC/AML/VASP eligibility decisions.",
            }
        ],
    }
    crosswalk = {
        "schema_version": "v1",
        "crosswalk_version": "v3",
        "mappings": [
            {
                "required_field": field,
                "runtime_data_class": "UNMAPPED",
                "runtime_control": row["runtime_control"],
                "responsibility_layer": row["responsibility_layer"],
                "field_roles": row["field_roles"],
                "transform_instruction": row["transform"],
                "destination": row["destination"],
                "required_exact": row["required_exact"],
                "mapping_status": "unmapped",
                "mapping_basis": row["requirement_id"],
            }
            for row in requirements
            for field in row["required_fields"]
        ],
    }
    outbound = {
        "schema_version": "v2",
        "artifact_id": "OR-DA-REGULATED-TRANSFER-002",
        "artifact_version": "v2",
        "matrix_ref": matrix["artifact_id"],
        "pipeline_ref": pipeline["artifact_id"],
        "requirements": requirements,
        "contract_gap": [
            "Approved transaction runtime input schema",
            "Approved policy snapshot schema",
            "Travel Rule provider payload schema",
            "VASP directory/provider response schema",
            "Destination profile enum",
            "Execution handoff id lifecycle",
            "Execution receipt/status ingestion",
            "Retry/reconciliation event schema",
            "Audit event schema",
        ],
    }
    write_json(BE_V3 / "policy_evaluations" / "PE-DA-REGULATED-TRANSFER-003.json", policy_eval)
    write_json(BE_V3 / "bindings" / "DAB-REGULATED-TRANSFER-003.json", binding)
    write_json(BE_V3 / "crosswalks" / "DA-RDC-REGULATED-TRANSFER-003.json", crosswalk)
    write_json(BE_V3 / "outbound_requirements" / "OR-DA-REGULATED-TRANSFER-002.json", outbound)


def validate_boundary(matrix: dict[str, Any], pipeline: dict[str, Any]) -> dict[str, Any]:
    runtime_controls = {row["runtime_control"] for row in matrix["requirements"]}
    text = json.dumps({"matrix": matrix, "pipeline": pipeline}, ensure_ascii=False)
    assertions = [
        ("no_KYC_STATUS_CHECK_runtime_control", "KYC_STATUS_CHECK" not in runtime_controls),
        ("no_AML_CHECK_runtime_control", "AML_CHECK" not in runtime_controls),
        ("no_VASP_ELIGIBILITY_CHECK_runtime_control", "VASP_ELIGIBILITY_CHECK" not in runtime_controls),
        ("pass_not_transaction_approval", "not transaction approval" in matrix["decision_semantics"]["PASS"].lower()),
        ("block_not_approval_cancellation", "approval cancellation" not in matrix["decision_semantics"]["BLOCK"].lower()),
        ("approved_transaction_input_exists", "Approved Transaction Load" in text),
        ("approved_requested_match_exists", "APPROVED_VS_REQUESTED_MATCH" in runtime_controls),
        ("required_field_presence_exists", "REQUIRED_OUTBOUND_FIELD_PRESENCE" in runtime_controls),
        ("transform_instruction_exists", "TRANSFORM_FIELD_SEPARATION" in matrix["fpg_boundary"]["runtime_controls"]),
        ("destination_mapping_exists", "DESTINATION_SPECIFIC_PAYLOAD" in matrix["fpg_boundary"]["runtime_controls"]),
        ("trace_binding_exists", "TRACE_BINDING" in runtime_controls),
        ("required_exact_transform_no_conflict", all(not (row["required_exact"] == "INTERNAL_ONLY" and "PASS_THROUGH" in row["transform"]) for row in matrix["requirements"])),
    ]
    return {
        "schema_version": "v1",
        "artifact_id": "CBV-DA-REGULATED-TRANSFER-001",
        "artifact_version": "v1",
        "assertions": [{"assertion": name, "status": "PASS" if passed else "FAIL"} for name, passed in assertions],
    }


def developer_doc(matrix: dict[str, Any], pipeline: dict[str, Any], validation: dict[str, Any]) -> None:
    reqs = matrix["requirements"]
    transform = Counter(t for row in reqs for t in row["transform"])
    destination = Counter(d for row in reqs for d in row["destination"])
    exact = Counter(row["required_exact"] for row in reqs)
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text(
        "\n".join(
            [
                "# BE Handoff Digital Asset V3",
                "",
                "## 1. FPG Role",
                "",
                "FPG Digital Asset is a Policy Enforcement Gateway. It enforces approved-vs-requested consistency, outbound field presence, exact preservation, transform, destination payload mapping, and trace binding for already-approved transactions.",
                "",
                "## 2. Approved Transaction Input Layer",
                "",
                "FPG input starts from an Approved Transaction plus an Approved Policy Snapshot. BE-owned identifiers remain CONTRACT_GAP until BE defines the runtime shape.",
                "",
                "## 3. Upstream Responsibility",
                "",
                "KYC execution, AML screening, VASP eligibility, sanctions screening, fraud/risk scoring, and transaction approval are upstream or external responsibilities.",
                "",
                "## 4. FPG Runtime Responsibility",
                "",
                ", ".join(matrix["fpg_boundary"]["runtime_controls"]),
                "",
                "## 5. Legal Obligation vs Runtime Control",
                "",
                "Legal obligations remain represented, but KYC/AML/VASP eligibility obligations are not converted into FPG runtime decision controls.",
                "",
                "## 6. Required Field",
                "",
                ", ".join(sorted({field for row in reqs for field in row["required_fields"]})),
                "",
                "## 7. Source",
                "",
                "Sources are approved transaction, approved policy snapshot, upstream customer/compliance/provider data, blockchain execution layer, and external execution response.",
                "",
                "## 8. Match",
                "",
                "FPG compares approved asset, amount/limit, destination, beneficiary reference, and approved period against the outbound request.",
                "",
                "## 9. Transform",
                "",
                json.dumps(dict(transform), ensure_ascii=False),
                "",
                "## 10. Destination",
                "",
                json.dumps(dict(destination), ensure_ascii=False),
                "",
                "## 11. Required Exact",
                "",
                json.dumps(dict(exact), ensure_ascii=False),
                "",
                "## 12. PASS / BLOCK / REVIEW",
                "",
                f"PASS: {matrix['decision_semantics']['PASS']}",
                "",
                f"BLOCK: {matrix['decision_semantics']['BLOCK']}",
                "",
                f"REVIEW: {matrix['decision_semantics']['REVIEW']}",
                "",
                "## 13. Runtime Pipeline",
                "",
                "\n".join(f"{step['step_number']}. {step['name']} - {step['fpg_responsibility']}" for step in pipeline["steps"]),
                "",
                "## 14. Artifact Description",
                "",
                "- `03_digital_asset/artifacts/outbound_design_v2/outbound_requirement_matrix.json`",
                "- `03_digital_asset/artifacts/outbound_design_v2/runtime_pipeline.json`",
                "- `03_digital_asset/artifacts/outbound_design_v2/control_boundary_validation.json`",
                "- `03_digital_asset/artifacts/be_handoff_v3/policy_evaluations/PE-DA-REGULATED-TRANSFER-003.json`",
                "- `03_digital_asset/artifacts/be_handoff_v3/bindings/DAB-REGULATED-TRANSFER-003.json`",
                "- `03_digital_asset/artifacts/be_handoff_v3/crosswalks/DA-RDC-REGULATED-TRANSFER-003.json`",
                "- `03_digital_asset/artifacts/be_handoff_v3/outbound_requirements/OR-DA-REGULATED-TRANSFER-002.json`",
                "",
                "## 15. BE Implementation Scope",
                "",
                "BE can implement artifact loading, field resolution, approved/requested match, exact validation, transform instruction application, destination-specific payload build, PASS/BLOCK/REVIEW return, handoff trace creation, and execution result binding.",
                "",
                "## 16. BE Non-Implementation Scope",
                "",
                "BE should not implement KYC engine, AML engine, VASP eligibility engine, sanctions screening, fraud detection, wallet/custody/signing, or settlement engine as FPG runtime controls.",
                "",
                "## 17. Contract Gap",
                "",
                "Approved transaction schema, approved policy snapshot schema, provider response schemas, destination profile enum, retry/reconciliation event schema, audit event schema, and execution receipt ingestion remain CONTRACT_GAP.",
                "",
                "## 18. Example Flow",
                "",
                "CASE 1 normal outbound: approved transaction exists -> requested values match -> required outbound fields exist -> transform -> payload build -> PASS -> external handoff.",
                "",
                "CASE 2 destination mismatch: approved destination differs from requested destination -> BLOCK. This stops outbound handoff, not transaction approval itself.",
                "",
                "CASE 3 required regulatory field missing: approval may exist but outbound field cannot resolve -> REVIEW when source is unresolved, BLOCK when exact request mismatch is confirmed.",
                "",
                "CASE 4 KYC/AML/VASP: upstream systems produce statuses or references; FPG does not re-score or re-decide them.",
                "",
                "## Boundary Validation",
                "",
                json.dumps(validation["assertions"], ensure_ascii=False),
                "",
                "## Synthetic Position",
                "",
                "Synthetic v1/v2/v3 remains EXPERIMENTAL_POLICY_SIMULATION and is not used as BE runtime control evidence.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def build_notebook() -> None:
    nb = nbf.v4.new_notebook()
    nb["metadata"] = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3.12"}}
    cells = [
        nbf.v4.new_markdown_cell("# FPG Control Boundary Validation\n\n## tl;dr\n\nThis notebook validates the boundary between legal obligation, upstream responsibility, and FPG runtime enforcement. KYC/AML/VASP eligibility are not FPG runtime controls."),
        nbf.v4.new_markdown_cell("## Context & Methods\n\nInputs are the control-boundary-corrected outbound matrix v2, runtime pipeline v2, BE handoff v3, and validation assertions.\n\n### Key Assumptions\n\nFPG starts from an Approved Transaction. It does not approve transactions, perform KYC/AML, determine VASP eligibility, custody assets, sign transactions, or guarantee settlement finality."),
        nbf.v4.new_code_cell(
            "# ruff: noqa: E501, E701, E702, I001\n"
            "\n"
            "from pathlib import Path\nimport json\nimport pandas as pd\nimport matplotlib.pyplot as plt\n"
            "ROOT = Path.cwd().resolve()\nif ROOT.name != 'ADP-DA': ROOT = next(p for p in [ROOT, *ROOT.parents] if p.name == 'ADP-DA')\n"
            "matrix = json.loads((ROOT/'03_digital_asset/artifacts/outbound_design_v2/outbound_requirement_matrix.json').read_text(encoding='utf-8'))\n"
            "pipeline = json.loads((ROOT/'03_digital_asset/artifacts/outbound_design_v2/runtime_pipeline.json').read_text(encoding='utf-8'))\n"
            "validation = json.loads((ROOT/'03_digital_asset/artifacts/outbound_design_v2/control_boundary_validation.json').read_text(encoding='utf-8'))\n"
            "req = pd.DataFrame(matrix['requirements'])\n"
            "print({'requirements': len(req), 'pipeline_steps': len(pipeline['steps']), 'validation_assertions': len(validation['assertions'])})"
        ),
        nbf.v4.new_markdown_cell("## Data\n\n### 1. Legal Obligation Count"),
        nbf.v4.new_code_cell("display(req.groupby(['evidence_type','responsibility_layer']).size().reset_index(name='count'))"),
        nbf.v4.new_markdown_cell("## Results\n\n### 2. Upstream Responsibility Items"),
        nbf.v4.new_code_cell("display(req[req['responsibility_layer'] == 'UPSTREAM_PRODUCED_DATA'][['requirement_id','required_fields','runtime_control','fpg_boundary_note']])"),
        nbf.v4.new_markdown_cell("### 3. FPG Runtime Enforcement Items"),
        nbf.v4.new_code_cell("display(req[['requirement_id','required_fields','runtime_control','validation_type']])\ncontrols = req['runtime_control'].value_counts().reset_index(); controls.columns=['runtime_control','count']; display(controls); controls.plot.bar(x='runtime_control', y='count', legend=False, color='#2f6f8f', title='FPG Runtime Control Distribution'); plt.xticks(rotation=45, ha='right'); plt.tight_layout()"),
        nbf.v4.new_markdown_cell("### 4. Approved-vs-Requested Match Items"),
        nbf.v4.new_code_cell("display(req[req['runtime_control'] == 'APPROVED_VS_REQUESTED_MATCH'][['requirement_id','required_fields','validation_type','on_mismatch']])"),
        nbf.v4.new_markdown_cell("### 5. Required Outbound Field"),
        nbf.v4.new_code_cell("display(req[req['runtime_control'] == 'REQUIRED_OUTBOUND_FIELD_PRESENCE'][['requirement_id','required_fields','on_missing','fpg_boundary_note']])"),
        nbf.v4.new_markdown_cell("### 6. Exact / Transform / Minimize / Internal-only Distribution"),
        nbf.v4.new_code_cell("exact = req['required_exact'].value_counts().reset_index(); exact.columns=['required_exact','count']; display(exact); exact.plot.bar(x='required_exact', y='count', legend=False, color='#4f8f65', title='Required Exact Classification'); plt.xticks(rotation=45, ha='right'); plt.tight_layout()"),
        nbf.v4.new_markdown_cell("### 7. Source System x Field Role"),
        nbf.v4.new_code_cell("roles = req.explode('field_roles'); display(roles.groupby(['runtime_control','field_roles']).size().unstack(fill_value=0))"),
        nbf.v4.new_markdown_cell("### 8. Destination x Field Role"),
        nbf.v4.new_code_cell("dest = req.explode('destination').explode('field_roles'); display(dest.groupby(['destination','field_roles']).size().unstack(fill_value=0))"),
        nbf.v4.new_markdown_cell("### 9. Legal Requirement -> Outbound Requirement Lineage"),
        nbf.v4.new_code_cell("display(req[['requirement_id','legal_basis','evidence_type','responsibility_layer','runtime_control','required_fields']])"),
        nbf.v4.new_markdown_cell("### 10. Boundary Assertion Validation"),
        nbf.v4.new_code_cell("assertions = pd.DataFrame(validation['assertions']); display(assertions); print({'all_pass': (assertions['status'] == 'PASS').all()})"),
        nbf.v4.new_markdown_cell("## Takeaways\n\nThe corrected artifacts contain no KYC/AML/VASP eligibility runtime control. FPG runtime control is limited to match, presence, exact preservation, transform/separation, destination-specific payload build, and trace binding."),
    ]
    nb["cells"] = cells
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, NOTEBOOK)


def main() -> None:
    matrix = build_matrix_v2()
    pipeline = runtime_pipeline_v2()
    schema_files()
    write_json(OUTBOUND_V2 / "outbound_requirement_matrix.json", matrix)
    write_json(OUTBOUND_V2 / "runtime_pipeline.json", pipeline)
    validation = validate_boundary(matrix, pipeline)
    write_json(OUTBOUND_V2 / "control_boundary_validation.json", validation)
    write_json(OUTBOUND_V2 / "validation_report.json", {"validations": []})
    jsonschema.validate(matrix, read_json(CONTRACTS / "outbound_requirement_matrix_v2.schema.json"))
    jsonschema.validate(validation, read_json(CONTRACTS / "control_boundary_validation.schema.json"))
    jsonschema.validate(pipeline, read_json(CONTRACTS / "runtime_pipeline.schema.json"))
    be_handoff_v3(matrix, pipeline)
    jsonschema.validate(
        read_json(BE_V3 / "policy_evaluations" / "PE-DA-REGULATED-TRANSFER-003.json"),
        read_json(CONTRACTS / "digital_asset_policy_evaluation.schema.json"),
    )
    report = {
        "validations": [
            {"schema": "03_digital_asset/contracts/outbound_requirement_matrix_v2.schema.json", "status": "PASS"},
            {"schema": "03_digital_asset/contracts/control_boundary_validation.schema.json", "status": "PASS"},
            {"schema": "03_digital_asset/contracts/runtime_pipeline.schema.json", "status": "PASS"},
            {"schema": "03_digital_asset/contracts/digital_asset_policy_evaluation.schema.json", "artifact": "PE-DA-REGULATED-TRANSFER-003", "status": "PASS"},
        ],
        "assertions": validation["assertions"],
    }
    write_json(OUTBOUND_V2 / "validation_report.json", report)
    developer_doc(matrix, pipeline, validation)
    build_notebook()


if __name__ == "__main__":
    main()
