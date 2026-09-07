# Digital Asset Candidate Policy v3

Scope: Ethereum transaction-level schema validation, regulatory field mapping, synthetic v3 generation, and candidate policy sensitivity.

## v2 -> v3 Changes

- SNAP Bitcoin OTC is retained only as SUPPORTING_NETWORK_DATA.
- Ethereum mainnet JSON-RPC sample is the MAIN_TRANSACTION_DATA.
- v2 SNAP-based on-chain/derivable ratio is deprecated for the main schema-gap conclusion.
- Ethereum on-chain direct coverage ratio: 0.5
- Ethereum on-chain extended coverage ratio: 0.5833
- Non-chain dependency ratio: 0.3333
- Sample rows: 50000

## Candidate Rule Status

Rules remain candidate-only. On-chain evidence upgraded for address, amount, hash, and timestamp fields; receipt status remains unresolved in the local sample; legal identity, KYC, and counterparty VASP status remain non-chain dependencies.

## Evidence Boundary

Legal basis, actual Ethereum schema evidence, and synthetic policy experiment evidence are separated. No BE handoff or runtime contract is modified.
