"""Freeze analyst notebook outputs after independent CSV consistency checks.

No notebook execution, cloud queries, source edits or new hypothesis tests.
Run from ADP-DA: python 03_digital_asset/src/build_da_00_01_handoff.py [--check]
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import math
import re
from collections import Counter
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import chi2_contingency, norm

ROOT = Path(__file__).resolve().parents[2]
DA = Path("03_digital_asset")
DATA = DA / "data/processed/da_master_transaction_sample_73410.csv"
NB0 = DA / "notebooks/runtime_validation/DA_00_master_sample.ipynb"
NB1 = DA / "notebooks/runtime_validation/DA_01_external_execution.ipynb"
DOC0 = DA / "docs/handoff/DA_00_master_sample_contract.md"
DOC1 = DA / "docs/handoff/DA_01_external_execution.md"


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def notebook(root: Path, path: Path) -> dict[str, Any]:
    value = json.loads((root / path).read_text(encoding="utf-8"))
    require(value["nbformat"] == 4, "Unsupported notebook format")
    require(
        not any(
            out.get("output_type") == "error"
            for cell in value["cells"]
            for out in cell.get("outputs", [])
        ),
        "Notebook has recorded errors",
    )
    return value


def output_text(nb: dict[str, Any], cell: int) -> str:
    return "\n".join(
        "".join(out.get("text", out.get("data", {}).get("text/plain", [])))
        for out in nb["cells"][cell].get("outputs", [])
    )


class TableReader(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self.row: list[str] = []
        self.cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag == "tr":
            self.row = []
        elif tag in {"th", "td"}:
            self.cell = []

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"th", "td"} and self.cell is not None:
            self.row.append("".join(self.cell).strip())
            self.cell = None
        elif tag == "tr":
            self.rows.append(self.row)


def table(nb: dict[str, Any], cell: int) -> list[list[str]]:
    reader = TableReader()
    for out in nb["cells"][cell].get("outputs", []):
        reader.feed("".join(out.get("data", {}).get("text/html", [])))
    rows = [row for row in reader.rows if row and row[0].isdigit()]
    require(bool(rows), f"Missing recorded table at cell {cell}")
    return rows


def literal(nb: dict[str, Any], cell: int, name: str) -> Any:
    tree = ast.parse("".join(nb["cells"][cell]["source"]))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise ValueError(f"Missing literal {name} in notebook cell {cell}")


def reported(nb: dict[str, Any], cell: int, label: str) -> str:
    match = re.search(re.escape(label) + r"\s*:\s*([^\n]+)", output_text(nb, cell))
    require(match is not None, f"Missing reported metric {label}")
    assert match is not None
    return match[1].strip()


def number(text: str) -> float:
    return float(text.replace(",", "").replace("%", "").removesuffix("건"))


def verify_sources(root: Path = ROOT) -> dict[str, Any]:
    nb0, nb1 = notebook(root, NB0), notebook(root, NB1)
    counts: Counter[tuple[int, int]] = Counter()
    hashes: set[str] = set()
    missing = duplicates = 0
    with (root / DATA).open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames
        for row in reader:
            missing += row["receipt_status"] == ""
            require(row["receipt_status"] in {"0", "1"}, "Invalid or missing receipt_status")
            require(
                bool(re.fullmatch(r"0x[0-9a-fA-F]{64}", row["transaction_hash"])),
                "Missing/invalid transaction hash",
            )
            duplicates += row["transaction_hash"] in hashes
            hashes.add(row["transaction_hash"])
            counts[int(row["transaction_type"]), int(row["receipt_status"])] += 1
    allocation = {int(row[1]): int(row[5]) for row in table(nb0, 25)}
    quality = {int(row[1]): int(row[2]) for row in table(nb0, 29)}
    types = sorted({key[0] for key in counts})
    sizes = {key: counts[key, 0] + counts[key, 1] for key in types}
    total = sum(sizes.values())
    require(sizes == allocation == quality, "CSV / planned / recorded allocation mismatch")
    require(total == number(reported(nb0, 29, "전체")) == 73410, "Sample count mismatch")
    require(
        len(hashes) == number(reported(nb0, 29, "Transaction Hash 고유값")) == total,
        "Unique hash count mismatch",
    )
    require(
        duplicates == number(reported(nb0, 29, "Transaction Hash 중복")) == 0,
        "Duplicate hash mismatch",
    )
    require(
        missing == number(reported(nb0, 29, "Receipt Status 결측")) == 0,
        "Receipt missingness mismatch",
    )
    require(f"({total}, {len(columns or [])})" in output_text(nb1, 1), "DA-01 shape mismatch")
    population = {
        int(re.search(r"Type (\d+)", row[1])[1]): {
            "transaction_count": int(row[2]),
            "population_share_pct_reported": float(row[3]),
        }
        for row in table(nb0, 19)
    }
    weights = literal(nb1, 4, "population_weight")
    require(set(weights) == set(types), "Weight type mismatch")
    require(math.isclose(sum(weights.values()), 1.0, abs_tol=1e-12), "Weight sum mismatch")
    population_n = sum(row["transaction_count"] for row in population.values())
    for key in types:
        require(
            math.isclose(
                weights[key] * 100, population[key]["population_share_pct_reported"], abs_tol=1e-6
            ),
            "DA-00 population / DA-01 weight mismatch",
        )
        require(
            math.isclose(
                population[key]["transaction_count"] / population_n * 100,
                population[key]["population_share_pct_reported"],
                abs_tol=1e-6,
            ),
            "Population share inconsistent with recorded count",
        )
    status_rows = table(nb1, 2)
    require(len(status_rows) == len(types), "Missing type outcome rows")
    for row in status_rows:
        key = int(row[0])
        require(
            [counts[key, 0], counts[key, 1], sizes[key]] == list(map(int, row[1:4])),
            "CSV / notebook execution counts mismatch",
        )
        require(f"{counts[key, 0] / sizes[key] * 100:.6f}" == row[4], "Failure rate mismatch")
        require(f"{counts[key, 1] / sizes[key] * 100:.6f}" == row[5], "Success rate mismatch")
    weighted = sum(counts[key, 0] / sizes[key] * weights[key] for key in types)
    require(
        f"{weighted * 100:.4f}%" == reported(nb1, 4, "가중 Execution 실패율"),
        "Weighted failure mismatch",
    )
    require(
        f"{(1 - weighted) * 100:.4f}%" == reported(nb1, 4, "가중 Execution 성공률"),
        "Weighted success mismatch",
    )
    contingency = np.array([[counts[key, 0], counts[key, 1]] for key in types])
    chi2, p_value, dof, expected = chi2_contingency(contingency)
    v = math.sqrt(chi2 / (total * min(contingency.shape[0] - 1, contingency.shape[1] - 1)))
    comparisons = [
        ("카이제곱 통계량", f"{chi2:,.4f}"),
        ("자유도", str(dof)),
        ("p-value", f"{p_value:.4e}"),
        ("크래머의 V", f"{v:.4f}"),
        ("최소 기대빈도", f"{expected.min():,.2f}"),
        ("기대빈도 5 미만 비율", f"{(expected < 5).mean() * 100:.2f}%"),
    ]
    for label, value in comparisons:
        require(reported(nb1, 7, label) == value, f"CSV / notebook {label} mismatch")
    posthoc = table(nb1, 10)
    require(len(posthoc) == number(reported(nb1, 10, "비교 수")) == 10, "Pair count mismatch")
    for row in posthoc:
        match = re.fullmatch(r"Type (\d+) vs Type (\d+)", row[1])
        require(match is not None, "Invalid comparison label")
        assert match is not None
        a, b = map(int, match.groups())
        ra, rb = counts[a, 0] / sizes[a], counts[b, 0] / sizes[b]
        pooled = (counts[a, 0] + counts[b, 0]) / (sizes[a] + sizes[b])
        z = (ra - rb) / math.sqrt(pooled * (1 - pooled) * (1 / sizes[a] + 1 / sizes[b]))
        p = float(2 * norm.sf(abs(z)))
        adjusted = min(p * len(posthoc), 1.0)
        values = [
            f"{ra * 100:.4f}",
            f"{rb * 100:.4f}",
            f"{(ra - rb) * 100:.4f}",
            f"{z:.4f}",
            f"{p:.6f}",
            f"{adjusted:.6f}",
            str(adjusted < 0.05),
        ]
        require(values == row[2:], "Recorded Bonferroni comparison mismatch")
    doc0, doc1 = ((root / path).read_text(encoding="utf-8") for path in (DOC0, DOC1))
    for count in sizes.values():
        require(f"{count:,}" in doc0, "DA-00 document allocation mismatch")
    for row in status_rows:
        require(f"{float(row[4]):.4f}%" in doc1, "DA-01 document failure rate mismatch")
    for _, value in comparisons:
        normalized = value.replace(".00%", "%")
        require(value in doc1 or normalized in doc1, "DA-01 document statistic mismatch")
    require(f"{weighted * 100:.4f}%" in doc1, "DA-01 document weighted rate mismatch")
    return {
        "nb0": nb0,
        "nb1": nb1,
        "sample_size": total,
        "type_counts": sizes,
        "columns": columns,
        "population": population,
        "weights": weights,
        "status_rows": status_rows,
        "posthoc": posthoc,
        "quality": {
            "rows": total,
            "unique_transaction_hash": len(hashes),
            "duplicate_transaction_hash": duplicates,
            "receipt_status_missing": missing,
        },
    }


def build_artifacts(generated_at: str, root: Path = ROOT) -> dict[Path, dict[str, Any]]:
    evidence = verify_sources(root)
    nb0, nb1 = evidence["nb0"], evidence["nb1"]

    def common(identifier: str, path: Path, cells: list[int]) -> dict[str, Any]:
        return {
            "artifact_id": identifier,
            "artifact_version": "1.0.0",
            "generated_at": generated_at,
            "source_notebook": path.as_posix(),
            "source_notebook_sha256": sha256(root / path),
            "source_data": DATA.as_posix(),
            "source_data_sha256": sha256(root / DATA),
            "analysis_scope": "Pectra 이후 Ethereum 거래의 분석·BE Handoff 근거; 운영 데이터 아님",
            "evidence_type": "PROCESSED_ANALYSIS_ARTIFACT",
            "hypothesis": None,
            "method": "저장된 Notebook 결과를 추출하고 CSV로 동일 계산 검산",
            "metrics": {},
            "result": {},
            "interpretation": "새 분석 또는 실제 BE 실행 결과가 아님",
            "runtime_implication": (
                "BE Contract 설계 근거. 운영 transaction source나 active policy 아님"
            ),
            "evidence_refs": [{"path": path.as_posix(), "cell_index": cell} for cell in cells]
            + [
                {"path": DATA.as_posix()},
                {"path": (DOC0 if path == NB0 else DOC1).as_posix()},
            ],
        }

    artifacts: dict[Path, dict[str, Any]] = {}

    def add(folder: str, name: str, path: Path, cells: list[int], **fields: Any) -> None:
        value = common(folder.upper() + ":" + name, path, cells)
        value.update(fields)
        artifacts[DA / "artifacts" / folder / (name + ".json")] = value

    population_test = {
        "sample_size": int(number(reported(nb0, 16, "전체 거래 N"))),
        "chi_square_reported": number(reported(nb0, 16, "Chi-square")),
        "degrees_of_freedom": int(number(reported(nb0, 16, "자유도"))),
        "p_value_bound_reported": reported(nb0, 16, "p-value"),
        "cramers_v_reported": number(reported(nb0, 16, "Cramér's V")),
        "minimum_expected_frequency_reported": number(reported(nb0, 16, "최소 기대빈도")),
        "expected_under_5_pct": number(reported(nb0, 16, "기대빈도 < 5 비율")),
        "verification_scope": (
            "Notebook 저장 출력 확인; 전체 역사 모집단 raw 집계 미제공으로 재계산 안 함"
        ),
    }
    add(
        "da_00_master_sample",
        "analysis_summary",
        NB0,
        [16, 18, 19, 29, 30],
        hypothesis="시기와 Transaction Type은 독립이다",
        metrics={"historical_population_test": population_test, **evidence["quality"]},
        result={
            "analysis_population_start": "2025-06-01",
            "transaction_types": [0, 1, 2, 3, 4],
            "master_sample_size": evidence["sample_size"],
        },
        interpretation="역사 전체를 단일 구조로 간주하지 않고 현재 환경의 Type별 층화표본 사용",
    )
    add(
        "da_00_master_sample",
        "sampling_contract",
        NB0,
        [19, 23, 25, 26, 29],
        method="불비례 층화표본: 비례할당 후 각 Type 최소 표본 보강",
        metrics={
            "base_sample_size": literal(nb0, 25, "BASE_SAMPLE_SIZE"),
            "minimum_stratum_sample": literal(nb0, 25, "MIN_STRATUM_SAMPLE"),
            "confidence_level": literal(nb0, 23, "CONFIDENCE_LEVEL"),
            "strata": [
                {
                    "transaction_type": key,
                    "sample_count": value,
                    **evidence["population"][key],
                    "population_weight_used_in_da01": evidence["weights"][key],
                }
                for key, value in sorted(evidence["type_counts"].items())
            ],
        },
        result={
            "sample_size": evidence["sample_size"],
            "population_weighting_required": True,
            "weight_formula": "전체 비율 = sum(층 내 관측비율 * 모집단 비중)",
            "individual_row_weight_exported": False,
        },
        interpretation="층별 비교는 추출 표본, 전체 추정은 Notebook에 고정된 모집단 비중 사용",
    )
    add(
        "da_00_master_sample",
        "data_provenance",
        NB0,
        [2, 28, 29, 31],
        metrics=evidence["quality"],
        result={
            "source_dataset_reported_in_handoff": (
                "bigquery-public-data.goog_blockchain_ethereum_mainnet_us"
            ),
            "source_dataset_verification": "Handoff 명시값; Notebook의 DATASET 초기화 미저장",
            "csv_columns": evidence["columns"],
            "csv_encoding": "UTF-8 with BOM",
            "sha256_scope": "실제 원본 파일 bytes; 줄바꿈/출력/인코딩 포함",
            "allowed_uses": [
                "DA 분석 재현",
                "Runtime 설계 근거",
                "DA-01~03 공통 거래 기준",
                "Handoff Evidence 검증",
            ],
            "operational_transaction_source": False,
            "contract_gaps": [
                "추출 SQL query_da01_sample 정의",
                "client/DATASET 초기화",
                "BigQuery job ID·snapshot cutoff·추출 seed/정렬 기준",
                "전체 역사·현재 모집단 raw 집계",
                "Notebook 로컬 절대경로",
            ],
        },
    )
    rates = [
        {
            "transaction_type": int(row[0]),
            "failed": int(row[1]),
            "succeeded": int(row[2]),
            "sample_size": int(row[3]),
            "failure_rate_pct_reported": float(row[4]),
            "success_rate_pct_reported": float(row[5]),
        }
        for row in evidence["status_rows"]
    ]
    add(
        "da_01_external_execution",
        "analysis_summary",
        NB1,
        [1, 2, 3, 4, 5],
        hypothesis="Transaction 기록만으로 Execution 성공을 판단할 수 있는가",
        metrics={
            "sample_size": evidence["sample_size"],
            "by_transaction_type": rates,
            "weighted_failure_rate_pct_reported": number(reported(nb1, 4, "가중 Execution 실패율")),
            "weighted_success_rate_pct_reported": number(reported(nb1, 4, "가중 Execution 성공률")),
        },
        result="Transaction Record != Execution Result",
        interpretation=(
            "모든 주요 Type에서 실패 관측. 유형별 실패 원인이나 운영 위험점수는 추정하지 않음"
        ),
        runtime_implication="SUBMITTED / SENT != EXECUTION_CONFIRMED; 실제 실행 증적 후 최종 판단",
    )
    add(
        "da_01_external_execution",
        "statistical_validation",
        NB1,
        [6, 7, 8, 9, 10, 11],
        hypothesis={
            "H0": "Transaction Type과 Execution Result는 서로 독립이다",
            "H1": "Transaction Type과 Execution Result는 서로 독립이 아니다",
        },
        method={
            "omnibus": "Chi-square independence test",
            "effect_size": "Cramer's V",
            "posthoc": "Two-sided pooled two-proportion Z test",
            "correction": "Bonferroni",
        },
        metrics={
            "sample_size": evidence["sample_size"],
            "chi_square_reported": number(reported(nb1, 7, "카이제곱 통계량")),
            "degrees_of_freedom": int(number(reported(nb1, 7, "자유도"))),
            "p_value_reported": number(reported(nb1, 7, "p-value")),
            "cramers_v_reported": number(reported(nb1, 7, "크래머의 V")),
            "minimum_expected_frequency_reported": number(reported(nb1, 7, "최소 기대빈도")),
            "expected_under_5_pct": number(reported(nb1, 7, "기대빈도 5 미만 비율")),
            "posthoc_comparisons": [
                {
                    "comparison": row[1],
                    "failure_rate_difference_pp_reported": float(row[4]),
                    "z_reported": float(row[5]),
                    "p_value_display": row[6],
                    "bonferroni_p_value_display": row[7],
                    "significant": row[8] == "True",
                }
                for row in evidence["posthoc"]
            ],
        },
        result={
            "reject_H0": True,
            "significant_posthoc_pairs": sum(row[8] == "True" for row in evidence["posthoc"]),
            "bonferroni_alpha": number(reported(nb1, 10, "Bonferroni 보정 유의수준")),
        },
        interpretation="Notebook 결과를 반올림 정밀도 그대로 보존. p_value_display 0.000000은 "
        "반올림 표기이며 정확한 0이 아님. CSV로 기존 통계만 검산; 새로운 검정/인과 추정 없음",
    )
    add(
        "da_01_external_execution",
        "runtime_requirements",
        NB1,
        [3, 5, 8, 11],
        result={
            "requirement": "SUBMITTED / SENT != EXECUTION_CONFIRMED",
            "not_sufficient_for_final_success": [
                "외부 요청 성공",
                "transaction 제출 성공",
                "tx_hash 확보",
                "blockchain 포함",
            ],
            "required_evidence": "Receipt 또는 동등한 실제 Execution Evidence 확인",
            "unknown_handling": (
                "임의 Success 승격 금지; 기존 BE External Status Query/Recovery 검토"
            ),
            "trace_audit_meanings": [
                "outbound request status",
                "transaction submission status",
                "transaction hash",
                "execution result",
                "execution result confirmed_at",
                "final runtime decision",
                "approval / policy trace reference",
            ],
            "field_name_authority": "BE Contract; 위 목록은 의미 요구이며 새 DB/API 필드가 아님",
            "new_runtime_enums": [],
            "new_runtime_fields": [],
            "new_active_runtime_controls": [],
            "out_of_scope": [
                "KYC",
                "AML",
                "Sanctions",
                "Wallet Risk",
                "VASP Risk",
                "Customer Risk Score",
                "신규 거래 승인 판단",
            ],
            "be_review_areas": [
                "Common Runtime",
                "External Status Query",
                "SENT_UNKNOWN",
                "Recovery",
                "Observability",
                "Audit / Trace",
            ],
            "crosswalk_document": DOC1.as_posix(),
        },
        interpretation=(
            "이미 승인된 Transaction의 외부 실행 결과를 검증·증명. upstream 판단 추가 없음"
        ),
    )
    for artifact in artifacts.values():
        for ref in artifact["evidence_refs"]:
            path = root / ref["path"]
            require(path.is_file(), f"Missing evidence: {ref['path']}")
            if "cell_index" in ref:
                require(
                    ref["cell_index"] < len(notebook(root, Path(ref["path"]))["cells"]),
                    "Evidence cell missing",
                )
    return artifacts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Check frozen artifacts without writing"
    )
    args = parser.parse_args()
    first = ROOT / DA / "artifacts/da_00_master_sample/analysis_summary.json"
    generated_at = (
        json.loads(first.read_text(encoding="utf-8"))["generated_at"]
        if args.check
        else datetime.now(UTC).isoformat()
    )
    artifacts = build_artifacts(generated_at)
    for path, expected in artifacts.items():
        if args.check:
            require(
                json.loads((ROOT / path).read_text(encoding="utf-8")) == expected,
                f"Stale or inconsistent artifact: {path}",
            )
        else:
            (ROOT / path).parent.mkdir(parents=True, exist_ok=True)
            (ROOT / path).write_text(
                json.dumps(expected, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                encoding="utf-8",
            )
    print(
        "PASS: 6 artifacts; CSV/notebook/docs consistency; SHA-256; evidence refs; "
        "73,410 rows; unique 73,410; duplicates 0; missing receipt 0; "
        "existing chi-square and 10 Bonferroni comparisons reproduced."
    )


if __name__ == "__main__":
    main()
