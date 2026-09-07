# ruff: noqa: E501, I001

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[2]
DA = ROOT / "03_digital_asset"
RAW_REG = DA / "data" / "raw" / "regulatory"
RAW_TX = DA / "data" / "raw" / "crypto_card"
PROCESSED = DA / "data" / "processed"
ARTIFACTS = DA / "artifacts" / "candidate_policy_v1"
HANDOFF = DA / "artifacts" / "be_handoff_v1"
CONTRACTS = DA / "contracts"
NOTEBOOK = DA / "notebooks" / "01_crypto_regulatory_analysis.ipynb"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def stable_digest(data: Any) -> str:
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


REG_COLUMNS = [
    "source",
    "jurisdiction",
    "regulation_name",
    "article",
    "paragraph",
    "effective_date",
    "effective_status",
    "applicable_entity",
    "obligation_id",
    "obligation_text",
    "subject",
    "action",
    "object",
    "condition",
    "control_type",
    "required_field",
    "source_system",
    "fpg_scope",
    "source_url",
    "source_note",
]


def regulatory_rows() -> list[dict[str, str]]:
    return [
        {
            "source": "LAW_GO_KR",
            "jurisdiction": "KR",
            "regulation_name": "Act on Reporting and Using Specified Financial Transaction Information",
            "article": "Article 2",
            "paragraph": "1-ha",
            "effective_date": "2026-08-20",
            "effective_status": "CURRENT",
            "applicable_entity": "VASP",
            "obligation_id": "DA-OBL-001",
            "obligation_text": "VASP is included in financial companies etc. for specified financial transaction information obligations.",
            "subject": "VASP",
            "action": "classify_entity",
            "object": "virtual_asset_service_provider",
            "condition": "regulated virtual asset transfer context",
            "control_type": "COUNTERPARTY_VASP_VERIFY",
            "required_field": "counterparty_vasp",
            "source_system": "VASP_INTERNAL",
            "fpg_scope": "EXTERNAL_RESULT_CHECK",
            "source_url": "https://www.law.go.kr/lsLinkCommonInfo.do?chrClsCd=010202&lsJoLnkSeq=1027653489",
            "source_note": "Official law portal; current law page observed as effective 2026-08-20.",
        },
        {
            "source": "LAW_GO_KR",
            "jurisdiction": "KR",
            "regulation_name": "Act on Reporting and Using Specified Financial Transaction Information",
            "article": "Article 5-2",
            "paragraph": "1",
            "effective_date": "2026-08-20",
            "effective_status": "CURRENT",
            "applicable_entity": "financial_company_or_vasp",
            "obligation_id": "DA-OBL-002",
            "obligation_text": "Customer due diligence obligation before or during financial transaction relationship.",
            "subject": "customer",
            "action": "verify_status",
            "object": "customer_due_diligence",
            "condition": "before regulated transfer request is handed off",
            "control_type": "KYC_STATUS_CHECK",
            "required_field": "kyc_status",
            "source_system": "EXTERNAL_KYC_SYSTEM",
            "fpg_scope": "EXTERNAL_RESULT_CHECK",
            "source_url": "https://www.law.go.kr/lsInfoP.do?lsId=009244",
            "source_note": "FPG checks returned status only; KYC execution remains outside FPG.",
        },
        {
            "source": "LAW_GO_KR",
            "jurisdiction": "KR",
            "regulation_name": "Act on Reporting and Using Specified Financial Transaction Information",
            "article": "Article 5-3",
            "paragraph": "1",
            "effective_date": "2026-08-20",
            "effective_status": "CURRENT",
            "applicable_entity": "financial_company_or_vasp",
            "obligation_id": "DA-OBL-003",
            "obligation_text": "Restrict or refuse transaction when customer verification cannot be completed.",
            "subject": "transfer_request",
            "action": "restrict_transfer",
            "object": "unverified_customer_transfer",
            "condition": "required customer verification is not satisfied",
            "control_type": "TRANSFER_RESTRICTION",
            "required_field": "kyc_status",
            "source_system": "FPG_POLICY_INPUT",
            "fpg_scope": "DIRECT_ENFORCEMENT",
            "source_url": "https://www.law.go.kr/lsInfoP.do?lsId=009244",
            "source_note": "Legal basis is represented as candidate control, not final legal judgment.",
        },
        {
            "source": "LAW_GO_KR",
            "jurisdiction": "KR",
            "regulation_name": "Enforcement Decree of Act on Reporting and Using Specified Financial Transaction Information",
            "article": "Article 10-10",
            "paragraph": "1",
            "effective_date": "2026-08-20",
            "effective_status": "CURRENT",
            "applicable_entity": "VASP",
            "obligation_id": "DA-OBL-004",
            "obligation_text": "VASP transfer information duties include originator and beneficiary information handling.",
            "subject": "originator",
            "action": "verify_identity",
            "object": "originator_identity",
            "condition": "virtual asset transfer between VASPs",
            "control_type": "ORIGINATOR_VERIFY",
            "required_field": "originator_identity",
            "source_system": "VASP_INTERNAL",
            "fpg_scope": "FPG_REQUIRED_INPUT",
            "source_url": "https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=288765",
            "source_note": "Identity itself is not on-chain; FPG requires a trusted input or result.",
        },
        {
            "source": "LAW_GO_KR",
            "jurisdiction": "KR",
            "regulation_name": "Enforcement Decree of Act on Reporting and Using Specified Financial Transaction Information",
            "article": "Article 10-10",
            "paragraph": "1",
            "effective_date": "2026-08-20",
            "effective_status": "CURRENT",
            "applicable_entity": "VASP",
            "obligation_id": "DA-OBL-005",
            "obligation_text": "VASP transfer information duties include beneficiary information handling.",
            "subject": "beneficiary",
            "action": "verify_identity",
            "object": "beneficiary_identity",
            "condition": "virtual asset transfer between VASPs",
            "control_type": "BENEFICIARY_VERIFY",
            "required_field": "beneficiary_identity",
            "source_system": "VASP_INTERNAL",
            "fpg_scope": "FPG_REQUIRED_INPUT",
            "source_url": "https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=288765",
            "source_note": "Identity itself is not on-chain; FPG requires a trusted input or result.",
        },
        {
            "source": "KOFIU",
            "jurisdiction": "KR",
            "regulation_name": "KoFIU AML/CDD virtual asset guidance",
            "article": "Travel Rule guidance",
            "paragraph": "originator-beneficiary information",
            "effective_date": "REVIEW_REQUIRED",
            "effective_status": "CURRENT",
            "applicable_entity": "VASP",
            "obligation_id": "DA-OBL-006",
            "obligation_text": "Transfer-related originator and beneficiary information should be transmitted or retained for the counterpart VASP.",
            "subject": "transfer_information",
            "action": "transfer_information",
            "object": "originator_beneficiary_information",
            "condition": "travel-rule applicable transfer",
            "control_type": "INFORMATION_TRANSFER",
            "required_field": "transaction_id",
            "source_system": "VASP_INTERNAL",
            "fpg_scope": "EXTERNAL_RESULT_CHECK",
            "source_url": "https://www.kofiu.go.kr/kor/policy/guide04.do",
            "source_note": "Official KoFIU guidance page; exact paragraph remains REVIEW_REQUIRED.",
        },
        {
            "source": "LAW_GO_KR",
            "jurisdiction": "KR",
            "regulation_name": "Virtual Asset User Protection Act",
            "article": "Article 9",
            "paragraph": "1",
            "effective_date": "2024-07-19",
            "effective_status": "CURRENT",
            "applicable_entity": "VASP",
            "obligation_id": "DA-OBL-007",
            "obligation_text": "VASP must create, preserve, and make searchable transaction records for virtual asset transactions.",
            "subject": "execution_record",
            "action": "record_keep",
            "object": "virtual_asset_transaction_record",
            "condition": "after virtual asset transaction",
            "control_type": "RECORD_KEEPING",
            "required_field": "execution_status",
            "source_system": "EXTERNAL_EXECUTION_SYSTEM",
            "fpg_scope": "EXTERNAL_RESULT_CHECK",
            "source_url": "https://law.go.kr/lsInfoP.do?lsiSeq=252731",
            "source_note": "FPG records execution handoff/result, not direct asset transfer.",
        },
        {
            "source": "FATF",
            "jurisdiction": "GLOBAL",
            "regulation_name": "FATF Recommendation 15 Interpretive Note",
            "article": "INR.15",
            "paragraph": "7(b)",
            "effective_date": "2019-06",
            "effective_status": "CURRENT",
            "applicable_entity": "VASP",
            "obligation_id": "DA-OBL-008",
            "obligation_text": "Originating VASPs obtain and hold required and accurate originator information and required beneficiary information.",
            "subject": "originating_vasp",
            "action": "obtain_hold",
            "object": "originator_and_beneficiary_information",
            "condition": "virtual asset transfer",
            "control_type": "ORIGINATOR_VERIFY",
            "required_field": "originator_identity",
            "source_system": "VASP_INTERNAL",
            "fpg_scope": "FPG_REQUIRED_INPUT",
            "source_url": "https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Regulation-virtual-assets-interpretive-note.html",
            "source_note": "FATF official public statement with INR.15 draft/final adoption context.",
        },
        {
            "source": "FATF",
            "jurisdiction": "GLOBAL",
            "regulation_name": "FATF Recommendation 15 Interpretive Note",
            "article": "INR.15",
            "paragraph": "7(b)",
            "effective_date": "2019-06",
            "effective_status": "CURRENT",
            "applicable_entity": "beneficiary_vasp",
            "obligation_id": "DA-OBL-009",
            "obligation_text": "Beneficiary VASPs obtain and hold required originator information and required and accurate beneficiary information.",
            "subject": "beneficiary_vasp",
            "action": "obtain_hold",
            "object": "originator_and_beneficiary_information",
            "condition": "virtual asset transfer",
            "control_type": "BENEFICIARY_VERIFY",
            "required_field": "beneficiary_identity",
            "source_system": "VASP_INTERNAL",
            "fpg_scope": "FPG_REQUIRED_INPUT",
            "source_url": "https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Regulation-virtual-assets-interpretive-note.html",
            "source_note": "FATF official public statement with INR.15 draft/final adoption context.",
        },
        {
            "source": "FATF",
            "jurisdiction": "GLOBAL",
            "regulation_name": "FATF Recommendations",
            "article": "Recommendation 16",
            "paragraph": "payment transparency",
            "effective_date": "2026-06",
            "effective_status": "CURRENT",
            "applicable_entity": "financial_institution_or_vasp",
            "obligation_id": "DA-OBL-010",
            "obligation_text": "Wire transfer transparency requirements inform originator/beneficiary information controls for virtual asset transfers.",
            "subject": "transfer_information",
            "action": "transmit_information",
            "object": "originator_beneficiary_information",
            "condition": "transfer transparency requirement applies",
            "control_type": "INFORMATION_TRANSFER",
            "required_field": "transaction_id",
            "source_system": "VASP_INTERNAL",
            "fpg_scope": "EXTERNAL_RESULT_CHECK",
            "source_url": "https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Fatf-recommendations.html",
            "source_note": "FATF Recommendations page observed as amended June 2026.",
        },
        {
            "source": "FATF",
            "jurisdiction": "GLOBAL",
            "regulation_name": "FATF Virtual Assets guidance",
            "article": "Virtual assets topic page",
            "paragraph": "VASP preventive measures",
            "effective_date": "2026-07-16",
            "effective_status": "CURRENT",
            "applicable_entity": "VASP",
            "obligation_id": "DA-OBL-011",
            "obligation_text": "VASPs need preventive measures including CDD, record keeping, suspicious transaction reporting, and secure originator/beneficiary transfer information.",
            "subject": "vasp_controls",
            "action": "monitor_and_record",
            "object": "preventive_measures",
            "condition": "virtual asset services",
            "control_type": "RECORD_KEEPING",
            "required_field": "execution_status",
            "source_system": "VASP_INTERNAL",
            "fpg_scope": "EXTERNAL_RESULT_CHECK",
            "source_url": "https://www.fatf-gafi.org/en/topics/virtual-assets.html",
            "source_note": "FATF virtual assets topic page includes 2026 targeted update.",
        },
        {
            "source": "FATF",
            "jurisdiction": "GLOBAL",
            "regulation_name": "FATF Recommendation 15 Interpretive Note",
            "article": "INR.15",
            "paragraph": "7(b)",
            "effective_date": "2019-06",
            "effective_status": "CURRENT",
            "applicable_entity": "VASP",
            "obligation_id": "DA-OBL-012",
            "obligation_text": "Other R.16 requirements including monitoring information availability and freezing/prohibiting transactions with designated persons apply on the same basis.",
            "subject": "transfer_request",
            "action": "restrict_transfer",
            "object": "restricted_or_designated_transfer",
            "condition": "information unavailable or designated-person restriction applies",
            "control_type": "TRANSFER_RESTRICTION",
            "required_field": "execution_status",
            "source_system": "FPG_POLICY_INPUT",
            "fpg_scope": "DIRECT_ENFORCEMENT",
            "source_url": "https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Regulation-virtual-assets-interpretive-note.html",
            "source_note": "Candidate control only; designated-person screening engine is external to this repo.",
        },
        {
            "source": "LAW_GO_KR",
            "jurisdiction": "KR",
            "regulation_name": "Virtual Asset User Protection Act",
            "article": "Article 6",
            "paragraph": "1",
            "effective_date": "2024-07-19",
            "effective_status": "CURRENT",
            "applicable_entity": "VASP",
            "obligation_id": "DA-OBL-013",
            "obligation_text": "User assets must be managed separately from VASP assets.",
            "subject": "user_asset",
            "action": "verify_asset",
            "object": "requested_asset",
            "condition": "virtual asset user asset transfer",
            "control_type": "ADDRESS_VERIFY",
            "required_field": "asset",
            "source_system": "FPG_POLICY_INPUT",
            "fpg_scope": "DIRECT_ENFORCEMENT",
            "source_url": "https://law.go.kr/lsInfoP.do?lsiSeq=252731",
            "source_note": "Used only as an asset binding candidate, not settlement execution.",
        },
        {
            "source": "FSC",
            "jurisdiction": "KR",
            "regulation_name": "FSC virtual asset policy release",
            "article": "Policy release",
            "paragraph": "2026-08-11",
            "effective_date": "2026-08-11",
            "effective_status": "FUTURE",
            "applicable_entity": "VASP",
            "obligation_id": "DA-OBL-014",
            "obligation_text": "Future virtual asset policy direction is monitored but not enforced as current runtime policy.",
            "subject": "future_policy",
            "action": "monitor",
            "object": "future_virtual_asset_policy",
            "condition": "not current enforceable obligation in this artifact",
            "control_type": "RECORD_KEEPING",
            "required_field": "source_note",
            "source_system": "POLICY_MONITORING",
            "fpg_scope": "OUT_OF_SCOPE",
            "source_url": "https://www.fsc.go.kr/po010103/87499",
            "source_note": "Marked FUTURE/OUT_OF_SCOPE to avoid mixing current and future enforcement.",
        },
    ]


FIELD_SOURCE_MAP = {
    "originator_identity": "VASP_INTERNAL",
    "beneficiary_identity": "VASP_INTERNAL",
    "originator_address": "ONCHAIN_AVAILABLE",
    "beneficiary_address": "ONCHAIN_AVAILABLE",
    "amount": "ONCHAIN_AVAILABLE",
    "asset": "ONCHAIN_AVAILABLE",
    "counterparty_vasp": "VASP_INTERNAL",
    "kyc_status": "EXTERNAL_CONTROL_RESULT",
    "transaction_id": "FPG_REQUIRED_INPUT",
    "tx_hash": "ONCHAIN_AVAILABLE",
    "execution_status": "EXTERNAL_CONTROL_RESULT",
    "timestamp": "ONCHAIN_AVAILABLE",
}


def dataset_inventory() -> list[dict[str, Any]]:
    return [
        {
            "dataset_id": "ELLIPTIC_BITCOIN_DATASET",
            "public": True,
            "download_path": "https://www.kaggle.com/datasets/ellipticco/elliptic-data-set/data",
            "license": "CC BY-NC-ND 4.0",
            "columns": "txId, class, time_step, 166 anonymized transaction/graph features, edge list",
            "transaction_unit": "Bitcoin transaction graph node",
            "label_available": True,
            "actual_transaction_fields": "time_step, graph links, anonymized local/aggregate features; exact addresses and identities not disclosed",
            "fpg_usefulness": "Useful for risk/status distribution and temporal bins; insufficient for pre-execution identity/KYC/VASP enforcement.",
            "selected_for_synthetic_basis": True,
            "selection_reason": "Officially documented class proportions and 49 time steps can seed non-arbitrary risk and temporal distributions.",
        },
        {
            "dataset_id": "DUNE_ETHEREUM_TRANSACTIONS",
            "public": True,
            "download_path": "https://dune.mintlify.app/data-catalog/evm/ethereum/raw/transactions",
            "license": "Platform/query access terms; not bundled",
            "columns": "block_time, block_number, value, gas fields, success, from, to, hash, type",
            "transaction_unit": "Ethereum on-chain transaction",
            "label_available": False,
            "actual_transaction_fields": "from, to, value, hash, success, timestamp, gas fields",
            "fpg_usefulness": "Useful for on-chain field availability mapping; lacks identity, KYC, approved policy, and counterparty VASP status.",
            "selected_for_synthetic_basis": True,
            "selection_reason": "Column documentation supports ONCHAIN_AVAILABLE classification for address, amount, tx hash, timestamp, and execution status.",
        },
        {
            "dataset_id": "ETHEREUM_ORG_TRANSACTION_OBJECT",
            "public": True,
            "download_path": "https://ethereum.org/developers/docs/transactions",
            "license": "Ethereum.org documentation terms",
            "columns": "from, to, signature, nonce, value, input data, gasLimit, fee fields",
            "transaction_unit": "Ethereum transaction object reference",
            "label_available": False,
            "actual_transaction_fields": "from, to, value, nonce, signature, input data, gas fields",
            "fpg_usefulness": "Confirms on-chain transaction object does not provide legal identity, KYC, or approved policy fields.",
            "selected_for_synthetic_basis": False,
            "selection_reason": "Used for schema gap evidence only, not distribution generation.",
        },
    ]


def schema_gap_rows(reg_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    legal_fields = [
        "originator_identity",
        "beneficiary_identity",
        "originator_address",
        "beneficiary_address",
        "amount",
        "asset",
        "counterparty_vasp",
        "kyc_status",
        "transaction_id",
        "tx_hash",
        "execution_status",
        "timestamp",
    ]
    legal_basis_by_field: dict[str, list[str]] = defaultdict(list)
    for row in reg_rows:
        field = row["required_field"]
        if field == "source_note":
            continue
        mapped = {
            "originator_identity": ["originator_identity"],
            "beneficiary_identity": ["beneficiary_identity"],
            "kyc_status": ["kyc_status"],
            "counterparty_vasp": ["counterparty_vasp"],
            "transaction_id": ["transaction_id"],
            "execution_status": ["execution_status"],
            "asset": ["asset"],
        }.get(field, [field])
        for item in mapped:
            legal_basis_by_field[item].append(row["obligation_id"])
    onchain_fields = {
        "originator_address": "from / input address surrogate",
        "beneficiary_address": "to / output address surrogate",
        "amount": "value / output volume",
        "asset": "chain/native asset or token context",
        "tx_hash": "hash / txId",
        "execution_status": "success / receipt_status",
        "timestamp": "block_time / time_step",
    }
    rows = []
    for field in legal_fields:
        availability = FIELD_SOURCE_MAP[field]
        rows.append(
            {
                "field": field,
                "legal_required": bool(legal_basis_by_field.get(field)),
                "legal_basis": "|".join(sorted(set(legal_basis_by_field.get(field, [])))) or "ANALYSIS_REQUIRED",
                "public_transaction_field": onchain_fields.get(field, ""),
                "availability_class": availability,
                "fpg_enforcement_input": availability in {"VASP_INTERNAL", "EXTERNAL_CONTROL_RESULT", "FPG_REQUIRED_INPUT"},
                "gap_status": "AVAILABLE" if availability == "ONCHAIN_AVAILABLE" else "FPG_REQUIRED_INPUT",
                "notes": "Public chain data alone is insufficient for pre-execution enforcement." if availability != "ONCHAIN_AVAILABLE" else "Available from public on-chain transaction data or documented transaction object.",
            }
        )
    return rows


def make_synthetic_transfers(n: int = 240) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = datetime(2026, 1, 5, 9, 0)
    assets = ["BTC", "ETH", "USDT", "USDC"]
    vasps = ["KR-VASP-A", "KR-VASP-B", "GLOBAL-VASP-C", "UNREGISTERED"]
    kyc_cycle = ["VERIFIED"] * 78 + ["PENDING"] * 12 + ["FAILED"] * 6 + ["MISSING"] * 4
    status_cycle = ["EXECUTED"] * 86 + ["BLOCKED"] * 8 + ["REVIEW"] * 4 + ["FAILED"] * 2
    risk_cycle = ["unknown"] * 77 + ["licit"] * 21 + ["illicit"] * 2
    for i in range(n):
        time_step = (i % 49) + 1
        requested_at = start + timedelta(days=time_step * 2, minutes=(i * 37) % 1440)
        amount_bucket = i % 10
        amount = round([40, 75, 120, 220, 450, 900, 1600, 3100, 6200, 12500][amount_bucket] * (1 + (i % 7) / 20), 2)
        approved_limit = [500, 1000, 2000, 5000, 10000][i % 5]
        approved_asset = assets[i % len(assets)]
        requested_asset = approved_asset if i % 13 else assets[(i + 1) % len(assets)]
        approved_destination = vasps[i % 3]
        requested_destination = approved_destination if i % 17 else "UNREGISTERED"
        kyc_status = kyc_cycle[i % len(kyc_cycle)]
        execution_status = status_cycle[i % len(status_cycle)]
        rows.append(
            {
                "transfer_id": f"DA-TX-{i + 1:05d}",
                "originator_id": f"ORG-{(i % 55) + 1:04d}",
                "beneficiary_id": f"BEN-{(i * 3 % 71) + 1:04d}",
                "originator_address": f"0xORG{(i % 80) + 1:036d}",
                "beneficiary_address": f"0xBEN{(i * 5 % 95) + 1:036d}",
                "counterparty_vasp": requested_destination,
                "kyc_status": kyc_status,
                "approved_asset": approved_asset,
                "requested_asset": requested_asset,
                "approved_amount_limit": approved_limit,
                "requested_amount": amount,
                "approved_destination": approved_destination,
                "requested_destination": requested_destination,
                "approved_period_start": "2026-01-01T00:00:00",
                "approved_period_end": "2026-12-31T23:59:59" if i % 19 else "2026-01-15T23:59:59",
                "requested_at": requested_at.isoformat(),
                "external_tx_id": f"0xTX{(i * 7919) % 10**12:012d}" if execution_status == "EXECUTED" else "",
                "execution_status": execution_status,
                "public_dataset_basis": "ELLIPTIC_TIME_STEP_AND_CLASS_PROPORTION",
                "risk_label_basis": risk_cycle[i % len(risk_cycle)],
            }
        )
    return rows


def evaluate_policy(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        requested_at = datetime.fromisoformat(row["requested_at"])
        period_end = datetime.fromisoformat(row["approved_period_end"])
        checks = {
            "asset_match": row["approved_asset"] == row["requested_asset"],
            "amount_within_limit": float(row["requested_amount"]) <= float(row["approved_amount_limit"]),
            "destination_match": row["approved_destination"] == row["requested_destination"],
            "period_valid": requested_at <= period_end,
            "kyc_verified": row["kyc_status"] == "VERIFIED",
            "counterparty_registered": row["counterparty_vasp"] != "UNREGISTERED",
            "execution_trace_present": bool(row["external_tx_id"]) if row["execution_status"] == "EXECUTED" else True,
        }
        action = "PASS" if all(checks.values()) else "BLOCK"
        if row["kyc_status"] in {"PENDING", "MISSING"} or row["counterparty_vasp"] == "UNREGISTERED":
            action = "REVIEW"
        if row["execution_status"] == "FAILED":
            action = "REVIEW"
        out.append({**row, **checks, "policy_decision": action})
    return out


def build_artifacts(reg_rows: list[dict[str, str]], gap_rows: list[dict[str, Any]], evaluated: list[dict[str, Any]]) -> None:
    active_rows = [r for r in reg_rows if r["fpg_scope"] != "OUT_OF_SCOPE"]
    controls_by_type: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in active_rows:
        controls_by_type[row["control_type"]].append(row)
    controls = [
        {
            "control_id": f"DA-CTRL-{idx:03d}",
            "control_type": control_type,
            "required_fields": sorted({r["required_field"] for r in rows}),
            "legal_basis": sorted({r["obligation_id"] for r in rows}),
            "evidence_source": sorted({r["source"] for r in rows}),
            "fpg_scope": sorted({r["fpg_scope"] for r in rows}),
            "status": "CANDIDATE",
        }
        for idx, (control_type, rows) in enumerate(sorted(controls_by_type.items()), start=1)
    ]
    required_fields = [
        {
            "field": row["field"],
            "availability_class": row["availability_class"],
            "gap_status": row["gap_status"],
            "legal_basis": row["legal_basis"],
            "fpg_required_input": row["fpg_enforcement_input"],
        }
        for row in gap_rows
    ]
    policy_rules = []
    rule_seed = [
        ("DA-POL-001", "KYC_STATUS_CHECK", "kyc_status", "equals", "VERIFIED", "REVIEW", "EXTERNAL_RESULT_CHECK"),
        ("DA-POL-002", "COUNTERPARTY_VASP_VERIFY", "counterparty_vasp", "not_equals", "UNREGISTERED", "REVIEW", "EXTERNAL_RESULT_CHECK"),
        ("DA-POL-003", "TRANSFER_RESTRICTION", "requested_amount", "less_or_equal_field", "approved_amount_limit", "BLOCK", "DIRECT_ENFORCEMENT"),
        ("DA-POL-004", "ADDRESS_VERIFY", "requested_destination", "equals_field", "approved_destination", "REVIEW", "DIRECT_ENFORCEMENT"),
        ("DA-POL-005", "ADDRESS_VERIFY", "requested_asset", "equals_field", "approved_asset", "BLOCK", "DIRECT_ENFORCEMENT"),
        ("DA-POL-006", "TRANSFER_RESTRICTION", "requested_at", "within_period", "approved_period_start..approved_period_end", "BLOCK", "DIRECT_ENFORCEMENT"),
        ("DA-POL-007", "RECORD_KEEPING", "external_tx_id", "required_when_executed", "present", "REVIEW", "EXTERNAL_RESULT_CHECK"),
    ]
    basis_lookup = defaultdict(list)
    for row in active_rows:
        basis_lookup[row["control_type"]].append(row["obligation_id"])
    for rule_id, control_type, field, operator, expected, fail_action, scope in rule_seed:
        if not basis_lookup.get(control_type):
            continue
        policy_rules.append(
            {
                "policy_rule_id": rule_id,
                "control_type": control_type,
                "required_field": field,
                "legal_basis": sorted(set(basis_lookup[control_type])),
                "evidence_source": "03_digital_asset/data/raw/regulatory/crypto_regulation_raw.csv",
                "evaluation_operator": operator,
                "expected_value_or_constraint": expected,
                "on_fail_action": fail_action,
                "fpg_scope": scope,
                "traceability": {
                    "regulatory_basis": sorted(set(basis_lookup[control_type])),
                    "data_basis": "03_digital_asset/data/processed/regulatory_schema_gap.json",
                    "experiment_basis": "03_digital_asset/data/processed/policy_enforcement_experiment_v1.json",
                },
            }
        )
    summary_counts = Counter(r["policy_decision"] for r in evaluated)
    write_json(ARTIFACTS / "regulatory_controls.json", controls)
    write_json(ARTIFACTS / "required_fields.json", required_fields)
    write_json(ARTIFACTS / "schema_gap.json", gap_rows)
    write_json(
        ARTIFACTS / "candidate_policy.json",
        {
            "artifact_id": "DA-CANDIDATE-POLICY-REGULATED-TRANSFER-001",
            "artifact_version": "v1",
            "status": "candidate",
            "runtime_scope": "regulated_virtual_asset_transfer_pre_execution_gateway",
            "policy_rules": policy_rules,
            "explicit_non_decisions": [
                "FPG does not execute asset transfers.",
                "KYC execution remains outside FPG.",
                "Future policy release rows are not promoted to runtime policy.",
                "Legal interpretation remains REVIEW_REQUIRED where exact application is unclear.",
            ],
            "digest": {"algorithm": "sha256", "value": stable_digest(policy_rules)},
        },
    )
    (ARTIFACTS / "analysis_summary.md").write_text(
        "\n".join(
            [
                "# Digital Asset Candidate Policy v1",
                "",
                "Scope: regulated virtual asset transfer pre-execution gateway.",
                "",
                f"- Regulatory obligations analyzed: {len(reg_rows)}",
                f"- Candidate controls: {len(controls)}",
                f"- Required fields: {len(required_fields)}",
                f"- Synthetic evaluated transfers: {len(evaluated)}",
                f"- Policy decisions: {dict(sorted(summary_counts.items()))}",
                "",
                "Excluded claims: FPG asset execution, final legal judgment, KYC execution, settlement finality, and production latency thresholds.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    handoff_refs = [{"ref_id": rule["policy_rule_id"], "ref_type": "candidate_policy_rule", "version": "v1"} for rule in policy_rules]
    write_json(
        HANDOFF / "policy_evaluations" / "PE-DA-REGULATED-TRANSFER-001.json",
        {
            "schema_version": "v1",
            "artifact_id": "PE-DA-REGULATED-TRANSFER-001",
            "artifact_version": "v1",
            "analysis_status": "candidate",
            "policy_action": "candidate_handoff",
            "approved_policy_ref": "DA-CANDIDATE-POLICY-REGULATED-TRANSFER-001",
            "execution_request_ref": "synthetic_regulatory_transfer_v1",
            "policy_rule_refs": handoff_refs,
            "required_input_fields": [r["field"] for r in required_fields if r["fpg_required_input"]],
            "decision_values": ["PASS", "BLOCK", "REVIEW"],
            "handoff_chain": [
                "Approved Policy",
                "Execution Request",
                "Policy Evaluation",
                "PASS/BLOCK/REVIEW",
                "External Execution Handoff",
                "Execution Status",
                "Reconciliation/Audit",
            ],
            "limitations": [
                "Public on-chain datasets do not contain legal identity, KYC status, approved policy, or counterparty VASP verification.",
                "Synthetic data is derived from documented public dataset shape and proportions, not from downloaded raw blockchain records.",
                "No final production threshold, latency SLO, or settlement-finality rule is asserted.",
            ],
            "digest": {"algorithm": "sha256", "value": stable_digest(handoff_refs)},
        },
    )
    write_json(
        HANDOFF / "bindings" / "DAB-REGULATED-TRANSFER-001.json",
        {
            "schema_version": "v1",
            "binding_version": "v1",
            "bindings": [
                {
                    "digital_asset_runtime": "REGULATED_VIRTUAL_ASSET_TRANSFER",
                    "workload_id": "UNMAPPED",
                    "purpose": "regulated_virtual_asset_transfer_pre_execution_check",
                    "execution_boundary": "FPG_PRE_EXECUTION_GATEWAY_ONLY",
                    "binding_status": "candidate",
                }
            ],
        },
    )
    write_json(
        HANDOFF / "crosswalks" / "DA-RDC-REGULATED-TRANSFER-001.json",
        {
            "schema_version": "v1",
            "crosswalk_version": "v1",
            "mappings": [
                {
                    "regulatory_required_field": row["field"],
                    "availability_class": row["availability_class"],
                    "runtime_data_class": "UNMAPPED",
                    "mapping_status": "unmapped" if row["availability_class"] != "ONCHAIN_AVAILABLE" else "candidate",
                    "mapping_basis": row["legal_basis"],
                }
                for row in gap_rows
            ],
        },
    )


def build_contracts() -> None:
    write_json(
        CONTRACTS / "candidate_policy.schema.json",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Digital Asset Candidate Policy",
            "type": "object",
            "required": ["artifact_id", "artifact_version", "status", "runtime_scope", "policy_rules", "digest"],
            "properties": {
                "artifact_id": {"type": "string"},
                "artifact_version": {"type": "string"},
                "status": {"type": "string", "enum": ["candidate", "validated", "hold", "rejected"]},
                "runtime_scope": {"type": "string"},
                "policy_rules": {"type": "array", "items": {"type": "object"}},
                "explicit_non_decisions": {"type": "array", "items": {"type": "string"}},
                "digest": {"type": "object"},
            },
            "additionalProperties": False,
        },
    )
    write_json(
        CONTRACTS / "digital_asset_policy_evaluation.schema.json",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Digital Asset PolicyEvaluation Handoff",
            "type": "object",
            "required": [
                "schema_version",
                "artifact_id",
                "artifact_version",
                "analysis_status",
                "policy_action",
                "approved_policy_ref",
                "execution_request_ref",
                "policy_rule_refs",
                "required_input_fields",
                "decision_values",
                "handoff_chain",
                "limitations",
                "digest",
            ],
            "properties": {
                "schema_version": {"type": "string", "const": "v1"},
                "artifact_id": {"type": "string"},
                "artifact_version": {"type": "string"},
                "analysis_status": {"type": "string", "enum": ["candidate", "validated", "hold", "rejected"]},
                "policy_action": {"type": "string", "enum": ["candidate_handoff", "requires_evaluation", "hold", "reject"]},
                "approved_policy_ref": {"type": "string"},
                "execution_request_ref": {"type": "string"},
                "policy_rule_refs": {"type": "array", "items": {"type": "object"}},
                "required_input_fields": {"type": "array", "items": {"type": "string"}},
                "decision_values": {"type": "array", "items": {"type": "string"}},
                "handoff_chain": {"type": "array", "items": {"type": "string"}},
                "limitations": {"type": "array", "items": {"type": "string"}},
                "digest": {"type": "object"},
            },
            "additionalProperties": False,
        },
    )


def build_notebook() -> None:
    nb = nbf.v4.new_notebook()
    nb["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12"},
    }
    cells = [
        nbf.v4.new_markdown_cell(
            "# Digital Asset Regulatory Transfer Analysis\n\n"
            "This notebook analyzes the regulated virtual asset transfer use case for FPG. "
            "It intentionally separates regulatory evidence, schema availability, synthetic transfer evaluation, and candidate handoff."
        ),
        nbf.v4.new_markdown_cell("## tl;dr\n\nRun all cells to refresh the observed counts. No final runtime policy or legal judgment is asserted here."),
        nbf.v4.new_markdown_cell("## Context & Methods\n\nThe fixed sequence is regulatory source structure -> legal controls -> required fields -> transaction schema mapping -> schema gap -> synthetic regulatory transfer dataset -> policy experiment -> candidate policy."),
        nbf.v4.new_code_cell(
            "# ruff: noqa: E501, E702, I001\n"
            "\n"
            "from pathlib import Path\n"
            "import itertools\n"
            "import pandas as pd\n"
            "import matplotlib.pyplot as plt\n"
            "ROOT = Path.cwd().resolve()\n"
            "if ROOT.name != 'ADP-DA':\n"
            "    ROOT = next(p for p in [ROOT, *ROOT.parents] if p.name == 'ADP-DA')\n"
            "REG_PATH = ROOT / '03_digital_asset/data/raw/regulatory/crypto_regulation_raw.csv'\n"
            "GAP_PATH = ROOT / '03_digital_asset/data/processed/regulatory_schema_gap.csv'\n"
            "SYN_PATH = ROOT / '03_digital_asset/data/processed/synthetic_regulatory_transfer_v1.csv'\n"
            "reg = pd.read_csv(REG_PATH)\n"
            "gap = pd.read_csv(GAP_PATH)\n"
            "tx = pd.read_csv(SYN_PATH)\n"
            "reg.head()"
        ),
        nbf.v4.new_markdown_cell("## Data\n\nInputs are local artifacts generated by the Digital Asset pipeline builder. Public datasets are not downloaded into this repository."),
        nbf.v4.new_code_cell(
            "print({'regulatory_rows': len(reg), 'schema_gap_fields': len(gap), 'synthetic_transfers': len(tx)})\n"
            "display(reg[['source','jurisdiction','obligation_id','control_type','required_field','fpg_scope']].head(10))"
        ),
        nbf.v4.new_markdown_cell("## Results\n\n### 1. Korea Regulatory Control Frequency"),
        nbf.v4.new_code_cell(
            "korea_freq = reg[reg['jurisdiction']=='KR']['control_type'].value_counts().rename_axis('control_type').reset_index(name='count')\n"
            "display(korea_freq)\n"
            "korea_freq.plot.bar(x='control_type', y='count', legend=False, color='#3f7f93', title='Korea Control Frequency')\n"
            "plt.xticks(rotation=45, ha='right'); plt.tight_layout()"
        ),
        nbf.v4.new_markdown_cell("### 2. FATF Control Frequency"),
        nbf.v4.new_code_cell(
            "fatf_freq = reg[reg['jurisdiction']=='GLOBAL']['control_type'].value_counts().rename_axis('control_type').reset_index(name='count')\n"
            "display(fatf_freq)\n"
            "fatf_freq.plot.bar(x='control_type', y='count', legend=False, color='#446fb3', title='FATF Control Frequency')\n"
            "plt.xticks(rotation=45, ha='right'); plt.tight_layout()"
        ),
        nbf.v4.new_markdown_cell("### 3. Korea x FATF Control Cross-tab"),
        nbf.v4.new_code_cell(
            "cross_tab = pd.crosstab(reg['control_type'], reg['jurisdiction'])\n"
            "display(cross_tab)"
        ),
        nbf.v4.new_markdown_cell("### 4. Common Control Intersection"),
        nbf.v4.new_code_cell(
            "kr_controls = set(reg.loc[reg['jurisdiction']=='KR','control_type'])\n"
            "fatf_controls = set(reg.loc[reg['jurisdiction']=='GLOBAL','control_type'])\n"
            "common_controls = sorted(kr_controls & fatf_controls)\n"
            "print(common_controls)"
        ),
        nbf.v4.new_markdown_cell("### 5. Jaccard Similarity"),
        nbf.v4.new_code_cell(
            "jaccard = len(kr_controls & fatf_controls) / len(kr_controls | fatf_controls)\n"
            "print({'jaccard_similarity': round(jaccard, 4), 'intersection': len(kr_controls & fatf_controls), 'union': len(kr_controls | fatf_controls)})"
        ),
        nbf.v4.new_markdown_cell("### 6. Control Co-occurrence"),
        nbf.v4.new_code_cell(
            "pairs = []\n"
            "for regulation, group in reg.groupby('regulation_name'):\n"
            "    for a, b in itertools.combinations(sorted(set(group['control_type'])), 2):\n"
            "        pairs.append({'pair': f'{a} | {b}', 'regulation_name': regulation})\n"
            "cooccurrence = pd.DataFrame(pairs).groupby('pair').size().reset_index(name='count').sort_values('count', ascending=False) if pairs else pd.DataFrame(columns=['pair','count'])\n"
            "display(cooccurrence.head(15))"
        ),
        nbf.v4.new_markdown_cell("### 7. Required Field Frequency"),
        nbf.v4.new_code_cell(
            "field_freq = reg[reg['required_field']!='source_note']['required_field'].value_counts().rename_axis('required_field').reset_index(name='count')\n"
            "display(field_freq)\n"
            "field_freq.plot.bar(x='required_field', y='count', legend=False, color='#4f8f65', title='Required Field Frequency')\n"
            "plt.xticks(rotation=45, ha='right'); plt.tight_layout()"
        ),
        nbf.v4.new_markdown_cell("### 8. FPG Scope Ratio"),
        nbf.v4.new_code_cell(
            "scope_ratio = reg['fpg_scope'].value_counts(normalize=True).mul(100).round(2).rename_axis('fpg_scope').reset_index(name='pct')\n"
            "display(scope_ratio)"
        ),
        nbf.v4.new_markdown_cell("### 9. CURRENT / FUTURE Regulation Split"),
        nbf.v4.new_code_cell(
            "status_split = reg['effective_status'].value_counts().rename_axis('effective_status').reset_index(name='count')\n"
            "display(status_split)"
        ),
        nbf.v4.new_markdown_cell("### 10. Regulation -> Control -> Required Field"),
        nbf.v4.new_code_cell(
            "mapping = reg[['regulation_name','article','obligation_id','control_type','required_field','fpg_scope']].sort_values(['regulation_name','control_type','required_field'])\n"
            "display(mapping)"
        ),
        nbf.v4.new_markdown_cell("## Schema Gap\n\nPublic blockchain data is compared with legal required fields. Identity/KYC/counterparty VASP results remain outside public on-chain data."),
        nbf.v4.new_code_cell("display(gap[['field','availability_class','gap_status','legal_basis']])"),
        nbf.v4.new_markdown_cell("## Policy Experiment\n\nThe experiment checks single-condition and compound-condition behavior on synthetic transfers derived from documented public dataset shape/proportions."),
        nbf.v4.new_code_cell(
            "decision_counts = tx['policy_decision'].value_counts().rename_axis('policy_decision').reset_index(name='count')\n"
            "display(decision_counts)\n"
            "checks = ['asset_match','amount_within_limit','destination_match','period_valid','kyc_verified','counterparty_registered','execution_trace_present']\n"
            "failure_rates = (1 - tx[checks].mean()).mul(100).round(2).rename_axis('check').reset_index(name='failure_pct')\n"
            "display(failure_rates)"
        ),
        nbf.v4.new_markdown_cell("## Takeaways\n\nThe repeatable evidence is structural: public on-chain data can support addresses, amount, asset, tx hash, execution status, and timestamp, but cannot by itself enforce regulated transfer conditions requiring identity, KYC, approved policy, and counterparty VASP status."),
    ]
    nb["cells"] = cells
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, NOTEBOOK)


def main() -> None:
    reg_rows = regulatory_rows()
    write_csv(RAW_REG / "crypto_regulation_raw.csv", reg_rows, REG_COLUMNS)
    inventory = dataset_inventory()
    write_json(RAW_TX / "public_transaction_dataset_inventory.json", inventory)
    write_csv(
        RAW_TX / "public_transaction_dataset_inventory.csv",
        inventory,
        [
            "dataset_id",
            "public",
            "download_path",
            "license",
            "columns",
            "transaction_unit",
            "label_available",
            "actual_transaction_fields",
            "fpg_usefulness",
            "selected_for_synthetic_basis",
            "selection_reason",
        ],
    )
    gap_rows = schema_gap_rows(reg_rows)
    write_json(PROCESSED / "regulatory_schema_gap.json", gap_rows)
    write_csv(
        PROCESSED / "regulatory_schema_gap.csv",
        gap_rows,
        ["field", "legal_required", "legal_basis", "public_transaction_field", "availability_class", "fpg_enforcement_input", "gap_status", "notes"],
    )
    synthetic = make_synthetic_transfers()
    evaluated = evaluate_policy(synthetic)
    synthetic_columns = list(evaluated[0].keys())
    write_csv(PROCESSED / "synthetic_regulatory_transfer_v1.csv", evaluated, synthetic_columns)
    write_json(
        PROCESSED / "synthetic_regulatory_transfer_manifest.json",
        {
            "dataset_id": "synthetic_regulatory_transfer_v1",
            "rows": len(evaluated),
            "generation_basis": [
                "Elliptic Bitcoin dataset documented 49 time steps and licit/illicit/unknown class proportions.",
                "Ethereum transaction documentation for on-chain field availability.",
                "Regulatory required fields from crypto_regulation_raw.csv.",
            ],
            "non_claims": [
                "Not real customer data.",
                "Not a production fraud model dataset.",
                "Not a settlement or asset execution ledger.",
            ],
            "digest": {"algorithm": "sha256", "value": stable_digest(evaluated)},
        },
    )
    write_json(
        PROCESSED / "policy_enforcement_experiment_v1.json",
        {
            "experiment_id": "DA-POLICY-EXPERIMENT-001",
            "dataset": "synthetic_regulatory_transfer_v1",
            "rows": len(evaluated),
            "decision_counts": dict(sorted(Counter(r["policy_decision"] for r in evaluated).items())),
            "check_failure_counts": {
                key: sum(1 for r in evaluated if not r[key])
                for key in [
                    "asset_match",
                    "amount_within_limit",
                    "destination_match",
                    "period_valid",
                    "kyc_verified",
                    "counterparty_registered",
                    "execution_trace_present",
                ]
            },
            "claim_scope": "Structural policy-enforcement experiment only; no production threshold or legal conclusion.",
        },
    )
    build_artifacts(reg_rows, gap_rows, evaluated)
    build_contracts()
    build_notebook()


if __name__ == "__main__":
    main()
