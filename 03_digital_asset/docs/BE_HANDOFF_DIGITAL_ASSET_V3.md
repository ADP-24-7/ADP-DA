# BE Handoff Digital Asset V3

## 1. FPG Role

FPG Digital Asset is a Policy Enforcement Gateway. It enforces approved-vs-requested consistency, outbound field presence, exact preservation, transform, destination payload mapping, and trace binding for already-approved transactions.

## 2. Approved Transaction Input Layer

FPG input starts from an Approved Transaction plus an Approved Policy Snapshot. BE-owned identifiers remain CONTRACT_GAP until BE defines the runtime shape.

## 3. Upstream Responsibility

KYC execution, AML screening, VASP eligibility, sanctions screening, fraud/risk scoring, and transaction approval are upstream or external responsibilities.

## 4. FPG Runtime Responsibility

APPROVED_VS_REQUESTED_MATCH, REQUIRED_OUTBOUND_FIELD_PRESENCE, REQUIRED_EXACT_PRESERVATION, TRANSFORM_FIELD_SEPARATION, DESTINATION_SPECIFIC_PAYLOAD, TRACE_BINDING

## 5. Legal Obligation vs Runtime Control

Legal obligations remain represented, but KYC/AML/VASP eligibility obligations are not converted into FPG runtime decision controls.

## 6. Required Field

amount, asset, beneficiary_address, beneficiary_identity, counterparty_vasp, execution_status, kyc_status, originator_address, originator_identity, timestamp, transaction_id, tx_hash

## 7. Source

Sources are approved transaction, approved policy snapshot, upstream customer/compliance/provider data, blockchain execution layer, and external execution response.

## 8. Match

FPG compares approved asset, amount/limit, destination, beneficiary reference, and approved period against the outbound request.

## 9. Transform

{"MAP_TO_EXTERNAL_SCHEMA": 5, "FORMAT_NORMALIZE": 12, "OMIT": 2, "MINIMIZE": 4, "PASS_THROUGH": 11}

## 10. Destination

{"TRAVEL_RULE_PROVIDER": 8, "INTERNAL_AUDIT_ONLY": 7, "NOT_EXTERNALIZED": 2, "EXTERNAL_VASP": 4, "INTERNAL_RECONCILIATION_ONLY": 10, "BLOCKCHAIN_EXECUTION_SYSTEM": 4}

## 11. Required Exact

{"FORMAT_TRANSFORM_ALLOWED": 1, "INTERNAL_ONLY": 2, "MINIMIZATION_ALLOWED": 4, "EXACT_REQUIRED": 11}

## 12. PASS / BLOCK / REVIEW

PASS: Current outbound handoff requirements are satisfied. This is not transaction approval.

BLOCK: The transaction may already be approved, but the current outbound request does not satisfy approved values or mandatory outbound handoff conditions.

REVIEW: Information required to construct outbound handoff is unresolved, unmapped, pending, or ambiguous. Do not use KYC/AML/VASP risk judgment as FPG runtime control.

## 13. Runtime Pipeline

1. Approved Transaction Load - load existing approval; do not approve transactions
2. Approved Policy Snapshot Load - load snapshot; do not invent policy
3. Regulatory Outbound Requirement Load - load handoff requirements
4. Required Field Resolution - consume upstream data; do not determine KYC/AML/VASP eligibility
5. Approved Value vs Requested Value Match - compare values
6. Required Field Presence Check - check required outbound information exists
7. Required Exact Validation - verify exact fields are not lossy-transformed
8. Transform / Field Separation - normalize, minimize, omit, split, and map fields
9. Destination-specific Payload Build - build execution, Travel Rule, VASP, audit, reconciliation payloads
10. Outbound Handoff Decision - decide handoff readiness only
11. External Execution Handoff - forward payload; no wallet/signing/custody responsibility
12. Execution Result Binding - bind returned execution references only
13. Audit / Reconciliation Trace - retain lineage for audit and reconciliation

## 14. Artifact Description

- `03_digital_asset/artifacts/outbound_design_v2/outbound_requirement_matrix.json`
- `03_digital_asset/artifacts/outbound_design_v2/runtime_pipeline.json`
- `03_digital_asset/artifacts/outbound_design_v2/control_boundary_validation.json`
- `03_digital_asset/artifacts/be_handoff_v3/policy_evaluations/PE-DA-REGULATED-TRANSFER-003.json`
- `03_digital_asset/artifacts/be_handoff_v3/bindings/DAB-REGULATED-TRANSFER-003.json`
- `03_digital_asset/artifacts/be_handoff_v3/crosswalks/DA-RDC-REGULATED-TRANSFER-003.json`
- `03_digital_asset/artifacts/be_handoff_v3/outbound_requirements/OR-DA-REGULATED-TRANSFER-002.json`

## 15. BE Implementation Scope

BE can implement artifact loading, field resolution, approved/requested match, exact validation, transform instruction application, destination-specific payload build, PASS/BLOCK/REVIEW return, handoff trace creation, and execution result binding.

## 16. BE Non-Implementation Scope

BE should not implement KYC engine, AML engine, VASP eligibility engine, sanctions screening, fraud detection, wallet/custody/signing, or settlement engine as FPG runtime controls.

## 17. Contract Gap

Approved transaction schema, approved policy snapshot schema, provider response schemas, destination profile enum, retry/reconciliation event schema, audit event schema, and execution receipt ingestion remain CONTRACT_GAP.

## 18. Example Flow

CASE 1 normal outbound: approved transaction exists -> requested values match -> required outbound fields exist -> transform -> payload build -> PASS -> external handoff.

CASE 2 destination mismatch: approved destination differs from requested destination -> BLOCK. This stops outbound handoff, not transaction approval itself.

CASE 3 required regulatory field missing: approval may exist but outbound field cannot resolve -> REVIEW when source is unresolved, BLOCK when exact request mismatch is confirmed.

CASE 4 KYC/AML/VASP: upstream systems produce statuses or references; FPG does not re-score or re-decide them.

## Boundary Validation

[{"assertion": "no_KYC_STATUS_CHECK_runtime_control", "status": "PASS"}, {"assertion": "no_AML_CHECK_runtime_control", "status": "PASS"}, {"assertion": "no_VASP_ELIGIBILITY_CHECK_runtime_control", "status": "PASS"}, {"assertion": "pass_not_transaction_approval", "status": "PASS"}, {"assertion": "block_not_approval_cancellation", "status": "PASS"}, {"assertion": "approved_transaction_input_exists", "status": "PASS"}, {"assertion": "approved_requested_match_exists", "status": "PASS"}, {"assertion": "required_field_presence_exists", "status": "PASS"}, {"assertion": "transform_instruction_exists", "status": "PASS"}, {"assertion": "destination_mapping_exists", "status": "PASS"}, {"assertion": "trace_binding_exists", "status": "PASS"}, {"assertion": "required_exact_transform_no_conflict", "status": "PASS"}]

## Synthetic Position

Synthetic v1/v2/v3 remains EXPERIMENTAL_POLICY_SIMULATION and is not used as BE runtime control evidence.
