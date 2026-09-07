# DA-02 Exact Preservation BE Handoff

## 개요

DA-02는 Digital Asset Amount가 FLOAT64 처리 과정에서 원값 그대로 보존되지 않을 수 있음을 실증한 분석이다. 이 문서는 DA-02 분석 결과를 BE Runtime 구현 관점의 architecture contract로 변환한다.

현재 Digital Asset vNext의 공통 Runtime Contract는 이미 `amount`를 `EXACT_REQUIRED`로 분류하고 `PASS_THROUGH`만 허용한다. 따라서 이번 반영은 새로운 법률/금융 판단을 추가하지 않고, 기존 Amount 책임을 `amount_atomic` 중심의 exact-safe runtime binding으로 구체화한다.

상태:

`FPG DA-02 BE HANDOFF READY WITH NON-BLOCKING GAPS`

## 반영한 분석 Evidence

- Ethereum Master Sample: 73,410건
- BigQuery 원본 Amount 매칭 및 분석 대상: 73,266건
- Decimal Exact Preservation: 100.0000%
- FLOAT64 Precision Loss: 3,280건
- 전체 FLOAT64 Precision Loss Rate: 4.4768%
- Positive Amount 기준 Precision Loss Rate: 11.3287%
- `2^53` 이하: 16,784건 / Precision Loss 0건
- `2^53` 초과: 12,169건 / Precision Loss 3,280건 / 손실률 26.9537%
- 최대 절대오차: 351,232 wei
- Fisher's Exact Test p-value: 0
- Haldane-Anscombe corrected OR: 12,387.9976
- Risk Difference: 26.9537%p

중요 해석:

DA-02는 `2^53` 이상 거래를 차단하기 위한 분석이 아니다. FLOAT64에서 Amount 원값 보존이 보장되지 않음을 실증하여, Digital Asset Amount를 Runtime 전체에서 exact-safe canonical representation으로 처리해야 한다는 설계 근거를 제공한다.

## 기존 DA Architecture와의 연결

DA-01은 `Transaction Record != Execution Result`를 확정했다. DA-02는 여기에 Amount exact preservation을 추가한다.

Runtime 흐름은 다음과 같이 연결된다.

1. Approval Policy
2. Canonical Amount Binding
3. Pre-Execution Exact Validation
4. External Execution
5. Post-Execution Amount Binding
6. State / Reconciliation
7. Audit Trace

핵심 분리:

- 거래가 기록되었다는 사실과 실행 결과는 별도로 검증한다.
- 승인된 Amount가 outbound 및 실제 실행까지 정확히 유지되었는지도 별도로 검증한다.

## Canonical Amount 설계

Digital Asset Amount의 Runtime canonical value는 자산 최소단위의 exact value여야 한다.

Ethereum 기준 예시는 다음과 같다.

- `amount_atomic = "1000000000000000000"`
- `amount_display = "1.0"`
- `decimal_scale = 18`

BE Runtime 판단, 비교, trace, 외부 실행 검증은 `amount_display`가 아니라 `amount_atomic`을 기준으로 수행한다.

구현 원칙:

- FLOAT64 / double은 canonical amount 저장, 비교, 전송 타입으로 사용하지 않는다.
- JSON/API 경계에서 integer precision 보장이 불명확하면 `amount_atomic`은 integer string으로 전달한다.
- `amount_display`는 UI/표시용 값이며 runtime decision의 기준값이 아니다.
- token별 decimal scale은 provider/token schema가 확정된 뒤 contract에 연결한다.

## PRE_EXECUTION Exact Guard

외부 실행 직전 BE Runtime은 승인된 canonical amount와 outbound canonical amount가 동일한지 검증해야 한다.

필수 조건:

`approved_amount_atomic == outbound_amount_atomic`

불일치 시:

- 외부 실행을 진행하지 않는다.
- Runtime decision은 `BLOCK`이다.
- BLOCK 사유는 approved/requested 또는 approved/outbound exact mismatch로 직렬화한다.

이 검증은 단순 schema validation이 아니다. 승인된 값이 execution boundary까지 그대로 보존되었는지 확인하는 exact preservation guard이다.

## POST_EXECUTION Amount Binding

외부 실행 결과에서 실제 실행 Amount를 확인할 수 있는 경우 BE Runtime은 다음 조건을 검증해야 한다.

`approved_amount_atomic == executed_amount_atomic`

주의:

- provider HTTP 성공 또는 transaction submission 성공만으로 exact preservation 성공으로 판단하지 않는다.
- `tx_hash`, `execution_status`, `timestamp`는 DA-01 기준에 따라 POST_EXECUTION `EXTERNAL_EXECUTION_RESPONSE`에서 binding한다.
- 실행 Amount 확인이 불가능한 경우 임의로 `PASS`를 확정하지 않고, 기존 DA Runtime의 state/reconciliation semantics에 맞춰 `REVIEW`, `PENDING`, `UNKNOWN` 계열 상태로 연결한다.
- 새로운 enum 이름은 BE-owned runtime enum gap이므로 이 문서에서 임의 확정하지 않는다.

## Trace / Evidence 요구사항

Audit trace는 최소한 다음 관계를 증명할 수 있어야 한다.

- approved amount
- outbound amount
- executed amount 또는 확인 가능한 execution evidence
- asset
- decimal scale
- exact validation result

권장 field mapping:

- `asset`
- `amount_atomic`
- `amount_display`
- `decimal_scale`
- `exact_required`
- `approved_amount_atomic`
- `outbound_amount_atomic`
- `executed_amount_atomic`
- `exact_validation_result`

기존 schema/contract에 동일 의미 필드가 이미 있으면 중복 필드를 만들지 않고 기존 필드에 매핑한다.

## Contract / Schema 변경 여부

이번 반영에서는 기존 Digital Asset vNext runtime contract를 대규모 변경하지 않는다.

기존 contract에서 확인된 사항:

- `amount`는 `EXACT_REQUIRED`이다.
- `amount` outbound transform은 `PASS_THROUGH`만 허용된다.
- `amount` destination은 `BLOCKCHAIN_EXECUTION_SYSTEM` 및 `INTERNAL_RECONCILIATION_ONLY`로 분리되어 있다.
- `amount`는 PRE_EXECUTION approved/requested comparison 대상이다.

DA-02가 추가로 구체화한 사항:

- BE 구현에서 `amount`의 runtime representation은 `amount_atomic` 기준이어야 한다.
- `amount_display`는 표시값이며 decision 기준값이 아니다.
- POST_EXECUTION에서 실행 Amount 확인이 가능하면 `executed_amount_atomic`을 approved canonical amount와 비교해야 한다.

신규 schema field는 이번 PR에서 강제하지 않는다. provider-specific payload schema, execution receipt/status schema, token decimal schema가 BE contract로 확정될 때 `amount_atomic`, `amount_display`, `decimal_scale`, `executed_amount_atomic`의 최종 필드명을 확정한다.

## BE 구현 항목

BE는 다음을 구현할 수 있다.

- canonical amount parser
- integer string 기반 `amount_atomic` transport
- FLOAT64/double canonical amount 사용 금지 검증
- PRE_EXECUTION `approved_amount_atomic == outbound_amount_atomic` guard
- POST_EXECUTION `approved_amount_atomic == executed_amount_atomic` binding 및 검증
- exact mismatch validation error serializer
- amount evidence trace writer
- DA-01 execution result binding과 DA-02 amount binding의 reconciliation 연결

## Non-blocking Gap

- BE-owned runtime enum
- provider-specific payload schema
- execution receipt/status schema
- token-specific decimal scale schema
- reconciliation event schema
- audit event schema
- executed amount을 제공하지 않는 provider의 상태 전이 정책

위 항목은 Common Runtime Engine 구현을 막지 않는다. 다만 미확정 상태에서는 임의로 `PASS`를 확정하지 않고 기존 `REVIEW` 또는 BE-owned pending/unknown 상태와 연결해야 한다.

## Evidence Source

- [DA-02 Evidence Summary](handoff/DA_02_exact_preservation.md)
- [DA-02 Exact Preservation Notebook](../notebooks/runtime_validation/DA_02_exact_preservation.ipynb)
- [DA-01 External Execution Contract](handoff/DA-01_EXTERNAL-EXECUTION-CONTRACT.md)
- [Digital Asset vNext BE Handoff](BE_HANDOFF_DIGITAL_ASSET_VNEXT.md)
