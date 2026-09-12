# Digital Asset P0 Local Product E2E

Status: `DIGITAL ASSET DA-01~DA-06 FINAL VALIDATED`

## Final closure on 2026-09-12

ADP-BE PR [#59](https://github.com/ADP-24-7/ADP-BE/pull/59) executed all six
canonical DA fixtures through the existing Runtime API and PostgreSQL path. The original closure
suite passed 548 tests with zero failures; after merging the latest BE main, the final regression
passed 562 tests with zero failures and one skipped test. The locked demo integration passed with
BE, DA, FE, Docs, PostgreSQL, and Flyway V52 healthy. No DA fixture, analysis statistic, BE
production class, or migration was changed for this validation.

The final Runtime flow is fixed as:

`Approval`
→ `Requested Transaction`
→ `Pre-Execution Policy Guard`
→ `External Execution`
→ `Execution Evidence`
→ `Reconciliation`
→ `Final State`
→ `Decision Trace`
→ `Admin Operations`

| DA Evidence | Validated flow segment |
| --- | --- |
| DA-01 | External Execution → Execution Evidence → Final State |
| DA-02 | Approval → Requested Transaction → Guard → Execution Evidence |
| DA-03 | Approval → Request → Attempt/Evidence → Final State → Decision Trace |
| DA-04 | Approved Destination → Guard → External Execution boundary |
| DA-05 | Approval → Requested Transaction → PASS/BLOCK |
| DA-06 | External Execution → Reconciliation → Final State → Admin Operations |

## BE work boundary reviewed on 2026-09-10

| PR | State | BE-owned scope | DA impact |
| --- | --- | --- | --- |
| #42 | OPEN | Policy Operations Read Model and FE read integration | Do not add DA read APIs or duplicate lifecycle/history queries. |
| #41 | MERGED | Reference Evidence registry, validation, persistence, admin trace read plane | Reuse its evidence ingestion contract; DA supplies evidence references. |
| #40 | MERGED | PostgreSQL recovery worker, review/retry/reconcile APIs, status query and safe retry | Fixtures assert reconcile-first and no blind resend. |
| #38 | MERGED | Prometheus, alerts, structured logging, Operations Monitoring read model | Do not add DA metrics or monitoring APIs. |
| #36 | MERGED | Policy activation, current selection and rollback | Fixtures target the active server-owned selection. |
| #35/#34 | MERGED | Shadow evidence and approval gate | Do not model lifecycle state in DA artifacts. |
| #33 | MERGED | Post-execution receipt/finality/transfer/trace evidence | Fixtures declare expected evidence and final state. |
| #32 | MERGED | Six-control pre-execution guard and trace evidence | Fixtures declare PASS/BLOCK before connector execution. |
| #31/#29 | MERGED | NCP/local bundle content store, validation and CANDIDATE ingestion | Keep the frozen Bundle v1 wire contract unchanged. |
| #30 | MERGED | Versioned runtime snapshot and active artifact selection | Fixtures bind to the existing Digital Asset Bundle identity. |
| #28/#27 | MERGED | Canonical contract and approved/requested domain contracts | Runtime request payloads reuse the exact BE field names and string amounts. |

PR #43 is the AI Evaluation Contract runtime and does not own Digital Asset fixture behavior.

## DA-01 through DA-06 gap matrix

| DA Evidence | DA Runtime Requirement | BE implementation location | Status | Remaining work |
| --- | --- | --- | --- | --- |
| DA-01 | Do not treat `tx_hash` as success; distinguish SUCCESS/FAILED/UNKNOWN using receipt/finality | `EXECUTION_FAILED`: transaction hash present, independent receipt `FAILED`, final state `FAILED` | VALIDATED | None for the canonical local P0 path. |
| DA-02 | Preserve authoritative atomic amounts as exact strings and compare Approved/Requested/Executed without float | String atomic values, exact comparison and persisted exact-amount digest verified | VALIDATED | None for the canonical local P0 path. |
| DA-03 | Bind Approval, Request, Attempt, transaction hash, receipt, transfer/trace and final state | One execution/trace binds snapshot, guard, connector, independent evidence, reconciliation and final state | VALIDATED | None for the canonical local P0 path. |
| DA-04 | Enforce destination profile fields and fail closed on unsupported/unresolved provider mappings | `BLOCK_DESTINATION`: server-owned destination mismatch blocked before provider/connector; external effect 0 | VALIDATED | Real-provider wire schema remains outside local P0. |
| DA-05 | Compare PURPOSE, ASSET, AMOUNT, COUNTERPARTY, DESTINATION and PERIOD with PASS/BLOCK/REVIEW | Amount/destination mismatches blocked with effect 0; PASS fixtures alone execute | VALIDATED | Counterparty remains the approved beneficiary reference in this contract. |
| DA-06 | Preserve idempotency, reconcile SENT_UNKNOWN before retry, prohibit blind resend, recover terminal state | Reconcile-first recovery and duplicate replay each retain one total external effect | VALIDATED | Real-provider idempotency behavior remains adapter scope. |

## Final Validation Matrix

| DA Evidence | Runtime Requirement | BE Runtime Result | Actual | Final |
| --- | --- | --- | --- | --- |
| DA-01 | Transaction != Execution Result | Receipt/Evidence judgment | Failed receipt overrides transaction-hash presence; `FAILED` | VALIDATED |
| DA-02 | Exact Preservation | Lossless Exact Amount | Approved/requested/executed atomic strings and exact digest preserved | VALIDATED |
| DA-03 | Trace Binding | Approval → Final State | Execution ID binds snapshot, attempt, evidence, reconciliation, final trace | VALIDATED |
| DA-04 | Destination Control | Pre/Outbound Guard | Server-owned mismatch blocked; connector/provider/effect 0 | VALIDATED |
| DA-05 | Approved vs Requested | PASS/BLOCK | Amount and destination mismatch block; matching cases execute | VALIDATED |
| DA-06 | Recovery / Idempotency | SENT_UNKNOWN / Reconciliation | No blind retry, reconcile-first, immutable snapshot, one-effect replay | VALIDATED |

## Canonical Bundle assessment

The Bundle v1 manifest already binds artifact/version/schema/digests. Its five documents carry the
active workload/purpose/destination binding, PASS/BLOCK/REVIEW semantics, exact preservation,
destination controls, trace binding and ordered runtime stages. The BE consumer uses an exact
five-role schema with `additionalProperties: false`, so DA cannot add reason-code or recovery
fields without a coordinated Bundle v2 change in BE.

The Bundle v1 bytes remain unchanged to preserve current ingestion compatibility. Explicit
reason-code and recovery expectations live in the DA-owned Local Product E2E fixture contract.
This avoids defining BE runtime tables, lifecycle state or APIs in a DA artifact.

## Deterministic fixtures

All files under `artifacts/local_product_e2e_v1` use `source=SYNTHETIC`, contain the exact BE
Runtime API request shape, bind DA evidence, and include a SHA-256 digest over canonical JSON
excluding `content_digest`.
The runner must replace `${CURRENT_UTC_ISO8601}` immediately before submission and supply the
local API credential from the environment; no credential is stored in a fixture.

| Fixture | Pre-execution | External/recovery result | Final state | Current BE local support |
| --- | --- | --- | --- | --- |
| `GOLDEN_PASS` | PASS | settled, receipt success, finalized, evidence verified | COMPLETED | Supported |
| `BLOCK_AMOUNT` | BLOCK | connector not called | BLOCKED | Supported |
| `BLOCK_DESTINATION` | BLOCK | connector not called | BLOCKED | Supported |
| `EXECUTION_FAILED` | PASS | receipt failed | FAILED | Supported and validated by BE PR #59 |
| `SENT_UNKNOWN_RECOVERED` | PASS | one effect, status query, no resend | EXTERNALLY_RECONCILED | Supported and validated by BE PR #59 |
| `DUPLICATE_REQUEST` | PASS | identical request submitted twice, one connector effect | COMPLETED | Supported |

These are inputs and assertions for the actual BE runtime path. They do not implement a second
policy engine, runtime state machine, evidence store or reconciliation service.

The two frozen fixture `runtime_support` strings retain their generation-time capability markers
because changing them would alter canonical fixture bytes and digests. Current support is
authoritatively recorded by this validation matrix and BE PR #59 evidence.

## Validation

```bash
python 03_digital_asset/src/da_p0_local_product_e2e.py --check
python -m pytest 03_digital_asset/tests/test_da_p0_local_product_e2e.py
python scripts/validate_contracts.py
```
