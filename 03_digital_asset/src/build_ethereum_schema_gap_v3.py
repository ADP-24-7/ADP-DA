# ruff: noqa: E501, E701, E702, I001

from __future__ import annotations

import csv
import json
import math
import os
import statistics
import time
import urllib.request
from urllib.error import HTTPError
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any

import nbformat as nbf


getcontext().prec = 40

ROOT = Path(__file__).resolve().parents[2]
DA = ROOT / "03_digital_asset"
RAW_TX = DA / "data" / "raw" / "transactions"
RAW_CARD = DA / "data" / "raw" / "crypto_card"
PROCESSED = DA / "data" / "processed"
V2 = DA / "artifacts" / "candidate_policy_v2"
V3 = DA / "artifacts" / "candidate_policy_v3"
NOTEBOOK = DA / "notebooks" / "03_ethereum_transaction_schema_validation.ipynb"

RPC_URL = os.getenv("ETHEREUM_RPC_URL", "https://ethereum.publicnode.com")
TARGET_ROWS = int(os.getenv("FPG_ETHEREUM_SAMPLE_ROWS", "50000"))
MAX_BLOCKS = int(os.getenv("FPG_ETHEREUM_MAX_BLOCKS", "650"))
BATCH_SIZE = int(os.getenv("FPG_ETHEREUM_RECEIPT_BATCH_SIZE", "80"))
FETCH_RECEIPTS = os.getenv("FPG_ETHEREUM_FETCH_RECEIPTS", "0") == "1"


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


def hex_int(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    return int(value, 16)


def value_eth(value_wei: int | None) -> str:
    if value_wei is None:
        return ""
    return str(Decimal(value_wei) / Decimal(10**18))


def rpc_call(method: str, params: list[Any]) -> Any:
    payload = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode("utf-8")
    request = urllib.request.Request(
        RPC_URL,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "ADP-DA-FPG-research/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    if "error" in data:
        raise RuntimeError(data["error"])
    return data["result"]


def rpc_batch(calls: list[dict[str, Any]]) -> list[Any]:
    payload = json.dumps(calls).encode("utf-8")
    request = urllib.request.Request(
        RPC_URL,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "ADP-DA-FPG-research/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    by_id = {item["id"]: item for item in data}
    results = []
    for call in calls:
        item = by_id[call["id"]]
        if "error" in item:
            results.append(None)
        else:
            results.append(item.get("result"))
    return results


def fetch_ethereum_transactions() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    RAW_TX.mkdir(parents=True, exist_ok=True)
    latest_block = hex_int(rpc_call("eth_blockNumber", []))
    assert latest_block is not None
    rows: list[dict[str, Any]] = []
    started_at = datetime.now(tz=UTC)
    start_block = latest_block
    blocks_checked = 0
    receipt_access_status = "NOT_REQUESTED - set FPG_ETHEREUM_FETCH_RECEIPTS=1 to attempt receipt_status extraction"
    extraction_query = "\n".join(
        [
            "-- JSON-RPC extraction equivalent to:",
            "-- eth_blockNumber",
            "-- eth_getBlockByNumber(block_number, true)",
            "-- eth_getTransactionReceipt(transaction_hash)",
            f"-- endpoint: {RPC_URL}",
            f"-- target_rows: {TARGET_ROWS}",
            f"-- max_blocks: {MAX_BLOCKS}",
        ]
    )
    (RAW_TX / "ethereum_transactions_query.sql").write_text(extraction_query + "\n", encoding="utf-8")

    for block_number in range(start_block, max(start_block - MAX_BLOCKS, 0), -1):
        block_hex = hex(block_number)
        block = rpc_call("eth_getBlockByNumber", [block_hex, True])
        blocks_checked += 1
        if not block or not block.get("transactions"):
            continue
        block_time = datetime.fromtimestamp(hex_int(block["timestamp"]) or 0, tz=UTC)
        txs = block["transactions"]
        receipt_lookup: dict[str, Any] = {}
        if FETCH_RECEIPTS:
            try:
                for offset in range(0, len(txs), BATCH_SIZE):
                    batch = [
                        {"jsonrpc": "2.0", "method": "eth_getTransactionReceipt", "params": [tx["hash"]], "id": offset + i}
                        for i, tx in enumerate(txs[offset : offset + BATCH_SIZE])
                    ]
                    for tx, receipt in zip(txs[offset : offset + BATCH_SIZE], rpc_batch(batch), strict=True):
                        receipt_lookup[tx["hash"]] = receipt or {}
                receipt_access_status = "SUCCESS"
            except HTTPError as exc:
                receipt_access_status = f"FAILED_HTTP_{exc.code} - receipt_status left blank; block transaction fields retained"
                receipt_lookup = {}
                os.environ["FPG_ETHEREUM_FETCH_RECEIPTS"] = "0"
        for tx in txs:
            value_wei = hex_int(tx.get("value"))
            receipt = receipt_lookup.get(tx["hash"], {})
            input_data = tx.get("input") or ""
            rows.append(
                {
                    "hash": tx["hash"],
                    "from_address": tx.get("from") or "",
                    "to_address": tx.get("to") or "",
                    "value_wei": value_wei if value_wei is not None else "",
                    "value_eth": value_eth(value_wei),
                    "block_timestamp": block_time.isoformat(),
                    "block_number": hex_int(tx.get("blockNumber")),
                    "transaction_index": hex_int(tx.get("transactionIndex")),
                    "nonce": hex_int(tx.get("nonce")),
                    "gas": hex_int(tx.get("gas")),
                    "gas_price": hex_int(tx.get("gasPrice")),
                    "max_fee_per_gas": hex_int(tx.get("maxFeePerGas")),
                    "max_priority_fee_per_gas": hex_int(tx.get("maxPriorityFeePerGas")),
                    "input_size": max(0, (len(input_data) - 2) // 2) if input_data.startswith("0x") else len(input_data),
                    "has_input": input_data not in ("", "0x"),
                    "transaction_type": tx.get("type", ""),
                    "receipt_status": hex_int(receipt.get("status")) if receipt else "",
                    "receipt_gas_used": hex_int(receipt.get("gasUsed")) if receipt else "",
                }
            )
            if len(rows) >= TARGET_ROWS:
                break
        if len(rows) >= TARGET_ROWS:
            break
        time.sleep(0.03)

    fields = [
        "hash",
        "from_address",
        "to_address",
        "value_wei",
        "value_eth",
        "block_timestamp",
        "block_number",
        "transaction_index",
        "nonce",
        "gas",
        "gas_price",
        "max_fee_per_gas",
        "max_priority_fee_per_gas",
        "input_size",
        "has_input",
        "transaction_type",
        "receipt_status",
        "receipt_gas_used",
    ]
    write_csv(RAW_TX / "ethereum_transactions_sample.csv", rows, fields)
    metadata = {
        "dataset_name": "Ethereum mainnet JSON-RPC transaction sample",
        "provider": "ethereum.publicnode.com JSON-RPC",
        "source_url": RPC_URL,
        "extraction_method": "eth_getBlockByNumber(full transactions)" + (" plus eth_getTransactionReceipt by transaction hash" if FETCH_RECEIPTS else "; receipt extraction not requested in this run"),
        "extraction_query": "03_digital_asset/data/raw/transactions/ethereum_transactions_query.sql",
        "extraction_date": started_at.isoformat(),
        "chain": "Ethereum mainnet",
        "sampling_period": {
            "start_block_descending_from": start_block,
            "end_block_reached": rows[-1]["block_number"] if rows else None,
            "min_block_timestamp": min((r["block_timestamp"] for r in rows), default=None),
            "max_block_timestamp": max((r["block_timestamp"] for r in rows), default=None),
            "blocks_checked": blocks_checked,
            "row_limit": TARGET_ROWS,
        },
        "receipt_access_status": receipt_access_status,
        "row_count": len(rows),
        "columns": fields,
        "license_or_terms": "Public Ethereum mainnet data accessed through a public JSON-RPC endpoint; endpoint terms depend on provider.",
        "limitations": [
            "Recent-block sample only, not a full-chain distribution.",
            "No VASP customer identity, KYC status, approved policy, or counterparty VASP verification.",
            "Public endpoint availability and rate limits affect exact reproducibility.",
        ],
        "reproducibility_note": "Set ETHEREUM_RPC_URL, FPG_ETHEREUM_SAMPLE_ROWS, FPG_ETHEREUM_MAX_BLOCKS, and rerun 03_digital_asset/src/build_ethereum_schema_gap_v3.py.",
    }
    write_json(RAW_TX / "ethereum_transactions_metadata.json", metadata)
    return rows, metadata


def load_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8-sig", newline="") as fp:
        return list(csv.DictReader(fp))


def gini(values: list[int]) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    total = sum(sorted_values)
    if total == 0:
        return 0.0
    weighted = sum((i + 1) * value for i, value in enumerate(sorted_values))
    return round((2 * weighted) / (len(values) * total) - (len(values) + 1) / len(values), 4)


def pct(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    pos = (len(values) - 1) * q
    lower = math.floor(pos)
    upper = math.ceil(pos)
    if lower == upper:
        return values[lower]
    return values[lower] + (values[upper] - values[lower]) * (pos - lower)


def profile_ethereum(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = [float(r["value_eth"]) for r in rows if r["value_eth"] not in ("", None)]
    senders = Counter(r["from_address"] for r in rows if r["from_address"])
    receivers = Counter(r["to_address"] for r in rows if r["to_address"])
    days = Counter(r["block_timestamp"][:10] for r in rows)
    hashes = [r["hash"] for r in rows]
    duplicates = len(hashes) - len(set(hashes))
    sender_counts = list(senders.values())
    receiver_counts = list(receivers.values())
    one_pct_senders = max(1, math.ceil(len(sender_counts) * 0.01))
    one_pct_receivers = max(1, math.ceil(len(receiver_counts) * 0.01))
    total = len(rows)
    missing = {
        key: round(sum(r.get(key) in ("", None) for r in rows) / total, 4)
        for key in rows[0]
    }
    return {
        "dataset_name": "Ethereum mainnet JSON-RPC transaction sample",
        "dataset_role": "MAIN_TRANSACTION_DATA",
        "row_count": total,
        "columns": list(rows[0].keys()),
        "dtypes": {
            "hash": "hex_string",
            "from_address": "address",
            "to_address": "address_nullable_for_contract_creation",
            "value_wei": "integer",
            "value_eth": "decimal_eth",
            "block_timestamp": "datetime_utc",
            "block_number": "integer",
            "transaction_index": "integer",
            "nonce": "integer",
            "gas": "integer",
            "gas_price": "integer_nullable",
            "receipt_status": "integer_nullable",
        },
        "missing_rate": missing,
        "unique_transaction_hash": len(set(hashes)),
        "duplicate_transaction_count": duplicates,
        "hash_uniqueness_ratio": round(len(set(hashes)) / total, 4),
        "from_to_availability": {
            "from_address_available_ratio": round(sum(bool(r["from_address"]) for r in rows) / total, 4),
            "to_address_available_ratio": round(sum(bool(r["to_address"]) for r in rows) / total, 4),
        },
        "value_availability_ratio": round(sum(r["value_eth"] not in ("", None) for r in rows) / total, 4),
        "timestamp_availability_ratio": round(sum(bool(r["block_timestamp"]) for r in rows) / total, 4),
        "status_availability_ratio": round(sum(r["receipt_status"] not in ("", None) for r in rows) / total, 4),
        "value_distribution_eth": {
            "count": len(values),
            "mean": round(statistics.fmean(values), 12) if values else 0,
            "std": round(statistics.pstdev(values), 12) if len(values) > 1 else 0,
            "min": pct(values, 0),
            "p25": pct(values, 0.25),
            "median": pct(values, 0.5),
            "p75": pct(values, 0.75),
            "p90": pct(values, 0.9),
            "p95": pct(values, 0.95),
            "p99": pct(values, 0.99),
            "max": pct(values, 1),
            "zero_value_ratio": round(sum(v == 0 for v in values) / len(values), 4) if values else 0,
            "top_1pct_value_share": round(sum(sorted(values, reverse=True)[: max(1, math.ceil(len(values) * 0.01))]) / sum(values), 4) if sum(values) else 0,
        },
        "transaction_frequency": {
            "daily_transaction_count": dict(sorted(days.items())),
            "mean_transactions_per_day": round(total / max(1, len(days)), 4),
            "max_transactions_per_day": max(days.values()) if days else 0,
        },
        "sender_concentration": {
            "unique_senders": len(senders),
            "top_10_share": round(sum(c for _, c in senders.most_common(10)) / total, 4),
            "top_1pct_share": round(sum(sorted(sender_counts, reverse=True)[:one_pct_senders]) / total, 4),
            "gini": gini(sender_counts),
        },
        "receiver_concentration": {
            "unique_receivers": len(receivers),
            "top_10_share": round(sum(c for _, c in receivers.most_common(10)) / total, 4),
            "top_1pct_share": round(sum(sorted(receiver_counts, reverse=True)[:one_pct_receivers]) / total, 4),
            "gini": gini(receiver_counts),
        },
        "identity_and_replay_fields": {
            "hash": "unique transaction identifier in sample",
            "nonce": "available sequencing value within sender account",
            "block_number": "available chain ordering context",
            "transaction_index": "available ordering within block",
            "receipt_status": "available only when receipt extraction succeeds; otherwise unresolved in local sample",
            "claim_boundary": "These fields support structural uniqueness/sequencing analysis only; this sample does not prove FPG replay prevention effectiveness.",
        },
    }


def update_inventory(row_count: int) -> None:
    rows = load_csv(RAW_CARD / "public_transaction_dataset_inventory.csv")
    for row in rows:
        if row["dataset_name"] == "SNAP Bitcoin OTC trust weighted signed network":
            row["dataset_role"] = "SUPPORTING_NETWORK_DATA"
            row["fpg_usability"] = "Supporting network data only: counterparty relationship, sender/receiver concentration, and network structure."
            row["limitations"] = "Not a blockchain transaction execution ledger; not used as main schema-gap evidence in v3."
        elif row["dataset_name"] == "Ethereum public transactions":
            row["dataset_role"] = "MAIN_TRANSACTION_DATA"
            row["row_count"] = row_count
            row["download_url"] = RPC_URL
            row["source"] = "Ethereum JSON-RPC public endpoint / Ethereum public schema"
            row["license"] = "Public Ethereum mainnet data; endpoint terms depend on provider."
            row["status_info"] = "Receipt status exists via eth_getTransactionReceipt, but is not populated in the local v3 sample unless FPG_ETHEREUM_FETCH_RECEIPTS=1 succeeds."
            row["fpg_usability"] = "Main transaction-level schema-gap dataset for v3."
            row["limitations"] = "No VASP identity, KYC status, approved asset/amount/destination, or counterparty VASP verification."
    if "dataset_role" not in rows[0]:
        for row in rows:
            row["dataset_role"] = row.get("dataset_role", "")
    fieldnames = list(rows[0].keys())
    if "dataset_role" not in fieldnames:
        fieldnames.append("dataset_role")
    write_csv(RAW_CARD / "public_transaction_dataset_inventory.csv", rows, fieldnames)
    write_json(RAW_CARD / "public_transaction_dataset_inventory.json", rows)


def ethereum_field_mapping(status_available: bool) -> list[dict[str, Any]]:
    v2_fields = read_json(V2 / "required_fields.json")
    legal = {item["required_field"]: item.get("legal_control", "ANALYSIS_REQUIRED") for item in v2_fields}
    mapping = [
        ("originator_identity", "", "VASP_INTERNAL", "Blockchain from_address is wallet address, not legal originator identity.", "high", "Ethereum schema has from_address but not customer identity."),
        ("beneficiary_identity", "", "VASP_INTERNAL", "Blockchain to_address is wallet/contract address, not legal beneficiary identity.", "high", "Ethereum schema has to_address but not customer identity."),
        ("originator_address", "from_address", "ONCHAIN_AVAILABLE", "Use transaction from_address.", "high", "Present in Ethereum transactions."),
        ("beneficiary_address", "to_address", "ONCHAIN_AVAILABLE", "Use transaction to_address; missing for contract creation.", "high", "Present in Ethereum transactions with nullable contract-creation cases."),
        ("amount", "value_eth|value_wei", "ONCHAIN_AVAILABLE", "Convert value_wei to ETH as value_eth.", "high", "Present in Ethereum transactions."),
        ("asset", "", "DERIVABLE_FROM_ONCHAIN", "Native ETH is derivable from chain context for this sample; token asset needs logs/token_transfers.", "medium", "This sample is native transaction table, not token-transfer table."),
        ("counterparty_vasp", "", "VASP_INTERNAL", "Requires VASP/customer registry or counterparty VASP verification service.", "high", "Not present on public chain."),
        ("kyc_status", "", "EXTERNAL_CONTROL_RESULT", "Requires KYC/compliance provider or VASP internal result.", "high", "Not present on public chain."),
        ("transaction_id", "hash", "ONCHAIN_AVAILABLE", "Use Ethereum transaction hash.", "high", "Present and unique in sample."),
        ("tx_hash", "hash", "ONCHAIN_AVAILABLE", "Use Ethereum transaction hash.", "high", "Present and unique in sample."),
        (
            "execution_status",
            "receipt_status" if status_available else "",
            "ONCHAIN_AVAILABLE" if status_available else "MISSING",
            "Use transaction receipt status returned by eth_getTransactionReceipt." if status_available else "Receipt status extraction was rate-limited or unavailable in the local sample.",
            "medium" if status_available else "high",
            "Available through receipt lookup in this sample." if status_available else "Not populated in ethereum_transactions_sample.csv.",
        ),
        ("timestamp", "block_timestamp", "ONCHAIN_AVAILABLE", "Use block timestamp.", "high", "Present via block data."),
    ]
    return [
        {
            "required_field": field,
            "legal_control": legal.get(field, "ANALYSIS_REQUIRED"),
            "ethereum_field": eth_field,
            "availability_class": cls,
            "derivation_method": method,
            "confidence": confidence,
            "evidence": evidence,
            "note": "v3 mapping uses Ethereum transaction-level data as MAIN_TRANSACTION_DATA.",
        }
        for field, eth_field, cls, method, confidence, evidence in mapping
    ]


def schema_gap_metrics(mapping: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(mapping)
    counts = Counter(row["availability_class"] for row in mapping)
    for key in ["ONCHAIN_AVAILABLE", "DERIVABLE_FROM_ONCHAIN", "VASP_INTERNAL", "EXTERNAL_CONTROL_RESULT", "PRE_EXECUTION_INTERNAL", "MISSING", "NOT_APPLICABLE"]:
        counts.setdefault(key, 0)
    return {
        "total_required_fields": total,
        "availability_counts": dict(sorted(counts.items())),
        "availability_ratios": {key: round(value / total, 4) for key, value in sorted(counts.items())},
        "metric_definitions": {
            "On-chain Direct Coverage Ratio": "ONCHAIN_AVAILABLE / Total Required Fields.",
            "On-chain Extended Coverage Ratio": "(ONCHAIN_AVAILABLE + DERIVABLE_FROM_ONCHAIN) / Total Required Fields.",
            "Non-chain Dependency Ratio": "(VASP_INTERNAL + EXTERNAL_CONTROL_RESULT + PRE_EXECUTION_INTERNAL) / Total Required Fields.",
            "FPG Runtime Dependency Ratio": "Fields FPG must receive from internal/external runtime systems rather than public blockchain execution data.",
        },
        "onchain_direct_coverage_ratio": round(counts["ONCHAIN_AVAILABLE"] / total, 4),
        "onchain_extended_coverage_ratio": round((counts["ONCHAIN_AVAILABLE"] + counts["DERIVABLE_FROM_ONCHAIN"]) / total, 4),
        "non_chain_dependency_ratio": round((counts["VASP_INTERNAL"] + counts["EXTERNAL_CONTROL_RESULT"] + counts["PRE_EXECUTION_INTERNAL"]) / total, 4),
        "fpg_runtime_dependency_ratio": round((counts["VASP_INTERNAL"] + counts["EXTERNAL_CONTROL_RESULT"] + counts["PRE_EXECUTION_INTERNAL"]) / total, 4),
        "v2_snap_ratio_deprecated_for_main_conclusion": True,
    }


def control_coverage(mapping: list[dict[str, Any]]) -> list[dict[str, Any]]:
    core_controls = [
        "ORIGINATOR_VERIFY",
        "BENEFICIARY_VERIFY",
        "ADDRESS_VERIFY",
        "COUNTERPARTY_VASP_VERIFY",
        "KYC_STATUS_CHECK",
        "TRANSFER_RESTRICTION",
        "INFORMATION_TRANSFER",
        "RECORD_KEEPING",
    ]
    control_to_fields = {
        "ORIGINATOR_VERIFY": ["originator_identity", "originator_address"],
        "BENEFICIARY_VERIFY": ["beneficiary_identity", "beneficiary_address"],
        "ADDRESS_VERIFY": ["originator_address", "beneficiary_address"],
        "COUNTERPARTY_VASP_VERIFY": ["counterparty_vasp"],
        "KYC_STATUS_CHECK": ["kyc_status"],
        "TRANSFER_RESTRICTION": ["asset", "amount", "timestamp", "kyc_status", "counterparty_vasp"],
        "INFORMATION_TRANSFER": ["transaction_id", "tx_hash", "timestamp"],
        "RECORD_KEEPING": ["transaction_id", "tx_hash", "execution_status", "timestamp"],
    }
    by_field = {row["required_field"]: row for row in mapping}
    out = []
    for control in core_controls:
        fields = [by_field[f] for f in control_to_fields[control] if f in by_field]
        onchain = sum(f["availability_class"] in {"ONCHAIN_AVAILABLE", "DERIVABLE_FROM_ONCHAIN"} for f in fields)
        internal = sum(f["availability_class"] == "VASP_INTERNAL" for f in fields)
        external = sum(f["availability_class"] == "EXTERNAL_CONTROL_RESULT" for f in fields)
        pre_exec = sum(f["availability_class"] == "PRE_EXECUTION_INTERNAL" for f in fields)
        readiness = "READY_WITH_CHAIN_DATA" if fields and onchain == len(fields) else "REQUIRES_NON_CHAIN_INPUT"
        out.append(
            {
                "control": control,
                "required_field_count": len(fields),
                "onchain_field_count": onchain,
                "internal_dependency_count": internal,
                "external_dependency_count": external,
                "pre_execution_dependency_count": pre_exec,
                "runtime_readiness": readiness,
                "fields": [f["required_field"] for f in fields],
            }
        )
    return out


def build_synthetic_v3(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    values = [float(r["value_eth"]) for r in rows if r["value_eth"] not in ("", None)]
    positive_values = [v for v in values if v > 0]
    if not positive_values:
        positive_values = [0.001, 0.01, 0.1, 1.0]
    senders = [r["from_address"] for r in rows if r["from_address"]]
    receivers = [r["to_address"] for r in rows if r["to_address"]]
    timestamps = [datetime.fromisoformat(r["block_timestamp"]) for r in rows]
    out: list[dict[str, Any]] = []
    for i in range(720):
        eth = positive_values[(i * 97) % len(positive_values)]
        source = senders[(i * 53) % len(senders)]
        target = receivers[(i * 89) % len(receivers)]
        observed_ts = timestamps[(i * 31) % len(timestamps)]
        requested_at = observed_ts + timedelta(minutes=i % 90)
        approved_limit = [0.05, 0.25, 1.0, 5.0, 20.0][i % 5]
        requested_asset = "ETH" if i % 17 else "UNAPPROVED_TOKEN"
        requested_destination = target if i % 19 else "0x000000000000000000000000000000000000dEaD"
        kyc = "VERIFIED" if i % 8 else ("PENDING" if i % 16 else "FAILED")
        vasp = "VERIFIED" if i % 11 else "UNKNOWN"
        status_raw = rows[(i * 43) % len(rows)]["receipt_status"]
        execution_status = "SUCCESS" if str(status_raw) == "1" else ("FAILED" if str(status_raw) == "0" else "UNKNOWN_STATUS_NOT_EXTRACTED")
        out.append(
            {
                "transfer_id": f"DA-V3-{i+1:05d}",
                "originator_address": source,
                "beneficiary_address": target,
                "originator_identity": f"VASPCUST-S-{i % 211:04d}",
                "beneficiary_identity": f"VASPCUST-B-{i % 307:04d}",
                "kyc_status": kyc,
                "counterparty_vasp_status": vasp,
                "approved_asset": "ETH",
                "approved_amount_limit_eth": approved_limit,
                "approved_destination": target,
                "approved_period_start": "2026-01-01T00:00:00+00:00",
                "approved_period_end": "2026-12-31T23:59:59+00:00" if i % 23 else "2026-01-15T23:59:59+00:00",
                "requested_asset": requested_asset,
                "requested_amount_eth": round(eth, 18),
                "requested_destination": requested_destination,
                "requested_at": requested_at.isoformat(),
                "transaction_identifier": rows[(i * 43) % len(rows)]["hash"],
                "tx_hash": rows[(i * 43) % len(rows)]["hash"],
                "execution_status": execution_status,
                "ethereum_block_number": rows[(i * 43) % len(rows)]["block_number"],
                "ethereum_transaction_index": rows[(i * 43) % len(rows)]["transaction_index"],
            }
        )
    metadata = [
        {"column": "originator_address", "source_type": "REAL_DISTRIBUTION", "generation_rule": "Sample from Ethereum from_address distribution.", "rationale": "Uses actual sender concentration."},
        {"column": "beneficiary_address", "source_type": "REAL_DISTRIBUTION", "generation_rule": "Sample from Ethereum to_address distribution.", "rationale": "Uses actual receiver concentration."},
        {"column": "requested_amount_eth", "source_type": "REAL_DISTRIBUTION", "generation_rule": "Sample positive Ethereum value_eth distribution.", "rationale": "Uses actual transaction value distribution without IQR trimming."},
        {"column": "requested_at", "source_type": "REAL_DISTRIBUTION", "generation_rule": "Sample Ethereum block_timestamp distribution with small deterministic offset.", "rationale": "Uses actual temporal pattern."},
        {"column": "transaction_identifier", "source_type": "REAL_DISTRIBUTION", "generation_rule": "Sample actual Ethereum transaction hash.", "rationale": "Uses real transaction identifier field."},
        {"column": "execution_status", "source_type": "DERIVED", "generation_rule": "Map receipt_status=1 to SUCCESS and 0 to FAILED; otherwise mark UNKNOWN_STATUS_NOT_EXTRACTED.", "rationale": "Uses actual receipt status only where available."},
        {"column": "originator_identity", "source_type": "SYNTHETIC_POLICY_FIELD", "generation_rule": "Deterministic pseudonymous customer ids.", "rationale": "Legal identity is not public-chain data."},
        {"column": "kyc_status", "source_type": "SYNTHETIC_POLICY_FIELD", "generation_rule": "Deterministic VERIFIED/PENDING/FAILED scenarios.", "rationale": "KYC result is external/internal control data."},
        {"column": "counterparty_vasp_status", "source_type": "SYNTHETIC_POLICY_FIELD", "generation_rule": "Deterministic VERIFIED/UNKNOWN scenarios.", "rationale": "Counterparty VASP verification is not public-chain data."},
    ]
    return out, metadata


def evaluate(rows: list[dict[str, Any]], removed: set[str] | None = None) -> list[str]:
    removed = removed or set()
    decisions = []
    for row in rows:
        checks = {}
        if "KYC_STATUS_CHECK" not in removed:
            checks["kyc"] = row["kyc_status"] == "VERIFIED"
        if "ADDRESS_VERIFY" not in removed:
            checks["address"] = bool(row["originator_address"]) and bool(row["beneficiary_address"])
        if "COUNTERPARTY_VASP_VERIFY" not in removed:
            checks["counterparty"] = row["counterparty_vasp_status"] == "VERIFIED"
        if "AMOUNT_CONSTRAINT" not in removed:
            checks["amount"] = float(row["requested_amount_eth"]) <= float(row["approved_amount_limit_eth"])
        if "DESTINATION_CONSTRAINT" not in removed:
            checks["destination"] = row["requested_destination"].lower() == row["approved_destination"].lower()
        if "ASSET_CONSTRAINT" not in removed:
            checks["asset"] = row["requested_asset"] == row["approved_asset"]
        if all(checks.values()):
            decisions.append("PASS")
        elif any(k in checks and not checks[k] for k in ("kyc", "counterparty")):
            decisions.append("REVIEW")
        else:
            decisions.append("BLOCK")
    return decisions


def sensitivity(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    baseline = evaluate(rows)
    baseline_counts = Counter(baseline)
    scenarios = {
        "baseline_all_fields": set(),
        "remove_KYC_STATUS_CHECK": {"KYC_STATUS_CHECK"},
        "remove_ADDRESS_VERIFY": {"ADDRESS_VERIFY"},
        "remove_COUNTERPARTY_VASP_VERIFY": {"COUNTERPARTY_VASP_VERIFY"},
        "remove_AMOUNT_CONSTRAINT": {"AMOUNT_CONSTRAINT"},
        "remove_DESTINATION_CONSTRAINT": {"DESTINATION_CONSTRAINT"},
        "remove_ASSET_CONSTRAINT": {"ASSET_CONSTRAINT"},
    }
    out = []
    for name, removed in scenarios.items():
        decisions = evaluate(rows, removed)
        counts = Counter(decisions)
        false_allow = sum(1 for base, decision in zip(baseline, decisions, strict=True) if base != "PASS" and decision == "PASS")
        false_block = sum(1 for base, decision in zip(baseline, decisions, strict=True) if base == "PASS" and decision == "BLOCK")
        normal_preservation = sum(1 for base, decision in zip(baseline, decisions, strict=True) if base == "PASS" and decision == "PASS")
        out.append(
            {
                "scenario": name,
                "removed_fields": sorted(removed),
                "pass_count": counts["PASS"],
                "block_count": counts["BLOCK"],
                "review_count": counts["REVIEW"],
                "false_allow": false_allow,
                "false_block": false_block,
                "review_increase": counts["REVIEW"] - baseline_counts["REVIEW"],
                "normal_preservation_rate": round(normal_preservation / max(1, baseline_counts["PASS"]), 4),
                "delta_false_allow": false_allow,
                "delta_review": counts["REVIEW"] - baseline_counts["REVIEW"],
                "evidence_boundary": "Synthetic policy scenario result, not real market fraud/failure rate.",
            }
        )
    return out


def cramers_v(rows: list[dict[str, Any]], col_a: str, decisions: list[str]) -> float:
    table: dict[Any, Counter] = defaultdict(Counter)
    for row, decision in zip(rows, decisions, strict=True):
        table[row[col_a]][decision] += 1
    row_keys = list(table)
    col_keys = sorted({col for counter in table.values() for col in counter})
    n = len(rows)
    chi2 = 0.0
    for row_key in row_keys:
        row_total = sum(table[row_key].values())
        for col_key in col_keys:
            col_total = sum(table[r][col_key] for r in row_keys)
            expected = row_total * col_total / n
            if expected:
                chi2 += (table[row_key][col_key] - expected) ** 2 / expected
    denom = n * max(1, min(len(row_keys) - 1, len(col_keys) - 1))
    return round((chi2 / denom) ** 0.5, 4)


def build_v3_artifacts(
    mapping: list[dict[str, Any]],
    metrics: dict[str, Any],
    controls: list[dict[str, Any]],
    synthetic: list[dict[str, Any]],
    sens: list[dict[str, Any]],
    profile: dict[str, Any],
) -> None:
    v2_policy = read_json(V2 / "candidate_policy_v2.json")
    candidate = {
        "artifact_id": "DA-CANDIDATE-POLICY-REGULATED-TRANSFER-003",
        "artifact_version": "v3",
        "status": "candidate",
        "v2_ref": v2_policy.get("artifact_id"),
        "main_dataset": "Ethereum mainnet JSON-RPC transaction sample",
        "supporting_dataset": "SNAP Bitcoin OTC trust weighted signed network",
        "policy_rules": [
            {
                "policy_rule_id": f"DA-V3-RULE-{i+1:03d}",
                "required_field": row["required_field"],
                "ethereum_field": row["ethereum_field"],
                "availability_class": row["availability_class"],
                "status": "CANDIDATE",
                "evidence": row["evidence"],
                "non_decision": "Candidate only; not promoted to runtime policy.",
            }
            for i, row in enumerate(mapping)
        ],
        "v2_to_v3_changes": {
            "snap_dataset_role_changed_to": "SUPPORTING_NETWORK_DATA",
            "main_transaction_dataset_changed_to": "Ethereum mainnet JSON-RPC transaction sample",
            "v2_snap_onchain_ratio_deprecated_for_main_conclusion": True,
            "v3_onchain_direct_coverage_ratio": metrics["onchain_direct_coverage_ratio"],
            "v3_onchain_extended_coverage_ratio": metrics["onchain_extended_coverage_ratio"],
            "synthetic_v3_real_distribution_inputs": ["value_eth", "block_timestamp", "from_address", "to_address", "hash"],
            "receipt_status_status": "UNRESOLVED_IN_LOCAL_SAMPLE",
            "candidate_rule_changes": "Retained candidate boundary; evidence upgraded for on-chain fields only.",
        },
        "non_decisions": [
            "No BE handoff artifact, runtime enum, execution API, reconciliation API, or audit schema was modified.",
            "Synthetic v3 sensitivity results are policy scenario outputs, not real fraud or regulatory failure rates.",
            "H5 is structural evidence only because no retry/reconciliation event dataset is present.",
        ],
    }
    write_json(V3 / "regulatory_controls.json", controls)
    write_json(V3 / "required_fields.json", mapping)
    write_json(V3 / "schema_gap_detailed.json", {"mapping": mapping, "metrics": metrics, "profile_ref": "03_digital_asset/data/processed/ethereum_transaction_profile_v3.json"})
    write_json(V3 / "control_coverage.json", controls)
    write_json(V3 / "policy_sensitivity_results.json", sens)
    write_json(V3 / "candidate_policy_v3.json", candidate)
    summary = [
        "# Digital Asset Candidate Policy v3",
        "",
        "Scope: Ethereum transaction-level schema validation, regulatory field mapping, synthetic v3 generation, and candidate policy sensitivity.",
        "",
        "## v2 -> v3 Changes",
        "",
        "- SNAP Bitcoin OTC is retained only as SUPPORTING_NETWORK_DATA.",
        "- Ethereum mainnet JSON-RPC sample is the MAIN_TRANSACTION_DATA.",
        "- v2 SNAP-based on-chain/derivable ratio is deprecated for the main schema-gap conclusion.",
        f"- Ethereum on-chain direct coverage ratio: {metrics['onchain_direct_coverage_ratio']}",
        f"- Ethereum on-chain extended coverage ratio: {metrics['onchain_extended_coverage_ratio']}",
        f"- Non-chain dependency ratio: {metrics['non_chain_dependency_ratio']}",
        f"- Sample rows: {profile['row_count']}",
        "",
        "## Candidate Rule Status",
        "",
        "Rules remain candidate-only. On-chain evidence upgraded for address, amount, hash, and timestamp fields; receipt status remains unresolved in the local sample; legal identity, KYC, and counterparty VASP status remain non-chain dependencies.",
        "",
        "## Evidence Boundary",
        "",
        "Legal basis, actual Ethereum schema evidence, and synthetic policy experiment evidence are separated. No BE handoff or runtime contract is modified.",
    ]
    (V3 / "analysis_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")


def build_notebook() -> None:
    nb = nbf.v4.new_notebook()
    nb["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12"},
    }
    cells = [
        nbf.v4.new_markdown_cell("# Ethereum Transaction Schema Validation v3\n\n## tl;dr\n\nThis notebook validates FPG Digital Asset schema gaps using Ethereum transaction-level data as the main dataset. SNAP Bitcoin OTC is retained only as supporting network evidence."),
        nbf.v4.new_markdown_cell("## Context & Methods\n\nThe sample was extracted via Ethereum JSON-RPC from recent mainnet blocks. It includes transaction hash, from/to address, value, block timestamp, block number, nonce, transaction index, gas fields, input size, type, receipt status, and receipt gas used.\n\n### Key Assumptions\n\nThe sample is recent-block transaction evidence, not a full-chain market distribution. Synthetic v3 policy outcomes are scenario tests, not observed fraud or regulatory failure rates."),
        nbf.v4.new_code_cell(
            "# ruff: noqa: E501, E701, E702, I001\n"
            "\n"
            "from pathlib import Path\nimport json\nimport pandas as pd\nimport matplotlib.pyplot as plt\n"
            "ROOT = Path.cwd().resolve()\nif ROOT.name != 'ADP-DA': ROOT = next(p for p in [ROOT, *ROOT.parents] if p.name == 'ADP-DA')\n"
            "eth = pd.read_csv(ROOT/'03_digital_asset/data/raw/transactions/ethereum_transactions_sample.csv')\n"
            "profile = json.loads((ROOT/'03_digital_asset/data/processed/ethereum_transaction_profile_v3.json').read_text(encoding='utf-8'))\n"
            "mapping = pd.read_csv(ROOT/'03_digital_asset/data/processed/regulatory_transaction_field_mapping_v3.csv')\n"
            "synthetic = pd.read_csv(ROOT/'03_digital_asset/data/processed/synthetic_regulated_transfer_v3.csv')\n"
            "sensitivity = pd.DataFrame(json.loads((ROOT/'03_digital_asset/artifacts/candidate_policy_v3/policy_sensitivity_results.json').read_text(encoding='utf-8')))\n"
            "controls = pd.DataFrame(json.loads((ROOT/'03_digital_asset/artifacts/candidate_policy_v3/control_coverage.json').read_text(encoding='utf-8')))\n"
            "print({'ethereum_rows': len(eth), 'synthetic_v3_rows': len(synthetic), 'required_fields': len(mapping)})"
        ),
        nbf.v4.new_markdown_cell("## Data\n\n### 1. Schema Profile\n\nCheck row count, columns, dtypes, missingness, hash uniqueness, duplicate transactions, and field availability."),
        nbf.v4.new_code_cell("display(eth.head())\ndisplay(pd.DataFrame({'column': eth.columns, 'dtype': [str(t) for t in eth.dtypes], 'missing_rate': eth.isna().mean().round(4).values}))\nprint({k: profile[k] for k in ['row_count','unique_transaction_hash','duplicate_transaction_count','hash_uniqueness_ratio','from_to_availability','value_availability_ratio','timestamp_availability_ratio','status_availability_ratio']})"),
        nbf.v4.new_markdown_cell("## Results\n\n### 2. ETH Value Distribution\n\nUse log and percentile views; no IQR outlier deletion is applied because blockchain values are heavy-tailed by design."),
        nbf.v4.new_code_cell("value = pd.to_numeric(eth['value_eth'], errors='coerce').fillna(0)\ndisplay(pd.Series(profile['value_distribution_eth']).to_frame('value'))\nvalue.plot.hist(bins=60, color='#2f6f8f', title='ETH value distribution')\nplt.tight_layout()"),
        nbf.v4.new_markdown_cell("### 3. log(value) Distribution\n\nZero-value transactions are excluded from the log chart only for numerical plotting."),
        nbf.v4.new_code_cell("positive = value[value > 0]\npositive.apply(lambda x: __import__('math').log10(x)).plot.hist(bins=60, color='#4f8f65', title='log10(ETH value), positive transactions only')\nplt.tight_layout()"),
        nbf.v4.new_markdown_cell("### 4. Daily Transaction Frequency\n\nThe sampling window is bounded by the fetched recent block range."),
        nbf.v4.new_code_cell("eth['day'] = pd.to_datetime(eth['block_timestamp']).dt.date\ndaily = eth.groupby('day').size().reset_index(name='transactions')\ndisplay(daily)\ndaily.plot(x='day', y='transactions', legend=False, color='#446fb3', title='Daily transaction frequency in sample')\nplt.xticks(rotation=45, ha='right'); plt.tight_layout()"),
        nbf.v4.new_markdown_cell("### 5. Sender Concentration"),
        nbf.v4.new_code_cell("sender_top = eth['from_address'].value_counts().head(15).reset_index(); sender_top.columns=['from_address','transactions']\ndisplay(sender_top)\nsender_top.plot.bar(x='from_address', y='transactions', legend=False, color='#7a6f45', title='Top sender concentration')\nplt.xticks([]); plt.tight_layout()\nprint(profile['sender_concentration'])"),
        nbf.v4.new_markdown_cell("### 6. Receiver Concentration"),
        nbf.v4.new_code_cell("receiver_top = eth['to_address'].value_counts().head(15).reset_index(); receiver_top.columns=['to_address','transactions']\ndisplay(receiver_top)\nreceiver_top.plot.bar(x='to_address', y='transactions', legend=False, color='#8b5a5a', title='Top receiver concentration')\nplt.xticks([]); plt.tight_layout()\nprint(profile['receiver_concentration'])"),
        nbf.v4.new_markdown_cell("### 7. Transaction Identity / Replay-Relevant Fields\n\nHash, nonce, block number, and transaction index support structural uniqueness and sequencing evidence only. This does not prove FPG replay prevention without retry/reconciliation event data."),
        nbf.v4.new_code_cell("display(eth[['hash','nonce','block_number','transaction_index','receipt_status']].head())\nprint(profile['identity_and_replay_fields'])"),
        nbf.v4.new_markdown_cell("### 8. Regulatory Required Field Mapping v3"),
        nbf.v4.new_code_cell("display(mapping[['required_field','legal_control','ethereum_field','availability_class','confidence','evidence']])"),
        nbf.v4.new_markdown_cell("### 9. Ethereum Schema Gap Metrics"),
        nbf.v4.new_code_cell("gap = json.loads((ROOT/'03_digital_asset/artifacts/candidate_policy_v3/schema_gap_detailed.json').read_text(encoding='utf-8'))\nprint(gap['metrics'])\navailability = mapping['availability_class'].value_counts().rename_axis('availability_class').reset_index(name='count')\navailability.plot.bar(x='availability_class', y='count', legend=False, color='#2f6f8f', title='Ethereum Required Field Availability')\nplt.xticks(rotation=45, ha='right'); plt.tight_layout()"),
        nbf.v4.new_markdown_cell("### 10. Control-Level Coverage"),
        nbf.v4.new_code_cell("display(controls[['control','required_field_count','onchain_field_count','internal_dependency_count','external_dependency_count','pre_execution_dependency_count','runtime_readiness']])\ncontrols.set_index('control')[['onchain_field_count','internal_dependency_count','external_dependency_count']].plot.bar(color=['#2f6f8f','#7a6f45','#8b5a5a'], title='Control-level coverage')\nplt.xticks(rotation=45, ha='right'); plt.tight_layout()"),
        nbf.v4.new_markdown_cell("### 11. Synthetic v3 Provenance\n\nSynthetic v3 uses real Ethereum distributions for value, timestamps, address concentration, transaction hash, and status; policy fields remain synthetic or derived."),
        nbf.v4.new_code_cell("meta = pd.DataFrame(json.loads((ROOT/'03_digital_asset/data/processed/synthetic_regulated_transfer_v3_metadata.json').read_text(encoding='utf-8')))\ndisplay(meta)\ndisplay(synthetic.head())"),
        nbf.v4.new_markdown_cell("### 12. Policy Removal Sensitivity\n\nThese are synthetic policy scenario outcomes, not observed market fraud/failure rates."),
        nbf.v4.new_code_cell("display(sensitivity)\nsensitivity.set_index('scenario')[['pass_count','block_count','review_count']].plot.bar(color=['#2f6f8f','#7a6f45','#8b5a5a'], title='Policy Removal - PASS/BLOCK/REVIEW')\nplt.xticks(rotation=45, ha='right'); plt.tight_layout()"),
        nbf.v4.new_markdown_cell("### 13. False Allow Sensitivity"),
        nbf.v4.new_code_cell("sensitivity.set_index('scenario')['false_allow'].plot.bar(color='#a84c3d', title='Policy Removal - False Allow')\nplt.xticks(rotation=45, ha='right'); plt.tight_layout()"),
        nbf.v4.new_markdown_cell("## Takeaways\n\nH1 is supported by Ethereum schema evidence because identity, KYC, and counterparty VASP status remain non-chain dependencies. H2 is supported by regulatory structure. H3 and H4 are supported by synthetic policy experiments. H5 is structural evidence only, not statistical retry/reconciliation validation."),
    ]
    nb["cells"] = cells
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, NOTEBOOK)


def main() -> None:
    existing = RAW_TX / "ethereum_transactions_sample.csv"
    if existing.exists() and os.getenv("FPG_REFRESH_ETHEREUM_SAMPLE", "0") != "1":
        rows = load_csv(existing)
        metadata = read_json(RAW_TX / "ethereum_transactions_metadata.json")
    else:
        rows, metadata = fetch_ethereum_transactions()
    if not rows:
        raise RuntimeError("No Ethereum transaction rows were extracted.")
    update_inventory(len(rows))
    profile = profile_ethereum(rows)
    mapping = ethereum_field_mapping(profile["status_availability_ratio"] > 0)
    metrics = schema_gap_metrics(mapping)
    controls = control_coverage(mapping)
    synthetic, synthetic_meta = build_synthetic_v3(rows)
    baseline = evaluate(synthetic)
    for row, decision in zip(synthetic, baseline, strict=True):
        row["baseline_policy_decision"] = decision
    sens = sensitivity(synthetic)
    stats = {
        "categorical_effect_sizes": {
            "kyc_status_vs_decision_cramers_v": cramers_v(synthetic, "kyc_status", baseline),
            "counterparty_vasp_status_vs_decision_cramers_v": cramers_v(synthetic, "counterparty_vasp_status", baseline),
            "requested_asset_vs_decision_cramers_v": cramers_v(synthetic, "requested_asset", baseline),
        },
        "unsupported_tests_not_run": [
            "No Mann-Whitney/Kruskal claim is made for real regulatory failure because labels are synthetic policy scenarios.",
            "No real fraud-rate or regulatory failure-rate inference is made from synthetic v3.",
            "No retry/reconciliation statistical validation is made because no retry/reconciliation event dataset is present.",
        ],
        "hypotheses": {
            "H1": "REAL_SCHEMA_EVIDENCE",
            "H2": "REGULATORY_STRUCTURE_EVIDENCE",
            "H3": "SYNTHETIC_POLICY_EXPERIMENT",
            "H4": "SYNTHETIC_POLICY_EXPERIMENT",
            "H5": "STRUCTURAL_EVIDENCE_ONLY",
        },
    }
    write_json(PROCESSED / "ethereum_transaction_profile_v3.json", profile)
    write_csv(
        PROCESSED / "regulatory_transaction_field_mapping_v3.csv",
        mapping,
        ["required_field", "legal_control", "ethereum_field", "availability_class", "derivation_method", "confidence", "evidence", "note"],
    )
    write_json(PROCESSED / "schema_gap_metrics_v3.json", metrics)
    write_csv(PROCESSED / "synthetic_regulated_transfer_v3.csv", synthetic, list(synthetic[0].keys()))
    write_json(PROCESSED / "synthetic_regulated_transfer_v3_metadata.json", synthetic_meta)
    write_json(PROCESSED / "statistical_support_v3.json", stats)
    build_v3_artifacts(mapping, metrics, controls, synthetic, sens, profile)
    build_notebook()
    write_json(PROCESSED / "ethereum_extraction_runtime_v3.json", metadata)


if __name__ == "__main__":
    main()
