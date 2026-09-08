# DA-02 Exact Preservation Contract

DA-02 defines exact preservation requirements for Digital Asset fields that must not be altered by outbound transforms.

## Core Rule

`EXACT_REQUIRED` means the runtime value must preserve the approved/requested value exactly for the applicable comparison contract.

`PASS_THROUGH` means the value itself is not changed. It does not mean the value must be externalized.

External payload inclusion is decided by destination policy and the payload builder, not by `PASS_THROUGH` alone.

DA-02 is not a threshold blocking policy for transactions at or above `2^53`. The analysis validates exact preservation risk and runtime comparison requirements.

FLOAT64 / double must not be used as the canonical amount storage, comparison, or transfer type.

Required runtime comparisons:

- `approved_amount_atomic == outbound_amount_atomic`
- `approved_amount_atomic == executed_amount_atomic`

New enum names remain a BE-owned runtime enum gap.

## Transform Semantics

For `EXACT_REQUIRED` fields, outbound transforms are limited to non-mutating behavior unless a contract explicitly allows otherwise.

Lossy or value-changing transforms are not allowed for exact-preservation fields:

- `MASK`
- `HMAC`
- `TOKENIZE`
- `REDACT`
- lossy `FORMAT_NORMALIZE`

Comparison-time canonicalization must be modeled separately from outbound payload mutation. Chain-specific or legal/financial normalization rules that are not explicitly defined remain `CONTRACT_GAP` or `ANALYST_DECISION_REQUIRED`.

## Protected Field Examples

- amount
- asset
- originator address
- beneficiary address
- transaction identifier
- tx hash
- timestamp
- execution status

## Runtime Outcome

- exact match: `PASS`
- value mismatch: `BLOCK`
- unresolved mapping or missing approved/requested evidence: `REVIEW`
