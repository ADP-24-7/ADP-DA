from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DA = ROOT / "03_digital_asset"
NOTEBOOK = DA / "notebooks" / "runtime_validation" / "DA_03_trace_binding.ipynb"
EVIDENCE_DOC = DA / "docs" / "handoff" / "DA_03_trace_binding.md"
HANDOFF_DOC = DA / "docs" / "handoff" / "DA_03_trace_binding.md"
ARTIFACT_DIR = DA / "artifacts" / "da_03_trace_binding"


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def read_notebook_text() -> str:
    payload = read_json(NOTEBOOK)
    parts = []
    for cell in payload["cells"]:
        parts.append("".join(cell.get("source", [])))
        for output in cell.get("outputs", []):
            parts.append("".join(output.get("text", [])))
            data = output.get("data", {})
            parts.append("".join(data.get("text/plain", [])))
    return "\n".join(parts)


def test_da_03_notebook_evidence_is_present() -> None:
    assert NOTEBOOK.is_file()
    text = read_notebook_text()

    for expected in (
        "73410",
        "44422",
        "3,452",
        "100.00%",
        "3,364",
        "88",
        "2,131",
        "61.73%",
        "1,321",
        "102",
        "2,233",
        "64.69%",
        "1,219",
        "63.08%",
        "66.26%",
        "Transaction Record",
        "Execution Result",
        "Transaction Value",
        "Total Asset Movement",
    ):
        assert expected in text


def test_da_03_artifacts_capture_required_metrics() -> None:
    summary = read_json(ARTIFACT_DIR / "analysis_summary.json")
    metrics = summary["metrics"]

    assert metrics["ethereum_master_sample"] == 73410
    assert metrics["zero_value_transactions"] == 44422
    assert metrics["analysis_population"]["zero_value_transactions"] == 3452
    assert metrics["receipt_binding"] == {
        "bound": 3452,
        "total": 3452,
        "rate_pct": 100.0,
        "status_1": 3364,
        "status_0": 88,
    }
    assert metrics["token_transfer"] == {
        "present": 2131,
        "missing": 1321,
        "present_rate_pct": 61.73,
    }
    assert metrics["trace_followup_for_token_missing"]["internal_eth_movement"] == 102
    assert metrics["asset_movement"]["token_transfer_or_internal_eth_movement"] == 2233
    assert metrics["asset_movement"]["neither_detected"] == 1219
    assert metrics["asset_movement"]["detected_rate_pct"] == 64.69
    assert metrics["asset_movement"]["wilson_95_ci_pct"] == {"lower": 63.08, "upper": 66.26}
    assert summary["result"]["transaction_record_is_execution_result"] is False
    assert summary["result"]["transaction_value_is_total_asset_movement"] is False


def test_da_03_binding_contract_fields_and_ordering() -> None:
    contract = read_json(ARTIFACT_DIR / "evidence_binding_contract.json")
    requirements = read_json(ARTIFACT_DIR / "runtime_requirements.json")

    assert contract["binding_key"] == "transaction_hash"
    assert contract["source_phase"] == "POST_EXECUTION"
    assert [step["name"] for step in contract["binding_chain"]] == [
        "Transaction Record",
        "Receipt Execution Result",
        "Trace Internal ETH Movement",
        "Token Transfer Asset Movement",
        "Final Execution State",
    ]
    assert set(contract["required_runtime_fields"]) == {
        "transaction_hash",
        "block_number",
        "block_timestamp",
        "transaction_value",
        "receipt_status",
        "trace_present",
        "internal_eth_movement",
        "token_transfer_present",
        "asset_movement_detected",
        "final_execution_state",
    }
    assert contract["forbidden_inference"]["rule"] == (
        "transaction_value == 0 -> no asset movement"
    )
    assert requirements["post_execution_ordering"] == [
        "Transaction identification",
        "Receipt binding",
        "Execution success/failure decision",
        "Trace / Token Transfer evidence lookup",
        "Asset movement decision",
        "Final execution state settlement",
    ]


def test_da_03_handoff_doc_preserves_runtime_message() -> None:
    text = HANDOFF_DOC.read_text(encoding="utf-8")

    assert "Transaction Record != Execution Result" in text
    assert "Transaction Value != Total Asset Movement" in text
    assert "transaction_value == 0" in text
    assert "asset_movement_detected = false" in text
    assert "64.69%" in text
    assert "Ethereum" in text
    assert "Transaction -> Receipt -> Trace / Token Transfer -> Final Execution State" in text


def test_da_03_markdown_links_resolve() -> None:
    for path in (EVIDENCE_DOC, HANDOFF_DOC):
        for link in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if not link.startswith(("http://", "https://", "#")):
                assert (path.parent / link.split("#")[0]).exists(), (path, link)
