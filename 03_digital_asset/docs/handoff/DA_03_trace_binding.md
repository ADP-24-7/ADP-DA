# DA-03 Transaction Receipt Trace Transfer Binding

DA-03 defines post-execution evidence binding from transaction to receipt, trace, token transfer, and final execution state.

Transaction Record != Execution Result

Transaction Value != Total Asset Movement

## Confirmed Analysis Result

- Ethereum master sample: 73,410 transactions
- zero-value transactions: 44,422
- DA-03 analysis target: 2026-01 zero-value transactions, 3,452 rows
- receipt binding: 3,452 / 3,452 = 100%
- receipt `status=1`: 3,364
- receipt `status=0`: 88
- token transfer present: 2,131 (61.73%)
- token transfer missing: 1,321
- trace was additionally checked for the 1,321 token-missing transactions
- internal ETH movement present: 102
- token transfer or internal ETH movement present: 2,233 (64.69%)
- neither evidence present: 1,219
- Wilson 95% CI: 63.08% to 66.26%

The 64.69% figure is observed only for the current DA-03 analysis target of 3,452 transactions. It is not an Ethereum population estimate.

## Runtime Rule

Runtime must not conclude:

`transaction_value == 0 -> no asset movement`

Instead, BE must bind the evidence chain by `transaction_hash`:

`Transaction -> Receipt -> Trace / Token Transfer -> Final Execution State`

## Required Evidence Fields

- `transaction_hash`
- `block_number`
- `block_timestamp`
- `transaction_value`
- `receipt_status`
- `trace_present`
- `internal_eth_movement`
- `token_transfer_present`
- `asset_movement_detected`
- `final_execution_state`

## Finalization Order

1. Identify the transaction.
2. Bind the receipt.
3. Determine execution success/failure.
4. Check trace and token transfer evidence.
5. Determine asset movement.
6. Finalize execution state.

Receipt success alone is not total asset-movement proof. Missing trace or token-transfer evidence must remain unresolved until the required post-execution evidence is bound.

When trace and token transfer evidence are both checked and neither shows movement, BE may bind `asset_movement_detected = false` for that finalized evidence state. This must not be inferred from `transaction_value == 0` alone.
