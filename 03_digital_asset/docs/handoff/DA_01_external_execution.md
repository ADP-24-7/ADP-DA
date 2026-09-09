# DA-01 External Execution Contract

DA-01 defines external execution evidence binding for Digital Asset runtime.

## Runtime Phase

Receipt and execution response fields are `POST_EXECUTION` evidence. They are not pre-execution outbound request inputs.

BE must bind external execution evidence by the same transaction identity used for the transaction record.

## Required Separation

Runtime must store these evidence groups separately:

- transaction record
- receipt execution result
- trace internal ETH movement
- token transfer asset movement

Receipt absence, incomplete provider response, or unavailable post-execution evidence must not be silently treated as execution success.

`SUBMITTED` or `SENT` is not `EXECUTION_CONFIRMED`. Connector status, provider response status, receipt status, settlement status, and final runtime decision remain separate meanings until BE maps them explicitly.

## Confirmed Frozen Evidence

Per-type receipt failure rates from the stored DA-01 notebook output:

- Type 0: 1.5000%
- Type 1: 1.0250%
- Type 2: 1.4055%
- Type 3: 0.0250%
- Type 4: 4.7875%
- weighted execution failure rate: 1.4354%

Statistical validation values preserved from the notebook output:

- chi-square: 672.6848
- degrees of freedom: 4
- p-value: 2.8604e-144
- Cramer's V: 0.0957
- minimum expected frequency: 127.39
- expected frequency under 5: 0%

## Decision Semantics

- `PASS`: required post-execution evidence is present and compatible with the approved/requested contract.
- `BLOCK`: required evidence is present and contradicts the approved/requested contract.
- `REVIEW`: evidence is missing, unresolved, provider-specific, or requires analyst/BE-owned mapping.

## Runtime Requirements And Trace

BE must preserve:

- external submission status separately from receipt execution result
- `externalTransactionId` separately from chain `tx_hash` until BE-owned mapping is confirmed
- receipt confirmation time separately from DB record timestamps
- final execution status separately from policy action
- unresolved or pending result states in recovery/reconciliation instead of final success

## Non-blocking Gaps

- provider-specific receipt schema
- execution receipt/status enum
- retry/reconciliation event schema
- audit event schema
- `externalTransactionId` to `tx_hash` mapping
- receipt confirmation timestamp and chain finality mapping
