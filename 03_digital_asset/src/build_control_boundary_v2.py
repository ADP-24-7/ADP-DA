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
OUTBOUND_VNEXT = DA / "artifacts" / "outbound_design_vNext"
BE_V3 = DA / "artifacts" / "be_handoff_v3"
BE_VNEXT = DA / "artifacts" / "be_handoff_vNext"
DOC = DA / "docs" / "BE_HANDOFF_DIGITAL_ASSET_V3.md"
DOC_VNEXT = DA / "docs" / "BE_HANDOFF_DIGITAL_ASSET_VNEXT.md"
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

EXECUTION_RESULT_FIELDS = {"tx_hash", "execution_status", "timestamp"}

APPROVED_REQUESTED_MATCH_FIELDS = {"amount", "asset", "originator_address", "beneficiary_address"}

INTERNAL_DESTINATIONS = {"NOT_EXTERNALIZED", "INTERNAL_AUDIT_ONLY", "INTERNAL_RECONCILIATION_ONLY"}
EXTERNAL_DESTINATIONS = {"BLOCKCHAIN_EXECUTION_SYSTEM", "TRAVEL_RULE_PROVIDER", "EXTERNAL_VASP"}

PIPELINE_STAGE_BY_PHASE = {
    "APPROVED_SOURCE_LOAD": "Approved Transaction Load",
    "REQUEST_SOURCE_LOAD": "Approved Value vs Requested Value Match",
    "UPSTREAM_SOURCE_RESOLUTION": "Required Field Resolution",
    "PRE_EXECUTION_PAYLOAD_BUILD": "Destination-specific Payload Build",
    "EXTERNAL_EXECUTION_RESPONSE_BINDING": "Execution Result Binding",
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
    "EXACT_REQUIRED": ["PASS_THROUGH"],
    "FORMAT_TRANSFORM_ALLOWED": ["MAP_TO_EXTERNAL_SCHEMA", "FORMAT_NORMALIZE"],
    "MINIMIZATION_ALLOWED": ["MINIMIZE", "MAP_TO_EXTERNAL_SCHEMA"],
    "INTERNAL_ONLY": ["OMIT"],
}

ALLOWED_TRANSFORM_BY_EXACT_CLASS = {
    "EXACT_REQUIRED": {"PASS_THROUGH"},
    "FORMAT_TRANSFORM_ALLOWED": {"MAP_TO_EXTERNAL_SCHEMA", "FORMAT_NORMALIZE"},
    "MINIMIZATION_ALLOWED": {"MINIMIZE", "MAP_TO_EXTERNAL_SCHEMA"},
    "INTERNAL_ONLY": {"OMIT"},
}

NON_MUTATING_CANONICALIZATION_BY_FIELD = {
    "amount": "NONE_CONTRACTED",
    "asset": "NONE_CONTRACTED",
    "originator_address": "NONE_CONTRACTED",
    "beneficiary_address": "NONE_CONTRACTED",
    "transaction_id": "NONE_CONTRACTED",
    "tx_hash": "NONE_CONTRACTED",
    "timestamp": "NONE_CONTRACTED",
    "execution_status": "NONE_CONTRACTED",
    "originator_identity": "CONTRACT_GAP_PROVIDER_SCHEMA_CANONICALIZATION",
    "beneficiary_identity": "CONTRACT_GAP_PROVIDER_SCHEMA_CANONICALIZATION",
    "counterparty_vasp": "CONTRACT_GAP_PROVIDER_SCHEMA_CANONICALIZATION",
    "kyc_status": "NONE_CONTRACTED_INTERNAL_ONLY",
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
    if field in EXECUTION_RESULT_FIELDS:
        return "EXTERNAL_EXECUTION_RESPONSE", "TRACE_BINDING", "External execution result fields are bound only after external handoff; they are not pre-execution outbound inputs."
    return "FPG_ENFORCEMENT_INPUT", RUNTIME_CONTROL_BY_FIELD[field], "FPG validates outbound handoff readiness only."


def source_contract_for_field(field: str, runtime_control: str) -> dict[str, Any]:
    if field in EXECUTION_RESULT_FIELDS:
        return {
            "source_phase": "POST_EXECUTION",
            "source_type": "EXTERNAL_EXECUTION_RESPONSE",
            "approved_source": "NOT_APPLICABLE",
            "requested_source": "NOT_PRE_EXECUTION_INPUT",
            "comparison_sources": [],
            "pre_execution_required": False,
            "post_execution_binding": True,
            "pipeline_stage": PIPELINE_STAGE_BY_PHASE["EXTERNAL_EXECUTION_RESPONSE_BINDING"],
        }
    if runtime_control == "APPROVED_VS_REQUESTED_MATCH":
        return {
            "source_phase": "PRE_EXECUTION",
            "source_type": "APPROVED_AND_REQUESTED_VALUE_PAIR",
            "approved_source": "APPROVED_TRANSACTION|APPROVED_POLICY_SNAPSHOT",
            "requested_source": "OUTBOUND_REQUEST",
            "comparison_sources": ["APPROVED_TRANSACTION_OR_POLICY_SNAPSHOT", "OUTBOUND_REQUEST"],
            "pre_execution_required": True,
            "post_execution_binding": False,
            "pipeline_stage": PIPELINE_STAGE_BY_PHASE["REQUEST_SOURCE_LOAD"],
        }
    if field in UPSTREAM_BY_FIELD:
        return {
            "source_phase": "PRE_EXECUTION",
            "source_type": "UPSTREAM_PRODUCED_DATA",
            "approved_source": "UPSTREAM_SYSTEM_OR_PROVIDER",
            "requested_source": "NOT_OUTBOUND_REQUEST_SOURCE",
            "comparison_sources": [],
            "pre_execution_required": True,
            "post_execution_binding": False,
            "pipeline_stage": PIPELINE_STAGE_BY_PHASE["UPSTREAM_SOURCE_RESOLUTION"],
        }
    return {
        "source_phase": "PRE_EXECUTION",
        "source_type": "APPROVED_TRANSACTION_TRACE_INPUT",
        "approved_source": "APPROVED_TRANSACTION",
        "requested_source": "OUTBOUND_REQUEST",
        "comparison_sources": [],
        "pre_execution_required": True,
        "post_execution_binding": False,
        "pipeline_stage": PIPELINE_STAGE_BY_PHASE["APPROVED_SOURCE_LOAD"],
    }


def destination_transform_for_field(field: str, exact_class: str) -> dict[str, str]:
    destinations = DESTINATION_BY_FIELD[field]
    if exact_class == "EXACT_REQUIRED":
        return {destination: "PASS_THROUGH" for destination in destinations}
    if exact_class == "INTERNAL_ONLY":
        return {destination: "OMIT" for destination in destinations}
    if exact_class == "MINIMIZATION_ALLOWED":
        return {destination: "MINIMIZE" if destination in EXTERNAL_DESTINATIONS else "MAP_TO_EXTERNAL_SCHEMA" for destination in destinations}
    if exact_class == "FORMAT_TRANSFORM_ALLOWED":
        return {destination: "MAP_TO_EXTERNAL_SCHEMA" if destination in EXTERNAL_DESTINATIONS else "FORMAT_NORMALIZE" for destination in destinations}
    return {destination: "CONTRACT_GAP" for destination in destinations}


def build_matrix_v2() -> dict[str, Any]:
    v1 = read_json(OUTBOUND_V1 / "outbound_requirement_matrix.json")
    requirements = []
    for item in v1["requirements"]:
        field = item["required_fields"][0]
        responsibility_layer, runtime_control, boundary_note = normalize_source(item["source"], field)
        exact_class = EXACT_CLASS_BY_FIELD[field]
        transforms = TRANSFORM_BY_EXACT_CLASS[exact_class]
        source_contract = source_contract_for_field(field, runtime_control)
        destination_transform = destination_transform_for_field(field, exact_class)
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
                "approved_source": source_contract["approved_source"],
                "requested_source": source_contract["requested_source"],
                "source_phase": source_contract["source_phase"],
                "source_type": source_contract["source_type"],
                "comparison_sources": source_contract["comparison_sources"],
                "pipeline_stage": source_contract["pipeline_stage"],
                "pre_execution_required": source_contract["pre_execution_required"],
                "post_execution_binding": source_contract["post_execution_binding"],
                "required_fields": item["required_fields"],
                "field_roles": ROLE_BY_FIELD[field],
                "transform": transforms,
                "comparison_canonicalization": NON_MUTATING_CANONICALIZATION_BY_FIELD[field],
                "outbound_transform_by_destination": destination_transform,
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
        "artifact_id": "ORM-DA-REGULATED-TRANSFER-VNEXT",
        "artifact_version": "vNext",
        "scope": "BE handoff-ready Digital Asset outbound runtime contract matrix.",
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
        "transform_semantics": {
            "PASS_THROUGH": "Outbound value must be emitted without mutation.",
            "FORMAT_NORMALIZE": "Allowed only as non-lossy, non-mutating comparison canonicalization unless explicitly destination-scoped for FORMAT_TRANSFORM_ALLOWED fields.",
            "MINIMIZE": "Destination-specific payload reduction for MINIMIZATION_ALLOWED fields; schema remains CONTRACT_GAP until BE/provider contract exists.",
            "MAP_TO_EXTERNAL_SCHEMA": "Destination-specific mapping into provider schema; provider schema remains CONTRACT_GAP.",
            "OMIT": "Do not externalize the field value.",
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
        "artifact_id": "RTP-DA-REGULATED-TRANSFER-VNEXT",
        "artifact_version": "vNext",
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
            "required": ["schema_version", "artifact_id", "artifact_version", "fpg_boundary", "decision_semantics", "transform_semantics", "requirements"],
            "properties": {
                "schema_version": {"type": "string", "const": "v2"},
                "artifact_id": {"type": "string"},
                "artifact_version": {"type": "string"},
                "scope": {"type": "string"},
                "fpg_boundary": {"type": "object"},
                "decision_semantics": {"type": "object"},
                "transform_semantics": {"type": "object"},
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
                            "source_phase",
                            "source_type",
                            "comparison_sources",
                            "pipeline_stage",
                            "pre_execution_required",
                            "post_execution_binding",
                            "required_fields",
                            "field_roles",
                            "transform",
                            "comparison_canonicalization",
                            "outbound_transform_by_destination",
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
                            "source_phase": {"type": "string"},
                            "source_type": {"type": "string"},
                            "comparison_sources": {"type": "array", "items": {"type": "string"}},
                            "pipeline_stage": {"type": "string"},
                            "pre_execution_required": {"type": "boolean"},
                            "post_execution_binding": {"type": "boolean"},
                            "required_fields": {"type": "array", "items": {"type": "string"}},
                            "field_roles": {"type": "array", "items": {"type": "string"}},
                            "transform": {"type": "array", "items": {"type": "string"}},
                            "comparison_canonicalization": {"type": "string"},
                            "outbound_transform_by_destination": {"type": "object", "additionalProperties": {"type": "string"}},
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
            "required": ["schema_version", "artifact_id", "artifact_version", "status", "failures", "assertions"],
            "properties": {
                "schema_version": {"type": "string", "const": "v1"},
                "artifact_id": {"type": "string"},
                "artifact_version": {"type": "string"},
                "status": {"type": "string"},
                "failures": {"type": "array", "items": {"type": "object"}},
                "assertions": {"type": "array", "items": {"type": "object"}},
            },
            "additionalProperties": False,
        },
    )


def be_handoff_v3(matrix: dict[str, Any], pipeline: dict[str, Any]) -> None:
    requirements = matrix["requirements"]
    policy_eval = {
        "schema_version": "v1",
        "artifact_id": "PE-DA-REGULATED-TRANSFER-VNEXT",
        "artifact_version": "vNext",
        "analysis_status": "candidate",
        "policy_action": "candidate_handoff",
        "approved_policy_ref": "DA-CANDIDATE-POLICY-REGULATED-TRANSFER-VNEXT",
        "execution_request_ref": "APPROVED_TRANSACTION_RUNTIME_INPUT",
        "policy_rule_refs": [{"ref_id": row["requirement_id"], "ref_type": "outbound_requirement", "version": "vNext"} for row in requirements],
        "required_input_fields": sorted({field for row in requirements if row["pre_execution_required"] for field in row["required_fields"]}),
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
        "binding_version": "vNext",
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
        "crosswalk_version": "vNext",
        "mappings": [
            {
                "required_field": field,
                "runtime_data_class": "UNMAPPED",
                "runtime_control": row["runtime_control"],
                "responsibility_layer": row["responsibility_layer"],
                "source_phase": row["source_phase"],
                "source_type": row["source_type"],
                "field_roles": row["field_roles"],
                "transform_instruction": row["transform"],
                "comparison_canonicalization": row["comparison_canonicalization"],
                "outbound_transform_by_destination": row["outbound_transform_by_destination"],
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
        "artifact_id": "OR-DA-REGULATED-TRANSFER-VNEXT",
        "artifact_version": "vNext",
        "matrix_ref": matrix["artifact_id"],
        "pipeline_ref": pipeline["artifact_id"],
        "requirements": requirements,
        "contract_gap": [
            "BE-owned runtime enum",
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
    write_json(BE_VNEXT / "policy_evaluations" / "PE-DA-REGULATED-TRANSFER-VNEXT.json", policy_eval)
    write_json(BE_VNEXT / "bindings" / "DAB-REGULATED-TRANSFER-VNEXT.json", binding)
    write_json(BE_VNEXT / "crosswalks" / "DA-RDC-REGULATED-TRANSFER-VNEXT.json", crosswalk)
    write_json(BE_VNEXT / "outbound_requirements" / "OR-DA-REGULATED-TRANSFER-VNEXT.json", outbound)


def validate_boundary(matrix: dict[str, Any], pipeline: dict[str, Any]) -> dict[str, Any]:
    runtime_controls = {row["runtime_control"] for row in matrix["requirements"]}
    text = json.dumps({"matrix": matrix, "pipeline": pipeline}, ensure_ascii=False)
    pipeline_steps = {step["name"]: step["step_number"] for step in pipeline["steps"]}
    assertions = []

    def add_assertion(
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
                "rule": rule,
                "field": field,
                "destination": destination,
                "detail": detail,
            }
        )

    add_assertion("no_KYC_STATUS_CHECK_runtime_control", "KYC_STATUS_CHECK" not in runtime_controls, "FORBIDDEN_RUNTIME_CONTROL")
    add_assertion("no_AML_CHECK_runtime_control", "AML_CHECK" not in runtime_controls, "FORBIDDEN_RUNTIME_CONTROL")
    add_assertion("no_VASP_ELIGIBILITY_CHECK_runtime_control", "VASP_ELIGIBILITY_CHECK" not in runtime_controls, "FORBIDDEN_RUNTIME_CONTROL")
    add_assertion("pass_not_transaction_approval", "not transaction approval" in matrix["decision_semantics"]["PASS"].lower(), "DECISION_SEMANTICS")
    add_assertion("block_not_approval_cancellation", "approval cancellation" not in matrix["decision_semantics"]["BLOCK"].lower(), "DECISION_SEMANTICS")
    add_assertion("review_keeps_unresolved_mapping", "unresolved" in matrix["decision_semantics"]["REVIEW"].lower(), "DECISION_SEMANTICS")
    add_assertion("approved_transaction_input_exists", "Approved Transaction Load" in text, "PIPELINE_REQUIRED_STEP")
    add_assertion("approved_requested_match_exists", "APPROVED_VS_REQUESTED_MATCH" in runtime_controls, "RUNTIME_CONTROL_REQUIRED")
    add_assertion("required_field_presence_exists", "REQUIRED_OUTBOUND_FIELD_PRESENCE" in runtime_controls, "RUNTIME_CONTROL_REQUIRED")
    add_assertion("transform_instruction_exists", "TRANSFORM_FIELD_SEPARATION" in matrix["fpg_boundary"]["runtime_controls"], "RUNTIME_CONTROL_REQUIRED")
    add_assertion("destination_mapping_exists", "DESTINATION_SPECIFIC_PAYLOAD" in matrix["fpg_boundary"]["runtime_controls"], "RUNTIME_CONTROL_REQUIRED")
    add_assertion("trace_binding_exists", "TRACE_BINDING" in runtime_controls, "RUNTIME_CONTROL_REQUIRED")

    for row in matrix["requirements"]:
        field = row["required_fields"][0]
        exact_class = row["required_exact"]
        transforms = set(row["transform"])
        destinations = set(row["destination"])
        external_destinations = destinations & EXTERNAL_DESTINATIONS
        destination_transform = row.get("outbound_transform_by_destination", {})
        source_phase = row.get("source_phase")
        source_type = row.get("source_type")
        pipeline_stage = row.get("pipeline_stage")

        disallowed = transforms - ALLOWED_TRANSFORM_BY_EXACT_CLASS[exact_class]
        add_assertion(
            "transform_allowed_for_class",
            not disallowed,
            "TRANSFORM_CLASS_COMPATIBILITY",
            field=field,
            detail=f"disallowed={sorted(disallowed)} allowed={sorted(ALLOWED_TRANSFORM_BY_EXACT_CLASS[exact_class])}",
        )
        add_assertion(
            "exact_required_outbound_transform_whitelist",
            exact_class != "EXACT_REQUIRED" or transforms <= {"PASS_THROUGH"},
            "EXACT_REQUIRED_NO_LOSSY_OUTBOUND_TRANSFORM",
            field=field,
            detail=f"transforms={sorted(transforms)}",
        )
        add_assertion(
            "exact_required_no_mutating_normalization",
            exact_class != "EXACT_REQUIRED" or "FORMAT_NORMALIZE" not in transforms,
            "COMPARISON_NORMALIZATION_SEPARATED_FROM_OUTBOUND_TRANSFORM",
            field=field,
            detail="FORMAT_NORMALIZE cannot be an EXACT_REQUIRED outbound transform.",
        )
        add_assertion(
            "internal_only_not_externalized",
            exact_class != "INTERNAL_ONLY" or not external_destinations,
            "INTERNAL_ONLY_NO_EXTERNAL_DESTINATION",
            field=field,
            detail=f"external_destinations={sorted(external_destinations)}",
        )
        add_assertion(
            "internal_only_transform_omit_only",
            exact_class != "INTERNAL_ONLY" or transforms <= {"OMIT"},
            "INTERNAL_ONLY_OMIT_ONLY",
            field=field,
            detail=f"transforms={sorted(transforms)}",
        )
        add_assertion(
            "minimization_destination_transform_explicit",
            exact_class != "MINIMIZATION_ALLOWED" or destinations <= set(destination_transform),
            "MINIMIZATION_REQUIRES_DESTINATION_SPECIFIC_TRANSFORM",
            field=field,
            detail=f"destinations={sorted(destinations)} mapped={sorted(destination_transform)}",
        )
        for destination, transform in destination_transform.items():
            add_assertion(
                "destination_specific_transform_allowed",
                transform in ALLOWED_TRANSFORM_BY_EXACT_CLASS[exact_class],
                "DESTINATION_TRANSFORM_CLASS_COMPATIBILITY",
                field=field,
                destination=destination,
                detail=f"transform={transform} class={exact_class}",
            )
        add_assertion(
            "format_transform_class_whitelist",
            exact_class != "FORMAT_TRANSFORM_ALLOWED" or transforms <= ALLOWED_TRANSFORM_BY_EXACT_CLASS["FORMAT_TRANSFORM_ALLOWED"],
            "FORMAT_TRANSFORM_ALLOWED_WHITELIST",
            field=field,
            detail=f"transforms={sorted(transforms)}",
        )
        add_assertion(
            "execution_result_not_pre_execution_payload",
            field not in EXECUTION_RESULT_FIELDS or (source_phase == "POST_EXECUTION" and source_type == "EXTERNAL_EXECUTION_RESPONSE" and row.get("pre_execution_required") is False),
            "EXECUTION_RESULT_POST_EXECUTION_ONLY",
            field=field,
            detail=f"source_phase={source_phase} source_type={source_type} pre_execution_required={row.get('pre_execution_required')}",
        )
        add_assertion(
            "transaction_id_not_external_execution_result",
            field != "transaction_id" or source_type != "EXTERNAL_EXECUTION_RESPONSE",
            "TRACE_IDENTIFIER_SEPARATION",
            field=field,
            detail=f"source_type={source_type}",
        )
        add_assertion(
            "source_phase_pipeline_stage_exists",
            pipeline_stage in PIPELINE_STAGE_BY_PHASE.values() and pipeline_stage in pipeline_steps,
            "SOURCE_PHASE_PIPELINE_STAGE_EXISTS",
            field=field,
            detail=f"pipeline_stage={pipeline_stage}",
        )
        if source_phase == "POST_EXECUTION":
            add_assertion(
                "post_execution_after_handoff",
                pipeline_steps.get("Execution Result Binding", 0) > pipeline_steps.get("External Execution Handoff", 999),
                "SOURCE_PHASE_PIPELINE_ORDERING",
                field=field,
                detail="Execution Result Binding must occur after External Execution Handoff.",
            )
        if row["runtime_control"] == "APPROVED_VS_REQUESTED_MATCH":
            add_assertion(
                "approved_requested_sources_present",
                set(row.get("comparison_sources", [])) == {"APPROVED_TRANSACTION_OR_POLICY_SNAPSHOT", "OUTBOUND_REQUEST"},
                "APPROVED_REQUESTED_COMPARISON_SOURCE_PAIR",
                field=field,
                detail=f"comparison_sources={row.get('comparison_sources', [])}",
            )

    for forbidden in FORBIDDEN_RUNTIME_CONTROLS:
        add_assertion(
            f"no_forbidden_runtime_control_reentry_{forbidden}",
            forbidden not in runtime_controls,
            "FORBIDDEN_KYC_AML_VASP_RUNTIME_CONTROL_REENTRY",
            detail=forbidden,
        )

    failed = [assertion for assertion in assertions if assertion["status"] == "FAIL"]
    return {
        "schema_version": "v1",
        "artifact_id": "CBV-DA-REGULATED-TRANSFER-VNEXT",
        "artifact_version": "vNext",
        "status": "PASS" if not failed else "FAIL",
        "failures": failed,
        "assertions": assertions,
    }


def evaluate_handoff_decision(
    *,
    approved_requested_match: bool,
    required_fields_resolved: bool,
    mapping_resolved: bool,
    forbidden_runtime_control: str | None = None,
) -> dict[str, str]:
    if forbidden_runtime_control in FORBIDDEN_RUNTIME_CONTROLS:
        return {
            "decision": "REVIEW",
            "reason": "FORBIDDEN_RUNTIME_CONTROL",
            "detail": "KYC/AML/VASP eligibility/risk/sanctions controls must remain upstream or external.",
        }
    if not approved_requested_match:
        return {
            "decision": "BLOCK",
            "reason": "APPROVED_REQUESTED_MISMATCH",
            "detail": "Outbound handoff stops; this is not transaction approval cancellation.",
        }
    if not required_fields_resolved or not mapping_resolved:
        return {
            "decision": "REVIEW",
            "reason": "UNRESOLVED_MAPPING_OR_FIELD",
            "detail": "Required handoff data or destination mapping is unresolved.",
        }
    return {
        "decision": "PASS",
        "reason": "HANDOFF_READY",
        "detail": "Outbound handoff contract requirements are satisfied.",
    }


def developer_doc(matrix: dict[str, Any], pipeline: dict[str, Any], validation: dict[str, Any]) -> None:
    reqs = matrix["requirements"]
    transform = Counter(t for row in reqs for t in row["transform"])
    destination = Counter(d for row in reqs for d in row["destination"])
    exact = Counter(row["required_exact"] for row in reqs)
    source_phase = Counter(row["source_phase"] for row in reqs)
    DOC_VNEXT.parent.mkdir(parents=True, exist_ok=True)
    DOC_VNEXT.write_text(
        "\n".join(
            [
                "# BE Handoff Digital Asset vNext",
                "",
                "## A. DA에서 확정된 것",
                "",
                "### Field responsibility",
                "",
                "FPG Digital Asset is a Policy Enforcement Gateway for already-approved transactions before external execution handoff. It enforces approved-vs-requested consistency, upstream-produced outbound field presence, exact preservation, transform compatibility, destination payload separation, and trace binding.",
                "",
                "KYC execution, AML screening, VASP eligibility, sanctions screening, fraud/risk scoring, transaction approval, wallet custody/signing, and settlement finality are not FPG runtime controls.",
                "",
                "### Exact/minimization/internal classification",
                "",
                json.dumps(dict(exact), ensure_ascii=False),
                "",
                "### Source phase",
                "",
                json.dumps(dict(source_phase), ensure_ascii=False),
                "",
                "`tx_hash`, `execution_status`, and `timestamp` are POST_EXECUTION fields sourced from EXTERNAL_EXECUTION_RESPONSE. They are not pre-execution outbound request inputs. `transaction_id` remains an approved/request trace identifier and is distinct from external execution result fields.",
                "",
                "### Allowed transform semantics",
                "",
                json.dumps(matrix["transform_semantics"], ensure_ascii=False),
                "",
                "EXACT_REQUIRED outbound transform is restricted to PASS_THROUGH. Non-mutating comparison canonicalization is represented separately as `comparison_canonicalization`; chain-specific or lossy normalization remains CONTRACT_GAP.",
                "",
                "### Destination separation",
                "",
                json.dumps(dict(destination), ensure_ascii=False),
                "",
                "External destinations are separated from internal audit/reconciliation destinations by `destination` and `outbound_transform_by_destination`.",
                "",
                "### PASS/BLOCK/REVIEW semantics",
                "",
                f"PASS: {matrix['decision_semantics']['PASS']}",
                "",
                f"BLOCK: {matrix['decision_semantics']['BLOCK']}",
                "",
                f"REVIEW: {matrix['decision_semantics']['REVIEW']}",
                "",
                "## B. BE가 구현할 것",
                "",
                "- Runtime loading: load vNext matrix, runtime pipeline, binding, crosswalk, and outbound requirement artifacts.",
                "- Validator: enforce machine-readable validation rules from control boundary validation, including field/destination/rule failure reporting.",
                "- Transform executor: execute only allowed outbound transforms; keep comparison canonicalization non-mutating.",
                "- Destination payload builder: build destination-specific payloads without leaking INTERNAL_ONLY values to external destinations.",
                "- Trace binding: bind approved transaction identifiers and FPG internal trace identifiers separately from external execution result fields.",
                "- Execution response binding: bind `tx_hash`, `execution_status`, and `timestamp` only from EXTERNAL_EXECUTION_RESPONSE after external handoff.",
                "",
                "## C. CONTRACT_GAP",
                "",
                "- BE-owned runtime enum",
                "- Approved transaction schema",
                "- Approved policy snapshot schema",
                "- Provider-specific payload schema",
                "- Execution receipt/status schema",
                "- Retry/reconciliation event schema",
                "- Audit event schema",
                "",
                "These gaps are intentionally not filled with inferred enum values, legal rules, provider schemas, or chain-specific normalization behavior.",
                "",
                "## Runtime Pipeline",
                "",
                "\n".join(f"{step['step_number']}. {step['name']} - {step['fpg_responsibility']}" for step in pipeline["steps"]),
                "",
                "## Artifact Description",
                "",
                "- `03_digital_asset/artifacts/outbound_design_vNext/outbound_requirement_matrix.json`",
                "- `03_digital_asset/artifacts/outbound_design_vNext/runtime_pipeline.json`",
                "- `03_digital_asset/artifacts/outbound_design_vNext/control_boundary_validation.json`",
                "- `03_digital_asset/artifacts/be_handoff_vNext/policy_evaluations/PE-DA-REGULATED-TRANSFER-VNEXT.json`",
                "- `03_digital_asset/artifacts/be_handoff_vNext/bindings/DAB-REGULATED-TRANSFER-VNEXT.json`",
                "- `03_digital_asset/artifacts/be_handoff_vNext/crosswalks/DA-RDC-REGULATED-TRANSFER-VNEXT.json`",
                "- `03_digital_asset/artifacts/be_handoff_vNext/outbound_requirements/OR-DA-REGULATED-TRANSFER-VNEXT.json`",
                "",
                "## Boundary Validation",
                "",
                json.dumps({"status": validation["status"], "failures": validation["failures"], "transform_counts": dict(transform)}, ensure_ascii=False),
                "",
                "## ANALYST_DECISION_REQUIRED",
                "",
                "- Provider-specific exact schemas for Travel Rule and external VASP identity payloads.",
                "- Whether any future chain-specific address, amount, timestamp, status, or tx hash canonicalization can be contractually non-lossy.",
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
            "matrix = json.loads((ROOT/'03_digital_asset/artifacts/outbound_design_vNext/outbound_requirement_matrix.json').read_text(encoding='utf-8'))\n"
            "pipeline = json.loads((ROOT/'03_digital_asset/artifacts/outbound_design_vNext/runtime_pipeline.json').read_text(encoding='utf-8'))\n"
            "validation = json.loads((ROOT/'03_digital_asset/artifacts/outbound_design_vNext/control_boundary_validation.json').read_text(encoding='utf-8'))\n"
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
    write_json(OUTBOUND_VNEXT / "outbound_requirement_matrix.json", matrix)
    write_json(OUTBOUND_VNEXT / "runtime_pipeline.json", pipeline)
    validation = validate_boundary(matrix, pipeline)
    write_json(OUTBOUND_VNEXT / "control_boundary_validation.json", validation)
    write_json(OUTBOUND_VNEXT / "validation_report.json", {"validations": []})
    jsonschema.validate(matrix, read_json(CONTRACTS / "outbound_requirement_matrix_v2.schema.json"))
    jsonschema.validate(validation, read_json(CONTRACTS / "control_boundary_validation.schema.json"))
    jsonschema.validate(pipeline, read_json(CONTRACTS / "runtime_pipeline.schema.json"))
    be_handoff_v3(matrix, pipeline)
    jsonschema.validate(
        read_json(BE_VNEXT / "policy_evaluations" / "PE-DA-REGULATED-TRANSFER-VNEXT.json"),
        read_json(CONTRACTS / "digital_asset_policy_evaluation.schema.json"),
    )
    report = {
        "validations": [
            {"schema": "03_digital_asset/contracts/outbound_requirement_matrix_v2.schema.json", "status": "PASS"},
            {"schema": "03_digital_asset/contracts/control_boundary_validation.schema.json", "status": "PASS"},
            {"schema": "03_digital_asset/contracts/runtime_pipeline.schema.json", "status": "PASS"},
            {"schema": "03_digital_asset/contracts/digital_asset_policy_evaluation.schema.json", "artifact": "PE-DA-REGULATED-TRANSFER-VNEXT", "status": "PASS"},
        ],
        "assertions": validation["assertions"],
    }
    write_json(OUTBOUND_VNEXT / "validation_report.json", report)
    developer_doc(matrix, pipeline, validation)
    build_notebook()


if __name__ == "__main__":
    main()
