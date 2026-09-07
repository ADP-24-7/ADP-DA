from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "03_digital_asset/src"))
runtime = importlib.import_module("da_05_approval_match")
builder = importlib.import_module("build_da_05_handoff")


@pytest.fixture
def inputs():
    address = "0x" + "a" * 40
    approval = {
        "approval_id": "approval-7",
        "approved_asset": "ETH",
        "approved_max_amount": "9007199254740993",
        "approved_destination": address,
        "valid_from": "2026-01-01T00:00:00Z",
        "valid_until": "2026-01-02T00:00:00Z",
    }
    request = {
        "request_id": "request-99",
        "requested_asset": "ETH",
        "requested_amount": "9007199254740993",
        "requested_destination": address,
        "requested_at": "2026-01-01T12:00:00Z",
        "transaction_type": 2,
        "request_type": "ADDRESS_TRANSACTION",
    }
    return approval, request


def evaluate(inputs, binding=None):
    a, r = inputs
    return runtime.evaluate(
        a,
        r,
        binding
        if binding is not None
        else {"approval_id": a["approval_id"], "request_id": r["request_id"]},
        evaluated_at="2026-01-01T12:00:01Z",
        contract_version="1.0.0",
        evidence_reference="TEST_FIXTURE",
    )


def test_equal_amount_and_all_matches_pass(inputs):
    result = evaluate(inputs)
    assert result["decision"] == "PASS" and result["violation_count"] == 0
    assert result["approval_id"] != result["request_id"]


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("requested_asset", "USDC", "asset_match"),
        ("requested_amount", "9007199254740994", "amount_match"),
        ("requested_destination", "0x" + "b" * 40, "destination_match"),
        ("requested_at", "2026-01-02T00:00:01Z", "period_match"),
        ("requested_at", "2025-12-31T23:59:59Z", "period_match"),
    ],
)
def test_mismatch_blocks(inputs, field, value, reason):
    inputs[1][field] = value
    result = evaluate(inputs)
    assert result["decision"] == "BLOCK"
    assert result["violation_reasons"] == [reason]


@pytest.mark.parametrize(
    "when", ["2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z", "2026-01-01T09:00:00+09:00"]
)
def test_inclusive_period_and_timezone(inputs, when):
    inputs[1]["requested_at"] = when
    assert evaluate(inputs)["decision"] == "PASS"


def test_creation_is_na_not_pass(inputs):
    inputs[1].update(request_type="CONTRACT_CREATION", requested_destination=None)
    inputs[0]["approved_destination"] = None
    result = evaluate(inputs)
    assert result["decision"] == "PASS"
    assert result["destination_applicability"] == "NOT_APPLICABLE"
    assert result["destination_match"] is None
    assert result["violation_count"] == 0
    inputs[1]["requested_asset"] = "USDC"
    assert evaluate(inputs)["decision"] == "BLOCK"


def test_post_address_never_substituted(inputs):
    inputs[1].update(request_type="CONTRACT_CREATION", contract_address="0x" + "a" * 40)
    with pytest.raises(runtime.MatchContractError, match="POST_EXECUTION"):
        evaluate(inputs)
    del inputs[1]["contract_address"]
    with pytest.raises(runtime.MatchContractError, match="SUBSTITUTION"):
        evaluate(inputs)


def test_multiple_applicable_violations(inputs):
    inputs[1].update(requested_asset="USDC", requested_amount="9007199254740994")
    result = evaluate(inputs)
    assert result["decision"] == "BLOCK" and result["violation_count"] == 2


def test_explicit_binding_failure(inputs):
    with pytest.raises(runtime.MatchContractError, match="BINDING"):
        evaluate(inputs, {"approval_id": "wrong", "request_id": "request-99"})


@pytest.mark.parametrize("value", [1.0, True, "1.0", "1e3", -1, None])
def test_lossy_or_invalid_amount_rejected(inputs, value):
    inputs[1]["requested_amount"] = value
    with pytest.raises(runtime.MatchContractError, match="EXACT"):
        evaluate(inputs)


@pytest.mark.parametrize("kind", [0, 1, 2, 3, 4])
def test_type_does_not_decide_or_skip_zero_amount(inputs, kind):
    inputs[1].update(transaction_type=kind, requested_amount="0")
    inputs[0]["approved_max_amount"] = "0"
    result = evaluate(inputs)
    assert result["decision"] == "PASS"
    assert result["rule_applicability"]["amount"] == "APPLICABLE"
    inputs[1]["requested_asset"] = "USDC"
    assert evaluate(inputs)["decision"] == "BLOCK"


@pytest.mark.parametrize("value", ["not-a-time", "2026-01-01", None])
def test_invalid_period_fails_closed(inputs, value):
    inputs[1]["requested_at"] = value
    with pytest.raises(runtime.MatchContractError):
        evaluate(inputs)


def test_address_normalization_and_missing_address(inputs):
    inputs[1]["requested_destination"] = "0x" + "A" * 40
    assert evaluate(inputs)["destination_match"] is True
    inputs[1]["requested_destination"] = None
    with pytest.raises(runtime.MatchContractError):
        evaluate(inputs)


def test_artifact_source_and_schema_consistency():
    folder = ROOT / builder.OUT
    summary = json.loads((folder / "analysis_summary.json").read_text(encoding="utf-8"))
    values = builder.build(generated_at=summary["generated_at"])
    schema = json.loads((ROOT / builder.SCHEMA).read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    assert len(values) == 7
    for name, value in values.items():
        assert json.loads((folder / (name + ".json")).read_text(encoding="utf-8")) == value
        jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(
            value
        )
        for ref in value["evidence_refs"]:
            assert (ROOT / ref["path"]).is_file()
