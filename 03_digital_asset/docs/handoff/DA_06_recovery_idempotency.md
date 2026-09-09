# DA-06 Recovery Idempotency Contract

DA-06 defines retry, replay, recovery, and reconciliation responsibilities for Digital Asset runtime.

## Core Rule

Recovery must be idempotent. BE must avoid duplicate external execution while allowing unresolved or partial evidence to be reconciled after execution.

## Runtime Responsibilities

- bind retry/replay attempts to the original trace identifier
- distinguish internal trace identifiers from external execution result identifiers
- preserve post-execution evidence from receipt, trace, and token transfer binding
- emit machine-readable recovery state and validation errors
- reconcile final state without inventing missing provider evidence

## Decision Semantics

- `PASS`: recovery evidence confirms the approved/requested/runtime contract.
- `BLOCK`: recovery evidence contradicts the contract or duplicate execution risk is confirmed.
- `REVIEW`: provider evidence, retry state, receipt state, or reconciliation state is unresolved.

## Non-blocking Gaps

- retry event schema
- reconciliation event schema
- provider adapter idempotency key behavior
- audit event schema
