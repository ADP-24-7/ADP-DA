# DA-00 Master Sample Contract

DA-00 defines the sampled Ethereum transaction evidence used by the Digital Asset handoff chain.

## Confirmed Evidence

- Ethereum master sample size: 73,410 transactions
- zero-value transaction count: 44,422
- DA-03 January 2026 zero-value analysis target: 3,452 transactions
- Type 0 sample allocation: 8,000
- Type 1 sample allocation: 8,000
- Type 2 sample allocation: 41,410
- Type 3 sample allocation: 8,000
- Type 4 sample allocation: 8,000

These values are artifact evidence, not runtime thresholds.

## Runtime Responsibility

BE must preserve the original transaction record separately from execution and asset-movement evidence.

Required identity fields:

- `transaction_hash`
- `block_number`
- `block_timestamp`
- `transaction_value`

DA-00 does not authorize this shortcut:

`transaction_value == 0 -> no asset movement`

The transaction record is only the first evidence source. Runtime finalization must continue through receipt, trace, and token transfer binding where required by the relevant DA contract.

## Source Evidence And Data Provenance

Authoritative DA-00 evidence is the stored notebook output and the processed master CSV:

- `03_digital_asset/notebooks/runtime_validation/DA_00_master_sample.ipynb`
- `03_digital_asset/data/processed/da_master_transaction_sample_73410.csv`

The CSV is a `PROCESSED_ANALYSIS_ARTIFACT`. It is not a BE production transaction source and it is not an active runtime policy.

The original DA-00/DA-01 evidence gap document noted that the notebook's local path and BigQuery session dependencies were preserved as evidence. This consolidation keeps that limitation here rather than treating the sample as fully source-reproducible raw extraction evidence.

## Gap Handling

Sampling coverage, provider availability, and upstream evidence completeness gaps remain non-blocking unless a downstream runtime rule explicitly requires complete evidence for a final decision.

Remaining DA-00 unresolved gaps:

- `client`, `DATASET`, and the original `query_da01_sample` extraction context are not fully stored in this repository.
- BigQuery job ID, fixed query cutoff, random seed, and ordering criteria are not independently available.
- Population statistics are validated against stored notebook output and exported artifact values, not by rerunning the original source extraction.
- Duplicate local copies and unreferenced generated figures are excluded from the active evidence package.
