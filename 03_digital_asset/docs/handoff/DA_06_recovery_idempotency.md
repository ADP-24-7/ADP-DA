## 9. BE Handoff

DA-06 결과를 기반으로 BE Runtime은 다음 항목을 구현해야 한다.

### 필수 저장 필드

- `request_id`
- `idempotency_key`
- `external_transaction_id`
- `submission_status`
- `execution_status`
- `reconciliation_status`
- `retry_count`
- `parent_request_id`
- `created_at`
- `last_checked_at`

### 필수 제약

1. 동일 `idempotency_key`의 중복 요청 감지
2. 기존 `external_transaction_id` 존재 여부 확인
3. `SENT_UNKNOWN` 발생 시 즉시 재전송 금지
4. 기존 외부 Transaction 상태 조회 우선
5. 조회 결과와 내부 상태 Reconciliation
6. `FINALIZED` Transaction 재전송 차단
7. Retry 발생 시 기존 요청과 lineage 유지
8. 모든 상태 전이를 Audit Trace에 기록

### 상태 규칙

`SENT_UNKNOWN → RETRY`

직접 전이는 금지한다.

허용되는 기본 경로는:

`SENT_UNKNOWN`
→ `RECONCILING`
→ `FINALIZED`

또는

`SENT_UNKNOWN`
→ `RECONCILING`
→ `FAILED`
→ `RETRY_ELIGIBLE`

또는

`SENT_UNKNOWN`
→ `RECONCILING`
→ `RECONCILIATION_REQUIRED`

이다.