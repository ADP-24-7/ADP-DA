# AI Contract Gap Analysis

## Scope

This document organizes the first-pass FPG AI analysis structure against the
existing ADP-DA repository and contract boundary.

No BE handoff JSON artifact is generated in this step.

The purpose of this review is limited to:

- Repository placement
- Analysis-to-analysis traceability
- Mapping between EVAL-AI-001 through EVAL-AI-004 and existing contract fields
- Contract gaps that must remain `TBD`, `UNRESOLVED`, or `UNMAPPED`

The legacy mixed-domain evidence and gateway structures have been split by
domain. AI evidence and gateway sources now live under
`02_ai/evidence_ontology/` and `02_ai/gateway_rules/`; AI handoff contracts
live under `02_ai/contracts/`.

## Repository Placement

| File | Final location | Role | Runtime handoff status |
|---|---|---|---|
| `01_evaluation_ai_field_utility_v1.ipynb` | `02_ai/notebooks/01_evaluation_ai_field_utility_v1.ipynb` | Reproducible Field Utility analysis notebook | Not a BE runtime artifact |
| `02_evaluation_ai_workload_v1.ipynb` | `02_ai/notebooks/02_evaluation_ai_workload_v1.ipynb` | Reproducible Workload analysis notebook | Not a BE runtime artifact |
| `03_evaluation_ai_transform_tradeoff_v1.ipynb` | `02_ai/notebooks/03_evaluation_ai_transform_tradeoff_v1.ipynb` | Reproducible Transform Privacy-Utility analysis notebook | Not a BE runtime artifact |
| `04_evaluation_ai_legal_constraint_v1.ipynb` | `02_ai/notebooks/04_evaluation_ai_legal_constraint_v1.ipynb` | Reproducible Legal Constraint analysis notebook | Not a BE runtime artifact |
| `AI_POLICY_VALIDATION.md` | `02_ai/docs/AI_POLICY_VALIDATION.md` | Human-readable integrated AI policy validation note | Not a BE runtime artifact |
| `AI_CONTRACT_GAP_ANALYSIS.md` | `02_ai/docs/AI_CONTRACT_GAP_ANALYSIS.md` | Contract gap and traceability review | Not a BE runtime artifact |

Note: the notebook filenames currently place Field Utility before Workload.
The logical evaluation order below follows the policy analysis order required
for FPG AI.

## Analysis Traceability

| Evaluation ID | Logical analysis step | Source notebook | Provides | Does not provide |
|---|---|---|---|---|
| `EVAL-AI-001` | Workload analysis | `02_ai/notebooks/02_evaluation_ai_workload_v1.ipynb` | Topic-Action structure, Action sharing, basis for `Role + Purpose + Action` access-scope design | BE-owned `workload_id`, final runtime purpose enum, final field access list |
| `EVAL-AI-002` | Field Utility analysis | `02_ai/notebooks/01_evaluation_ai_field_utility_v1.ipynb` | Field-level utility requirement differences, Exact/Partial/Relationship/Reversibility analysis basis | Final transform per field, AI utility threshold, model quality threshold |
| `EVAL-AI-003` | Transform Privacy-Utility analysis | `02_ai/notebooks/03_evaluation_ai_transform_tradeoff_v1.ipynb` | MASK strength collision results, relationship preservation results, HMAC/TOKEN operational distinction | Final transform selection, acceptable failure level, latency threshold |
| `EVAL-AI-004` | Legal Constraint analysis | `02_ai/notebooks/04_evaluation_ai_legal_constraint_v1.ipynb` | Law/Article/Constraint/Gateway Control candidate basis | Final legal judgment, final `ALLOW/BLOCK/TRANSFORM/REVIEW`, BE runtime enforcement result |

Integrated trace:

```text
EVAL-AI-001
Workload analysis
-> Role + Purpose + Action
-> Required Data Scope basis

EVAL-AI-002
Field Utility analysis
-> Field-level Utility Requirement differences
-> Exact / Relationship / Reversibility basis

EVAL-AI-003
Transform Privacy-Utility analysis
-> MASK strength collision / relationship preservation
-> Transform Candidate selection basis

EVAL-AI-004
Legal Constraint analysis
-> Law / Article / Obligation / Condition
-> Gateway Control Candidate basis
```

The combined first-pass FPG AI policy structure is:

```text
Role
+ Purpose
+ Action
-> Required Data / Data Class
-> Field-level Utility Requirement
-> Legal Constraint
-> Transform Candidate
-> Runtime Decision Candidate
```

This is a candidate analysis structure only. It is not an active runtime policy.

## Existing Contract Inventory

Confirmed schemas in `02_ai/contracts/`:

| Requested schema | Actual repository status |
|---|---|
| `evaluation_artifact.schema.json` | Exists |
| `policy_evaluation_artifact.schema.json` | Exists |
| `workload_purpose_binding.schema.json` | Exists |
| `runtime_data_class_crosswalk.schema.json` | Exists |
| `bundle_manifest.schema.json` | Not present in `02_ai/contracts/`; no alternate bundle schema found |

Related frozen sources:

| Layer | Frozen source | Boundary |
|---|---|---|
| Evidence / Requirement Candidate | `02_ai/evidence_ontology/processed/evidence_master.json`, `02_ai/evidence_ontology/processed/requirement_candidates.json` | Regulatory evidence and requirement candidates only; no direct runtime decision |
| Control / Test / Policy Candidate | `02_ai/gateway_rules/processed/controls.json`, `02_ai/gateway_rules/processed/tests.json`, `02_ai/gateway_rules/processed/policy_candidates.json`, `02_ai/gateway_rules/processed/traceability.json` | Evaluation inputs only; no active runtime policy |
| AI-related Policy Candidate references | `PC-009`, `PC-010`; related controls include `CTRL-RUNTIME-008` and AI governance controls | Require validation evidence before promotion |

## Contract Field Gap Table

Status values:

- `AVAILABLE`: the current AI analysis can support the field or evidence basis.
- `TBD`: a value can be filled later, but this step does not create the artifact or version.
- `UNRESOLVED`: analysis indicates the issue remains open or requires later evaluation.
- `UNMAPPED`: existing analysis does not map to this field, or BE-owned values are absent.

| Contract / Field | Provided by EVAL-AI-001~004 | Current value exists? | Evidence notebook | Status | Further AI experiment needed? |
|---|---|---:|---|---|---|
| `evaluation_artifact.artifact_id` | Evaluation IDs are logically defined as `EVAL-AI-001~004` | No JSON artifact value created | `AI_POLICY_VALIDATION.md` | `TBD` | No, packaging step needed |
| `evaluation_artifact.artifact_version` | Not provided by notebooks | No | N/A | `TBD` | No, release/versioning decision needed |
| `evaluation_artifact.status` | Current analysis is candidate-level only | Partial human-readable basis | `AI_POLICY_VALIDATION.md` | `TBD` | Yes, validation run needed before `validated` |
| `evaluation_artifact.workload_id` | `Role + Purpose + Action` basis from workload analysis | No BE-owned workload ID | `02_evaluation_ai_workload_v1.ipynb` | `UNMAPPED` | No, BE binding needed |
| `evaluation_artifact.experiment_id` | `EVAL-AI-001~004` can serve as experiment-level identifiers later | No artifact field emitted | All four notebooks | `TBD` | No, packaging step needed |
| `evaluation_artifact.dataset_version` | Source datasets are used, but no versioned dataset contract exists | No | Workload, Field Utility, Transform notebooks | `TBD` | No, dataset manifest/versioning needed |
| `evaluation_artifact.source_ids` | Legal analysis has law IDs/articles; 02 Evidence has EV refs | Partial | Legal notebook, 02 evidence artifacts | `TBD` | No, reference packaging needed |
| `evaluation_artifact.metrics` | Workload, utility, and transform notebooks contain metrics | Yes in notebooks only | EVAL-AI-001, EVAL-AI-002, EVAL-AI-003 | `AVAILABLE` | Yes for AI model runtime metrics |
| `evaluation_artifact.metrics.threshold` | Thresholds are not established | No | N/A | `UNRESOLVED` | Yes |
| `evaluation_artifact.threshold_basis` | No AI utility, latency, or failure threshold basis finalized | No | N/A | `UNRESOLVED` | Yes |
| `evaluation_artifact.claim_scope` | Each analysis states limited claim scope | Yes in prose | All four notebooks, `AI_POLICY_VALIDATION.md` | `AVAILABLE` | No |
| `evaluation_artifact.limitations` | v1 limitations and follow-up AI experiments are identified | Yes in prose | `AI_POLICY_VALIDATION.md` | `AVAILABLE` | Yes |
| `evaluation_artifact.failure_cases` | Future failure cases are listed as follow-up, not measured | Partial | `AI_POLICY_VALIDATION.md` | `UNRESOLVED` | Yes |
| `evaluation_artifact.digest` | Not generated | No | N/A | `TBD` | No, packaging step needed |
| `policy_evaluation_artifact.schema_version` | Contract requires `v1` | Schema exists, artifact not created | `policy_evaluation_artifact.schema.json` | `TBD` | No |
| `policy_evaluation_artifact.artifact_id` | Not generated | No | N/A | `TBD` | No, packaging step needed |
| `policy_evaluation_artifact.artifact_version` | Not generated | No | N/A | `TBD` | No, packaging step needed |
| `policy_evaluation_artifact.analysis_status` | Candidate-level analysis only | Partial | `AI_POLICY_VALIDATION.md` | `TBD` | Yes before validated status |
| `policy_evaluation_artifact.policy_action` | Final policy action is not decided | No | N/A | `UNRESOLVED` | Yes |
| `policy_evaluation_artifact.matched_policy_refs` | AI candidates such as `PC-009` and `PC-010` are relevant | Partial | `02_ai/gateway_rules/processed/policy_candidates.json` | `TBD` | No, selection/review needed |
| `policy_evaluation_artifact.matched_rule_refs` | Legacy `GR-*` refs are provenance only | Partial | `02_ai/gateway_rules/processed/traceability.json` | `TBD` | No |
| `policy_evaluation_artifact.requirement_refs` | AI Evidence/Requirement refs exist in AI lineage | Partial | `02_ai/evidence_ontology`, `02_ai/gateway_rules/processed/traceability.json` | `TBD` | No, packaging needed |
| `policy_evaluation_artifact.evidence_refs` | AI Evidence refs exist, including `EV-00035~EV-00042` area | Partial | `02_ai/evidence_ontology/processed/evidence_master.json` | `TBD` | No, packaging needed |
| `policy_evaluation_artifact.required_controls` | Gateway control candidate basis exists | Partial | Legal notebook, `02_ai/gateway_rules/processed/controls.json` | `AVAILABLE` | Yes for runtime/control validation |
| `policy_evaluation_artifact.validation_artifact_refs` | Current notebooks are not JSON Evaluation Artifacts yet | No valid refs | All four notebooks | `TBD` | No, artifact generation later |
| `policy_evaluation_artifact.applicability.status` | Candidate-level applicability can be described | Partial | Workload and Legal notebooks | `TBD` | Yes before validation |
| `policy_evaluation_artifact.applicability.scope` | `Role + Purpose + Action` and legal constraint scope basis exists | Yes in prose | EVAL-AI-001, EVAL-AI-004 | `AVAILABLE` | No |
| `policy_evaluation_artifact.applicability.limitations` | Limitations are identified | Yes in prose | `AI_POLICY_VALIDATION.md` | `AVAILABLE` | Yes for unresolved runtime items |
| `policy_evaluation_artifact.processing_contexts` | `ai_use` exists in 02/03 artifacts; workload contexts need binding | Partial | 02/03 artifacts, Legal notebook | `TBD` | No, binding needed |
| `policy_evaluation_artifact.regulatory_data_categories` | Legal analysis identifies personal/credit information concepts | Partial | Legal notebook, 02 evidence artifacts | `TBD` | No, taxonomy mapping needed |
| `policy_evaluation_artifact.runtime_binding.mapping_status` | BE-owned mapping is not available | No | N/A | `UNMAPPED` | No, BE binding needed |
| `policy_evaluation_artifact.runtime_binding.runtime_data_class` | BE-owned enum is not available | No | N/A | `UNMAPPED` | No, BE binding needed |
| `policy_evaluation_artifact.runtime_binding.workload_id` | BE-owned workload ID is not available | No | N/A | `UNMAPPED` | No, BE binding needed |
| `policy_evaluation_artifact.runtime_binding.purpose` | BE-owned purpose value is not available | No | N/A | `UNMAPPED` | No, BE binding needed |
| `policy_evaluation_artifact.runtime_binding.binding_ref` | No binding artifact generated | No | N/A | `TBD` | No, packaging/binding step needed |
| `policy_evaluation_artifact.digest` | Not generated | No | N/A | `TBD` | No, packaging step needed |
| `workload_purpose_binding.schema_version` | Contract requires `v1` | Schema exists, artifact not created | `workload_purpose_binding.schema.json` | `TBD` | No |
| `workload_purpose_binding.binding_version` | Not generated | No | N/A | `TBD` | No, versioning needed |
| `workload_purpose_binding.bindings.workload_id` | Workload analysis supports dynamic scope design, not BE ID | No | EVAL-AI-001 | `UNMAPPED` | No, BE binding needed |
| `workload_purpose_binding.bindings.purpose` | Purpose is analytical concept only | No BE enum/value | EVAL-AI-001 | `UNMAPPED` | No, BE binding needed |
| `workload_purpose_binding.bindings.processing_context` | `ai_use` and consultation contexts are identifiable | Partial | EVAL-AI-001, 02/03 artifacts | `TBD` | No, taxonomy/binding needed |
| `workload_purpose_binding.bindings.runtime_data_class` | BE-owned runtime data class absent | No | N/A | `UNMAPPED` | No, BE binding needed |
| `workload_purpose_binding.bindings.binding_status` | Binding not resolved | No | N/A | `UNRESOLVED` | No, BE binding needed |
| `runtime_data_class_crosswalk.schema_version` | Contract requires `v1` | Schema exists, artifact not created | `runtime_data_class_crosswalk.schema.json` | `TBD` | No |
| `runtime_data_class_crosswalk.crosswalk_version` | Not generated | No | N/A | `TBD` | No, versioning needed |
| `runtime_data_class_crosswalk.mappings.regulatory_data_category` | Legal and evidence artifacts provide regulatory categories | Partial | EVAL-AI-004, 02 evidence artifacts | `AVAILABLE` | No |
| `runtime_data_class_crosswalk.mappings.runtime_data_class` | BE-owned runtime enum absent | No | N/A | `UNMAPPED` | No, BE binding needed |
| `runtime_data_class_crosswalk.mappings.mapping_status` | No mapping has been resolved | No | N/A | `UNRESOLVED` | No, BE binding needed |
| `runtime_data_class_crosswalk.mappings.mapping_basis` | Field utility and legal analysis can support later basis | Partial | EVAL-AI-002, EVAL-AI-004 | `TBD` | Yes for unresolved utility/runtime evidence |
| `runtime_data_class_crosswalk.mappings.version` | Not generated | No | N/A | `TBD` | No, versioning needed |
| `bundle_manifest.schema.json` | Requested contract is absent | No schema found | N/A | `UNRESOLVED` | No, contract definition needed |

## Explicit Non-Decisions

The current analysis does not finalize or infer:

- Field-level final Transform
- Final `ALLOW`, `BLOCK`, `TRANSFORM`, or `REVIEW`
- AI Utility Threshold
- Latency Threshold
- Model-specific quality criteria
- Acceptable failure level
- BE-owned workload identifiers
- BE-owned purpose values
- BE-owned runtime data class enums
- Bundle manifest schema fields

Any future artifact must carry these as `TBD`, `UNRESOLVED`, or `UNMAPPED` until
the relevant evaluation, binding, or contract definition exists.

## Core Gaps

| Gap | Impact | Current handling |
|---|---|---|
| No `bundle_manifest.schema.json` exists in `02_ai/contracts/` | Immutable release bundle cannot be contract-validated from current schema set | Mark bundle contract as `UNRESOLVED` |
| Notebooks are not Evaluation Artifact JSONs | `validation_artifact_refs` cannot yet reference valid JSON artifacts | Defer artifact generation |
| BE workload/purpose/runtime data class values are absent | Runtime binding and crosswalk cannot be resolved | Mark as `UNMAPPED` |
| Transform experiment supports candidates but not final policy | BE must not select MASK/HMAC/TOKEN/KEEP by default | Mark final transform as `UNRESOLVED` |
| AI runtime/model experiments not yet executed | Utility, latency, model quality, and failure thresholds cannot be set | Mark thresholds and failure tolerance as `UNRESOLVED` |
| Legal analysis provides control candidates, not final legal approval | Runtime action cannot be finalized from legal notebook alone | Keep policy action `UNRESOLVED` |

## Next Step Boundary

The next step may generate versioned Evaluation Artifact JSONs only after the
team explicitly moves from structure/gap review to handoff artifact generation.
This document does not create or imply such JSON artifacts.
