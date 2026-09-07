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
RAW_REG = DA / "data" / "raw" / "regulatory" / "crypto_regulation_raw.csv"
PROCESSED = DA / "data" / "processed"
CONTRACTS = DA / "contracts"
OUTBOUND = DA / "artifacts" / "outbound_design_v1"
BE = DA / "artifacts" / "be_handoff_v2"
V3 = DA / "artifacts" / "candidate_policy_v3"
NOTEBOOK = DA / "notebooks" / "foundation" / "04_regulatory_outbound_design_analysis.ipynb"
DOC = DA / "docs" / "BE_HANDOFF_DIGITAL_ASSET_V2.md"


FIELD_META: dict[str, dict[str, str | bool]] = {
    "originator_identity": {
        "source_system": "INTERNAL_CUSTOMER_MASTER",
        "source_trust_level": "TRUSTED_INTERNAL",
        "field_role": "REGULATORY_ATTRIBUTE|OUTBOUND_PAYLOAD_FIELD",
        "transform_type": "MINIMIZE|MAP_TO_EXTERNAL_SCHEMA",
        "destination": "TRAVEL_RULE_PROVIDER|EXTERNAL_VASP",
        "required_exact": True,
        "retention_requirement": "RETAIN_FOR_REGULATORY_RECORD",
        "audit_requirement": "AUDIT_REQUIRED",
    },
    "beneficiary_identity": {
        "source_system": "INTERNAL_CUSTOMER_MASTER|TRAVEL_RULE_PROVIDER",
        "source_trust_level": "TRUSTED_INTERNAL_OR_PROVIDER",
        "field_role": "REGULATORY_ATTRIBUTE|OUTBOUND_PAYLOAD_FIELD",
        "transform_type": "MINIMIZE|MAP_TO_EXTERNAL_SCHEMA",
        "destination": "TRAVEL_RULE_PROVIDER|EXTERNAL_VASP",
        "required_exact": True,
        "retention_requirement": "RETAIN_FOR_REGULATORY_RECORD",
        "audit_requirement": "AUDIT_REQUIRED",
    },
    "originator_address": {
        "source_system": "APPROVED_TRANSACTION|BLOCKCHAIN_EXECUTION_LAYER",
        "source_trust_level": "APPROVED_INPUT_OR_CHAIN_OBSERVED",
        "field_role": "REQUEST_VALUE|OUTBOUND_PAYLOAD_FIELD|TRACE_FIELD",
        "transform_type": "FORMAT_NORMALIZE",
        "destination": "BLOCKCHAIN_EXECUTION_SYSTEM|INTERNAL_RECONCILIATION_ONLY",
        "required_exact": True,
        "retention_requirement": "RETAIN_FOR_TRACE",
        "audit_requirement": "AUDIT_REQUIRED",
    },
    "beneficiary_address": {
        "source_system": "APPROVED_TRANSACTION|BLOCKCHAIN_EXECUTION_LAYER",
        "source_trust_level": "APPROVED_INPUT_OR_CHAIN_OBSERVED",
        "field_role": "REQUEST_VALUE|DESTINATION_ATTRIBUTE|OUTBOUND_PAYLOAD_FIELD|TRACE_FIELD",
        "transform_type": "FORMAT_NORMALIZE",
        "destination": "BLOCKCHAIN_EXECUTION_SYSTEM|INTERNAL_RECONCILIATION_ONLY",
        "required_exact": True,
        "retention_requirement": "RETAIN_FOR_TRACE",
        "audit_requirement": "AUDIT_REQUIRED",
    },
    "amount": {
        "source_system": "APPROVED_TRANSACTION|BLOCKCHAIN_EXECUTION_LAYER",
        "source_trust_level": "APPROVED_INPUT_OR_CHAIN_OBSERVED",
        "field_role": "PRE_APPROVED_VALUE|REQUEST_VALUE|OUTBOUND_PAYLOAD_FIELD|TRACE_FIELD",
        "transform_type": "FORMAT_NORMALIZE",
        "destination": "BLOCKCHAIN_EXECUTION_SYSTEM|INTERNAL_RECONCILIATION_ONLY",
        "required_exact": True,
        "retention_requirement": "RETAIN_FOR_TRACE",
        "audit_requirement": "AUDIT_REQUIRED",
    },
    "asset": {
        "source_system": "APPROVED_TRANSACTION|INTERNAL_POLICY_STORE",
        "source_trust_level": "APPROVED_INTERNAL",
        "field_role": "PRE_APPROVED_VALUE|REQUEST_VALUE|OUTBOUND_PAYLOAD_FIELD",
        "transform_type": "FORMAT_NORMALIZE",
        "destination": "BLOCKCHAIN_EXECUTION_SYSTEM|TRAVEL_RULE_PROVIDER",
        "required_exact": True,
        "retention_requirement": "RETAIN_FOR_TRACE",
        "audit_requirement": "AUDIT_REQUIRED",
    },
    "counterparty_vasp": {
        "source_system": "VASP_DIRECTORY_OR_PROVIDER|TRAVEL_RULE_PROVIDER",
        "source_trust_level": "TRUSTED_EXTERNAL_RESULT",
        "field_role": "REGULATORY_ATTRIBUTE|DESTINATION_ATTRIBUTE",
        "transform_type": "MAP_TO_EXTERNAL_SCHEMA|SPLIT_INTERNAL_EXTERNAL",
        "destination": "TRAVEL_RULE_PROVIDER|EXTERNAL_VASP|INTERNAL_AUDIT_ONLY",
        "required_exact": True,
        "retention_requirement": "RETAIN_FOR_REGULATORY_RECORD",
        "audit_requirement": "AUDIT_REQUIRED",
    },
    "kyc_status": {
        "source_system": "KYC_AML_SYSTEM",
        "source_trust_level": "TRUSTED_EXTERNAL_RESULT",
        "field_role": "REGULATORY_ATTRIBUTE|TRANSFORM_INPUT",
        "transform_type": "OMIT",
        "destination": "NOT_EXTERNALIZED|INTERNAL_AUDIT_ONLY",
        "required_exact": True,
        "retention_requirement": "RETAIN_STATUS_REFERENCE_ONLY",
        "audit_requirement": "AUDIT_REQUIRED",
    },
    "transaction_id": {
        "source_system": "APPROVED_TRANSACTION|BLOCKCHAIN_EXECUTION_LAYER",
        "source_trust_level": "APPROVED_INPUT_OR_CHAIN_OBSERVED",
        "field_role": "TRACE_FIELD|OUTBOUND_PAYLOAD_FIELD",
        "transform_type": "PASS_THROUGH",
        "destination": "TRAVEL_RULE_PROVIDER|INTERNAL_RECONCILIATION_ONLY",
        "required_exact": True,
        "retention_requirement": "RETAIN_FOR_TRACE",
        "audit_requirement": "AUDIT_REQUIRED",
    },
    "tx_hash": {
        "source_system": "BLOCKCHAIN_EXECUTION_LAYER|EXTERNAL_EXECUTION_RESPONSE",
        "source_trust_level": "CHAIN_OBSERVED_OR_EXECUTION_RESPONSE",
        "field_role": "TRACE_FIELD|EXECUTION_RESULT_FIELD",
        "transform_type": "PASS_THROUGH",
        "destination": "INTERNAL_RECONCILIATION_ONLY",
        "required_exact": True,
        "retention_requirement": "RETAIN_FOR_RECONCILIATION",
        "audit_requirement": "AUDIT_REQUIRED",
    },
    "execution_status": {
        "source_system": "EXTERNAL_EXECUTION_RESPONSE",
        "source_trust_level": "TRUSTED_EXTERNAL_RESULT",
        "field_role": "EXECUTION_RESULT_FIELD|TRACE_FIELD",
        "transform_type": "PASS_THROUGH",
        "destination": "INTERNAL_RECONCILIATION_ONLY|INTERNAL_AUDIT_ONLY",
        "required_exact": True,
        "retention_requirement": "RETAIN_FOR_RECONCILIATION",
        "audit_requirement": "AUDIT_REQUIRED",
    },
    "timestamp": {
        "source_system": "BLOCKCHAIN_EXECUTION_LAYER|EXTERNAL_EXECUTION_RESPONSE",
        "source_trust_level": "CHAIN_OBSERVED_OR_EXECUTION_RESPONSE",
        "field_role": "TRACE_FIELD|EXECUTION_RESULT_FIELD",
        "transform_type": "PASS_THROUGH",
        "destination": "INTERNAL_RECONCILIATION_ONLY|INTERNAL_AUDIT_ONLY",
        "required_exact": True,
        "retention_requirement": "RETAIN_FOR_TRACE",
        "audit_requirement": "AUDIT_REQUIRED",
    },
}

TYPE_BY_CONTROL = {
    "COUNTERPARTY_VASP_VERIFY": "REQUIRED_EXTERNAL_STATUS",
    "KYC_STATUS_CHECK": "REQUIRED_CHECK",
    "TRANSFER_RESTRICTION": "REQUIRED_MATCH",
    "ORIGINATOR_VERIFY": "REQUIRED_TRANSFER",
    "BENEFICIARY_VERIFY": "REQUIRED_TRANSFER",
    "INFORMATION_TRANSFER": "REQUIRED_INCLUDE",
    "RECORD_KEEPING": "REQUIRED_RETAIN",
    "ADDRESS_VERIFY": "REQUIRED_DESTINATION_CHECK",
}

OPERATIONAL_FIELDS = {
    "originator_address": "Approved/execution address is needed to build the outbound execution payload and trace what was handed off.",
    "beneficiary_address": "Requested/approved destination address is needed for handoff destination validation.",
    "amount": "Requested/approved value is needed for outbound amount validation.",
    "tx_hash": "Execution tx hash is needed after handoff for audit and reconciliation trace.",
    "timestamp": "Execution or request timestamp is needed for trace ordering and retention.",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8-sig", newline="") as fp:
        return list(csv.DictReader(fp))


def digest_payload(payload: Any) -> dict[str, str]:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return {"algorithm": "sha256", "value": hashlib.sha256(encoded).hexdigest()}


def requirement_row(raw: dict[str, str], mapping_by_field: dict[str, dict[str, str]], idx: int) -> dict[str, Any]:
    field = raw["required_field"]
    meta = FIELD_META[field]
    mapping = mapping_by_field.get(field, {})
    current = raw["effective_status"] == "CURRENT" and raw["fpg_scope"] != "OUT_OF_SCOPE"
    return {
        "requirement_id": f"OR-DA-{idx:03d}",
        "jurisdiction": raw["jurisdiction"],
        "regulation_name": raw["regulation_name"],
        "article": raw["article"],
        "paragraph": raw["paragraph"],
        "effective_status": raw["effective_status"],
        "obligation_id": raw["obligation_id"],
        "obligation_summary": raw["obligation_text"],
        "outbound_requirement_type": TYPE_BY_CONTROL.get(raw["control_type"], "REQUIRED_CHECK"),
        "required_field": field,
        "field_role": meta["field_role"],
        "source_system": meta["source_system"],
        "source_trust_level": meta["source_trust_level"],
        "transform_type": meta["transform_type"],
        "destination": meta["destination"],
        "mandatory_level": "MANDATORY" if current else "OUT_OF_SCOPE_OR_MONITORING",
        "trigger_condition": raw["condition"],
        "handoff_condition": "Required input must be resolved before outbound handoff." if current else "Do not enforce as current outbound handoff requirement.",
        "on_missing_action": "REVIEW" if raw["source_system"] in {"VASP_INTERNAL", "EXTERNAL_KYC_SYSTEM"} else ("BLOCK" if current else "NO_RUNTIME_ACTION"),
        "retention_requirement": meta["retention_requirement"],
        "audit_requirement": meta["audit_requirement"],
        "fpg_scope": raw["fpg_scope"],
        "legal_basis_reference": f"{raw['source']}::{raw['regulation_name']}::{raw['article']}::{raw['paragraph']}",
        "evidence_type": "LEGAL_REQUIREMENT" if current else "LEGAL_MONITORING_ONLY",
        "required_exact": str(meta["required_exact"]).upper(),
        "ethereum_field": mapping.get("ethereum_field", ""),
        "availability_class": mapping.get("availability_class", "UNMAPPED"),
        "note": raw["source_note"],
    }


def operational_requirement_rows(start_idx: int, mapping_by_field: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for offset, (field, reason) in enumerate(OPERATIONAL_FIELDS.items(), start=start_idx):
        meta = FIELD_META[field]
        mapping = mapping_by_field.get(field, {})
        evidence_type = "EXECUTION_REQUIREMENT" if field in {"tx_hash", "timestamp"} else "INTERNAL_APPROVAL_REQUIREMENT"
        rows.append(
            {
                "requirement_id": f"OR-DA-{offset:03d}",
                "jurisdiction": "SYSTEM",
                "regulation_name": "FPG Digital Asset outbound design",
                "article": "N/A",
                "paragraph": "N/A",
                "effective_status": "DESIGN_REQUIRED",
                "obligation_id": f"DA-DESIGN-{offset:03d}",
                "obligation_summary": reason,
                "outbound_requirement_type": "REQUIRED_TRACE" if field in {"tx_hash", "timestamp"} else "REQUIRED_MATCH",
                "required_field": field,
                "field_role": meta["field_role"],
                "source_system": meta["source_system"],
                "source_trust_level": meta["source_trust_level"],
                "transform_type": meta["transform_type"],
                "destination": meta["destination"],
                "mandatory_level": "MANDATORY_FOR_HANDOFF_DESIGN",
                "trigger_condition": "approved transaction is prepared for outbound handoff",
                "handoff_condition": "Required exact value must be present or resolvable for its destination layer.",
                "on_missing_action": "BLOCK" if field not in {"tx_hash", "timestamp"} else "REVIEW_AFTER_HANDOFF",
                "retention_requirement": meta["retention_requirement"],
                "audit_requirement": meta["audit_requirement"],
                "fpg_scope": "DIRECT_ENFORCEMENT" if field not in {"tx_hash", "timestamp"} else "TRACE_RECONCILIATION",
                "legal_basis_reference": "INTERNAL_APPROVAL_OR_EXECUTION_REQUIREMENT",
                "evidence_type": evidence_type,
                "required_exact": str(meta["required_exact"]).upper(),
                "ethereum_field": mapping.get("ethereum_field", ""),
                "availability_class": mapping.get("availability_class", "UNMAPPED"),
                "note": "Separated from legal obligation rows to avoid inventing legal basis.",
            }
        )
    return rows


def execution_mapping(requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def layer(availability: str, source: str) -> str:
        if availability == "ONCHAIN_AVAILABLE":
            return "ONCHAIN"
        if availability == "DERIVABLE_FROM_ONCHAIN":
            return "BOTH"
        if "KYC_AML_SYSTEM" in source or "VASP_DIRECTORY_OR_PROVIDER" in source or "TRAVEL_RULE_PROVIDER" in source:
            return "OFFCHAIN_EXTERNAL"
        if "INTERNAL" in source or "APPROVED_TRANSACTION" in source:
            return "OFFCHAIN_INTERNAL"
        return "NOT_AVAILABLE"

    rows = []
    for req in requirements:
        availability_layer = layer(req["availability_class"], req["source_system"])
        external_required = availability_layer in {"OFFCHAIN_EXTERNAL", "BOTH"} or "EXTERNAL" in req["source_system"]
        fpg_input_required = availability_layer != "ONCHAIN" or req["required_field"] in {"originator_identity", "beneficiary_identity", "kyc_status", "counterparty_vasp"}
        rows.append(
            {
                "requirement_id": req["requirement_id"],
                "required_field": req["required_field"],
                "ethereum_field": req["ethereum_field"],
                "availability_layer": availability_layer,
                "execution_availability": req["availability_class"],
                "external_source_required": str(external_required).upper(),
                "fpg_input_required": str(fpg_input_required).upper(),
                "outbound_destination": req["destination"],
                "note": "Execution layer fields do not replace off-chain regulatory attributes.",
            }
        )
    return rows


def build_matrix(requirements: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "v1",
        "artifact_id": "ORM-DA-REGULATED-TRANSFER-001",
        "artifact_version": "v1",
        "scope": "Digital Asset regulated outbound handoff requirement matrix",
        "fpg_role": "Policy Enforcement Gateway for already-approved transactions before external execution handoff.",
        "decision_semantics": {
            "PASS": "Current outbound handoff requirements are satisfied. This is not transaction approval.",
            "BLOCK": "The approved transaction may exist, but current outbound handoff requirements are not satisfied, so handoff stops.",
            "REVIEW": "Required internal/external information is missing, pending, unresolved, or ambiguous, so handoff is held.",
        },
        "requirements": [
            {
                "requirement_id": row["requirement_id"],
                "legal_basis": row["legal_basis_reference"],
                "trigger": row["trigger_condition"],
                "source": row["source_system"],
                "required_fields": [row["required_field"]],
                "field_roles": row["field_role"].split("|"),
                "transform": row["transform_type"].split("|"),
                "destination": row["destination"].split("|"),
                "required_exact": row["required_exact"] == "TRUE",
                "validation": row["handoff_condition"],
                "on_missing": row["on_missing_action"],
                "on_mismatch": "BLOCK for required exact approved/request mismatch; REVIEW when external status is pending.",
                "audit": row["audit_requirement"],
                "effective_status": row["effective_status"],
                "evidence_type": row["evidence_type"],
            }
            for row in requirements
        ],
    }


def runtime_pipeline() -> dict[str, Any]:
    steps = [
        ("Approved Transaction Load", "approved transaction id, requested asset/address/amount", "normalized approved/request values", "APPROVED_TRANSACTION", "missing approved transaction", "load and validate presence only"),
        ("Policy Snapshot Load", "approved policy snapshot id", "policy constraints", "INTERNAL_POLICY_STORE", "missing policy snapshot", "load current snapshot reference"),
        ("Regulatory Context Load", "jurisdiction, transfer context", "applicable outbound requirements", "FPG_REGULATORY_CONTEXT", "unmapped jurisdiction", "select candidate requirements"),
        ("External Status Load", "KYC, VASP, Travel Rule statuses", "trusted status references", "KYC_AML_SYSTEM|VASP_DIRECTORY_OR_PROVIDER|TRAVEL_RULE_PROVIDER", "pending or unavailable provider result", "consume status result only"),
        ("Required Field Resolution", "source system fields", "resolved required field set", "FPG", "unresolved field", "map fields without creating KYC/settlement facts"),
        ("Approved vs Requested Match", "approved/request values", "match result", "FPG", "destination/amount/asset mismatch", "compare required exact values"),
        ("Required Exact Validation", "exact fields", "exact validation result", "FPG", "lossy transform requested for exact field", "preserve exact values where legally/operationally required"),
        ("Transform / Field Separation", "resolved fields", "internal/external field partitions", "FPG", "unsafe externalization", "minimize, map, omit, or split fields by destination"),
        ("Destination-specific Payload Build", "field partitions", "execution/travel-rule payloads", "FPG", "destination schema gap", "build payload; do not send every field on-chain"),
        ("Outbound Handoff Decision", "validation outcomes", "PASS/BLOCK/REVIEW", "FPG", "ambiguous status", "decide handoff readiness only"),
        ("External Execution Handoff", "execution payload", "handoff id", "BLOCKCHAIN_EXECUTION_SYSTEM|EXTERNAL_VASP", "handoff failure", "forward payload; no custody or signing claim"),
        ("Execution Result Binding", "handoff response", "tx hash/status reference", "EXTERNAL_EXECUTION_RESPONSE", "missing execution result", "bind external result to trace"),
        ("Audit / Reconciliation Trace", "all refs and decisions", "audit trace", "FPG", "trace mismatch", "retain lineage for reconciliation"),
    ]
    return {
        "schema_version": "v1",
        "artifact_id": "RTP-DA-REGULATED-TRANSFER-001",
        "artifact_version": "v1",
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
            for i, (name, inp, out, system, failure, responsibility) in enumerate(steps, start=1)
        ],
    }


def schema_files() -> None:
    base_required = ["schema_version", "artifact_id", "artifact_version"]
    write_json(
        CONTRACTS / "outbound_requirement_matrix.schema.json",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Digital Asset Outbound Requirement Matrix",
            "type": "object",
            "required": [*base_required, "requirements", "decision_semantics"],
            "properties": {
                "schema_version": {"type": "string", "const": "v1"},
                "artifact_id": {"type": "string"},
                "artifact_version": {"type": "string"},
                "scope": {"type": "string"},
                "fpg_role": {"type": "string"},
                "decision_semantics": {"type": "object"},
                "requirements": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["requirement_id", "legal_basis", "source", "required_fields", "transform", "destination", "required_exact", "evidence_type"],
                        "properties": {
                            "requirement_id": {"type": "string"},
                            "legal_basis": {"type": "string"},
                            "trigger": {"type": "string"},
                            "source": {"type": "string"},
                            "required_fields": {"type": "array", "items": {"type": "string"}},
                            "field_roles": {"type": "array", "items": {"type": "string"}},
                            "transform": {"type": "array", "items": {"type": "string"}},
                            "destination": {"type": "array", "items": {"type": "string"}},
                            "required_exact": {"type": "boolean"},
                            "validation": {"type": "string"},
                            "on_missing": {"type": "string"},
                            "on_mismatch": {"type": "string"},
                            "audit": {"type": "string"},
                            "effective_status": {"type": "string"},
                            "evidence_type": {"type": "string"},
                        },
                        "additionalProperties": False,
                    },
                },
            },
            "additionalProperties": False,
        },
    )
    write_json(
        CONTRACTS / "runtime_pipeline.schema.json",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Digital Asset Runtime Pipeline",
            "type": "object",
            "required": [*base_required, "steps"],
            "properties": {
                "schema_version": {"type": "string", "const": "v1"},
                "artifact_id": {"type": "string"},
                "artifact_version": {"type": "string"},
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["step_number", "name", "input", "output", "responsible_system", "failure_mode", "fpg_responsibility"],
                        "properties": {
                            "step_number": {"type": "integer"},
                            "name": {"type": "string"},
                            "input": {"type": "string"},
                            "output": {"type": "string"},
                            "responsible_system": {"type": "string"},
                            "failure_mode": {"type": "string"},
                            "fpg_responsibility": {"type": "string"},
                        },
                        "additionalProperties": False,
                    },
                },
            },
            "additionalProperties": False,
        },
    )


def be_handoff(requirements: list[dict[str, Any]], matrix: dict[str, Any]) -> None:
    required_input_fields = sorted({row["required_field"] for row in requirements if row["mandatory_level"] != "OUT_OF_SCOPE_OR_MONITORING"})
    policy_eval = {
        "schema_version": "v1",
        "artifact_id": "PE-DA-REGULATED-TRANSFER-002",
        "artifact_version": "v2",
        "analysis_status": "candidate",
        "policy_action": "candidate_handoff",
        "approved_policy_ref": "DA-CANDIDATE-POLICY-REGULATED-TRANSFER-003",
        "execution_request_ref": "APPROVED_TRANSACTION_RUNTIME_INPUT",
        "policy_rule_refs": [{"ref_id": row["requirement_id"], "ref_type": "outbound_requirement", "version": "v1"} for row in requirements],
        "required_input_fields": required_input_fields,
        "decision_values": ["PASS", "BLOCK", "REVIEW"],
        "handoff_chain": [
            "Approved Transaction",
            "FPG Regulatory Outbound Processing",
            "Outbound Requirement Validation",
            "Transform / Field Mapping / Field Separation",
            "External Handoff",
            "Execution Result",
            "Trace / Reconciliation",
        ],
        "limitations": [
            "FPG is not a transaction approval system.",
            "FPG does not perform KYC/AML itself; it consumes trusted status results.",
            "FPG is not wallet, signing, custody, smart-contract, settlement, or finality infrastructure.",
            "Runtime data class, destination profile enum, retry policy, reconciliation event schema, and production settlement state remain CONTRACT_GAP.",
            "Synthetic v1/v2/v3 outputs are EXPERIMENTAL_POLICY_SIMULATION and not main design evidence.",
        ],
        "digest": digest_payload(matrix),
    }
    binding = {
        "schema_version": "v1",
        "binding_version": "v2",
        "bindings": [
            {
                "digital_asset_runtime": "REGULATED_VIRTUAL_ASSET_TRANSFER_OUTBOUND_HANDOFF",
                "approved_transaction_identifier": "CONTRACT_GAP",
                "approved_policy_snapshot_identifier": "CONTRACT_GAP",
                "workload_id": "UNMAPPED",
                "purpose": "UNMAPPED",
                "runtime_data_class": "UNMAPPED",
                "destination_profile": "CONTRACT_GAP",
                "binding_status": "candidate_contract_gap",
                "notes": "BE-owned identifiers/enums are not invented by DA analysis.",
            }
        ],
    }
    crosswalk = {
        "schema_version": "v1",
        "crosswalk_version": "v2",
        "mappings": [
            {
                "regulatory_required_field": row["required_field"],
                "source_system": row["source_system"],
                "field_role": row["field_role"],
                "destination": row["destination"],
                "transform_instruction": row["transform_type"],
                "required_exact": row["required_exact"],
                "runtime_data_class": "UNMAPPED",
                "mapping_status": "unmapped",
                "mapping_basis": row["requirement_id"],
            }
            for row in requirements
        ],
    }
    outbound_req = {
        "schema_version": "v1",
        "artifact_id": "OR-DA-REGULATED-TRANSFER-001",
        "artifact_version": "v1",
        "matrix_ref": matrix["artifact_id"],
        "requirements": matrix["requirements"],
        "contract_gap": [
            "Travel Rule provider payload schema",
            "VASP directory/provider response schema",
            "Approved transaction runtime input schema",
            "Destination profile enum",
            "Execution handoff id lifecycle",
            "Execution receipt/status ingestion",
            "Retry/reconciliation event schema",
            "Audit event schema",
        ],
    }
    write_json(BE / "policy_evaluations" / "PE-DA-REGULATED-TRANSFER-002.json", policy_eval)
    write_json(BE / "bindings" / "DAB-REGULATED-TRANSFER-002.json", binding)
    write_json(BE / "crosswalks" / "DA-RDC-REGULATED-TRANSFER-002.json", crosswalk)
    write_json(BE / "outbound_requirements" / "OR-DA-REGULATED-TRANSFER-001.json", outbound_req)


def developer_doc(requirements: list[dict[str, Any]], matrix: dict[str, Any], pipeline: dict[str, Any], exec_map: list[dict[str, Any]]) -> None:
    counts = Counter(row["outbound_requirement_type"] for row in requirements)
    source_counts = Counter(part for row in requirements for part in row["source_system"].split("|"))
    dest_counts = Counter(part for row in requirements for part in row["destination"].split("|"))
    transform_counts = Counter(part for row in requirements for part in row["transform_type"].split("|"))
    layer_counts = Counter(row["availability_layer"] for row in exec_map)
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text(
        "\n".join(
            [
                "# BE Handoff Digital Asset V2",
                "",
                "## 1. FPG Digital Asset Role",
                "",
                "FPG is a policy enforcement gateway for already-approved digital asset transactions immediately before external execution handoff. PASS means outbound handoff requirements are satisfied; it is not transaction approval.",
                "",
                "## 2. Out Of Scope",
                "",
                "FPG does not perform KYC/AML, wallet signing, custody, smart-contract execution, settlement, or settlement finality.",
                "",
                "## 3. Approved Transaction Input Layer",
                "",
                "BE must provide approved transaction id, policy snapshot id, requested asset, amount, destination, source/destination address where applicable, and runtime context. Missing BE-owned identifiers remain CONTRACT_GAP.",
                "",
                "## 4. Legal Obligation To Outbound Requirement",
                "",
                f"Current matrix rows: {len(requirements)}. Legal obligations are separated from internal approval and execution requirements so legal basis is not invented.",
                "",
                "## 5. Required Field",
                "",
                ", ".join(sorted({row["required_field"] for row in requirements})),
                "",
                "## 6. Source System",
                "",
                json.dumps(dict(source_counts), ensure_ascii=False),
                "",
                "## 7. Transform",
                "",
                json.dumps(dict(transform_counts), ensure_ascii=False),
                "",
                "## 8. Destination",
                "",
                json.dumps(dict(dest_counts), ensure_ascii=False),
                "",
                "## 9. PASS / BLOCK / REVIEW",
                "",
                "- PASS: current outbound handoff requirements are satisfied.",
                "- BLOCK: approved transaction may exist, but outbound handoff cannot proceed in the current state.",
                "- REVIEW: required internal/external information is pending, missing, unresolved, or ambiguous.",
                "",
                "## 10. Runtime Pipeline",
                "",
                "\n".join(f"{step['step_number']}. {step['name']} - {step['fpg_responsibility']}" for step in pipeline["steps"]),
                "",
                "## 11. JSON Artifacts",
                "",
                "- `03_digital_asset/artifacts/outbound_design_v1/outbound_requirement_matrix.json`",
                "- `03_digital_asset/artifacts/outbound_design_v1/runtime_pipeline.json`",
                "- `03_digital_asset/artifacts/be_handoff_v2/policy_evaluations/PE-DA-REGULATED-TRANSFER-002.json`",
                "- `03_digital_asset/artifacts/be_handoff_v2/bindings/DAB-REGULATED-TRANSFER-002.json`",
                "- `03_digital_asset/artifacts/be_handoff_v2/crosswalks/DA-RDC-REGULATED-TRANSFER-002.json`",
                "- `03_digital_asset/artifacts/be_handoff_v2/outbound_requirements/OR-DA-REGULATED-TRANSFER-001.json`",
                "",
                "## 12. Reused AI/BE Contract Concepts",
                "",
                "Reused: policy evaluation artifact id/version/status, binding, crosswalk, decision values, refs, digest, and candidate handoff semantics.",
                "",
                "## 13. BE Extensions Required",
                "",
                "Runtime enums are needed for approved transaction identifier, approved policy snapshot identifier, runtime data class, destination profile, transform instruction, external provider result, outbound decision, execution handoff id, execution tx hash/status, and audit trace id.",
                "",
                "## 14. Contract Gap",
                "",
                "Travel Rule payload, VASP provider response, retry policy, reconciliation event, production settlement state, and audit event schema remain CONTRACT_GAP.",
                "",
                "## 15. Example Flow",
                "",
                "CASE 1 PASS: approved transaction exists -> exact fields resolve -> destination/amount match -> payload builds -> external handoff.",
                "",
                "CASE 2 BLOCK: approved destination differs from requested destination -> transaction approval is not cancelled by FPG, but outbound handoff stops.",
                "",
                "CASE 3 REVIEW: counterparty VASP or Travel Rule provider result is pending -> outbound handoff is held.",
                "",
                "## Synthetic Position",
                "",
                "Synthetic v1/v2/v3 and false-allow experiments are classified as EXPERIMENTAL_POLICY_SIMULATION. They are not main design evidence and do not estimate real transaction failure or regulatory violation rates.",
                "",
                "## Current Coverage Summary",
                "",
                f"Outbound requirement types: {json.dumps(dict(counts), ensure_ascii=False)}",
                "",
                f"On-chain/off-chain mapping: {json.dumps(dict(layer_counts), ensure_ascii=False)}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def build_notebook() -> None:
    nb = nbf.v4.new_notebook()
    nb["metadata"] = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3.12"}}
    cells = [
        nbf.v4.new_markdown_cell("# Regulatory Outbound Design Analysis\n\n## tl;dr\n\nThis notebook converts Digital Asset regulatory analysis into outbound handoff design artifacts. It excludes synthetic policy simulation from main design evidence."),
        nbf.v4.new_markdown_cell("## Context & Methods\n\nInputs are regulatory raw obligations, Ethereum transaction field mapping v3, outbound requirement CSV, execution mapping, and runtime pipeline artifacts.\n\n### Key Assumptions\n\nFPG is a pre-external-handoff policy enforcement gateway. It does not approve transactions, perform KYC/AML, custody assets, sign transactions, execute smart contracts, or guarantee settlement finality."),
        nbf.v4.new_code_cell(
            "# ruff: noqa: E501, E701, E702, I001\n"
            "\n"
            "from pathlib import Path\nimport json\nimport pandas as pd\nimport matplotlib.pyplot as plt\n"
            "ROOT = Path.cwd().resolve()\nif ROOT.name != 'ADP-DA': ROOT = next(p for p in [ROOT, *ROOT.parents] if p.name == 'ADP-DA')\n"
            "req = pd.read_csv(ROOT/'03_digital_asset/data/processed/regulatory_outbound_requirements.csv')\n"
            "exec_map = pd.read_csv(ROOT/'03_digital_asset/data/processed/outbound_requirement_execution_mapping.csv')\n"
            "matrix = json.loads((ROOT/'03_digital_asset/artifacts/outbound_design_v1/outbound_requirement_matrix.json').read_text(encoding='utf-8'))\n"
            "pipeline = json.loads((ROOT/'03_digital_asset/artifacts/outbound_design_v1/runtime_pipeline.json').read_text(encoding='utf-8'))\n"
            "print({'requirements': len(req), 'pipeline_steps': len(pipeline['steps']), 'matrix_requirements': len(matrix['requirements'])})"
        ),
        nbf.v4.new_markdown_cell("## Data\n\n### 1. Legal Obligation Distribution"),
        nbf.v4.new_code_cell("display(req.groupby(['evidence_type','effective_status']).size().reset_index(name='count'))"),
        nbf.v4.new_markdown_cell("## Results\n\n### 2. Outbound Requirement Type Distribution"),
        nbf.v4.new_code_cell("counts = req['outbound_requirement_type'].value_counts().reset_index(); counts.columns=['outbound_requirement_type','count']; display(counts); counts.plot.bar(x='outbound_requirement_type', y='count', legend=False, color='#2f6f8f', title='Outbound Requirement Type Distribution'); plt.xticks(rotation=45, ha='right'); plt.tight_layout()"),
        nbf.v4.new_markdown_cell("### 3. Required Field x Source System"),
        nbf.v4.new_code_cell("src = req.assign(source_system=req['source_system'].str.split('|')).explode('source_system')\ndisplay(src.groupby(['required_field','source_system']).size().unstack(fill_value=0))"),
        nbf.v4.new_markdown_cell("### 4. Required Field x Destination"),
        nbf.v4.new_code_cell("dest = req.assign(destination=req['destination'].str.split('|')).explode('destination')\ndisplay(dest.groupby(['required_field','destination']).size().unstack(fill_value=0))"),
        nbf.v4.new_markdown_cell("### 5. Required Field x Transform"),
        nbf.v4.new_code_cell("tr = req.assign(transform_type=req['transform_type'].str.split('|')).explode('transform_type')\ndisplay(tr.groupby(['required_field','transform_type']).size().unstack(fill_value=0))"),
        nbf.v4.new_markdown_cell("### 6. On-chain vs Off-chain Distribution"),
        nbf.v4.new_code_cell("layers = exec_map['availability_layer'].value_counts().reset_index(); layers.columns=['availability_layer','count']; display(layers); layers.plot.bar(x='availability_layer', y='count', legend=False, color='#4f8f65', title='On-chain vs Off-chain Requirement Mapping'); plt.xticks(rotation=45, ha='right'); plt.tight_layout()"),
        nbf.v4.new_markdown_cell("### 7. Mandatory vs Conditional"),
        nbf.v4.new_code_cell("display(req['mandatory_level'].value_counts().rename_axis('mandatory_level').reset_index(name='count'))"),
        nbf.v4.new_markdown_cell("### 8. Required Exact Ratio"),
        nbf.v4.new_code_cell(
            "exact_ratio = req['required_exact'].mean() if req['required_exact'].dtype == bool else (req['required_exact'].astype(str) == 'TRUE').mean(); print({'required_exact_ratio': round(exact_ratio, 4)})"
        ),
        nbf.v4.new_markdown_cell("### 9. Externalized vs Internal-only"),
        nbf.v4.new_code_cell("destination_flags = dest.assign(externalized=dest['destination'].isin(['EXTERNAL_VASP','TRAVEL_RULE_PROVIDER','BLOCKCHAIN_EXECUTION_SYSTEM'])); display(destination_flags.groupby('externalized').size().reset_index(name='field_destination_rows'))"),
        nbf.v4.new_markdown_cell("### 10. Control -> Requirement -> Field -> Destination Lineage"),
        nbf.v4.new_code_cell("display(req[['requirement_id','obligation_id','outbound_requirement_type','required_field','source_system','destination','transform_type','evidence_type']])"),
        nbf.v4.new_markdown_cell("## Takeaways\n\nThe design separates legal requirement, internal approval requirement, execution requirement, and privacy requirement. BE can implement the handoff using versioned JSON artifacts, but BE-owned runtime enums and provider schemas remain contract gaps."),
    ]
    nb["cells"] = cells
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, NOTEBOOK)


def validate_outputs(matrix: dict[str, Any], pipeline: dict[str, Any]) -> dict[str, Any]:
    validations = []
    pairs = [
        (CONTRACTS / "outbound_requirement_matrix.schema.json", matrix),
        (CONTRACTS / "runtime_pipeline.schema.json", pipeline),
        (DA / "contracts" / "digital_asset_policy_evaluation.schema.json", read_json(BE / "policy_evaluations" / "PE-DA-REGULATED-TRANSFER-002.json")),
    ]
    for schema_path, payload in pairs:
        jsonschema.validate(payload, read_json(schema_path))
        validations.append({"schema": str(schema_path.relative_to(ROOT)), "status": "PASS"})
    return {"validations": validations}


def main() -> None:
    raw = load_csv(RAW_REG)
    mapping = load_csv(PROCESSED / "regulatory_transaction_field_mapping_v3.csv")
    mapping_by_field = {row["required_field"]: row for row in mapping}
    current_raw = [row for row in raw if row["effective_status"] == "CURRENT" and row["fpg_scope"] != "OUT_OF_SCOPE"]
    requirements = [requirement_row(row, mapping_by_field, idx) for idx, row in enumerate(current_raw, start=1)]
    requirements.extend(operational_requirement_rows(len(requirements) + 1, mapping_by_field))
    fields = [
        "requirement_id",
        "jurisdiction",
        "regulation_name",
        "article",
        "paragraph",
        "effective_status",
        "obligation_id",
        "obligation_summary",
        "outbound_requirement_type",
        "required_field",
        "field_role",
        "source_system",
        "source_trust_level",
        "transform_type",
        "destination",
        "mandatory_level",
        "trigger_condition",
        "handoff_condition",
        "on_missing_action",
        "retention_requirement",
        "audit_requirement",
        "fpg_scope",
        "legal_basis_reference",
        "evidence_type",
        "required_exact",
        "ethereum_field",
        "availability_class",
        "note",
    ]
    write_csv(PROCESSED / "regulatory_outbound_requirements.csv", requirements, fields)
    exec_map = execution_mapping(requirements)
    write_csv(
        PROCESSED / "outbound_requirement_execution_mapping.csv",
        exec_map,
        ["requirement_id", "required_field", "ethereum_field", "availability_layer", "execution_availability", "external_source_required", "fpg_input_required", "outbound_destination", "note"],
    )
    matrix = build_matrix(requirements)
    pipeline = runtime_pipeline()
    schema_files()
    write_json(OUTBOUND / "outbound_requirement_matrix.json", matrix)
    write_json(OUTBOUND / "runtime_pipeline.json", pipeline)
    be_handoff(requirements, matrix)
    developer_doc(requirements, matrix, pipeline, exec_map)
    build_notebook()
    validation = validate_outputs(matrix, pipeline)
    write_json(OUTBOUND / "validation_report.json", validation)


if __name__ == "__main__":
    main()
