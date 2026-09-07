"""Reproducible DA-04 field-level evidence, not a provider adapter or live policy."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jsonschema
import pandas as pd
from build_control_boundary_v2 import (
    ALLOWED_TRANSFORM_BY_EXACT_CLASS,
    EXTERNAL_DESTINATIONS,
    INTERNAL_DESTINATIONS,
    validate_boundary,
)

ROOT = Path(__file__).resolve().parents[2]
DA = Path("03_digital_asset")
ARTIFACT = DA / "artifacts/da_04_outbound_destination"
NOTEBOOK = DA / "notebooks/runtime_validation/DA_04_outbound_destination.ipynb"
MATRIX = DA / "artifacts/outbound_design_vNext/outbound_requirement_matrix.json"
PIPELINE = DA / "artifacts/outbound_design_vNext/runtime_pipeline.json"
MASTER = DA / "data/processed/da_master_transaction_sample_73410.csv"
REQUIREMENTS = DA / "data/processed/regulatory_outbound_requirements.csv"
MAPPING = DA / "data/processed/outbound_requirement_execution_mapping.csv"
SOURCES = [
    MASTER,
    REQUIREMENTS,
    MAPPING,
    MATRIX,
    PIPELINE,
    DA / "artifacts/outbound_design_vNext/control_boundary_validation.json",
    DA / "artifacts/outbound_design_vNext/validation_report.json",
    DA / "notebooks/foundation/01_crypto_regulatory_analysis.ipynb",
    DA / "notebooks/foundation/04_regulatory_outbound_design_analysis.ipynb",
    DA / "notebooks/foundation/05_fpg_control_boundary_validation.ipynb",
    DA / "artifacts/da_00_master_sample/sampling_contract.json",
    DA / "artifacts/da_01_external_execution/runtime_requirements.json",
    DA / "docs/DA_02_EXACT_PRESERVATION_BE_HANDOFF.md",
    DA / "artifacts/da_03_trace_binding/evidence_binding_contract.json",
    DA / "src/build_control_boundary_v2.py",
    DA / "src/da_04_outbound_destination.py",
    DA / "contracts/da_04_evidence.schema.json",
]
# 01. Explicit analysis crosswalk; no provider keys or approval values are invented.
COLUMN_CROSSWALK = {
    "originator_address": ("from_address", "from_address"),
    "beneficiary_address": ("to_address", "to_address"),
    "amount": ("value_eth|value_wei", "value_lossless"),
    "tx_hash": ("hash", "transaction_hash"),
    "timestamp": ("block_timestamp", "block_timestamp"),
}
GAP_TEXT = {
    "PROVIDER_SCHEMA": "MINIMIZE/MAP_TO_EXTERNAL_SCHEMA provider wire schema is unresolved.",
    "TRANSACTION_ID_PHASE": "Legacy hash mapping cannot supply PRE_EXECUTION approval trace ID.",
    "ASSET_CONTEXT": "Native ETH context cannot identify every token/approved asset or its scale.",
    "EXECUTION_STATUS_MAPPING": (
        "receipt_status is evidence, not a contracted provider/finality enum."
    ),
    "UPSTREAM_INPUT": "Identity/KYC/VASP and approval inputs are absent from Ethereum Master.",
    "LEGAL_REVIEW": "Inherited candidate/review wording is retained; no new legal determination.",
    "PROVIDER_WIRE_AND_E2E": (
        "Field profiles do not establish provider acceptance or live BE execution."
    ),
    "APPROVAL_TRACE": "Master contains POST_EXECUTION observations, not approval/request lineage.",
    "SOURCE_PROVENANCE": (
        "No cloud re-extraction or original amount ground-truth revalidation here."
    ),
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise ValueError(detail)


def records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return json.loads(frame.to_json(orient="records"))


def normalize(matrix: dict, regulatory: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
    """vNext owns runtime semantics; CSV owns legal lineage and legacy source mapping."""
    for table in (regulatory, mapping):
        require(not table.requirement_id.duplicated().any(), "Duplicate requirement_id")
    ids = [r["requirement_id"] for r in matrix["requirements"]]
    require(len(ids) == len(set(ids)), "Duplicate vNext requirement_id")
    require(
        set(ids) == set(regulatory.requirement_id) == set(mapping.requirement_id),
        "Unmatched requirement IDs across sources",
    )
    reg = regulatory.set_index("requirement_id").to_dict("index")
    maps = mapping.set_index("requirement_id").to_dict("index")
    rows = []
    for item in matrix["requirements"]:
        rid = item["requirement_id"]
        old, link = reg[rid], maps[rid]
        require(
            item["required_fields"] == [old["required_field"]] == [link["required_field"]],
            f"Field lineage mismatch: {rid}",
        )
        require(item["legal_basis"] == old["legal_basis_reference"], f"Legal lineage: {rid}")
        field = old["required_field"]
        gaps = []
        if "CONTRACT_GAP" in item["comparison_canonicalization"]:
            gaps.append("PROVIDER_SCHEMA")
        if field == "transaction_id":
            gaps.append("TRANSACTION_ID_PHASE")
        if field == "asset":
            gaps.append("ASSET_CONTEXT")
        if field == "execution_status":
            gaps.append("EXECUTION_STATUS_MAPPING")
        if item["source_type"] == "UPSTREAM_PRODUCED_DATA":
            gaps.append("UPSTREAM_INPUT")
        if re.search(r"REVIEW_REQUIRED|candidate", old["note"], re.IGNORECASE):
            gaps.append("LEGAL_REVIEW")
        require(
            set(item["destination"]) == set(item["outbound_transform_by_destination"]),
            f"Destination transform incomplete: {rid}",
        )
        for dest in item["destination"]:
            transform = item["outbound_transform_by_destination"][dest]
            rows.append(
                {
                    "requirement_id": rid,
                    "required_field": field,
                    "regulation_name": old["regulation_name"],
                    "article": old["article"],
                    "obligation_id": old["obligation_id"],
                    "legal_basis_reference": item["legal_basis"],
                    "evidence_type": item["evidence_type"],
                    "legal_note": old["note"],
                    "source_system": old["source_system"],
                    "source_type": item["source_type"],
                    "availability_layer": link["availability_layer"],
                    "execution_availability": link["execution_availability"],
                    "ethereum_field": link["ethereum_field"],
                    "transform_type": transform,
                    "destination": dest,
                    "mandatory_level": old["mandatory_level"],
                    "required_exact": item["required_exact"],
                    "on_missing_action": item["on_missing"],
                    "runtime_phase": item["source_phase"],
                    "externalizable": dest in EXTERNAL_DESTINATIONS
                    and transform != "OMIT"
                    and item["required_exact"] != "INTERNAL_ONLY",
                    "contract_gap": sorted(set(gaps)),
                    "legacy_destination": old["destination"],
                    "legacy_transform": old["transform_type"],
                    "legacy_required_exact": old["required_exact"],
                    "legacy_on_missing": old["on_missing_action"],
                }
            )
    return pd.DataFrame(rows)


def contract_violations(matrix: dict, pipeline: dict) -> list[dict]:
    failures = []
    for row in matrix["requirements"]:
        if not set(row["destination"]) <= EXTERNAL_DESTINATIONS | INTERNAL_DESTINATIONS:
            failures.append(
                {"rule": "UNSUPPORTED_DESTINATION", "requirement_id": row["requirement_id"]}
            )
        if set(row["destination"]) != set(row["outbound_transform_by_destination"]):
            failures.append(
                {"rule": "DESTINATION_TRANSFORM_MISSING", "requirement_id": row["requirement_id"]}
            )
    failures.extend(validate_boundary(matrix, pipeline)["failures"])
    return failures


def profiles_from(frame: pd.DataFrame) -> list[dict]:
    internal = sorted(set(frame.loc[frame.required_exact == "INTERNAL_ONLY", "required_field"]))
    profiles = []
    for (dest, phase), group in frame.groupby(["destination", "runtime_phase"], sort=True):
        emitted = group[
            (group.transform_type != "OMIT") & (group.destination != "NOT_EXTERNALIZED")
        ]
        fields = sorted(set(emitted.required_field))
        mandatory = emitted[emitted.mandatory_level.str.startswith("MANDATORY")]
        profiles.append(
            {
                "destination": dest,
                "runtime_phase": phase,
                "allowed_fields": fields,
                "required_fields": sorted(set(mandatory.required_field)),
                "internal_only_fields": internal,
                "required_input_fields": sorted(set(group.required_field)),
                "omitted_fields": sorted(set(group.required_field) - set(fields)),
                "required_exact_fields": sorted(
                    set(emitted.loc[emitted.required_exact == "EXACT_REQUIRED", "required_field"])
                ),
                "on_missing_action": {
                    f: sorted(set(g.on_missing_action)) for f, g in group.groupby("required_field")
                },
                "transform_by_field": {
                    f: sorted(set(g.transform_type)) for f, g in emitted.groupby("required_field")
                },
                "requirement_ids": sorted(set(group.requirement_id)),
                "wire_schema_status": "CONTRACT_GAP"
                if dest in EXTERNAL_DESTINATIONS
                else "INTERNAL_FIELD_PROFILE_ONLY",
            }
        )
    return profiles


def validate_payload(
    frame: pd.DataFrame,
    destination: str,
    phase: str,
    payload: dict,
    source_values: dict,
    *,
    fixture: bool = False,
) -> dict:
    """Field-level preflight. Never claims provider readiness or whole-runtime PASS."""
    issues = []
    group = frame[(frame.destination == destination) & (frame.runtime_phase == phase)]
    if group.empty:
        return {
            "decision": "REVIEW",
            "scope": "FIELD_PROFILE_ONLY",
            "issues": [{"rule": "UNSUPPORTED_DESTINATION_OR_PHASE"}],
        }
    allowed = set(group.loc[group.transform_type != "OMIT", "required_field"])
    if destination == "NOT_EXTERNALIZED":
        allowed = set()
    for field in sorted(set(payload) - allowed):
        issues.append({"rule": "FORBIDDEN_OR_UNRELATED_FIELD", "field": field, "action": "BLOCK"})
    post_only = set(frame.loc[frame.runtime_phase == "POST_EXECUTION", "required_field"])
    if phase == "PRE_EXECUTION":
        for field in sorted(set(payload) & post_only):
            issues.append(
                {"rule": "POST_EXECUTION_IN_PRE_EXECUTION", "field": field, "action": "BLOCK"}
            )
    for _, row in group.iterrows():
        field = row.required_field
        if row.transform_type not in ALLOWED_TRANSFORM_BY_EXACT_CLASS.get(
            row.required_exact, set()
        ):
            issues.append(
                {"rule": "EXACT_OR_TRANSFORM_VIOLATION", "field": field, "action": "BLOCK"}
            )
        if row.mandatory_level.startswith("MANDATORY"):
            if field not in source_values or source_values[field] in (None, ""):
                issues.append(
                    {
                        "rule": "REQUIRED_INPUT_MISSING",
                        "field": field,
                        "action": row.on_missing_action,
                    }
                )
            if field in allowed and (field not in payload or payload[field] in (None, "")):
                issues.append(
                    {
                        "rule": "REQUIRED_PAYLOAD_MISSING",
                        "field": field,
                        "action": row.on_missing_action,
                    }
                )
        if row.required_exact == "EXACT_REQUIRED" and field in payload:
            if payload[field] != source_values.get(field) or type(payload[field]) is not type(
                source_values.get(field)
            ):
                issues.append({"rule": "EXACT_VALUE_MISMATCH", "field": field, "action": "BLOCK"})
            if field == "amount" and (
                not isinstance(payload[field], str)
                or re.fullmatch(r"[0-9]+", payload[field]) is None
            ):
                issues.append(
                    {"rule": "NON_EXACT_AMOUNT_REPRESENTATION", "field": field, "action": "BLOCK"}
                )
    if not fixture and destination in EXTERNAL_DESTINATIONS:
        issues.append({"rule": "PROVIDER_WIRE_SCHEMA_UNRESOLVED", "action": "REVIEW"})
    return {
        "scope": "SIMULATION_FIELD_PROFILE" if fixture else "FIELD_PROFILE_ONLY",
        "decision": "BLOCK"
        if any(i.get("action") == "BLOCK" for i in issues)
        else "REVIEW"
        if issues
        else "PASS",
        "issues": issues,
    }


def negative_controls(frame: pd.DataFrame, matrix: dict, pipeline: dict) -> list[dict]:
    """SIMULATION only. Symbols test field partition; they are not identities or approvals."""
    dest = "BLOCKCHAIN_EXECUTION_SYSTEM"
    profile = next(p for p in profiles_from(frame) if p["destination"] == dest)
    fields = profile["allowed_fields"]
    source = {f: "SIMULATION:" + f for f in fields}
    source["amount"] = "9007199254740993"
    payload = dict(source)
    results = []

    def record(name: str, result: dict, rule: str | None = None) -> None:
        detected = result["decision"] != "PASS" if rule else result["decision"] == "PASS"
        if rule:
            detected = detected and any(i["rule"] == rule for i in result["issues"])
        results.append(
            {
                "case": name,
                "evidence_type": "SIMULATION",
                "expected_rule": rule,
                "detected_as_expected": detected,
                **result,
            }
        )

    record(
        "NORMAL_FIELD_PROFILE",
        validate_payload(frame, dest, "PRE_EXECUTION", payload, source, fixture=True),
    )
    for field in sorted(set(frame.loc[frame.required_exact == "INTERNAL_ONLY", "required_field"])):
        record(
            "A_INTERNAL_ONLY_LEAKAGE:" + field,
            validate_payload(
                frame, dest, "PRE_EXECUTION", {**payload, field: "SIMULATION"}, source, fixture=True
            ),
            "FORBIDDEN_OR_UNRELATED_FIELD",
        )
    missing = {f: v for f, v in payload.items() if f != "amount"}
    record(
        "B_REQUIRED_MISSING",
        validate_payload(frame, dest, "PRE_EXECUTION", missing, source, fixture=True),
        "REQUIRED_PAYLOAD_MISSING",
    )
    mutated = frame.copy(deep=True)
    mutated.loc[
        (mutated.required_field == "amount") & (mutated.destination == dest), "transform_type"
    ] = "MINIMIZE"
    record(
        "C_EXACT_LOSSY_TRANSFORM",
        validate_payload(mutated, dest, "PRE_EXECUTION", payload, source, fixture=True),
        "EXACT_OR_TRANSFORM_VIOLATION",
    )
    record(
        "D_POST_IN_PRE",
        validate_payload(
            frame, dest, "PRE_EXECUTION", {**payload, "tx_hash": "SIMULATION"}, source, fixture=True
        ),
        "POST_EXECUTION_IN_PRE_EXECUTION",
    )
    record(
        "E_UNSUPPORTED_DESTINATION",
        validate_payload(
            frame, "UNDEFINED_TEST_DESTINATION", "PRE_EXECUTION", payload, source, fixture=True
        ),
        "UNSUPPORTED_DESTINATION_OR_PHASE",
    )
    record(
        "F_EXACT_VALUE_MUTATED",
        validate_payload(
            frame,
            dest,
            "PRE_EXECUTION",
            {**payload, "amount": "9007199254740992"},
            source,
            fixture=True,
        ),
        "EXACT_VALUE_MISMATCH",
    )
    record(
        "G_UNRELATED_EXTERNAL_FIELD",
        validate_payload(
            frame,
            dest,
            "PRE_EXECUTION",
            {**payload, "originator_identity": "SIMULATION"},
            source,
            fixture=True,
        ),
        "FORBIDDEN_OR_UNRELATED_FIELD",
    )
    record(
        "H_FLOAT_AMOUNT",
        validate_payload(
            frame, dest, "PRE_EXECUTION", {**payload, "amount": 1.0}, source, fixture=True
        ),
        "NON_EXACT_AMOUNT_REPRESENTATION",
    )
    bad = copy.deepcopy(matrix)
    row = next(r for r in bad["requirements"] if r["required_fields"] == ["tx_hash"])
    row["source_phase"] = "PRE_EXECUTION"
    row["pre_execution_required"] = True
    failures = contract_violations(bad, pipeline)
    results.append(
        {
            "case": "I_CONTRACT_POST_REQUIREMENT_IN_PRE",
            "evidence_type": "SIMULATION",
            "decision": "BLOCK" if failures else "PASS",
            "scope": "CONTRACT_VALIDATION",
            "detected_as_expected": any(
                f["rule"] == "EXECUTION_RESULT_POST_EXECUTION_ONLY" for f in failures
            ),
            "issues": failures,
        }
    )
    return results


def analyze(root: Path = ROOT) -> dict:
    matrix, pipeline = read_json(root / MATRIX), read_json(root / PIPELINE)
    for path, schema in [
        (MATRIX, "outbound_requirement_matrix_v2"),
        (PIPELINE, "runtime_pipeline"),
    ]:
        jsonschema.validate(
            read_json(root / path), read_json(root / DA / "contracts" / (schema + ".schema.json"))
        )
    frame = normalize(
        matrix,
        pd.read_csv(root / REQUIREMENTS, dtype=str, keep_default_na=False),
        pd.read_csv(root / MAPPING, dtype=str, keep_default_na=False),
    )
    master = pd.read_csv(root / MASTER, dtype=str, keep_default_na=False)
    require(
        len(master) > 0 and not master.transaction_hash.duplicated().any(), "Empty/duplicate Master"
    )
    require(master.value_lossless.str.fullmatch(r"[0-9]+").all(), "Invalid atomic integer string")
    fields = []
    for field, group in frame.groupby("required_field", sort=True):
        row = group.iloc[0]
        column = COLUMN_CROSSWALK.get(field, (None, None))[1]
        if column:
            require(
                set(group.ethereum_field) == {COLUMN_CROSSWALK[field][0]}, f"Mapping drift: {field}"
            )
        observed = int(master[column].ne("").sum()) if column else 0
        fields.append(
            {
                "required_field": field,
                "availability_layer": row.availability_layer,
                "execution_availability": row.execution_availability,
                "runtime_phase": row.runtime_phase,
                "sample_column": column,
                "legacy_onchain_candidate": row.availability_layer == "ONCHAIN",
                "safely_mapped_sample_field": column is not None,
                "offchain_pre_execution_dependency": row.runtime_phase == "PRE_EXECUTION"
                and row.source_type
                in {"UPSTREAM_PRODUCED_DATA", "APPROVED_TRANSACTION_TRACE_INPUT"}
                or field == "asset",
                "post_execution_dependency": row.runtime_phase == "POST_EXECUTION",
                "sample_value_count": observed if column else None,
                "sample_value_rate_pct": 100 * observed / len(master) if column else None,
                "unmapped_candidate_column": "receipt_status"
                if field == "execution_status"
                else None,
                "sample_phase": "POST_EXECUTION",
                "pre_execution_approval_verified": False,
                "contract_gap": sorted({g for gs in group.contract_gap for g in gs}),
            }
        )
    field_frame = pd.DataFrame(fields)
    profiles = profiles_from(frame)
    superset = set(frame.loc[frame.externalizable, "required_field"])
    exposure = []
    for p in profiles:
        if p["destination"] not in EXTERNAL_DESTINATIONS:
            continue
        selected = set(p["allowed_fields"])
        required = set(p["required_fields"])
        reduction = len(superset - selected)
        exposure.append(
            {
                "destination": p["destination"],
                "externalizable_superset_field_count": len(superset),
                "destination_payload_field_count": len(selected),
                "unnecessary_external_field_count_in_superset": reduction,
                "unnecessary_external_field_count_in_profile": len(selected - required),
                "absolute_field_reduction": reduction,
                "relative_exposure_reduction_pct": 100 * reduction / len(superset),
                "required_field_retention_pct": 100 * len(required & selected) / len(required)
                if required
                else None,
                "retention_scope": "CONTRACT_FIELD_SET_NOT_OBSERVED_VALUES_OR_WIRE_SCHEMA",
            }
        )
    destination_summary = []
    for dest, group in frame.groupby("destination", sort=True):
        subset = field_frame[field_frame.required_field.isin(group.required_field)]
        destination_summary.append(
            {
                "destination": dest,
                "requirement_count": int(group.requirement_id.nunique()),
                "unique_required_field_count": int(group.required_field.nunique()),
                "onchain_field_count": int(subset.safely_mapped_sample_field.sum()),
                "offchain_dependency_count": int(subset.offchain_pre_execution_dependency.sum()),
                "post_execution_dependency_count": int(subset.post_execution_dependency.sum()),
                "exact_required_count": int(
                    group.loc[group.required_exact == "EXACT_REQUIRED", "required_field"].nunique()
                ),
                "omit_internal_only_count": int(
                    group.loc[
                        (group.transform_type == "OMIT")
                        | (group.required_exact == "INTERNAL_ONLY"),
                        "required_field",
                    ].nunique()
                ),
                "contract_gap_count": int(
                    group.loc[group.contract_gap.map(bool), "requirement_id"].nunique()
                ),
            }
        )
    violations = contract_violations(matrix, pipeline)
    controls = negative_controls(frame, matrix, pipeline)
    illegal = set(
        frame.loc[
            (frame.required_exact == "INTERNAL_ONLY") | (frame.destination == "NOT_EXTERNALIZED"),
            "required_field",
        ]
    )
    invariants = {
        "not_externalized_leakage": len(superset & illegal),
        "omit_externalized_rows": int(
            ((frame.transform_type == "OMIT") & frame.externalizable).sum()
        ),
        "exact_lossy_rows": int(
            (
                (frame.required_exact == "EXACT_REQUIRED")
                & (frame.transform_type != "PASS_THROUGH")
            ).sum()
        ),
        "external_pre_payload_post_field_count": sum(
            len(
                set(p["allowed_fields"])
                & set(field_frame.loc[field_frame.post_execution_dependency, "required_field"])
            )
            for p in profiles
            if p["destination"] in EXTERNAL_DESTINATIONS and p["runtime_phase"] == "PRE_EXECUTION"
        ),
        "contract_violation_count": len(violations),
        "negative_control_failures": sum(not x["detected_as_expected"] for x in controls),
        "pass_through_internal_only_destination_rows": int(
            (
                (frame.transform_type == "PASS_THROUGH")
                & frame.destination.isin(INTERNAL_DESTINATIONS)
            ).sum()
        ),
    }
    all_gaps = sorted(
        {g for gs in frame.contract_gap for g in gs}
        | {"PROVIDER_WIRE_AND_E2E", "APPROVAL_TRACE", "SOURCE_PROVENANCE"}
    )
    gap_records = [
        {
            "gap_id": g,
            "status": "CONTRACT_GAP",
            "detail": GAP_TEXT[g],
            "requirement_ids": sorted(
                set(
                    frame.loc[frame.contract_gap.map(lambda gs, key=g: key in gs), "requirement_id"]
                )
            ),
        }
        for g in all_gaps
    ]
    legacy = []
    for row in matrix["requirements"]:
        old = frame[frame.requirement_id == row["requirement_id"]].iloc[0]
        changes = {}
        for key, before, after in [
            ("destination", sorted(old.legacy_destination.split("|")), sorted(row["destination"])),
            ("transform", sorted(old.legacy_transform.split("|")), sorted(row["transform"])),
            ("on_missing", old.legacy_on_missing, row["on_missing"]),
            ("exact_class", old.legacy_required_exact, row["required_exact"]),
        ]:
            if before != after:
                changes[key] = {"legacy_csv": before, "vnext_authority": after}
        legacy.append({"requirement_id": row["requirement_id"], "changes": changes})
    summary = {
        "sample_rows": len(master),
        "unique_transaction_hashes": int(master.transaction_hash.nunique()),
        "missing_to_address": int(master.to_address.eq("").sum()),
        "amount_representation_valid_count": int(
            master.value_lossless.str.fullmatch(r"[0-9]+").sum()
        ),
        "requirement_count": int(frame.requirement_id.nunique()),
        "destination_count": int(frame.destination.nunique()),
        "field_count": len(fields),
        "normalized_row_count": len(frame),
        "safely_mapped_onchain_field_count": int(field_frame.safely_mapped_sample_field.sum()),
        "legacy_onchain_candidate_count": int(field_frame.legacy_onchain_candidate.sum()),
        "offchain_pre_execution_dependency_count": int(
            field_frame.offchain_pre_execution_dependency.sum()
        ),
        "post_execution_dependency_count": int(field_frame.post_execution_dependency.sum()),
        "contract_gap_category_count": len(gap_records),
        "externalizable_superset": sorted(superset),
    }
    for metric in [
        "safely_mapped_onchain_field",
        "offchain_pre_execution_dependency",
        "post_execution_dependency",
    ]:
        summary[metric + "_rate_pct"] = 100 * summary[metric + "_count"] / len(fields)
    return {
        "summary": summary,
        "field_availability": fields,
        "destination_summary": destination_summary,
        "destination_profiles": profiles,
        "exposure": exposure,
        "invariants": invariants,
        "negative_controls": controls,
        "contract_violations": violations,
        "contract_gaps": gap_records,
        "normalized_requirements": records(frame),
        "legacy_to_vnext": legacy,
        "pipeline": pipeline["steps"],
        "decision_semantics": matrix["decision_semantics"],
        "fpg_boundary": matrix["fpg_boundary"],
    }


def artifacts(result: dict, generated_at: str, root: Path = ROOT) -> dict[str, dict]:
    source_refs = [
        {
            "path": p.as_posix(),
            "sha256": sha256(root / p)
            if p == MASTER
            else hashlib.sha256((root / p).read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
            "sha256_scope": "RAW_BYTES" if p == MASTER else "UTF8_BYTES_CRLF_TO_LF",
        }
        for p in SOURCES
    ]
    nb = read_json(root / NOTEBOOK)
    code_digest = hashlib.sha256(
        json.dumps(
            ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"],
            ensure_ascii=False,
        ).encode()
    ).hexdigest()
    common = {
        "artifact_version": "1.0.0",
        "generated_at": generated_at,
        "source_notebook": NOTEBOOK.as_posix(),
        "source_notebook_code_sha256": code_digest,
        "notebook_digest_scope": (
            "ordered code cell sources; outputs excluded to avoid self-reference"
        ),
        "source_data": MASTER.as_posix(),
        "source_data_sha256": sha256(root / MASTER),
        "evidence_refs": source_refs,
        "analysis_scope": "DETERMINISTIC_CONTRACT_AND_OBSERVED_SAMPLE",
        "provider_wire_schema": False,
        "live_be_evaluation": False,
    }
    payloads = {
        "analysis_summary": {
            "metrics": result["summary"],
            "destination_summary": result["destination_summary"],
            "field_availability": result["field_availability"],
            "legacy_to_vnext": result["legacy_to_vnext"],
        },
        "validation_metrics": {
            k: result[k]
            for k in ["exposure", "invariants", "negative_controls", "contract_violations"]
        },
        "destination_payload_profile": {
            "contract_level": "FPG_FIELD_LEVEL_DESTINATION_CONTRACT",
            "profiles": result["destination_profiles"],
            "lineage": result["normalized_requirements"],
        },
        "runtime_requirements": {
            k: result[k] for k in ["pipeline", "decision_semantics", "fpg_boundary"]
        },
        "contract_gaps": {"gaps": result["contract_gaps"]},
    }
    payloads["runtime_requirements"]["validation_requirements"] = [
        "required_field_presence",
        "exact_preservation",
        "transform_compatibility",
        "externalization_policy",
        "phase_validation",
        "destination_validation",
    ]
    payloads["runtime_requirements"]["fail_closed"] = {
        "BLOCK": ["exact/value mismatch", "forbidden externalization", "phase violation"],
        "REVIEW": ["unsupported destination", "provider wire schema unresolved"],
        "missing_input": "Preserve requirement on_missing action; never PASS on mandatory absence.",
        "scope": "Analysis guard requirements; reuse BE naming, no new production enum.",
    }
    return {
        name: {**common, "artifact_id": "DA_04_OUTBOUND_DESTINATION:" + name, **value}
        for name, value in payloads.items()
    }


def export_artifacts(result: dict, root: Path = ROOT, *, check: bool = False) -> None:
    folder = root / ARTIFACT
    existing = folder / "analysis_summary.json"
    timestamp = (
        read_json(existing)["generated_at"] if existing.exists() else datetime.now(UTC).isoformat()
    )
    payloads = artifacts(result, timestamp, root)
    if not check:
        folder.mkdir(parents=True, exist_ok=True)
    for name, value in payloads.items():
        jsonschema.Draft202012Validator(
            read_json(root / DA / "contracts/da_04_evidence.schema.json"),
            format_checker=jsonschema.FormatChecker(),
        ).validate(value)
        path = folder / (name + ".json")
        if check:
            require(path.is_file() and read_json(path) == value, f"Artifact drift: {path.name}")
        else:
            path.write_text(
                json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = analyze()
    export_artifacts(result, check=args.check)
    print(json.dumps(result["summary"], indent=2))
    print(json.dumps(result["invariants"], indent=2))


if __name__ == "__main__":
    main()
