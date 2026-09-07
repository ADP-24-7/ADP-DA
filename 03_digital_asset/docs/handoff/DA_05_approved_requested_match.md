## BE Handoff

Backend Runtime에서는 외부 Transaction 제출 이전에 다음 검증을 수행해야 한다.

### 입력

Approval 객체

- `approval_id`
- `approved_asset`
- `approved_max_amount`
- `approved_destination`
- `valid_from`
- `valid_until`

Requested Transaction 객체

- `request_id`
- `requested_asset`
- `requested_amount`
- `requested_destination`
- `requested_at`
- `transaction_type`

### 파생 판정

- `asset_match`
- `amount_match`
- `destination_match`
- `period_match`
- `violation_count`
- `approval_match`

### Decision

- 모든 적용 가능한 Rule 충족 → `PASS`
- 하나 이상의 Rule 위반 → `BLOCK`

### Runtime 처리 기준

1. Approval과 Request를 고유 식별자로 Binding한다.
2. Transaction 구조에 따라 Rule Applicability를 결정한다.
3. 적용 가능한 승인조건을 Field 단위로 비교한다.
4. 하나 이상의 조건이 불일치하면 외부 실행을 수행하지 않는다.
5. 판정 결과와 각 Field Match 결과를 Trace에 기록한다.

Contract Creation처럼 일반적인 Destination이 존재하지 않는 Transaction에서는 Destination Rule을 실패로 처리하지 않고 `N/A`로 명시해야 한다.

또한 `contract_address`와 같이 실행 이후 생성되는 값은 Approval–Request 검증에 사용해서는 안 된다.