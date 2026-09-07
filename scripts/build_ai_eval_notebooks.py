"""Build reproducible notebooks; cells consume user-selected bundles or labelled test fixtures."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / "02_ai/notebooks"
SETUP = """import os
import sys
from pathlib import Path

ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "02_ai/src").is_dir())
sys.path.insert(0, str(ROOT / "02_ai/src"))
from adp_da.bundle_analysis import analyze_bundle  # noqa: E402
from adp_da.bundle_dataset import execution_dataframe  # noqa: E402
from adp_da.bundle_loader import load_bundle  # noqa: E402

source = os.environ.get("ADP_AI_BUNDLE_SOURCE")
synthetic = source is None or os.environ.get("ADP_AI_SYNTHETIC") == "1"
if source is None:
    source = str(ROOT / "02_ai/tests/fixtures/evaluation_bundle.synthetic.json")
bundle, metadata = load_bundle(
    source, ROOT / "02_ai/data/interim/ai_evaluation/raw",
    evaluation_run_id=os.environ.get("ADP_AI_EVALUATION_RUN_ID"),
    token=os.environ.get("ADP_BE_TOKEN"),
)
frame = execution_dataframe(bundle)
artifacts = analyze_bundle(
    frame, synthetic=synthetic,
    independent_cases=os.environ.get("ADP_AI_INDEPENDENT_CASES") == "1",
    symmetric_differences=os.environ.get("ADP_AI_SYMMETRIC_DIFFERENCES") == "1",
)
print("SYNTHETIC FIXTURE — SOFTWARE VALIDATION ONLY" if synthetic else "USER-SUPPLIED BUNDLE")
display({k: bundle["manifest"][k] for k in ("bundle_id", "content_digest", "execution_count")})
"""

SPECS = [
    (
        "AI_EVAL_01_bundle_validation",
        "Bundle 독립 검증",
        "BE Producer의 schema, digest, cardinality, provenance와 집계를 DA에서 재검증한다.",
        "모든 실행이 고유 Case×Model 조합이고 섹션 간 연결 및 입력 digest가 일치한다.",
        "manifest, execution_config, case_results, runtime_metrics, failure_summary, trace_index",
        "통계 검정 대신 계약의 결정적 불변조건을 검사한다. 원본 바이트는 별도 보존한다.",
        "모든 검사 PASS만 분석 허용. 실패하면 예외로 중단하며 값 보정은 하지 않는다. "
        "전체 Case 누락은 외부 등록 catalog 없이 판별할 수 없고 digest는 전자서명이 아니다.",
        """display(metadata["validation"])
display(frame[["execution_id", "eval_case_id", "model_profile_id", "expected_input_digest",
               "actual_input_digest", "input_tokens", "output_tokens", "total_tokens"]])
""",
    ),
    (
        "AI_EVAL_02_model_analysis",
        "모델별 운영 결과 비교",
        "동일 Case에서 model profile별 실제 runtime/final_action 결과 분포를 비교한다.",
        "H0: 동일 Case의 모델별 운영 완료 확률이 같다. 모델 품질/Utility 가설은 관측 변수가 없다.",
        "eval_case_id, model_profile_id, runtime_status, final_action, "
        "provider_status, error_category",
        "독립 Case임을 확인한 2모델 binary 비교는 exact McNemar와 paired rate difference. "
        "3모델 이상은 충분한 informative Case에서 Cochran Q. 반복 Case 구조이므로 "
        "독립 표본 Chi-square를 기본 적용하지 않는다. 범주 분포는 기술통계로 제시한다.",
        "검정 가정 미확인은 p-value 보류. 수행한 검정은 Holm 보정과 효과크기로 해석한다. "
        "workload_id와 quality score가 없어 Workload/품질 평가는 불가. "
        "합성 결과는 실증 근거가 아니다.",
        """display(artifacts["model_comparison"])
display(frame.pivot(index="eval_case_id", columns="model_profile_id", values="runtime_status"))
""",
    ),
    (
        "AI_EVAL_03_runtime_analysis",
        "Runtime 안정성 분석",
        "모델 품질과 분리하여 latency, 실패 및 token 관측 범위를 분석한다.",
        "H0: 동일 Case에서 full-response latency의 모델 간 paired 분포 차이가 없다.",
        "measurement_type, full_response_latency_millis, attempt_elapsed_millis, "
        "initial_runtime_latency_millis, provider_http_status, provider_status, "
        "token_usage_status와 token 수",
        "타입별 mean/median/P95/P99 및 성공·실패 strata. MOCK 0과 attempt는 실제 full response와 "
        "합치지 않는다. 2모델은 독립 Case 및 대칭 차이 확인 시 Wilcoxon+rank-biserial. "
        "3모델 이상 Friedman은 근사 유효성 조건 충족 시에만 실행하며 Kendall W를 표시한다.",
        "완전한 paired Case 수와 제외 수를 표시한다. 작은 표본의 P99는 SLA가 아니다. "
        "NOT_ATTEMPTED와 결측 token은 실패/0 token으로 일괄 치환하지 않는다. "
        "TRANSPORT에는 timeout 외 오류도 있으므로 timeout 비율은 평가 불가.",
        """display(artifacts["runtime_analysis"])
display(artifacts["failure_analysis"])
""",
    ),
    (
        "AI_EVAL_04_policy_effect_analysis",
        "Policy / Transform 평가 가능성",
        "Policy 강화의 Privacy–Utility–Runtime tradeoff를 현재 Bundle로 식별 가능한지 확인한다.",
        "H0: 같은 Case·Model·sampling 조건에서 Policy/Transform 개입의 결과 차이가 없다.",
        "policy_snapshot_digest, model_profile_id, final_action 및 현재 존재하는 runtime 변수",
        "먼저 처치 조건과 대조군, privacy/utility outcome, pairing 설계를 확인한다. "
        "모델 profile은 policy treatment가 아니다. "
        "v1에는 한 policy snapshot만 있어 인과 검정하지 않는다.",
        "NOT EVALUABLE WITH CURRENT BUNDLE. Final action은 실행 결과이지 랜덤 처치가 아니다. "
        "없는 Utility, privacy 점수나 transform 강도를 생성하지 않는다. 추가 실험을 명시한다.",
        """display(artifacts["policy_effect_analysis"])
display(artifacts["evaluation_summary"]["decision_candidates"])
display(artifacts["evaluation_summary"]["handoff_gaps"])
""",
    ),
]


def main() -> None:
    for name, title, purpose, hypothesis, variables, method, interpretation, code in SPECS:
        markdown = (
            f"# {title}\n\n## 분석 목적\n{purpose}\n\n## 가설\n{hypothesis}\n\n"
            f"## 사용할 변수\n{variables}\n\n## 통계기법 선택 이유\n{method}\n\n"
            f"## 해석 기준\n{interpretation}\n\n"
            "기본 입력은 **합성 Consumer 시험 fixture**이다. 실제 Bundle은 "
            "`ADP_AI_BUNDLE_SOURCE`로 지정한다. Case 독립성/대칭성은 자동 추정하지 않는다.\n"
        )
        cells = [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": markdown,
                "id": name.lower() + "-intro",
            }
        ]
        for index, source in enumerate((SETUP, code)):
            cells.append(
                {
                    "cell_type": "code",
                    "metadata": {},
                    "source": source,
                    "id": name.lower() + f"-{index}",
                    "execution_count": None,
                    "outputs": [],
                }
            )
        notebook = {
            "nbformat": 4,
            "nbformat_minor": 5,
            "cells": cells,
            "metadata": {
                "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
                "language_info": {"name": "python", "version": "3.12"},
            },
        }
        (NOTEBOOKS / (name + ".ipynb")).write_text(
            json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
