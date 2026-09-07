# BE Handoff AI vNext

## A. AI에서 확정된 것

- Runtime responsibility: FPG validates approved/requested AI handoff readiness; it does not define final business approval or legal judgment.
- Role/workload/purpose binding: EVAL-AI-001 supports Role + Purpose + Action as the binding basis; BE enum values remain CONTRACT_GAP.
- Field requirement: EXACT_REQUIRED, MINIMIZATION_ALLOWED, INTERNAL_ONLY, FORMAT_TRANSFORM_ALLOWED are mapped.
- Transform semantics: intent and method are separate; CONTRACT_GAP is used where final method evidence is insufficient.
- Destination control: model/tool/external destinations are checked separately from FPG trace and audit destinations.
- PASS/BLOCK/REVIEW: PASS means contract satisfied, BLOCK means clear mismatch, REVIEW means unresolved method, threshold, schema, or mapping.
- Trace binding: request, policy evaluation, validation artifact, and response references are required.
- Validation rule: failures are machine-readable with field, destination, rule, and detail.

## B. BE가 구현할 것

- Runtime contract loader
- Policy binding validator
- Transform executor
- Destination payload builder
- Response binding
- Trace writer
- Decision engine

## C. CONTRACT_GAP

- runtime enum
- model provider schema
- tool execution schema
- AI response schema
- audit event schema

## D. ANALYST_DECISION_REQUIRED

- final field-level MASK/HMAC/TOKEN selection
- utility threshold
- model quality threshold
- latency threshold
- failure tolerance
