# 03 Gateway Rules

This module consumes the frozen `02_evidence_ontology` outputs and designs project-level Control, Test, and Policy Candidate artifacts.

## Responsibility Boundary

- `02_evidence_ontology` owns Official Source, Evidence, and Requirement Candidate records.
- `03_gateway_rules` owns Control, Test, and Policy Candidate records.
- Legacy `GR-xxxx` rules are preserved only as migration provenance.
- Runtime activation, final transform selection, and threshold selection are out of scope.

The target chain is:

```text
Official Source -> Evidence -> Requirement Candidate -> Control -> Test -> Policy Candidate
```

## Semantic Redesign

The current outputs are derived from 59 Requirement Candidates, not from a `GR-0001 -> CTRL-0001 -> TEST-0001 -> PC-0001` pattern.

Requirements are classified as:

- `RUNTIME_ENFORCEABLE`
- `GOVERNANCE_CONTROL`
- `EVALUATION_DEPENDENT`
- `NON_RUNTIME_REFERENCE`

Controls may group multiple Requirements when they share the same technical or governance objective. A Requirement may influence policy only through a Control and Test chain.

## Outputs

- `processed/requirement_classification.json`
- `processed/controls.json`
- `processed/tests.json`
- `processed/policy_candidates.json`
- `processed/traceability.json`
- `provisional/project_provisional_rules.json`
- `migration/legacy_rule_mapping.json`
- `review/validation_report.json`
- `review/orphan_report.json`
- `review/downstream_todo.json`

## Legacy Files

These files are preserved and are not active runtime policy:

- `rules/gateway_rules.json`
- `rules/gateway_rules.csv`
- `mappings/evidence_rule_mapping.json`

`migration/legacy_rule_mapping.json` maps each legacy rule to Requirement Candidates as provenance only. Legacy actions such as `BLOCK` or `TRANSFORM` are not copied as final policy decisions.

## Policy Candidate Boundary

Policy Candidates are generated only for runtime-relevant or evaluation-dependent controls. Governance-only and non-runtime reference controls may have Tests without Policy Candidates.

Candidate actions may be:

- `REVIEW`
- `UNRESOLVED`

The schema still reserves `ALLOW`, `BLOCK`, and `TRANSFORM` as candidate values, but this semantic redesign does not promote legacy decisions into final runtime actions.

Concrete transform choices are represented only as `candidate_transform_options`, such as:

- `MASK`
- `HMAC-PSEUDO`
- `VAULT-TOKEN`
- `GENERALIZE`
- `FIELD-SEPARATION`
- `REMOVE`
- `KEEP`

No final transform or threshold is selected in this module.

## Validation

Run:

```bash
python 03_gateway_rules/scripts/validate_gateway_rules.py
```

The validator checks schema conformance, duplicate IDs, dangling references, orphan Requirements, runtime controls without policy candidates, direct Evidence references in Policy Candidates, `REVIEW_REQUIRED` promotion violations, final transform or threshold values without evaluation artifacts, accidental `ACTIVE` policies, and semantic warnings such as duplicated Test text or legacy-name reuse.

No migrated Test is marked `VALIDATED` without an actual validation artifact.
