# DA-05 Approval Request Match Contract

DA-05 defines runtime comparison between approved Digital Asset intent and requested execution payload.

## Runtime Scope

BE must compare approved/requested values before external execution and preserve exact fields according to [DA_02_exact_preservation.md](DA_02_exact_preservation.md).

The approval/request comparison must remain separate from post-execution evidence binding in [DA_03_trace_binding.md](DA_03_trace_binding.md).

## Required Comparison Dimensions

- purpose
- asset
- amount
- originator
- beneficiary
- destination
- period

Required fixture inputs preserved from the DA-05 notebook and artifacts:

- `approval_id`
- `request_id`
- `approved_max_amount`
- `valid_until`

## Decision Semantics

- `PASS`: approved and requested values match under the active runtime contract.
- `BLOCK`: approved and requested values conflict for an exact or required field.
- `REVIEW`: a mapping, enum, schema, or policy decision is unresolved.

Unresolved mappings must not be converted to `PASS` or `BLOCK` by inference.

## BE Responsibility

- approved transaction loader
- outbound request resolver
- field-level comparison validator
- machine-readable mismatch serializer
- `PASS` / `BLOCK` / `REVIEW` decision emission
