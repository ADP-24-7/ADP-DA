"""Build and validate deterministic Digital Asset Local Product E2E fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = Path("03_digital_asset/contracts/da_p0_local_product_e2e_fixture.schema.json")
OUT = Path("03_digital_asset/artifacts/local_product_e2e_v1")
SCHEMA_VERSION = "adp-digital-asset-local-product-e2e-fixture/v1"

EVIDENCE = {
    "DA-01": "03_digital_asset/docs/handoff/DA_01_external_execution.md",
    "DA-02": "03_digital_asset/docs/handoff/DA_02_exact_preservation.md",
    "DA-03": "03_digital_asset/docs/handoff/DA_03_trace_binding.md",
    "DA-04": "03_digital_asset/docs/handoff/DA_04_outbound_destination.md",
    "DA-05": "03_digital_asset/docs/handoff/DA_05_approval_request_match.md",
    "DA-06": "03_digital_asset/docs/handoff/DA_06_recovery_idempotency.md",
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def _approval(asset_symbol: str) -> dict[str, Any]:
    reference = (
        "approved-tx-local-001"
        if asset_symbol == "asset-krw-token-001"
        else f"approved-tx-{asset_symbol}"
    )
    return {
        "approval_reference": reference,
        "policy_version": "0.3.0",
        "purpose_code": "DIGITAL_ASSET_PURCHASE",
        "asset": {
            "chain_id": "eip155:1",
            "asset_kind": "FUNGIBLE_TOKEN",
            "asset_symbol": asset_symbol,
            "asset_contract_address": "0x0000000000000000000000000000000000000001",
            "operation": "TRANSFER",
        },
        "maximum_amount_atomic": "10000000",
        "counterparty_reference": "beneficiary-local-001",
        "destination_profile_id": "dest_mock_asset_platform_v1",
        "destination": "wallet-test-001",
        "valid_from": "2026-01-01T00:00:00Z",
        "valid_until": "2027-01-01T00:00:00Z",
    }


def _request(
    fixture_id: str,
    *,
    asset_symbol: str = "asset-krw-token-001",
    amount: str = "10000",
    destination: str = "wallet-test-001",
) -> dict[str, Any]:
    approval = _approval(asset_symbol)
    return {
        "headers": {
            "X-Request-Id": f"req_da_p0_{fixture_id.lower()}",
            "X-Trace-Id": f"trace_da_p0_{fixture_id.lower()}",
            "X-ADP-Request-Timestamp": "${CURRENT_UTC_ISO8601}",
        },
        "method": "POST",
        "path": "/v1/runtime/executions",
        "body": {
            "institutionId": "institution_local",
            "approvalReference": "approval_digital_asset_purchase_v1",
            "workloadId": "tokenized_asset_purchase",
            "purposeCode": "DIGITAL_ASSET_PURCHASE",
            "subjectScope": "customer:customer-100",
            "destinationProfileId": "dest_mock_asset_platform_v1",
            "idempotencyKey": f"idem_da_p0_{fixture_id.lower()}",
            "processingContexts": ["DIGITAL_ASSET"],
            "input": {
                "approvedTransactionReference": approval["approval_reference"],
                "customerId": "customer-100",
                "accountId": "acct-100-1",
                "outboundRequest": {
                    "requestedAsset": {
                        "chainId": "eip155:1",
                        "assetKind": "FUNGIBLE_TOKEN",
                        "assetSymbol": asset_symbol,
                        "assetContractAddress": (
                            "0x0000000000000000000000000000000000000001"
                        ),
                        "operation": "TRANSFER",
                        "tokenId": None,
                    },
                    "requestedAmount": amount,
                    "requestedDestination": destination,
                    "requestedBeneficiaryReference": "beneficiary-local-001",
                    "regulatoryOutboundData": {},
                },
            },
        },
    }


def _fixture(
    fixture_id: str,
    *,
    asset_symbol: str = "asset-krw-token-001",
    amount: str = "10000",
    destination: str = "wallet-test-001",
    pre_decision: str,
    external: dict[str, Any],
    reconciliation: dict[str, Any],
    final_state: str,
    reason_codes: list[str],
    evidence_ids: list[str],
    submission_count: int = 1,
    runtime_support: str = "SUPPORTED",
) -> dict[str, Any]:
    request = _request(
        fixture_id, asset_symbol=asset_symbol, amount=amount, destination=destination
    )
    approval = _approval(asset_symbol)
    value: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "fixture_id": fixture_id,
        "source": "SYNTHETIC",
        "runtime_support": runtime_support,
        "be_runtime_contract": {
            "endpoint": "/v1/runtime/executions",
            "execution_pack": "DIGITAL_ASSET",
            "local_connector": "FakeDigitalAssetConnector",
            "persistence": "PostgreSQL",
            "trace_endpoint_template": "/v1/runtime/executions/{executionId}/trace",
        },
        "approval": approval,
        "requested_transaction": request,
        "submission_count": submission_count,
        "expected_pre_execution_decision": pre_decision,
        "simulated_external_result": external,
        "external_evidence": {
            "transaction_hash_required": external["external_effect_count"] > 0,
            "receipt_status": external["receipt_status"],
            "finality_status": external["finality_status"],
            "transfer_or_trace_required": external["external_effect_count"] > 0,
            "evidence_source": "INDEPENDENT_EXTERNAL",
        },
        "expected_trace_binding": {
            "correlation_key": "execution_id",
            "required_nodes": [
                "APPROVAL",
                "REQUEST",
                "PRE_EXECUTION_GUARD",
                *(
                    ["EXECUTION_ATTEMPT", "TRANSACTION_HASH", "RECEIPT", "TRANSFER_OR_TRACE"]
                    if external["external_effect_count"] > 0
                    else []
                ),
                "FINAL_STATE",
            ],
        },
        "expected_reconciliation": reconciliation,
        "expected_final_state": final_state,
        "expected_reason_codes": reason_codes,
        "da_evidence_reference": [
            {"evidence_id": evidence_id, "path": EVIDENCE[evidence_id]}
            for evidence_id in evidence_ids
        ],
    }
    value["content_digest"] = digest(value)
    return value


def build_fixtures() -> dict[str, dict[str, Any]]:
    no_reconciliation = {
        "required": False,
        "status_query_required": False,
        "blind_resend_allowed": False,
        "expected_external_effect_count": 0,
        "expected_status": "NOT_REQUIRED",
    }
    return {
        "GOLDEN_PASS": _fixture(
            "GOLDEN_PASS",
            pre_decision="PASS",
            external={
                "scenario": "SETTLED_SUCCESS",
                "connector_status": "ACKNOWLEDGED",
                "execution_status": "SUCCESS",
                "receipt_status": "SUCCESS",
                "finality_status": "FINALIZED",
                "external_effect_count": 1,
            },
            reconciliation={
                **no_reconciliation,
                "expected_external_effect_count": 1,
                "expected_status": "VERIFIED",
            },
            final_state="COMPLETED",
            reason_codes=[],
            evidence_ids=["DA-01", "DA-02", "DA-03", "DA-04", "DA-05"],
        ),
        "BLOCK_AMOUNT": _fixture(
            "BLOCK_AMOUNT",
            amount="10000001",
            pre_decision="BLOCK",
            external={
                "scenario": "NOT_CALLED",
                "connector_status": "NOT_SENT",
                "execution_status": "NOT_EXECUTED",
                "receipt_status": "NOT_AVAILABLE",
                "finality_status": "UNCONFIRMED",
                "external_effect_count": 0,
            },
            reconciliation=no_reconciliation,
            final_state="BLOCKED",
            reason_codes=["DIGITAL_ASSET_APPROVED_AMOUNT_EXCEEDED"],
            evidence_ids=["DA-02", "DA-05"],
        ),
        "BLOCK_DESTINATION": _fixture(
            "BLOCK_DESTINATION",
            destination="wallet-not-approved",
            pre_decision="BLOCK",
            external={
                "scenario": "NOT_CALLED",
                "connector_status": "NOT_SENT",
                "execution_status": "NOT_EXECUTED",
                "receipt_status": "NOT_AVAILABLE",
                "finality_status": "UNCONFIRMED",
                "external_effect_count": 0,
            },
            reconciliation=no_reconciliation,
            final_state="BLOCKED",
            reason_codes=["DIGITAL_ASSET_APPROVED_DESTINATION_MISMATCH"],
            evidence_ids=["DA-04", "DA-05"],
        ),
        "EXECUTION_FAILED": _fixture(
            "EXECUTION_FAILED",
            asset_symbol="asset-execution-failed",
            pre_decision="PASS",
            external={
                "scenario": "RECEIPT_FAILED",
                "connector_status": "ACKNOWLEDGED",
                "execution_status": "FAILED",
                "receipt_status": "FAILED",
                "finality_status": "FINALIZED",
                "external_effect_count": 1,
            },
            reconciliation={
                **no_reconciliation,
                "expected_external_effect_count": 1,
                "expected_status": "FAILED_CONFIRMED",
            },
            final_state="FAILED",
            reason_codes=["RECEIPT_EXECUTION_FAILED"],
            evidence_ids=["DA-01", "DA-03"],
            runtime_support="REQUIRES_BE_LOCAL_FIXTURE_TRIGGER",
        ),
        "SENT_UNKNOWN_RECOVERED": _fixture(
            "SENT_UNKNOWN_RECOVERED",
            asset_symbol="asset-sent-unknown",
            pre_decision="PASS",
            external={
                "scenario": "TIMEOUT_AFTER_EXTERNAL_EFFECT",
                "connector_status": "SENT_UNKNOWN",
                "execution_status": "UNKNOWN",
                "receipt_status": "NOT_AVAILABLE",
                "finality_status": "UNCONFIRMED",
                "external_effect_count": 1,
            },
            reconciliation={
                "required": True,
                "status_query_required": True,
                "blind_resend_allowed": False,
                "expected_external_effect_count": 1,
                "expected_status": "EXTERNALLY_RECONCILED",
            },
            final_state="EXTERNALLY_RECONCILED",
            reason_codes=["SENT_UNKNOWN_RECONCILED"],
            evidence_ids=["DA-01", "DA-03", "DA-06"],
            runtime_support="REQUIRES_BE_RECOVERED_EXECUTION_EVIDENCE_TRIGGER",
        ),
        "DUPLICATE_REQUEST": _fixture(
            "DUPLICATE_REQUEST",
            pre_decision="PASS",
            external={
                "scenario": "IDENTICAL_IDEMPOTENCY_REPLAY",
                "connector_status": "ACKNOWLEDGED",
                "execution_status": "SUCCESS",
                "receipt_status": "SUCCESS",
                "finality_status": "FINALIZED",
                "external_effect_count": 1,
            },
            reconciliation={
                **no_reconciliation,
                "expected_external_effect_count": 1,
                "expected_status": "REPLAYED_EXISTING_EXECUTION",
            },
            final_state="COMPLETED",
            reason_codes=["IDEMPOTENCY_KEY_REUSED"],
            evidence_ids=["DA-03", "DA-06"],
            submission_count=2,
        ),
    }


def validate_fixture(value: dict[str, Any], schema: dict[str, Any]) -> None:
    Draft202012Validator(schema).validate(value)
    without_digest = {key: item for key, item in value.items() if key != "content_digest"}
    if value["content_digest"] != digest(without_digest):
        raise ValueError(f"{value['fixture_id']}: content digest mismatch")
    amount = value["requested_transaction"]["body"]["input"]["outboundRequest"][
        "requestedAmount"
    ]
    if not isinstance(amount, str) or not amount.isdigit():
        raise ValueError(f"{value['fixture_id']}: amount must be an exact decimal string")
    if value["expected_pre_execution_decision"] == "BLOCK":
        if value["simulated_external_result"]["external_effect_count"] != 0:
            raise ValueError(f"{value['fixture_id']}: blocked fixture has an external effect")
        if "EXECUTION_ATTEMPT" in value["expected_trace_binding"]["required_nodes"]:
            raise ValueError(f"{value['fixture_id']}: blocked fixture has an execution trace")
    reconciliation = value["expected_reconciliation"]
    if reconciliation["required"] and reconciliation["blind_resend_allowed"]:
        raise ValueError(f"{value['fixture_id']}: recovery permits blind resend")
    for reference in value["da_evidence_reference"]:
        if not (ROOT / reference["path"]).is_file():
            raise ValueError(f"{value['fixture_id']}: missing evidence {reference['path']}")


def validate_all(fixtures: dict[str, dict[str, Any]]) -> None:
    schema = json.loads((ROOT / SCHEMA).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    if set(fixtures) != {
        "GOLDEN_PASS",
        "BLOCK_AMOUNT",
        "BLOCK_DESTINATION",
        "EXECUTION_FAILED",
        "SENT_UNKNOWN_RECOVERED",
        "DUPLICATE_REQUEST",
    }:
        raise ValueError("fixture set is incomplete")
    for value in fixtures.values():
        validate_fixture(value, schema)
    duplicate = fixtures["DUPLICATE_REQUEST"]
    if duplicate["submission_count"] != 2:
        raise ValueError("duplicate request must submit the identical request twice")
    unknown = fixtures["SENT_UNKNOWN_RECOVERED"]
    if unknown["expected_reconciliation"]["expected_external_effect_count"] != 1:
        raise ValueError("SENT_UNKNOWN recovery must preserve one external effect")


def write_or_check(*, check: bool) -> None:
    fixtures = build_fixtures()
    validate_all(fixtures)
    for fixture_id, value in fixtures.items():
        path = ROOT / OUT / f"{fixture_id.lower()}.json"
        rendered = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
        if check:
            if not path.is_file() or path.read_text(encoding="utf-8") != rendered:
                raise ValueError(f"fixture drift: {path.relative_to(ROOT)}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(rendered, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    write_or_check(check=args.check)


if __name__ == "__main__":
    main()
