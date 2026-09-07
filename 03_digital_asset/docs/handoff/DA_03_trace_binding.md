# DA-03 Trace Binding Evidence Summary

## 목적

DA-03은 Ethereum Transaction 단일 레코드만으로 실제 실행 결과와 가치이동을 판정할 수 있는지 검증한 분석이다. 분석은 Transaction, Receipt, Trace, Token Transfer를 동일 `transaction_hash` 기준으로 연결해 POST_EXECUTION evidence chain이 어떻게 구성되어야 하는지 확인한다.

본 문서는 분석 결과를 요약하는 evidence source이며, BE 구현 지시는 별도 문서인 [DA-03 Trace Binding BE Handoff](../DA_03_TRACE_BINDING_BE_HANDOFF.md)에 정리한다.

## 분석 Evidence

- Ethereum Master Sample: 73,410건
- ZERO_VALUE Transaction: 44,422건
- DA-03 분석대상: 2026-01 ZERO_VALUE Transaction 3,452건
- Receipt Binding: 3,452 / 3,452 = 100%
- Receipt status=1: 3,364건
- Receipt status=0: 88건
- Token Transfer 확인: 2,131건 (61.73%)
- Token Transfer 미확인: 1,321건
- Token 미확인 1,321건에 대해 Trace 추가 조회
- Internal ETH Movement 확인: 102건
- Token Transfer 또는 Internal ETH Movement 확인: 2,233건 (64.69%)
- 둘 다 미확인: 1,219건
- Wilson 95% CI: 63.08% ~ 66.26%

## 설계 결론

DA-03의 핵심 명제는 다음 두 가지다.

`Transaction Record != Execution Result`

`Transaction Value != Total Asset Movement`

따라서 `transaction.value = 0`만으로 가치이동 없음이라고 판단해서는 안 된다. Digital Asset POST_EXECUTION 단계는 동일 `transaction_hash` 기준으로 다음 evidence chain을 구성해야 한다.

`Transaction -> Receipt -> Trace / Token Transfer -> Final Execution State`

64.69%는 Ethereum 전체 모집단 비율이 아니라 현재 DA-03 분석대상 3,452건에서 관측된 결과다.

## Evidence Artifact

- [DA-03 Trace Binding Notebook](../../notebooks/runtime_validation/DA_03_trace_binding.ipynb)
