# BE Handoff Digital Asset V2

## 1. FPG Digital Asset Role

FPG is a policy enforcement gateway for already-approved digital asset transactions immediately before external execution handoff. PASS means outbound handoff requirements are satisfied; it is not transaction approval.

## 2. Out Of Scope

FPG does not perform KYC/AML, wallet signing, custody, smart-contract execution, settlement, or settlement finality.

## 3. Approved Transaction Input Layer

BE must provide approved transaction id, policy snapshot id, requested asset, amount, destination, source/destination address where applicable, and runtime context. Missing BE-owned identifiers remain CONTRACT_GAP.

## 4. Legal Obligation To Outbound Requirement

Current matrix rows: 18. Legal obligations are separated from internal approval and execution requirements so legal basis is not invented.

## 5. Required Field

amount, asset, beneficiary_address, beneficiary_identity, counterparty_vasp, execution_status, kyc_status, originator_address, originator_identity, timestamp, transaction_id, tx_hash

## 6. Source System

{"VASP_DIRECTORY_OR_PROVIDER": 1, "TRAVEL_RULE_PROVIDER": 3, "KYC_AML_SYSTEM": 2, "INTERNAL_CUSTOMER_MASTER": 4, "APPROVED_TRANSACTION": 6, "BLOCKCHAIN_EXECUTION_LAYER": 7, "EXTERNAL_EXECUTION_RESPONSE": 5, "INTERNAL_POLICY_STORE": 1}

## 7. Transform

{"MAP_TO_EXTERNAL_SCHEMA": 5, "SPLIT_INTERNAL_EXTERNAL": 1, "OMIT": 2, "MINIMIZE": 4, "PASS_THROUGH": 7, "FORMAT_NORMALIZE": 4}

## 8. Destination

{"TRAVEL_RULE_PROVIDER": 8, "EXTERNAL_VASP": 5, "INTERNAL_AUDIT_ONLY": 7, "NOT_EXTERNALIZED": 2, "INTERNAL_RECONCILIATION_ONLY": 10, "BLOCKCHAIN_EXECUTION_SYSTEM": 4}

## 9. PASS / BLOCK / REVIEW

- PASS: current outbound handoff requirements are satisfied.
- BLOCK: approved transaction may exist, but outbound handoff cannot proceed in the current state.
- REVIEW: required internal/external information is pending, missing, unresolved, or ambiguous.

## 10. Runtime Pipeline

1. Approved Transaction Load - load and validate presence only
2. Policy Snapshot Load - load current snapshot reference
3. Regulatory Context Load - select candidate requirements
4. External Status Load - consume status result only
5. Required Field Resolution - map fields without creating KYC/settlement facts
6. Approved vs Requested Match - compare required exact values
7. Required Exact Validation - preserve exact values where legally/operationally required
8. Transform / Field Separation - minimize, map, omit, or split fields by destination
9. Destination-specific Payload Build - build payload; do not send every field on-chain
10. Outbound Handoff Decision - decide handoff readiness only
11. External Execution Handoff - forward payload; no custody or signing claim
12. Execution Result Binding - bind external result to trace
13. Audit / Reconciliation Trace - retain lineage for reconciliation

## 11. JSON Artifacts

- `03_digital_asset/artifacts/outbound_design_v1/outbound_requirement_matrix.json`
- `03_digital_asset/artifacts/outbound_design_v1/runtime_pipeline.json`
- `03_digital_asset/artifacts/be_handoff_v2/policy_evaluations/PE-DA-REGULATED-TRANSFER-002.json`
- `03_digital_asset/artifacts/be_handoff_v2/bindings/DAB-REGULATED-TRANSFER-002.json`
- `03_digital_asset/artifacts/be_handoff_v2/crosswalks/DA-RDC-REGULATED-TRANSFER-002.json`
- `03_digital_asset/artifacts/be_handoff_v2/outbound_requirements/OR-DA-REGULATED-TRANSFER-001.json`

## 12. Reused AI/BE Contract Concepts

Reused: policy evaluation artifact id/version/status, binding, crosswalk, decision values, refs, digest, and candidate handoff semantics.

## 13. BE Extensions Required

Runtime enums are needed for approved transaction identifier, approved policy snapshot identifier, runtime data class, destination profile, transform instruction, external provider result, outbound decision, execution handoff id, execution tx hash/status, and audit trace id.

## 14. Contract Gap

Travel Rule payload, VASP provider response, retry policy, reconciliation event, production settlement state, and audit event schema remain CONTRACT_GAP.

## 15. Example Flow

CASE 1 PASS: approved transaction exists -> exact fields resolve -> destination/amount match -> payload builds -> external handoff.

CASE 2 BLOCK: approved destination differs from requested destination -> transaction approval is not cancelled by FPG, but outbound handoff stops.

CASE 3 REVIEW: counterparty VASP or Travel Rule provider result is pending -> outbound handoff is held.

## Synthetic Position

Synthetic v1/v2/v3 and false-allow experiments are classified as EXPERIMENTAL_POLICY_SIMULATION. They are not main design evidence and do not estimate real transaction failure or regulatory violation rates.

## Current Coverage Summary

Outbound requirement types: {"REQUIRED_EXTERNAL_STATUS": 1, "REQUIRED_CHECK": 1, "REQUIRED_MATCH": 5, "REQUIRED_TRANSFER": 4, "REQUIRED_INCLUDE": 2, "REQUIRED_RETAIN": 2, "REQUIRED_DESTINATION_CHECK": 1, "REQUIRED_TRACE": 2}

On-chain/off-chain mapping: {"OFFCHAIN_EXTERNAL": 5, "OFFCHAIN_INTERNAL": 2, "ONCHAIN": 7, "NOT_AVAILABLE": 3, "BOTH": 1}
