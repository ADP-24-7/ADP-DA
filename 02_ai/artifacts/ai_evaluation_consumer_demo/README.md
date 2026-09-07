# AI Evaluation Consumer 검증 결과

**합성 fixture 전용 결과입니다. 실제 BE Export 또는 모델 성능 실험 결과가 아닙니다.**

입력: `02_ai/tests/fixtures/evaluation_bundle.synthetic.json`

- 8 Case × 2 model profile = 16 execution
- Snapshot: `sha256:ed159d36cd3f7bfa47d0f05b4cd4334b9b2a09c15af14128b9baff6f5036501b`
- HTTP_FULL_RESPONSE / HTTP_ATTEMPT_NO_RESPONSE / NOT_ATTEMPTED / MOCK 분기 포함
- 원본 응답은 `raw/`에 보존

Git에는 검토용 JSON/보고서와 입력 fixture를 포함합니다. 중복 raw 사본과 생성된
Parquet는 로컬에 보존하되 commit에서 제외합니다. Notebook 출력도 재실행으로 생성하며,
실행 방법은 `02_ai/docs/AI_EVALUATION_CONSUMER.md`를 따릅니다.

## 기본 분석

[DA 보고서](ed159d36cd3f7bfa47d0f05b4cd4334b9b2a09c15af14128b9baff6f5036501b/synthetic-1_independent-0_symmetric-0/AI_EVALUATION_DA_REPORT.md)

Case 독립성은 Bundle에서 확인할 수 없어 기본 분석의 추론 검정은 보류합니다.
모델별 상태 분포, Case 비교, 측정 유형별 latency, token 및 실패 집계와
각 검정의 보류 이유를 보존합니다.

## 통계기법 실행 예제

[통계기법 검증용 보고서](ed159d36cd3f7bfa47d0f05b4cd4334b9b2a09c15af14128b9baff6f5036501b/synthetic-1_independent-1_symmetric-1/AI_EVALUATION_DA_REPORT.md)

합성 데이터에서만 독립성·대칭성 옵션을 명시적으로 켜서 알고리즘 경로를 실행했습니다.

| 검정 | paired Case | raw p | Holm p | 효과크기 |
|---|---:|---:|---:|---|
| Exact McNemar, 운영 완료 여부 | 7 | 0.5 | 0.5 | paired rate difference −0.285714 |
| Wilcoxon, full-response latency | 5 | 0.0625 | 0.125 | matched rank-biserial −1.0 |

위 수치는 fixture 설계에 따른 결과로 실제 모델에 대한 결론을 지지하지 않습니다.
Cochran Q와 Friedman 경로는 별도 합성 단위 테스트에서 확인합니다.

각 분석 디렉터리에 요청한 JSON 5종, `validation.json`, `executions.parquet`,
`AI_EVALUATION_DA_REPORT.md`가 있습니다. `evaluation_summary.json`에
Decision Candidate 6종과 기존 Handoff Gap 6개 항목의 연결 표를 포함합니다.

Utility와 Policy/Transform 효과는 **NOT EVALUABLE WITH CURRENT BUNDLE**입니다.
모델 allowlist, latency/failure 기준, REVIEW 정책도 확정하지 않았습니다.
실제 Export 검증과 대표성 있는 반복 실험·품질 라벨·DA 판단이 필요합니다.
