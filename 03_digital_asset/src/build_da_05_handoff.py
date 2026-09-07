"""Extract stored DA-05 evidence and export small contracts without rerunning the notebook."""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import jsonschema
import pandas as pd
from build_da_00_01_handoff import notebook, output_text, require, sha256, table

ROOT = Path(__file__).resolve().parents[2]
DA = Path("03_digital_asset")
NB = DA / "notebooks/runtime_validation/DA_05_approved_requested_match.ipynb"
DOC = DA / "docs/handoff/DA_05_approved_requested_match.md"
MASTER = DA / "data/processed/da_master_transaction_sample_73410.csv"
OUT = DA / "artifacts/da_05_approved_requested_match"
SCHEMA = DA / "contracts/da_05_handoff.schema.json"


def evidence(root: Path = ROOT) -> dict:
    nb = notebook(root, NB)
    summary = {r[1]: int(r[2]) for r in table(nb, 28)}
    expected = {
        "Total Requested Transactions": 73410,
        "PASS": 36514,
        "BLOCK": 36896,
        "Single Violation": 29557,
        "Multiple Violations": 7339,
        "Decision Correct": 73410,
        "Misclassified": 0,
    }
    require(summary == expected, "Notebook summary differs from requested evidence")
    require(
        summary["PASS"] + summary["BLOCK"] == summary["Total Requested Transactions"],
        "Decision total",
    )
    require(
        summary["Single Violation"] + summary["Multiple Violations"] == summary["BLOCK"],
        "Violation total",
    )
    require("100.0000%" in output_text(nb, 14), "Stored fixture accuracy")
    stats = output_text(nb, 20)
    chi = float(re.search(r"Chi-square\s*:\s*([\d.]+)", stats)[1])
    v = float(re.search(r"Cramér's V\s*:\s*([\d.]+)", stats)[1])
    dof = int(re.search(r"df\s*:\s*(\d+)", stats)[1])
    require((chi, v, dof) == (12024.2817, 0.4047, 4), "Recorded statistic mismatch")
    master = pd.read_csv(root / MASTER, dtype=str, keep_default_na=False)
    require(len(master) == summary["Total Requested Transactions"], "Master count mismatch")
    require(master.transaction_hash.nunique() == len(master), "Duplicate master request ID")
    creation = int(master.to_address.eq("").sum())
    require(creation == 46 and "46" in output_text(nb, 5), "Creation count mismatch")
    require(master.value_lossless.str.fullmatch(r"[0-9]+").all(), "Non-exact master amount")
    contingency = pd.crosstab(
        master.transaction_type,
        master.value_lossless.map(lambda x: "POSITIVE" if int(x) > 0 else "ZERO"),
    )
    stored = {r[0]: [int(r[1]), int(r[2])] for r in table(nb, 20)}
    require(
        contingency[["POSITIVE", "ZERO"]].T.to_dict("list") == stored,
        "Stored amount structure differs",
    )
    positive = {key: 100 * values[0] / sum(values) for key, values in stored.items()}
    require(positive["3"] == 0 and positive["4"] == 5.8375, "Positive amount share mismatch")
    for term in ["approval_id", "request_id", "approved_max_amount", "valid_until"]:
        require(term in (root / DOC).read_text(encoding="utf-8"), "Handoff input mismatch")
    return {
        "fixture_summary": summary,
        "fixture_decision_accuracy_pct": 100 * summary["Decision Correct"] / len(master),
        "contract_creation_count": creation,
        "amount_structure": {
            "chi_square_reported": chi,
            "degrees_of_freedom": dof,
            "cramers_v_reported": v,
            "p_value_interpretation": "p < 0.001; printed 0 is numerical underflow, not exact zero",
            "positive_amount_pct": positive,
        },
        "verification_scope": (
            "Stored outputs cross-checked against Master "
            "structure; no fixture replay or cloud rerun"
        ),
    }


def build(root: Path = ROOT, generated_at: str = "") -> dict:
    observed = evidence(root)
    refs = [
        NB,
        DOC,
        MASTER,
        DA / "artifacts/outbound_design_vNext/outbound_requirement_matrix.json",
        DA / "docs/DA_02_EXACT_PRESERVATION_BE_HANDOFF.md",
        DA / "artifacts/da_03_trace_binding/evidence_binding_contract.json",
        DA / "artifacts/da_04_outbound_destination/runtime_requirements.json",
    ]
    common = {
        "artifact_version": "1.0.0",
        "generated_at": generated_at,
        "source_notebook": NB.as_posix(),
        "source_notebook_sha256": sha256(root / NB),
        "source_markdown": DOC.as_posix(),
        "source_markdown_sha256": sha256(root / DOC),
        "source_data": MASTER.as_posix(),
        "source_data_sha256": sha256(root / MASTER),
        "evidence_type": "APPROVAL_FIXTURE_WITH_OBSERVED_ETHEREUM_REQUEST_CONTEXT",
        "source_phase": "PRE_EXECUTION",
        "be_runtime_implemented": False,
        "evidence_refs": [{"path": p.as_posix()} for p in refs],
    }
    gaps = [
        "Real institution approval/request logs and trusted binding resolver are absent.",
        (
            "Notebook reads a personal Downloads path and uses np "
            "before its import; no fresh Run All claim."
        ),
        (
            "Notebook fixture setup uses positional assignment; BE "
            "must use explicit trusted ID binding."
        ),
        (
            "Numeric Ethereum transaction_type is not request_type "
            "CONTRACT_CREATION; BE structure source must be trusted."
        ),
        (
            "vNext beneficiary_address presence must become applicability-aware "
            "for authorized creation; no blanket DA-04 bypass."
        ),
        "approved_max_amount limit check does not replace DA-02 approved/outbound exact equality.",
        (
            "Purpose/counterparty appear in introductory scope but are not "
            "tested; only four final rules are handed off."
        ),
        (
            "Provider payload, token unit/scale, timezone/address "
            "adapter and audit field naming need BE mapping."
        ),
        (
            "Fixture request_id derives from a historical hash; a live "
            "PRE_EXECUTION ID cannot depend on a future hash."
        ),
        (
            "Zero amount still has an applicable max-amount rule; "
            "positive-only restriction concerns fixture injection."
        ),
    ]
    approval_fields = [
        "approval_id",
        "approved_asset",
        "approved_max_amount",
        "approved_destination",
        "valid_from",
        "valid_until",
    ]
    request_fields = [
        "request_id",
        "requested_asset",
        "requested_amount",
        "requested_destination",
        "requested_at",
        "transaction_type",
    ]
    rules = {
        "asset": "requested_asset == approved_asset",
        "amount": "requested_amount <= approved_max_amount (exact atomic integer)",
        "destination": "lower(valid requested Ethereum address) == lower(valid approved address)",
        "period": "valid_from <= requested_at <= valid_until (inclusive, timezone-aware UTC)",
    }
    applicability = {
        "asset": "APPLICABLE",
        "amount": "APPLICABLE",
        "period": "APPLICABLE",
        "destination": {"ADDRESS_TRANSACTION": "APPLICABLE", "CONTRACT_CREATION": "NOT_APPLICABLE"},
    }
    components = [
        "Approval Resolver",
        "Request Resolver",
        "Approval / Request Binding",
        "Transaction Structure Context",
        "Rule Applicability Resolver",
        "Asset Comparator",
        "Exact Amount Comparator",
        "Destination Comparator",
        "Period Comparator",
        "Violation Aggregator",
        "Decision",
        "Trace / Evidence Binding",
    ]
    payloads = {
        "analysis_summary": {"metrics": observed, "not_runtime_thresholds": True},
        "validation_metrics": {
            "metrics": observed["fixture_summary"],
            "accuracy_pct": observed["fixture_decision_accuracy_pct"],
            "scope": "STORED_APPROVAL_FIXTURE_RESULTS_NOT_REAL_APPROVAL_VIOLATION_RATES",
        },
        "approval_request_match_contract": {
            "contract_level": "CONCEPTUAL_DA_FIELD_CONTRACT_NOT_BE_WIRE_SCHEMA",
            "approval_fields": approval_fields,
            "request_fields": request_fields,
            "binding": {
                "keys": ["approval_id", "request_id"],
                "source": "trusted explicit association",
                "forbidden": ["array index", "row position", "implicit ordering"],
            },
            "rules": rules,
            "amount_representation": (
                "nonnegative atomic integer or digit string; no float/rounding"
            ),
            "structure_context": (
                "request_type separate from numeric transaction_type; trusted resolver required"
            ),
            "decision": {
                "all_applicable_match": "PASS",
                "any_applicable_violation": "BLOCK",
                "invalid_or_unbound_input": (
                    "FAIL_CLOSED_NO_PASS; reference raises MatchContractError"
                ),
            },
        },
        "rule_applicability": {
            "rules": applicability,
            "not_applicable_result": None,
            "not_applicable_is_pass": False,
            "not_applicable_violation_count": 0,
            "forbidden_source": "contract_address is POST_EXECUTION; never requested_destination",
        },
        "runtime_architecture": {
            "components": components,
            "existing_pipeline_stage": "Approved Value vs Requested Value Match",
            "ordering": "After approved source resolution; before destination payload/handoff",
            "naming": (
                "Conceptual responsibilities; map to existing BE components, no new enum mandate"
            ),
        },
        "runtime_requirements": {
            "rules": rules,
            "applicability": applicability,
            "trace_fields": [
                "approval_id",
                "request_id",
                "rule_applicability",
                "asset_match",
                "amount_match",
                "destination_applicability",
                "destination_match",
                "period_match",
                "violation_reasons",
                "violation_count",
                "approval_match",
                "decision",
                "evaluated_at",
                "contract_version",
                "validation_evidence_reference",
            ],
            "invariants": [
                "Approval PASS != Execution Success",
                "Transaction Record != Execution Result",
                "Transaction Type != PASS/BLOCK Rule",
                "NOT_APPLICABLE != PASS",
                "contract_address != requested_destination",
                "Amount comparison = Exact",
                "DA-05 address match != DA-04 payload destination authorization",
            ],
        },
        "contract_gaps": {"status": "CONTRACT_GAP", "gaps": gaps},
    }
    return {
        name: {**common, "artifact_id": "DA_05_APPROVED_REQUESTED_MATCH:" + name, **value}
        for name, value in payloads.items()
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    folder = ROOT / OUT
    old = folder / "analysis_summary.json"
    timestamp = (
        json.loads(old.read_text(encoding="utf-8"))["generated_at"]
        if old.exists()
        else datetime.now(UTC).isoformat()
    )
    schema = json.loads((ROOT / SCHEMA).read_text(encoding="utf-8"))
    values = build(generated_at=timestamp)
    if not args.check:
        folder.mkdir(parents=True, exist_ok=True)
    for name, value in values.items():
        jsonschema.validate(value, schema)
        path = folder / (name + ".json")
        if args.check:
            require(
                json.loads(path.read_text(encoding="utf-8")) == value, "Artifact drift: " + name
            )
        else:
            path.write_text(
                json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
    print("PASS: 7 artifacts; stored evidence / Master structure / JSON Schema / source hashes")


if __name__ == "__main__":
    main()
