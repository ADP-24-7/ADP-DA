from __future__ import annotations

import copy
import importlib
import json
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "03_digital_asset/src"))
fixtures = importlib.import_module("da_p0_local_product_e2e")


@pytest.fixture(scope="module")
def built():
    return fixtures.build_fixtures()


def test_six_deterministic_fixtures_match_saved_artifacts(built):
    assert len(built) == 6
    fixtures.validate_all(built)
    for fixture_id, value in built.items():
        path = ROOT / fixtures.OUT / f"{fixture_id.lower()}.json"
        assert json.loads(path.read_text(encoding="utf-8")) == value


def test_fixture_schema_and_content_digests(built):
    schema = json.loads((ROOT / fixtures.SCHEMA).read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )
    for value in built.values():
        validator.validate(value)
        without_digest = {key: item for key, item in value.items() if key != "content_digest"}
        assert value["content_digest"] == fixtures.digest(without_digest)


def test_block_fixtures_are_fail_closed_before_external_execution(built):
    for fixture_id in ("BLOCK_AMOUNT", "BLOCK_DESTINATION"):
        value = built[fixture_id]
        assert value["expected_pre_execution_decision"] == "BLOCK"
        assert value["simulated_external_result"]["connector_status"] == "NOT_SENT"
        assert value["simulated_external_result"]["external_effect_count"] == 0


def test_amounts_are_lossless_decimal_strings(built):
    for value in built.values():
        request = value["requested_transaction"]["body"]
        amount = request["input"]["outboundRequest"]["requestedAmount"]
        assert isinstance(amount, str) and amount.isdigit()
        assert isinstance(value["approval"]["maximum_amount_atomic"], str)


def test_recovery_and_duplicate_never_create_a_second_external_effect(built):
    unknown = built["SENT_UNKNOWN_RECOVERED"]
    assert unknown["expected_reconciliation"]["status_query_required"] is True
    assert unknown["expected_reconciliation"]["blind_resend_allowed"] is False
    assert unknown["expected_reconciliation"]["expected_external_effect_count"] == 1

    duplicate = built["DUPLICATE_REQUEST"]
    assert duplicate["submission_count"] == 2
    assert duplicate["expected_reconciliation"]["expected_external_effect_count"] == 1


def test_execution_trace_binds_intent_attempt_evidence_and_final_state(built):
    for value in built.values():
        nodes = value["expected_trace_binding"]["required_nodes"]
        assert nodes[:3] == ["APPROVAL", "REQUEST", "PRE_EXECUTION_GUARD"]
        assert nodes[-1] == "FINAL_STATE"
        if value["expected_pre_execution_decision"] == "BLOCK":
            assert "EXECUTION_ATTEMPT" not in nodes
        else:
            assert nodes[3:-1] == [
                "EXECUTION_ATTEMPT",
                "TRANSACTION_HASH",
                "RECEIPT",
                "TRANSFER_OR_TRACE",
            ]


def test_digest_or_semantic_tampering_is_rejected(built):
    changed = copy.deepcopy(built["BLOCK_AMOUNT"])
    changed["requested_transaction"]["body"]["input"]["outboundRequest"][
        "requestedAmount"
    ] = "10000"
    schema = json.loads((ROOT / fixtures.SCHEMA).read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="digest mismatch"):
        fixtures.validate_fixture(changed, schema)

    changed = copy.deepcopy(built["BLOCK_DESTINATION"])
    changed["simulated_external_result"]["external_effect_count"] = 1
    changed["content_digest"] = fixtures.digest(
        {key: value for key, value in changed.items() if key != "content_digest"}
    )
    with pytest.raises(ValueError, match="external effect"):
        fixtures.validate_fixture(changed, schema)


def test_current_be_consumer_contract_and_supported_triggers(built):
    be_root = ROOT.parent / "ADP-BE"
    if not be_root.is_dir():
        pytest.fail("ADP-BE sibling checkout is required for DA/BE compatibility validation")

    java_root = be_root / "src/main/java/com/adp/gateway"
    request_contract = (java_root / "runtime/api/RuntimeExecutionRequest.java").read_text()
    outbound_contract = (
        java_root / "runtime/api/DigitalAssetOutboundRequestContract.java"
    ).read_text()
    connector = (
        java_root / "digitalasset/infrastructure/FakeDigitalAssetConnector.java"
    ).read_text()
    reason_codes = (java_root / "common/error/ReasonCode.java").read_text()

    for field in built["GOLDEN_PASS"]["requested_transaction"]["body"]:
        assert field in request_contract
    outbound = built["GOLDEN_PASS"]["requested_transaction"]["body"]["input"]["outboundRequest"]
    for field in outbound:
        assert field in outbound_contract
    assert "asset-sent-unknown" in connector
    assert "asset-execution-failed" in connector
    assert "DIGITAL_ASSET_APPROVED_AMOUNT_EXCEEDED" in reason_codes
    assert "DIGITAL_ASSET_APPROVED_DESTINATION_MISMATCH" in reason_codes
    assert "IDEMPOTENCY_KEY_REUSED" in reason_codes
