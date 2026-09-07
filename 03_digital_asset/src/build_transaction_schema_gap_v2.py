# ruff: noqa: E501, E701, E702, I001

from __future__ import annotations

import csv
import gzip
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[2]
DA = ROOT / "03_digital_asset"
RAW_TX = DA / "data" / "raw" / "transactions"
RAW_CARD = DA / "data" / "raw" / "crypto_card"
PROCESSED = DA / "data" / "processed"
V1 = DA / "artifacts" / "candidate_policy_v1"
V2 = DA / "artifacts" / "candidate_policy_v2"
NOTEBOOK = DA / "notebooks" / "foundation" / "02_crypto_transaction_schema_analysis.ipynb"


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


def load_bitcoin_otc() -> list[dict[str, Any]]:
    src = RAW_TX / "soc-sign-bitcoinotc.csv.gz"
    rows: list[dict[str, Any]] = []
    with gzip.open(src, "rt", encoding="utf-8") as fp:
        for i, line in enumerate(fp, start=1):
            source, target, rating, timestamp = line.strip().split(",")
            rows.append(
                {
                    "event_id": f"BITCOIN-OTC-{i:06d}",
                    "source_user_id": int(source),
                    "target_user_id": int(target),
                    "rating": int(rating),
                    "timestamp": float(timestamp),
                    "event_time": datetime.fromtimestamp(float(timestamp), tz=UTC).isoformat(),
                }
            )
    write_csv(
        RAW_TX / "soc-sign-bitcoinotc.csv",
        rows,
        ["event_id", "source_user_id", "target_user_id", "rating", "timestamp", "event_time"],
    )
    return rows


def dataset_inventory(actual_rows: int) -> list[dict[str, Any]]:
    return [
        {
            "dataset_name": "SNAP Bitcoin OTC trust weighted signed network",
            "source": "Stanford SNAP",
            "official_research_public": "research_public",
            "download_url": "https://snap.stanford.edu/data/soc-sign-bitcoinotc.csv.gz",
            "license": "research dataset; SNAP distribution terms",
            "chain": "Bitcoin ecosystem platform graph, not on-chain Bitcoin ledger",
            "row_count": actual_rows,
            "main_columns": "source_user_id,target_user_id,rating,timestamp",
            "transaction_level_data": "NO - counterparty trust/rating event, not blockchain execution transaction",
            "graph_data": "YES",
            "label_exists": "YES - signed rating can be used as counterparty risk proxy only",
            "amount_info": "NO",
            "timestamp_info": "YES",
            "sender_from_info": "YES - source_user_id",
            "receiver_to_info": "YES - target_user_id",
            "tx_hash_id": "NO",
            "status_info": "NO",
            "fpg_usability": "Usable for observed counterparty concentration, temporal frequency, graph-link, and risk-proxy distribution only.",
            "limitations": "Cannot validate amount, address, tx hash, execution status, KYC, legal identity, or approved policy fields.",
        },
        {
            "dataset_name": "Zenodo Bitcoin dust transactions",
            "source": "Zenodo / University of Pisa",
            "official_research_public": "research_public",
            "download_url": "https://zenodo.org/records/18938800",
            "license": "Zenodo record; files total 25.6 GB",
            "chain": "Bitcoin",
            "row_count": "all transactions in first 479,970 blocks; exact local row count not downloaded",
            "main_columns": "timestamp,blockId,txId,isCoinbase,fee,approxSize,inputs,outputs,addressId,amount,prevTxId,offset,scriptType",
            "transaction_level_data": "YES",
            "graph_data": "DERIVABLE",
            "label_exists": "NO",
            "amount_info": "YES",
            "timestamp_info": "YES",
            "sender_from_info": "DERIVABLE_FROM_INPUTS",
            "receiver_to_info": "DERIVABLE_FROM_OUTPUTS",
            "tx_hash_id": "YES via txhash_id_map.csv.xz",
            "status_info": "NO explicit confirmation status beyond inclusion in block",
            "fpg_usability": "Best public fit for amount/address/timestamp/tx id, but too large for this local run.",
            "limitations": "25.6 GB compressed files were not downloaded; no KYC, identity, approved policy, or VASP status.",
        },
        {
            "dataset_name": "Ethereum public transactions",
            "source": "ethereum.org / ethereum-etl / Dune-style public schemas",
            "official_research_public": "official_public_schema",
            "download_url": "https://ethereum.org/developers/docs/transactions",
            "license": "documentation/schema reference; raw data access depends on provider",
            "chain": "Ethereum",
            "row_count": "provider-dependent",
            "main_columns": "hash,from,to,value,nonce,input,gas,gas_price,block_timestamp,receipt_status",
            "transaction_level_data": "YES",
            "graph_data": "DERIVABLE",
            "label_exists": "NO",
            "amount_info": "YES",
            "timestamp_info": "YES",
            "sender_from_info": "YES",
            "receiver_to_info": "YES",
            "tx_hash_id": "YES",
            "status_info": "YES via receipt status where receipt table exists",
            "fpg_usability": "Strong field mapping reference for on-chain availability.",
            "limitations": "No legal identity, KYC status, counterparty VASP status, or pre-approved policy fields.",
        },
        {
            "dataset_name": "Elliptic Bitcoin Dataset",
            "source": "Elliptic / Kaggle",
            "official_research_public": "research_public",
            "download_url": "https://www.kaggle.com/datasets/ellipticco/elliptic-data-set/data",
            "license": "CC BY-NC-ND 4.0",
            "chain": "Bitcoin",
            "row_count": "203,769 nodes reported by dataset documentation",
            "main_columns": "txId,class,time_step,166 anonymized features,edges",
            "transaction_level_data": "PARTIAL - graph node with anonymized features",
            "graph_data": "YES",
            "label_exists": "YES",
            "amount_info": "NO explicit amount in public anonymized feature columns",
            "timestamp_info": "PARTIAL - time_step",
            "sender_from_info": "NO",
            "receiver_to_info": "NO",
            "tx_hash_id": "PARTIAL - txId anonymized identifier",
            "status_info": "NO",
            "fpg_usability": "Useful for risk-label and graph experiments, weak for required-field mapping.",
            "limitations": "Kaggle access not downloaded in this step; anonymized fields do not satisfy regulated transfer inputs.",
        },
    ]


def profile_actual(rows: list[dict[str, Any]]) -> dict[str, Any]:
    senders = Counter(r["source_user_id"] for r in rows)
    receivers = Counter(r["target_user_id"] for r in rows)
    dates = Counter(r["event_time"][:10] for r in rows)
    ratings = Counter(r["rating"] for r in rows)
    duplicate_pairs = sum(count - 1 for count in Counter((r["source_user_id"], r["target_user_id"]) for r in rows).values() if count > 1)
    top_sender_share = sum(c for _, c in senders.most_common(10)) / len(rows)
    top_receiver_share = sum(c for _, c in receivers.most_common(10)) / len(rows)
    return {
        "dataset_name": "SNAP Bitcoin OTC trust weighted signed network",
        "row_count": len(rows),
        "columns": list(rows[0].keys()),
        "dtypes": {
            "event_id": "string",
            "source_user_id": "integer",
            "target_user_id": "integer",
            "rating": "integer",
            "timestamp": "float_unix_timestamp",
            "event_time": "datetime_utc",
        },
        "missing_rate": {key: 0 for key in rows[0]},
        "duplicate_transaction": "NOT_APPLICABLE - no transaction hash/id field",
        "tx_identifier_uniqueness": "NOT_APPLICABLE",
        "address_availability": "MISSING - user ids are platform ids, not blockchain addresses",
        "amount_distribution": "MISSING - no amount column in actual file",
        "timestamp_distribution": {
            "min_event_time": min(r["event_time"] for r in rows),
            "max_event_time": max(r["event_time"] for r in rows),
            "active_days": len(dates),
            "top_day_count": max(dates.values()),
        },
        "transaction_frequency": {
            "mean_events_per_day": round(len(rows) / len(dates), 4),
            "max_events_per_day": max(dates.values()),
        },
        "sender_receiver_relationship": {
            "unique_senders": len(senders),
            "unique_receivers": len(receivers),
            "duplicate_source_target_pairs": duplicate_pairs,
            "top_10_sender_share": round(top_sender_share, 4),
            "top_10_receiver_share": round(top_receiver_share, 4),
        },
        "status_confirmation_field_exists": False,
        "graph_link_info_exists": True,
        "label_risk_info_exists": True,
        "rating_distribution": dict(sorted(ratings.items())),
    }


def field_mapping(required_fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    map_rows = []
    actual_cols = {"source_user_id", "target_user_id", "rating", "timestamp", "event_id"}
    mapping = {
        "originator_identity": ("source_user_id", "VASP_INTERNAL", "Platform user id is not legal identity.", "low"),
        "beneficiary_identity": ("target_user_id", "VASP_INTERNAL", "Platform user id is not legal identity.", "low"),
        "originator_address": ("", "MISSING", "Actual file has no blockchain address.", "high"),
        "beneficiary_address": ("", "MISSING", "Actual file has no blockchain address.", "high"),
        "amount": ("", "MISSING", "Actual file has no amount/value column.", "high"),
        "asset": ("", "NOT_APPLICABLE", "Dataset is Bitcoin ecosystem trust graph, not asset transfer ledger.", "medium"),
        "counterparty_vasp": ("", "VASP_INTERNAL", "VASP status is not present in public graph data.", "high"),
        "kyc_status": ("", "EXTERNAL_CONTROL_RESULT", "KYC result is never observable on public chain or trust graph.", "high"),
        "transaction_id": ("event_id", "DERIVABLE_FROM_ONCHAIN", "A local event id can be derived, but it is not blockchain tx hash.", "medium"),
        "tx_hash": ("", "MISSING", "Actual file has no transaction hash.", "high"),
        "execution_status": ("", "EXTERNAL_CONTROL_RESULT", "Execution status must come from execution/receipt system.", "high"),
        "timestamp": ("timestamp|event_time", "ONCHAIN_AVAILABLE", "Actual file has Unix timestamp for graph event.", "high"),
    }
    control_lookup = defaultdict(list)
    for item in required_fields:
        control_lookup[item["field"]].append(item.get("legal_basis", ""))
    for field, (actual, availability, method, confidence) in mapping.items():
        map_rows.append(
            {
                "required_field": field,
                "legal_control": "|".join(sorted(set(control_lookup.get(field, ["ANALYSIS_REQUIRED"])))),
                "actual_dataset_field": actual if actual in actual_cols or "|" in actual else "",
                "availability_class": availability,
                "derivation_method": method,
                "confidence": confidence,
                "note": "Actual dataset evidence prioritized over v1 assumption.",
            }
        )
    return map_rows


def coverage_metrics(mapping: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(mapping)
    counts = Counter(r["availability_class"] for r in mapping)
    by_control = defaultdict(list)
    for row in mapping:
        for control in row["legal_control"].split("|"):
            if control:
                by_control[control].append(row)
    return {
        "total_regulatory_required_fields": total,
        "availability_counts": dict(sorted(counts.items())),
        "availability_ratios": {k: round(v / total, 4) for k, v in sorted(counts.items())},
        "metric_definitions": {
            "Field Coverage Ratio": "Fields with any directly usable actual dataset column divided by total required fields.",
            "On-chain Coverage Ratio": "ONCHAIN_AVAILABLE or DERIVABLE_FROM_ONCHAIN fields divided by total required fields.",
            "External Dependency Ratio": "EXTERNAL_CONTROL_RESULT fields divided by total required fields.",
            "FPG Required Input Ratio": "VASP_INTERNAL, EXTERNAL_CONTROL_RESULT, PRE_EXECUTION_INTERNAL, or MISSING fields divided by total required fields.",
        },
        "field_coverage_ratio": round(sum(bool(r["actual_dataset_field"]) for r in mapping) / total, 4),
        "onchain_coverage_ratio": round(sum(r["availability_class"] in {"ONCHAIN_AVAILABLE", "DERIVABLE_FROM_ONCHAIN"} for r in mapping) / total, 4),
        "external_dependency_ratio": round(sum(r["availability_class"] == "EXTERNAL_CONTROL_RESULT" for r in mapping) / total, 4),
        "fpg_required_input_ratio": round(sum(r["availability_class"] in {"VASP_INTERNAL", "EXTERNAL_CONTROL_RESULT", "PRE_EXECUTION_INTERNAL", "MISSING"} for r in mapping) / total, 4),
    }


def synthetic_v2(actual_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    ratings = [r["rating"] for r in actual_rows]
    senders = [r["source_user_id"] for r in actual_rows]
    receivers = [r["target_user_id"] for r in actual_rows]
    timestamps = [datetime.fromisoformat(r["event_time"]) for r in actual_rows]
    base = datetime(2026, 1, 1, tzinfo=UTC)
    out: list[dict[str, Any]] = []
    for i in range(360):
        rating = ratings[(i * 97) % len(ratings)]
        source = senders[(i * 53) % len(senders)]
        target = receivers[(i * 89) % len(receivers)]
        observed_ts = timestamps[(i * 31) % len(timestamps)]
        requested_at = base + timedelta(days=(observed_ts.toordinal() % 180), minutes=(i * 17) % 1440)
        amount = round([30, 60, 110, 240, 520, 970, 2100, 4500, 9000, 18000][i % 10] * (1 + abs(rating) / 20), 2)
        limit = [500, 1000, 2500, 5000, 10000][(i + abs(rating)) % 5]
        asset = ["BTC", "ETH", "USDT", "USDC"][i % 4]
        requested_asset = asset if i % 11 else "UNAPPROVED_TOKEN"
        destination = ["KR-VASP-A", "KR-VASP-B", "GLOBAL-VASP-C"][i % 3]
        requested_destination = destination if i % 13 else "UNKNOWN_VASP"
        kyc = "VERIFIED" if rating > 0 and i % 9 else ("PENDING" if rating >= 0 else "FAILED")
        status = "EXECUTED" if i % 7 else "PENDING_RESULT"
        out.append(
            {
                "transfer_id": f"DA-V2-{i+1:05d}",
                "originator_id": f"OTC-SRC-{source}",
                "beneficiary_id": f"OTC-DST-{target}",
                "originator_address": "",
                "beneficiary_address": "",
                "kyc_status": kyc,
                "counterparty_vasp_status": "VERIFIED" if requested_destination != "UNKNOWN_VASP" else "UNKNOWN",
                "approved_asset": asset,
                "approved_amount_limit": limit,
                "approved_destination": destination,
                "approved_period_start": "2026-01-01T00:00:00+00:00",
                "approved_period_end": "2026-12-31T23:59:59+00:00" if i % 17 else "2026-01-15T23:59:59+00:00",
                "requested_asset": requested_asset,
                "requested_amount": amount,
                "requested_destination": requested_destination,
                "requested_at": requested_at.isoformat(),
                "transaction_identifier": f"DERIVED-OTC-{i+1:05d}",
                "execution_status": status,
                "actual_distribution_basis": "SNAP_BITCOIN_OTC",
                "actual_rating_proxy": rating,
            }
        )
    metadata = [
        {"column": "originator_id", "source_type": "DERIVED", "generation_rule": "Map actual source_user_id to pseudonymous originator id.", "rationale": "Actual graph sender concentration can seed requester concentration."},
        {"column": "beneficiary_id", "source_type": "DERIVED", "generation_rule": "Map actual target_user_id to pseudonymous beneficiary id.", "rationale": "Actual graph receiver concentration can seed beneficiary concentration."},
        {"column": "requested_at", "source_type": "REAL_DISTRIBUTION", "generation_rule": "Reuse observed timestamp ordinal/minute pattern from actual file.", "rationale": "Temporal concentration comes from real dataset."},
        {"column": "actual_rating_proxy", "source_type": "REAL_DISTRIBUTION", "generation_rule": "Sample actual signed rating distribution.", "rationale": "Used only as counterparty risk proxy, not legal status."},
        {"column": "requested_amount", "source_type": "SYNTHETIC_POLICY_FIELD", "generation_rule": "Heavy-tail scenario buckets scaled by observed rating magnitude.", "rationale": "Actual file has no amount; generation is explicitly synthetic."},
        {"column": "kyc_status", "source_type": "SYNTHETIC_POLICY_FIELD", "generation_rule": "Scenario rule from rating sign plus periodic pending cases.", "rationale": "KYC is external and missing from public data."},
        {"column": "counterparty_vasp_status", "source_type": "SYNTHETIC_POLICY_FIELD", "generation_rule": "Verified unless requested destination is UNKNOWN_VASP.", "rationale": "VASP verification result is internal/external control data."},
    ]
    return out, metadata


def evaluate(rows: list[dict[str, Any]], removed: set[str] | None = None) -> list[str]:
    removed = removed or set()
    decisions: list[str] = []
    for row in rows:
        checks = {}
        if "KYC_STATUS_CHECK" not in removed:
            checks["kyc"] = row["kyc_status"] == "VERIFIED"
        if "ADDRESS_VERIFY" not in removed:
            checks["asset"] = row["requested_asset"] == row["approved_asset"]
        if "COUNTERPARTY_VASP_VERIFY" not in removed:
            checks["counterparty"] = row["counterparty_vasp_status"] == "VERIFIED"
        if "AMOUNT_CONSTRAINT" not in removed:
            checks["amount"] = float(row["requested_amount"]) <= float(row["approved_amount_limit"])
        if "DESTINATION_CONSTRAINT" not in removed:
            checks["destination"] = row["requested_destination"] == row["approved_destination"]
        if "STATUS_INPUT" not in removed:
            checks["status"] = row["execution_status"] in {"EXECUTED", "PENDING_RESULT"}
        if "TRANSACTION_IDENTIFIER" not in removed:
            checks["identifier"] = bool(row["transaction_identifier"])
        if not checks:
            decisions.append("REVIEW")
        elif all(checks.values()):
            decisions.append("PASS")
        elif any(k in checks and not checks[k] for k in ("kyc", "counterparty", "status")):
            decisions.append("REVIEW")
        else:
            decisions.append("BLOCK")
    return decisions


def sensitivity(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    baseline = evaluate(rows)
    baseline_counter = Counter(baseline)
    scenarios = {
        "baseline_all_fields": set(),
        "remove_KYC_STATUS_CHECK": {"KYC_STATUS_CHECK"},
        "remove_ADDRESS_VERIFY": {"ADDRESS_VERIFY"},
        "remove_COUNTERPARTY_VASP_VERIFY": {"COUNTERPARTY_VASP_VERIFY"},
        "remove_AMOUNT_constraint": {"AMOUNT_CONSTRAINT"},
        "remove_destination_constraint": {"DESTINATION_CONSTRAINT"},
        "remove_transaction_identifier": {"TRANSACTION_IDENTIFIER"},
        "remove_status_related_input": {"STATUS_INPUT"},
    }
    results = []
    for scenario, removed in scenarios.items():
        decisions = evaluate(rows, removed)
        counter = Counter(decisions)
        false_allow = sum(1 for b, d in zip(baseline, decisions, strict=True) if b != "PASS" and d == "PASS")
        false_block = sum(1 for b, d in zip(baseline, decisions, strict=True) if b == "PASS" and d == "BLOCK")
        review_increase = counter["REVIEW"] - baseline_counter["REVIEW"]
        normal_preservation = sum(1 for b, d in zip(baseline, decisions, strict=True) if b == "PASS" and d == "PASS")
        results.append(
            {
                "scenario": scenario,
                "removed_fields": sorted(removed),
                "pass_count": counter["PASS"],
                "block_count": counter["BLOCK"],
                "review_count": counter["REVIEW"],
                "false_allow": false_allow,
                "false_block": false_block,
                "undetermined_review_increase": review_increase,
                "normal_transaction_preservation": normal_preservation,
                "delta_false_allow": false_allow,
                "delta_false_block": false_block,
                "delta_review": review_increase,
            }
        )
    return results


def cramers_v(rows: list[dict[str, Any]], col_a: str, col_b: str) -> float:
    table: dict[Any, Counter] = defaultdict(Counter)
    for row in rows:
        table[row[col_a]][row[col_b]] += 1
    row_keys = list(table)
    col_keys = sorted({c for counter in table.values() for c in counter})
    n = len(rows)
    row_totals = {r: sum(table[r].values()) for r in row_keys}
    col_totals = {c: sum(table[r][c] for r in row_keys) for c in col_keys}
    chi2 = 0.0
    for r in row_keys:
        for c in col_keys:
            expected = row_totals[r] * col_totals[c] / n
            if expected:
                chi2 += (table[r][c] - expected) ** 2 / expected
    denom = n * max(1, min(len(row_keys) - 1, len(col_keys) - 1))
    return round((chi2 / denom) ** 0.5, 4)


def build_v2_artifacts(
    mapping: list[dict[str, Any]],
    metrics: dict[str, Any],
    rows: list[dict[str, Any]],
    sens: list[dict[str, Any]],
    actual_row_count: int,
) -> None:
    v1_controls = read_json(V1 / "regulatory_controls.json")
    controls = []
    for control in v1_controls:
        fields = control.get("required_fields", [])
        mapped = [m for m in mapping if m["required_field"] in fields]
        controls.append(
            {
                **control,
                "actual_data_coverage": {
                    "field_count": len(mapped),
                    "onchain_or_derivable": sum(m["availability_class"] in {"ONCHAIN_AVAILABLE", "DERIVABLE_FROM_ONCHAIN"} for m in mapped),
                    "missing_or_internal": sum(m["availability_class"] in {"VASP_INTERNAL", "EXTERNAL_CONTROL_RESULT", "PRE_EXECUTION_INTERNAL", "MISSING"} for m in mapped),
                    "runtime_enforcement_readiness": "partial" if mapped else "review_required",
                },
            }
        )
    required_fields = [{**m, "v2_status": "actual_dataset_profiled"} for m in mapping]
    base_policy = read_json(V1 / "candidate_policy.json")
    kept_rules = []
    for rule in base_policy["policy_rules"]:
        rule = dict(rule)
        field = rule["required_field"]
        availability = next((m["availability_class"] for m in mapping if m["required_field"] == field), "MISSING")
        rule["actual_dataset_evidence"] = availability
        rule["v2_change"] = "kept_with_actual_data_gap" if availability != "MISSING" else "kept_but_actual_data_validation_unavailable"
        kept_rules.append(rule)
    candidate_v2 = {
        "artifact_id": "DA-CANDIDATE-POLICY-REGULATED-TRANSFER-002",
        "artifact_version": "v2",
        "status": "candidate",
        "v1_ref": "DA-CANDIDATE-POLICY-REGULATED-TRANSFER-001",
        "policy_rules": kept_rules,
        "v1_to_v2_changes": {
            "retained_rules": [r["policy_rule_id"] for r in kept_rules],
            "removed_rules": [],
            "actual_data_evidence_added_rules": [r["policy_rule_id"] for r in kept_rules if r["actual_dataset_evidence"] != "MISSING"],
            "regulatory_only_rules": [r["policy_rule_id"] for r in kept_rules if r["actual_dataset_evidence"] == "MISSING"],
            "future_vasp_internal_data_required_rules": [r["policy_rule_id"] for r in kept_rules if r["actual_dataset_evidence"] in {"VASP_INTERNAL", "EXTERNAL_CONTROL_RESULT", "PRE_EXECUTION_INTERNAL", "MISSING"}],
        },
        "non_decisions": [
            "No BE handoff artifact or runtime API was modified.",
            "Synthetic v2 is not represented as real market or production transaction statistics.",
            "Amount generation remains synthetic because the actual downloaded file has no amount column.",
        ],
    }
    write_json(V2 / "regulatory_controls.json", controls)
    write_json(V2 / "required_fields.json", required_fields)
    write_json(V2 / "schema_gap_detailed.json", {"mapping": mapping, "metrics": metrics})
    write_json(V2 / "candidate_policy_v2.json", candidate_v2)
    write_json(V2 / "policy_sensitivity_results.json", sens)
    (V2 / "analysis_summary.md").write_text(
        "\n".join(
            [
                "# Digital Asset Candidate Policy v2",
                "",
                "Scope: regulated virtual asset transfer schema-gap and policy sensitivity analysis.",
                "",
                f"- Actual dataset used: SNAP Bitcoin OTC trust weighted signed network ({actual_row_count} rows)",
                f"- Regulatory required fields: {metrics['total_regulatory_required_fields']}",
                f"- On-chain/derivable coverage ratio: {metrics['onchain_coverage_ratio']}",
                f"- FPG required input ratio: {metrics['fpg_required_input_ratio']}",
                f"- Sensitivity scenarios: {len(sens)}",
                "",
                "v2 keeps v1 candidate rules but adds actual dataset evidence/gap classification and policy removal sensitivity. No BE handoff artifact is changed.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def build_notebook() -> None:
    nb = nbf.v4.new_notebook()
    nb["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12"},
    }
    cells = [
        nbf.v4.new_markdown_cell("# Crypto Transaction Schema Analysis v2\n\nActual downloaded data is separated from synthetic policy fields. This notebook does not modify BE contracts or runtime APIs."),
        nbf.v4.new_markdown_cell("## Context & Inputs\n\nLoad the actual public Bitcoin OTC graph file, regulatory required-field mapping, synthetic v2 dataset, and policy sensitivity results."),
        nbf.v4.new_code_cell(
            "# ruff: noqa: E501, E701, E702, I001\n"
            "\n"
            "from pathlib import Path\nimport json\nimport pandas as pd\nimport matplotlib.pyplot as plt\n"
            "ROOT = Path.cwd().resolve()\nif ROOT.name != 'ADP-DA': ROOT = next(p for p in [ROOT, *ROOT.parents] if p.name == 'ADP-DA')\n"
            "actual = pd.read_csv(ROOT/'03_digital_asset/data/raw/transactions/soc-sign-bitcoinotc.csv')\n"
            "inventory = pd.read_csv(ROOT/'03_digital_asset/data/raw/crypto_card/public_transaction_dataset_inventory.csv')\n"
            "mapping = pd.read_csv(ROOT/'03_digital_asset/data/processed/regulatory_transaction_field_mapping.csv')\n"
            "synthetic = pd.read_csv(ROOT/'03_digital_asset/data/processed/synthetic_regulated_transfer_v2.csv')\n"
            "sensitivity = pd.DataFrame(json.loads((ROOT/'03_digital_asset/artifacts/candidate_policy_v2/policy_sensitivity_results.json').read_text(encoding='utf-8')))\n"
            "profile = json.loads((ROOT/'03_digital_asset/data/processed/actual_transaction_profile.json').read_text(encoding='utf-8'))\n"
            "print({'actual_rows': len(actual), 'synthetic_rows': len(synthetic), 'required_fields': len(mapping)})"
        ),
        nbf.v4.new_markdown_cell("## 1. Row Count, Columns, Types, Missingness\n\nThis verifies what execution-like fields actually exist in the downloaded file."),
        nbf.v4.new_code_cell("display(actual.head())\ndisplay(pd.DataFrame({'column': actual.columns, 'dtype': [str(t) for t in actual.dtypes], 'missing_rate': actual.isna().mean().round(4).values}))"),
        nbf.v4.new_markdown_cell("## 2. Identifier, Address, Status, Graph, Label Availability\n\nThe downloaded file has an event id and graph edges, but no blockchain transaction hash, address, amount, or execution status."),
        nbf.v4.new_code_cell("availability = {k: profile[k] for k in ['duplicate_transaction','tx_identifier_uniqueness','address_availability','amount_distribution','status_confirmation_field_exists','graph_link_info_exists','label_risk_info_exists']}\nprint(availability)"),
        nbf.v4.new_markdown_cell("## 3. Actual Temporal Distribution And Frequency\n\nFrequency is measured from actual event timestamps."),
        nbf.v4.new_code_cell("actual['event_day'] = pd.to_datetime(actual['event_time']).dt.date\nfreq = actual.groupby('event_day').size().reset_index(name='events')\ndisplay(freq.describe())\nfreq.plot(x='event_day', y='events', legend=False, color='#3f7f93', title='Actual Bitcoin OTC Event Frequency')\nplt.xticks(rotation=45, ha='right'); plt.tight_layout()"),
        nbf.v4.new_markdown_cell("## 4. Sender/Receiver Concentration\n\nSource and target user concentration are actual graph properties and are used for synthetic v2 concentration only."),
        nbf.v4.new_code_cell("sender_top = actual['source_user_id'].value_counts().head(10).reset_index(); sender_top.columns=['source_user_id','count']\nreceiver_top = actual['target_user_id'].value_counts().head(10).reset_index(); receiver_top.columns=['target_user_id','count']\ndisplay(sender_top); display(receiver_top)\nsender_top.plot.bar(x='source_user_id', y='count', legend=False, color='#446fb3', title='Top Actual Senders')\nplt.tight_layout()"),
        nbf.v4.new_markdown_cell("## 5. Amount Distribution\n\nThe actual downloaded file has no amount. The v2 amount column is therefore explicitly synthetic and must not be interpreted as observed market volume."),
        nbf.v4.new_code_cell("synthetic['requested_amount'].plot.hist(bins=30, color='#4f8f65', title='Synthetic v2 Requested Amount Distribution')\nplt.tight_layout()\ndisplay(synthetic['requested_amount'].describe())"),
        nbf.v4.new_markdown_cell("## 6. Regulatory -> Transaction Field Mapping\n\nMap each regulatory required field to an actual dataset column and availability class."),
        nbf.v4.new_code_cell("display(mapping[['required_field','legal_control','actual_dataset_field','availability_class','confidence']])"),
        nbf.v4.new_markdown_cell("## 7. Regulatory Field Availability Distribution"),
        nbf.v4.new_code_cell("availability = mapping['availability_class'].value_counts().rename_axis('availability_class').reset_index(name='count')\ndisplay(availability)\navailability.plot.bar(x='availability_class', y='count', legend=False, color='#3f7f93', title='Regulatory Field Availability')\nplt.xticks(rotation=45, ha='right'); plt.tight_layout()"),
        nbf.v4.new_markdown_cell("## 8. Control-Level Coverage\n\nControl readiness is quantified from mapped required fields, not inferred from legal text alone."),
        nbf.v4.new_code_cell("gap = json.loads((ROOT/'03_digital_asset/artifacts/candidate_policy_v2/schema_gap_detailed.json').read_text(encoding='utf-8'))\nprint(gap['metrics'])"),
        nbf.v4.new_markdown_cell("## 9. Policy Removal Sensitivity\n\nCompare baseline against removal scenarios for PASS/BLOCK/REVIEW and false allow/block deltas."),
        nbf.v4.new_code_cell("display(sensitivity)\nsensitivity.set_index('scenario')[['pass_count','block_count','review_count']].plot.bar(color=['#3f7f93','#446fb3','#9a6b45'], title='Policy Removal Decision Counts')\nplt.xticks(rotation=45, ha='right'); plt.tight_layout()"),
        nbf.v4.new_markdown_cell("## 10. False Allow Sensitivity"),
        nbf.v4.new_code_cell("sensitivity.set_index('scenario')['false_allow'].plot.bar(color='#b35a4a', title='False Allow by Policy Removal')\nplt.xticks(rotation=45, ha='right'); plt.tight_layout()"),
        nbf.v4.new_markdown_cell("## 11. Statistical Support\n\nUse effect sizes where the data supports it. Cramer's V is calculated for categorical associations; no unsupported p-value-only claims are made."),
        nbf.v4.new_code_cell("stats = json.loads((ROOT/'03_digital_asset/data/processed/statistical_support_v2.json').read_text(encoding='utf-8'))\nprint(stats)"),
        nbf.v4.new_markdown_cell("## Takeaways\n\nSupported: H1, H2, H3, H4. H5 remains a design requirement because the actual downloaded file lacks transaction hash and execution status fields."),
    ]
    nb["cells"] = cells
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, NOTEBOOK)


def main() -> None:
    actual_rows = load_bitcoin_otc()
    required_fields = read_json(V1 / "required_fields.json")
    mapping = field_mapping(required_fields)
    metrics = coverage_metrics(mapping)
    synthetic_rows, metadata = synthetic_v2(actual_rows)
    decisions = evaluate(synthetic_rows)
    for row, decision in zip(synthetic_rows, decisions, strict=True):
        row["baseline_policy_decision"] = decision
    sens = sensitivity(synthetic_rows)
    stats = {
        "categorical_effect_sizes": {
            "kyc_status_vs_decision_cramers_v": cramers_v(synthetic_rows, "kyc_status", "baseline_policy_decision"),
            "counterparty_vasp_status_vs_decision_cramers_v": cramers_v(synthetic_rows, "counterparty_vasp_status", "baseline_policy_decision"),
            "requested_asset_vs_decision_cramers_v": cramers_v(synthetic_rows, "requested_asset", "baseline_policy_decision"),
        },
        "unsupported_tests_not_run": [
            "Mann-Whitney U for actual amount: actual downloaded file has no amount.",
            "Kruskal-Wallis for execution status: actual downloaded file has no execution status.",
            "Proportion test for blockchain status: actual downloaded file has no blockchain receipt status.",
        ],
    }
    write_json(PROCESSED / "actual_transaction_profile.json", profile_actual(actual_rows))
    inventory = dataset_inventory(len(actual_rows))
    write_csv(
        RAW_CARD / "public_transaction_dataset_inventory.csv",
        inventory,
        [
            "dataset_name",
            "source",
            "official_research_public",
            "download_url",
            "license",
            "chain",
            "row_count",
            "main_columns",
            "transaction_level_data",
            "graph_data",
            "label_exists",
            "amount_info",
            "timestamp_info",
            "sender_from_info",
            "receiver_to_info",
            "tx_hash_id",
            "status_info",
            "fpg_usability",
            "limitations",
        ],
    )
    write_json(RAW_CARD / "public_transaction_dataset_inventory.json", inventory)
    write_csv(
        PROCESSED / "regulatory_transaction_field_mapping.csv",
        mapping,
        ["required_field", "legal_control", "actual_dataset_field", "availability_class", "derivation_method", "confidence", "note"],
    )
    write_json(PROCESSED / "schema_gap_metrics_v2.json", metrics)
    write_csv(PROCESSED / "synthetic_regulated_transfer_v2.csv", synthetic_rows, list(synthetic_rows[0].keys()))
    write_json(PROCESSED / "synthetic_regulated_transfer_v2_metadata.json", metadata)
    write_json(PROCESSED / "statistical_support_v2.json", stats)
    build_v2_artifacts(mapping, metrics, synthetic_rows, sens, len(actual_rows))
    build_notebook()


if __name__ == "__main__":
    main()
