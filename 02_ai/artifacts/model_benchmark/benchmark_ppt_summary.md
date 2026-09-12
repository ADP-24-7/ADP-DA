# 금융 AI 운영 적합성 검증

## 근거

NIST AI RMF / TEVV-aligned operational evaluation. NIST AI 600-1 기반 + NIST AI 200-2 Initial Public Draft 참고 + MLPerf inference metrics. 독립 적합성 평가 또는 MLPerf 결과가 아니다.

## 실험

- 30 Cases × 3 Models × 3 Runs = 270 Executions
- 6 Workload Groups
- 8 Operational Metrics
- Synthetic/non-linkable data only

## 모델별 핵심 결과

| Model | Quality | Mean latency | Tokens | Stability | Compliance | Consistency |
|---|---:|---:|---:|---:|---:|---:|
| Nemotron 3.5 Lightning | 80.2685 | 23611.1129 ms | 296.1 | 91.1111% | 65.5556% | 76.2222 |
| Muse Glimmer 30B | 89.1204 | 13306.4627 ms | 424.3556 | 100.0% | 76.6667% | 87.3333 |
| Gemma 4 31B IT | 84.75 | 8838.8065 ms | 258.2111 | 100.0% | 61.1111% | 81.7778 |

## Trade-off winners

- quality: Muse Glimmer 30B
- latency: Gemma 4 31B IT
- token: Gemma 4 31B IT
- cost: N/A
- stability: Muse Glimmer 30B; Gemma 4 31B IT
- policy: Muse Glimmer 30B
- format: Muse Glimmer 30B; Gemma 4 31B IT
- consistency: Muse Glimmer 30B

## 결론

- 추천 모델: **Gemma 4 31B IT**
- Available-metric weighted score: **79.9397**
- Cost는 공식 per-model API Trial 가격 미확인으로 N/A이며 임의 계산하지 않았다.
- Production Runtime은 `ACTIVE_FAIL_CLOSED / BLOCK`을 유지한다.
- Benchmark 실제 호출은 Production External Execution 승인을 의미하지 않는다.
