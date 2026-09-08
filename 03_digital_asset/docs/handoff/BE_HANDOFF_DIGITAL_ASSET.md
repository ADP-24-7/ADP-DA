# Digital Asset BE Handoff

Status: `FPG BE HANDOFF READY WITH NON-BLOCKING GAPS`

This is the active Digital Asset runtime handoff index. Historical V2/V3/vNext PR documents were consolidated here so BE can implement from one current contract set without following PR-level document history.

## Runtime Contract Scope

Digital Asset runtime uses the common FPG control flow:

1. Resolve source phase and source type.
2. Validate approved/requested/runtime evidence fields.
3. Apply only allowed transform semantics.
4. Build destination-specific payloads.
5. Bind post-execution response evidence.
6. Emit `PASS`, `BLOCK`, or `REVIEW`.
7. Write trace and validation errors.

The domain-specific rule is:

`Transaction Record != Execution Result`

`Transaction Value != Total Asset Movement`

Runtime must bind evidence by `transaction_hash` and finalize execution state only after the relevant post-execution evidence is available.

## Active Documents

- [DA_00_master_sample_contract.md](DA_00_master_sample_contract.md)
- [DA_01_external_execution.md](DA_01_external_execution.md)
- [DA_02_exact_preservation.md](DA_02_exact_preservation.md)
- [DA_03_trace_binding.md](DA_03_trace_binding.md)
- [DA_04_outbound_destination.md](DA_04_outbound_destination.md)
- [DA_05_approval_request_match.md](DA_05_approval_request_match.md)
- [DA_06_recovery_idempotency.md](DA_06_recovery_idempotency.md)

## BE Implementation Scope

- Common Runtime Contract loader
- source resolver
- policy validator
- field requirement validator
- transform executor
- destination payload builder
- `PASS` / `BLOCK` / `REVIEW` decision engine
- trace writer
- validation error serializer
- external execution response binding
- recovery and idempotency adapter

## Non-blocking Contract Gaps

These remain BE-owned or adapter-owned contract gaps. They must not be filled with inferred domain, legal, chain-specific, or provider-specific rules in the FPG analysis layer.

- runtime enum
- approved transaction schema
- approved policy snapshot schema
- provider-specific payload schema
- execution receipt/status schema
- retry/reconciliation event schema
- audit event schema

