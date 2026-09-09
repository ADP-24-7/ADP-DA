# Digital Asset P0 Local Product E2E

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
| DA-01 | Do not treat `tx_hash` as success; distinguish SUCCESS/FAILED/UNKNOWN using receipt/finality | `DigitalAssetPostExecutionEvidenceService`, `DigitalAssetSettlementOutcomeHandler`, PR #33 | IMPLEMENTED | Add a local connector trigger that returns a confirmed failed receipt for product E2E. |
| DA-02 | Preserve authoritative atomic amounts as exact strings and compare Approved/Requested/Executed without float | `DigitalAssetAmount`, `ApprovedTransactionBindingEvaluator`, `ExactExecutionAmountResolver`, PR #27/#33 | IMPLEMENTED | None for the canonical P0 path. |
| DA-03 | Bind Approval, Request, Attempt, transaction hash, receipt, transfer/trace and final state | runtime snapshot/guard/post-execution evidence tables and trace endpoints, PR #30/#32/#33 | IMPLEMENTED | Prove the complete chain in the six-case runnable harness. |
| DA-04 | Enforce destination profile fields and fail closed on unsupported/unresolved provider mappings | `DigitalAssetPreExecutionGuard`, destination profile adapter and response guard, PR #32 | IMPLEMENTED | Real provider wire schema remains outside P0. |
| DA-05 | Compare PURPOSE, ASSET, AMOUNT, COUNTERPARTY, DESTINATION and PERIOD with PASS/BLOCK/REVIEW | `ApprovedTransactionResolver`, `ApprovedTransactionBindingEvaluator`, `DigitalAssetPolicyGate`, PR #26/#27 | IMPLEMENTED | Counterparty is represented by the approved beneficiary reference in the current contract. |
| DA-06 | Preserve idempotency, reconcile SENT_UNKNOWN before retry, prohibit blind resend, recover terminal state | runtime idempotency persistence and `ExternalInteractionRecoveryService`, PR #40 | PARTIAL | Local SENT_UNKNOWN fixture currently reconciles connector acknowledgement without recovered receipt/transfer evidence. |

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
| `EXECUTION_FAILED` | PASS | receipt failed | FAILED | Needs a BE local connector/approval trigger |
| `SENT_UNKNOWN_RECOVERED` | PASS | one effect, status query, no resend | EXTERNALLY_RECONCILED | Needs recovered execution evidence in the local trigger |
| `DUPLICATE_REQUEST` | PASS | identical request submitted twice, one connector effect | COMPLETED | Supported |

These are inputs and assertions for the actual BE runtime path. They do not implement a second
policy engine, runtime state machine, evidence store or reconciliation service.

## Validation

```bash
python 03_digital_asset/src/da_p0_local_product_e2e.py --check
python -m pytest 03_digital_asset/tests/test_da_p0_local_product_e2e.py
python scripts/validate_contracts.py
```
