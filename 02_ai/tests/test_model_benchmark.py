from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from adp_da.model_benchmark import (
    HARNESS_MODE,
    MODELS,
    PRODUCTION_GOVERNANCE,
    WEIGHTS,
    WORKLOADS,
    _score,
    build_cases,
    prepare,
)


def test_case_catalog_is_frozen_balanced_and_synthetic() -> None:
    cases = build_cases()

    assert len(cases) == 30
    assert Counter(case["workload_type"] for case in cases) == Counter(
        {workload: 5 for workload in WORKLOADS}
    )
    assert len({case["case_id"] for case in cases}) == 30
    assert all(case["data_classification"] == "SYNTHETIC_NON_LINKABLE" for case in cases)
    assert all(case["case_digest"].startswith("sha256:") for case in cases)


def test_benchmark_contract_separates_evaluation_from_production(tmp_path: Path) -> None:
    prepare(tmp_path)
    payload = json.loads((tmp_path / "benchmark_cases.json").read_text(encoding="utf-8"))

    assert payload["status"] == "FROZEN_BEFORE_EXECUTION"
    assert payload["evaluation_harness"] == "ISOLATED BENCHMARK HARNESS"
    assert payload["production_governance"] == PRODUCTION_GOVERNANCE
    assert payload["production_governance"] == "ACTIVE_FAIL_CLOSED / BLOCK"
    assert payload["expected_executions"] == 270
    assert payload["models"] == MODELS
    assert payload["weights"] == WEIGHTS
    assert sum(payload["weights"].values()) == 1.0
    assert payload["benchmark_contract_digest"].startswith("sha256:")
    assert HARNESS_MODE == "BENCHMARK_EVALUATION_ONLY"


def test_score_requires_schema_evidence_and_exact_preservation() -> None:
    case = next(case for case in build_cases() if case["case_id"] == "BENCH-08")
    valid = json.dumps(
        {
            "case_id": "BENCH-08",
            "answer": "Yes: 500.00 covers 499.99.",
            "evidence_ids": ["CALC-B03"],
        }
    )
    altered = json.dumps(
        {
            "case_id": "BENCH-08",
            "answer": "Yes: 500 covers 499.99.",
            "evidence_ids": ["CALC-B03"],
        }
    )

    assert _score(case, valid)["policy_compliance"] is True
    altered_score: dict[str, Any] = _score(case, altered)
    assert altered_score["policy_compliance"] is False
    assert "REQUIRED_EXACT_NOT_PRESERVED" in altered_score["finding_types"]


def test_score_rejects_extra_output_fields() -> None:
    case = build_cases()[0]
    content = json.dumps(
        {
            "case_id": case["case_id"],
            "answer": "ACTIVE CHECKING",
            "evidence_ids": ["DOC-A01"],
            "ranking": 1,
        }
    )

    score = _score(case, content)
    assert score["format_compliance"] is False
    assert score["policy_compliance"] is False
    assert "OUTPUT_SCHEMA_INVALID" in score["finding_types"]
