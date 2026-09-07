# DA-02 Exact Preservation Evidence Summary

## 목적

DA-02는 Ethereum 거래의 Amount가 데이터 처리 과정에서 원값 그대로 보존되는지 검증한 분석이다. 기준 표본은 Ethereum Master Sample 73,410건이며, `transaction_hash`를 기준으로 BigQuery 원본 `value`를 다시 조회하여 wei 단위의 exact ground truth를 확보했다.

본 문서는 분석 결과를 요약하는 evidence source이며, BE 구현 지시는 별도 문서인 [DA-02 Exact Preservation BE Handoff](../DA_02_EXACT_PRESERVATION_BE_HANDOFF.md)에 정리한다.

## 분석 Evidence

- Ethereum Master Sample: 73,410건
- BigQuery 원본 Amount 매칭 및 분석 대상: 73,266건
- Decimal Exact Preservation: 100.0000%
- FLOAT64 Precision Loss: 3,280건
- 전체 FLOAT64 Precision Loss Rate: 4.4768%
- Positive Amount: 28,953건
- Positive Amount 기준 Precision Loss Rate: 11.3287%
- FLOAT64 연속 정수 정확 표현 경계: `2^53 = 9,007,199,254,740,992 wei`
- `2^53` 이하: 16,784건 / Precision Loss 0건
- `2^53` 초과: 12,169건 / Precision Loss 3,280건 / 손실률 26.9537%
- 최대 절대오차: 351,232 wei
- Fisher's Exact Test p-value: 0
- 원자료 Odds Ratio: infinity
- Haldane-Anscombe corrected OR: 12,387.9976
- Risk Difference: 26.9537%p

## 설계 결론

DA-02는 `2^53` 이상 Amount를 차단하기 위한 분석이 아니다.

분석 결론은 Digital Asset Amount 전체를 FLOAT64로 처리하지 않고, Runtime 전 구간에서 exact-safe canonical representation으로 처리해야 한다는 것이다.

즉 FPG Runtime은 승인값, outbound 값, 실행 결과 값을 비교할 때 표시용 decimal 값이 아니라 자산 최소단위의 canonical amount를 기준으로 해야 한다.

## Evidence Artifact

- [DA-02 Exact Preservation Notebook](../../notebooks/runtime_validation/DA_02_exact_preservation.ipynb)
