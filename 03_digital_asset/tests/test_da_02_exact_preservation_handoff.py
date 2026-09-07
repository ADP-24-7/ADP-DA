from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DA = ROOT / "03_digital_asset"
NOTEBOOK = DA / "notebooks" / "runtime_validation" / "DA_02_exact_preservation.ipynb"
EVIDENCE_DOC = DA / "docs" / "handoff" / "DA_02_exact_preservation.md"
HANDOFF_DOC = DA / "docs" / "DA_02_EXACT_PRESERVATION_BE_HANDOFF.md"
MATRIX = DA / "artifacts" / "outbound_design_vNext" / "outbound_requirement_matrix.json"
SCHEMA = DA / "contracts" / "outbound_requirement_matrix_v2.schema.json"


def read_notebook_text() -> str:
    payload = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    return "\n".join("".join(cell.get("source", [])) for cell in payload["cells"])


def amount_requirement() -> dict[str, Any]:
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    return next(row for row in matrix["requirements"] if row["required_fields"] == ["amount"])


def test_da_02_notebook_evidence_is_present() -> None:
    assert NOTEBOOK.is_file()
    text = read_notebook_text()

    for expected in (
        "Ethereum Master Sample 73,410건",
        "73,266건",
        "Decimal 기반 Exact Preservation: **100.0000%**",
        "FLOAT64 Precision Loss: **3,280건**",
        "Precision Loss Rate: **4.4768%**",
        "Positive Amount 28,953건",
        "Precision Loss Rate는 **11.3287%**",
        "2^53 = 9,007,199,254,740,992 wei",
        "16,784건 중 손실 **0건**",
        "12,169건 중 손실 **3,280건(26.9537%)**",
        "최대 절대오차: **351,232 wei**",
        "Haldane-Anscombe 보정 Odds Ratio: **12,387.9976**",
        "Risk Difference: **26.9537%p**",
    ):
        assert expected in text


def test_da_02_handoff_states_no_threshold_block_policy() -> None:
    text = HANDOFF_DOC.read_text(encoding="utf-8")

    assert "DA-02는 `2^53` 이상 거래를 차단하기 위한 분석이 아니다" in text
    assert "FLOAT64 / double은 canonical amount 저장, 비교, 전송 타입으로 사용하지 않는다" in text
    assert "`approved_amount_atomic == outbound_amount_atomic`" in text
    assert "`approved_amount_atomic == executed_amount_atomic`" in text
    assert "새로운 enum 이름은 BE-owned runtime enum gap" in text


def test_existing_amount_contract_supports_da_02_exact_semantics() -> None:
    row = amount_requirement()

    assert row["required_exact"] == "EXACT_REQUIRED"
    assert row["transform"] == ["PASS_THROUGH"]
    assert row["comparison_canonicalization"] == "NONE_CONTRACTED"
    assert row["source_phase"] == "PRE_EXECUTION"
    assert row["source_type"] == "APPROVED_AND_REQUESTED_VALUE_PAIR"
    assert row["pre_execution_required"] is True
    assert row["post_execution_binding"] is False
    assert row["validation_type"] == "MATCH_APPROVED_VALUE"
    assert row["outbound_transform_by_destination"] == {
        "BLOCKCHAIN_EXECUTION_SYSTEM": "PASS_THROUGH",
        "INTERNAL_RECONCILIATION_ONLY": "PASS_THROUGH",
    }


def test_da_02_does_not_require_schema_expansion() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    required = set(schema["properties"]["requirements"]["items"]["required"])

    assert "required_exact" in required
    assert "comparison_canonicalization" in required
    assert "outbound_transform_by_destination" in required
    assert "source_phase" in required
    assert "source_type" in required


def test_da_02_markdown_links_resolve() -> None:
    for path in (EVIDENCE_DOC, HANDOFF_DOC):
        for link in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if not link.startswith(("http://", "https://", "#")):
                assert (path.parent / link.split("#")[0]).exists(), (path, link)
