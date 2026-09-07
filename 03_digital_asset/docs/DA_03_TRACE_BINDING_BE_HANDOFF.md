# DA-03 Trace Binding BE Handoff

## 개요

DA-03은 Digital Asset POST_EXECUTION 단계에서 Transaction 단일 레코드만으로 최종 실행 상태와 실제 자산 이동을 확정할 수 없음을 확인한 분석이다. 이 문서는 DA-03 노트북의 실제 실행 결과를 BE Runtime 구현 관점의 handoff contract로 정리한다.

상태:

`FPG DA-03 BE HANDOFF READY WITH NON-BLOCKING GAPS`

## 핵심 원칙

DA-03은 다음 두 명제를 Runtime Contract에 반영한다.

`Transaction Record != Execution Result`

`Transaction Value != Total Asset Movement`

따라서 BE는 `transaction_value == 0`을 근거로 `asset_movement_detected = false`를 즉시 확정하면 안 된다. Transaction, Receipt, Trace, Token Transfer를 동일 `transaction_hash` 기준으로 분리 저장한 뒤 최종 단계에서 binding해야 한다.

## 반영한 분석 Evidence

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

64.69%는 Ethereum 전체 모집단 비율이 아니라 현재 DA-03 분석대상 3,452건에서 관측된 결과다.

## Runtime Evidence Chain

BE Runtime은 POST_EXECUTION 단계에서 다음 순서로 evidence를 binding한다.

1. Transaction 식별
2. Receipt Binding
3. Execution success/failure 판정
4. Trace / Token Transfer Evidence 확인
5. Asset Movement 판정
6. Final Execution State 확정

최종 handoff 구조:

`Transaction -> Receipt -> Trace / Token Transfer -> Final Execution State`

## Evidence Binding Field

DA-03 artifact는 다음 의미를 BE binding 대상으로 고정한다.

- `transaction_hash`
- `block_number`
- `block_timestamp`
- `transaction_value`
- `receipt_status`
- `trace_present`
- `internal_eth_movement`
- `token_transfer_present`
- `asset_movement_detected`
- `final_execution_state`

기존 BE schema에 동일 의미 필드가 있으면 중복 필드를 만들지 않고 기존 필드에 매핑한다. 정확한 enum 이름과 provider-specific schema는 BE-owned contract gap으로 남긴다.

## Runtime Rule

금지되는 판정:

`transaction_value == 0 -> no asset movement`

대신 BE는 다음 규칙을 적용한다.

- Receipt가 없으면 final execution success를 확정하지 않는다.
- Receipt status는 Transaction 기록 여부와 별도로 execution success/failure evidence로 저장한다.
- Token Transfer evidence가 있으면 `transaction_value = 0`이어도 asset movement가 확인된 것으로 처리할 수 있다.
- Token Transfer가 없더라도 Trace에서 internal ETH movement가 확인되면 asset movement가 확인된 것으로 처리할 수 있다.
- Token Transfer와 Internal ETH Movement가 모두 확인되지 않은 경우에도 “절대적 가치이동 없음”이 아니라 “DA-03 범위에서 추가 가치이동 evidence 미확인”으로 trace한다.

## BE 구현 항목

BE는 다음 항목을 구현할 수 있다.

- transaction hash 기반 receipt resolver
- transaction hash 기반 trace resolver
- transaction hash 기반 token transfer resolver
- receipt execution status binder
- trace internal ETH movement detector
- token transfer evidence binder
- asset movement decision builder
- final execution state builder
- missing evidence를 단순 성공으로 확정하지 않는 state/reconciliation 연결
- POST_EXECUTION evidence trace writer

## 기존 DA-01 / DA-02와의 연결

DA-01은 transaction record와 execution result를 분리했다.

DA-02는 approved amount가 outbound 및 executed amount까지 exact하게 보존되어야 함을 정리했다.

DA-03은 DA-01/DA-02 이후 POST_EXECUTION에서 execution evidence와 asset movement evidence를 `transaction_hash` 기준으로 binding한다.

연결 구조:

`DA-01 Execution Result Binding -> DA-02 Amount Exact Preservation -> DA-03 Trace / Token Transfer Binding`

## Non-blocking Gap

- BE-owned final execution state enum
- provider-specific receipt schema
- provider-specific trace schema
- provider-specific token transfer schema
- chain별 trace availability policy
- token standard별 movement schema
- missing evidence reconciliation event schema
- audit event schema

위 항목은 Common Runtime Engine 구현을 막는 blocking issue는 아니다. 다만 미확정 상태에서 BE는 receipt 또는 POST_EXECUTION evidence가 확인되지 않은 거래를 임의로 `PASS` 또는 final success로 확정하지 않아야 한다.

## Evidence Source

- [DA-03 Evidence Summary](handoff/DA_03_trace_binding.md)
- [DA-03 Trace Binding Notebook](../notebooks/runtime_validation/DA_03_trace_binding.ipynb)
- [DA-01 External Execution Contract](handoff/DA-01_EXTERNAL-EXECUTION-CONTRACT.md)
- [DA-02 Exact Preservation BE Handoff](DA_02_EXACT_PRESERVATION_BE_HANDOFF.md)
