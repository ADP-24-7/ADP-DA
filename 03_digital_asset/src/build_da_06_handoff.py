"""Freeze DA-06 saved outputs; never execute the notebook or recompute statistics."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import jsonschema
from build_da_00_01_handoff import TableReader, notebook, output_text, require, sha256

ROOT = Path(__file__).resolve().parents[2]
DA = Path("03_digital_asset")
NB = DA / "notebooks/runtime_validation/DA_06_recovery_idempotency.ipynb"
DOC = DA / "docs/handoff/DA_06_recovery_idempotency.md"
DATA = DA / "data/processed/da_master_transaction_sample_73410.csv"
ART = DA / "artifacts/da_06_recovery_idempotency"
SCHEMA = DA / "contracts/da_06_handoff.schema.json"
ORIGINAL_HASHES = {
    NB: "630010c2452a5a8cfb2d85b6cd3fe102c57dce440262d3b17525bdcb2fd962a3",
    DOC: "610752fcf549aad157f02010f6105ddaf9c3e266c684962ff3ed89688d7ca4b4",
    DATA: "506160f02d5c042062b1bffa56aa61932fd517deb8ffa7aeed51c8ad66c4c701",
}


def saved_tables(nb, cell):
    result = []
    for out in nb["cells"][cell].get("outputs", []):
        html = out.get("data", {}).get("text/html")
        if html:
            reader = TableReader()
            reader.feed("".join(html))
            result.append([r for r in reader.rows if r and r[0].isdigit()])
    return result


def verify_sources(root=ROOT):
    for path, digest in ORIGINAL_HASHES.items():
        require(sha256(root / path) == digest, f"Source snapshot changed: {path}")
    nb = notebook(root, NB)
    observed = saved_tables(nb, 3)
    require(len(observed) == 3, "Observed tables missing")
    require([int(r[-1]) for r in observed[0]] == [73410, 0, 73410, 0, 0], "Hash metrics disagree")
    require(
        [r[1:] for r in observed[1]] == [["1", "72241", "0.984076"], ["0", "1169", "0.015924"]],
        "Receipt metrics disagree",
    )
    require(observed[2][0][1:] == ["True", "73410", "1.0"], "Reference linkage disagrees")
    counterfactual = saved_tables(nb, 5)
    require(
        [float(r[-1]) for r in counterfactual[0]] == [73410, 73410, 1, 73410, 72241, 0, 0],
        "Counterfactual metrics disagree",
    )
    require(
        [r[1:] for r in counterfactual[1]]
        == [["FINALIZED", "72241", "0.984076"], ["FAILED", "1169", "0.015924"]],
        "Experiment state labels disagree",
    )
    require("[98.3145%, 98.4956%]" in output_text(nb, 6), "Wilson output missing")
    require(
        "98.4076%" in output_text(nb, 10) and "100.0000%" in output_text(nb, 10),
        "Paired effect output missing",
    )
    require("p < 0.001" in "".join(nb["cells"][11]["source"]), "McNemar conclusion missing")
    return nb


INVARIANTS = [
    ("INV-1", "Identify duplicate business requests within the existing idempotency scope."),
    ("INV-2", "With an external_transaction_id, query the existing execution before new outbound."),
    ("INV-3", "SENT_UNKNOWN is not FAILED."),
    ("INV-4", "Never immediately resend from SENT_UNKNOWN."),
    ("INV-5", "Reconcile using the existing external transaction and its bound request."),
    ("INV-6", "Never resend the same finalized business request."),
    ("INV-7", "Evaluate retry eligibility only after confirmed terminal failure and retry policy."),
    ("INV-8", "Preserve original-to-retry request lineage for every authorized retry."),
    ("INV-9", "Record every state transition in the audit trace."),
]
TRANSITIONS = [
    ("SUBMITTED", "SENT_UNKNOWN", ["submission_recorded", "response_uncertain"]),
    ("SENT_UNKNOWN", "RECONCILING", ["query_existing_execution"]),
    ("RECONCILING", "FINALIZED", ["bound_reference", "field_match", "finality_confirmed"]),
    ("RECONCILING", "FAILED", ["bound_reference", "terminal_failure_confirmed"]),
    ("RECONCILING", "RECONCILIATION_REQUIRED", ["unresolved_or_mismatch"]),
    ("FAILED", "RETRY_ELIGIBLE", ["terminal_failure_confirmed", "retry_policy_allows"]),
]


def payloads():
    return {
        "analysis_summary": {
            "evidence_kind": "OBSERVED_EVIDENCE",
            "sample_size": 73410,
            "metrics": {
                "hash_missing": 0,
                "unique_hashes": 73410,
                "duplicate_hash_rows": 0,
                "duplicate_hash_keys": 0,
                "hash_receipt_linked": 73410,
                "hash_receipt_linked_percent": 100,
                "receipt_success": 72241,
                "receipt_success_percent": 98.4076,
                "receipt_failed": 1169,
                "receipt_failed_percent": 1.5924,
            },
            "notebook_state_labels": {
                "FINALIZED": "receipt_status = 1 (experiment label only)",
                "FAILED": "receipt_status = 0",
            },
            "boundary": "Receipt success and unique hashes do not prove settlement finality, "
            "business idempotency or exactly-once external effects.",
            "source_cells": [1, 2, 3, 14],
        },
        "validation_metrics": {
            "evidence_kind": "COUNTERFACTUAL_EXPERIMENT",
            "sample_size": 73410,
            "scenario": "SENT_UNKNOWN_WITH_REFERENCE",
            "assumption": "Every observed transaction was submitted and its hash retained, "
            "but the response became uncertain; saved receipts stand in for lookup.",
            "naive_resend": {
                "duplicate_submission_risk_count": 73410,
                "duplicate_external_effect_risk_count": 72241,
                "duplicate_external_effect_risk_percent": 98.4076,
                "wilson_95_ci_percent": [98.3145, 98.4956],
            },
            "reconciliation_first": {
                "recoverable_count": 73410,
                "recoverable_percent": 100,
                "immediate_resend_count": 0,
                "duplicate_external_effect_risk_percent": 0,
            },
            "paired_comparison": {
                "method": "McNemar exact",
                "reported_p": "p < 0.001",
                "absolute_risk_difference_percentage_points": 98.4076,
                "relative_risk_reduction_percent": 100,
                "recomputed": False,
            },
            "interpretation": "Zero risk follows structurally from prohibiting new submission "
            "before lookup. Not a population inference or live incident rate. "
            "Printed p=0 is numerical output, not an exact probability of zero.",
            "source_cells": [4, 5, 6, 10, 11],
        },
        "runtime_requirements": {
            "evidence_kind": "IMPLEMENTATION_REQUIREMENTS",
            "implemented_by_this_artifact": False,
            "state_namespace": "DA_CONCEPTUAL_NOT_BE_ENUM",
            "invariants": [{"id": key, "requirement": value} for key, value in INVARIANTS],
            "transitions": [
                {"from": a, "to": b, "requires": conditions + ["audit_trace"]}
                for a, b, conditions in TRANSITIONS
            ],
            "prohibited": [
                "SENT_UNKNOWN -> RETRY",
                "FINALIZED -> RESUBMIT_SAME_REQUEST",
                "UNKNOWN_AS_FAILED",
                "RETRY_BEFORE_RECONCILIATION",
            ],
            "identifier_binding": [
                "idempotency_key",
                "external_transaction_id",
                "execution_status",
            ],
            "idempotency_scope": ["idempotency_institution_id", "workload_id", "idempotency_key"],
            "duplicate_handling": "Reuse the existing execution for matching request_hash; "
            "conflicting hash is a conflict, in-progress is not a new submission.",
            "missing_reference": "Use existing provider correlation lookup if supported; "
            "otherwise remain unresolved with manual reconciliation. No blind resend.",
            "retry_boundary": "RETRY_ELIGIBLE is not authorization to send. BE must define retry "
            "policy, atomic claim, limits and parent lineage before any retry.",
            "completion_boundary": "Amount/Asset/Destination mismatch prohibits "
            "automatic completion. "
            "Receipt status alone is insufficient for BE settlement finality.",
        },
        "runtime_architecture": {
            "evidence_kind": "IMPLEMENTATION_REQUIREMENTS",
            "pipeline": [
                "Scoped business request identity",
                "Existing execution lookup",
                "External reference binding",
                "Reconciliation",
                "Terminal evidence",
                "Retry eligibility assessment",
                "Lineage and audit",
            ],
            "be_repository": "ADP-24-7/ADP-BE",
            "be_reviewed_commit": "5d5f999310db3854e96bf96661f76438d7def6ff",
            "fields": field_mapping(),
            "state_mapping": {
                "SENT_UNKNOWN": "ConnectorStatus.SENT_UNKNOWN; "
                "asset settlement_status=SENT_UNKNOWN, "
                "reconciliation_result=WAIT; runtime EGRESSING.",
                "RECONCILING": "DA activity, not a new BE enum; recovery PENDING/CLAIMED workflow.",
                "FINALIZED": "DA conceptual terminal success. Existing BE completion requires "
                "settlementStatus=SETTLED and reconciliation MATCH/RECOVERED. "
                "Provider/chain finality policy remains BE-owned.",
                "FAILED": "Distinguish transport failure from confirmed terminal external failure.",
                "RECONCILIATION_REQUIRED": "Existing asset settlement status/review path; "
                "not automatically equivalent to a recovery enum.",
                "RETRY_ELIGIBLE": "DA eligibility concept, not automatic RETRY_ALLOWED mapping.",
            },
            "be_source_paths": [
                "src/main/resources/db/migration/V12__add_runtime_idempotency_core.sql",
                "src/main/resources/db/migration/V13__add_external_interaction_recovery.sql",
                "src/main/java/com/adp/gateway/runtime/application/RuntimeExecutionService.java",
                "src/main/java/com/adp/gateway/digitalasset/application/"
                "DigitalAssetSettlementOutcomeHandler.java",
                "src/main/java/com/adp/gateway/digitalasset/infrastructure/"
                "JdbcDigitalAssetTransactionPersistence.java",
            ],
        },
        "contract_gaps": {
            "evidence_kind": "IMPLEMENTATION_REQUIREMENTS",
            "gaps": [
                {
                    "id": "LIVE_RECOVERY",
                    "detail": "No gateway timeout, response-loss, retry logs, "
                    "provider recovery latency or actual business duplicate rate in sample.",
                },
                {"id": "NONCE", "detail": "No nonce; sender+nonce uniqueness was not validated."},
                {
                    "id": "BUSINESS_IDEMPOTENCY",
                    "detail": "No pre-submit business idempotency binding "
                    "in sample; concurrent claims, crash recovery and exactly-once "
                    "effects untested.",
                },
                {
                    "id": "FINALITY",
                    "detail": "Receipt status is not chain settlement finality. "
                    "BE must decide confirmations/reorg/provider terminal evidence criteria.",
                },
                {
                    "id": "RETRY_POLICY",
                    "detail": "Confirm terminal failure, retry limits, atomic "
                    "authorization and original/attempt key binding before implementing retry.",
                },
                {
                    "id": "RETRY_LINEAGE",
                    "detail": "parent_request_id and true outbound retry_count "
                    "have no verified equivalent; recovery attempt_count counts claims, not sends.",
                },
                {
                    "id": "NO_REFERENCE",
                    "detail": "Hash-absent recovery is outside this experiment; "
                    "define provider correlation lookup/manual workflow, never assume safe resend.",
                },
                {"id": "LEGAL_MAPPING", "detail": "No new legal mapping performed or claimed."},
            ],
        },
    }


def field_mapping():
    # Existing names first; an unresolved semantic is not silently aliased.
    return [
        {
            "semantic": "request_id",
            "existing": "runtime.runtime_execution.request_id",
            "note": "Join via execution_id; do not confuse provider external_request_id.",
        },
        {
            "semantic": "idempotency_key",
            "existing": "runtime.runtime_execution.idempotency_key",
            "note": "Before outbound; retain institution/workload scope and request_hash.",
        },
        {
            "semantic": "external_transaction_id",
            "existing": "digital_asset_transaction.external_transaction_id",
            "note": "Post-submission reference; Ethereum transaction_hash proxy, "
            "nullable before receipt.",
        },
        {
            "semantic": "submission_status",
            "existing": "external_interaction_recovery.observed_status",
            "note": "Connector observation; not settlement finality.",
        },
        {
            "semantic": "execution_status",
            "existing": "digital_asset_transaction.settlement_status",
            "note": "External outcome dimension; runtime_execution.status "
            "remains a separate dimension.",
        },
        {
            "semantic": "reconciliation_status",
            "existing": "digital_asset_transaction.reconciliation_result",
            "note": "Business outcome dimension; "
            "external_interaction_recovery.recovery_status is workflow.",
        },
        {
            "semantic": "retry_count",
            "existing": None,
            "note": "Gap: recovery attempt_count increments on claim, not actual outbound retry.",
        },
        {
            "semantic": "parent_request_id",
            "existing": None,
            "note": "Gap: define original/child lineage without changing "
            "business idempotency semantics.",
        },
        {
            "semantic": "created_at",
            "existing": "runtime.runtime_execution.created_at",
            "note": "Request creation time; distinguish transaction/recovery row creation.",
        },
        {
            "semantic": "last_checked_at",
            "existing": "external_interaction_recovery.last_status_queried_at",
            "note": "Use status_query_evidence_digest; updated_at is not a status-check timestamp.",
        },
    ]


def validate_contract(value):
    """Reject weakened handoff requirements; this does not execute a BE transition."""
    if not value["artifact_id"].endswith(":runtime_requirements"):
        return
    require(
        value["invariants"] == [{"id": k, "requirement": v} for k, v in INVARIANTS],
        "Invariant contract changed",
    )
    expected = [
        {"from": a, "to": b, "requires": conditions + ["audit_trace"]}
        for a, b, conditions in TRANSITIONS
    ]
    require(value["transitions"] == expected, "Transition contract changed")
    for key in (
        "prohibited",
        "identifier_binding",
        "idempotency_scope",
        "duplicate_handling",
        "missing_reference",
        "retry_boundary",
        "completion_boundary",
    ):
        require(value[key] == payloads()["runtime_requirements"][key], f"Contract changed: {key}")


def build(root=ROOT, check=False):
    verify_sources(root)
    schema = json.loads((root / SCHEMA).read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    target = root / ART
    existing = target / "analysis_summary.json"
    generated_at = (
        json.loads(existing.read_text(encoding="utf-8"))["generated_at"]
        if existing.exists()
        else datetime.now(UTC).isoformat()
    )
    common = {
        "artifact_version": "1.0.0",
        "generated_at": generated_at,
        "source_analysis": "DA-06",
        "domain": "DIGITAL_ASSET",
        "topic": ["IDEMPOTENCY", "SENT_UNKNOWN", "RECOVERY"],
        "source_notebook": NB.as_posix(),
        "sample_size": 73410,
        "live_be_evaluation": False,
        "evidence_refs": [
            {"path": p.as_posix(), "sha256": h, "sha256_scope": "RAW_BYTES"}
            for p, h in ORIGINAL_HASHES.items()
        ],
    }
    results = {}
    for name, body in payloads().items():
        value = {**common, "artifact_id": f"DA_06_RECOVERY_IDEMPOTENCY:{name}", **body}
        validator.validate(value)
        validate_contract(value)
        path = target / f"{name}.json"
        if check:
            require(
                json.loads(path.read_text(encoding="utf-8")) == value, f"Artifact drift: {path}"
            )
        else:
            target.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        results[name] = value
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    artifacts = build(check=args.check)
    print(
        f"PASS: {len(artifacts)} DA-06 artifacts; schema, saved outputs and source hashes verified"
    )
