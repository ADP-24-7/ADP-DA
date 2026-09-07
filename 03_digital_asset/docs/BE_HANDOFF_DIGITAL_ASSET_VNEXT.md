# BE Handoff Digital Asset vNext

## A. DA에서 확정된 것

### Field responsibility

FPG Digital Asset is a Policy Enforcement Gateway for already-approved transactions before external execution handoff. It enforces approved-vs-requested consistency, upstream-produced outbound field presence, exact preservation, transform compatibility, destination payload separation, and trace binding.

KYC execution, AML screening, VASP eligibility, sanctions screening, fraud/risk scoring, transaction approval, wallet custody/signing, and settlement finality are not FPG runtime controls.

### Exact/minimization/internal classification

{"FORMAT_TRANSFORM_ALLOWED": 1, "INTERNAL_ONLY": 2, "MINIMIZATION_ALLOWED": 4, "EXACT_REQUIRED": 11}

### Source phase

{"PRE_EXECUTION": 13, "POST_EXECUTION": 5}

`tx_hash`, `execution_status`, and `timestamp` are POST_EXECUTION fields sourced from EXTERNAL_EXECUTION_RESPONSE. They are not pre-execution outbound request inputs. `transaction_id` remains an approved/request trace identifier and is distinct from external execution result fields.

### Allowed transform semantics

{"PASS_THROUGH": "Outbound value must be emitted without mutation.", "FORMAT_NORMALIZE": "Allowed only as non-lossy, non-mutating comparison canonicalization unless explicitly destination-scoped for FORMAT_TRANSFORM_ALLOWED fields.", "MINIMIZE": "Destination-specific payload reduction for MINIMIZATION_ALLOWED fields; schema remains CONTRACT_GAP until BE/provider contract exists.", "MAP_TO_EXTERNAL_SCHEMA": "Destination-specific mapping into provider schema; provider schema remains CONTRACT_GAP.", "OMIT": "Do not externalize the field value."}

EXACT_REQUIRED outbound transform is restricted to PASS_THROUGH. Non-mutating comparison canonicalization is represented separately as `comparison_canonicalization`; chain-specific or lossy normalization remains CONTRACT_GAP.

### Destination separation

{"TRAVEL_RULE_PROVIDER": 8, "INTERNAL_AUDIT_ONLY": 7, "NOT_EXTERNALIZED": 2, "EXTERNAL_VASP": 4, "INTERNAL_RECONCILIATION_ONLY": 10, "BLOCKCHAIN_EXECUTION_SYSTEM": 4}

External destinations are separated from internal audit/reconciliation destinations by `destination` and `outbound_transform_by_destination`.

### PASS/BLOCK/REVIEW semantics

PASS: Current outbound handoff requirements are satisfied. This is not transaction approval.

BLOCK: The transaction may already be approved, but the current outbound request does not satisfy approved values or mandatory outbound handoff conditions.

REVIEW: Information required to construct outbound handoff is unresolved, unmapped, pending, or ambiguous. Do not use KYC/AML/VASP risk judgment as FPG runtime control.

## B. BE가 구현할 것

- Runtime loading: load vNext matrix, runtime pipeline, binding, crosswalk, and outbound requirement artifacts.
- Validator: enforce machine-readable validation rules from control boundary validation, including field/destination/rule failure reporting.
- Transform executor: execute only allowed outbound transforms; keep comparison canonicalization non-mutating.
- Destination payload builder: build destination-specific payloads without leaking INTERNAL_ONLY values to external destinations.
- Trace binding: bind approved transaction identifiers and FPG internal trace identifiers separately from external execution result fields.
- Execution response binding: bind `tx_hash`, `execution_status`, and `timestamp` only from EXTERNAL_EXECUTION_RESPONSE after external handoff.

## C. CONTRACT_GAP

- BE-owned runtime enum
- Approved transaction schema
- Approved policy snapshot schema
- Provider-specific payload schema
- Execution receipt/status schema
- Retry/reconciliation event schema
- Audit event schema

These gaps are intentionally not filled with inferred enum values, legal rules, provider schemas, or chain-specific normalization behavior.

## Runtime Pipeline

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

## Artifact Description

- `03_digital_asset/artifacts/outbound_design_vNext/outbound_requirement_matrix.json`
- `03_digital_asset/artifacts/outbound_design_vNext/runtime_pipeline.json`
- `03_digital_asset/artifacts/outbound_design_vNext/control_boundary_validation.json`
- `03_digital_asset/artifacts/be_handoff_vNext/policy_evaluations/PE-DA-REGULATED-TRANSFER-VNEXT.json`
- `03_digital_asset/artifacts/be_handoff_vNext/bindings/DAB-REGULATED-TRANSFER-VNEXT.json`
- `03_digital_asset/artifacts/be_handoff_vNext/crosswalks/DA-RDC-REGULATED-TRANSFER-VNEXT.json`
- `03_digital_asset/artifacts/be_handoff_vNext/outbound_requirements/OR-DA-REGULATED-TRANSFER-VNEXT.json`

## Boundary Validation

{"status": "PASS", "failures": [], "transform_counts": {"MAP_TO_EXTERNAL_SCHEMA": 5, "FORMAT_NORMALIZE": 1, "OMIT": 2, "MINIMIZE": 4, "PASS_THROUGH": 11}}

## ANALYST_DECISION_REQUIRED

- Provider-specific exact schemas for Travel Rule and external VASP identity payloads.
- Whether any future chain-specific address, amount, timestamp, status, or tx hash canonicalization can be contractually non-lossy.

## Synthetic Position

Synthetic v1/v2/v3 remains EXPERIMENTAL_POLICY_SIMULATION and is not used as BE runtime control evidence.
