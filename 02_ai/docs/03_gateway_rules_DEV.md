# 03 Gateway Rules — Developer Handoff

03 Gateway Rules의 frozen DA artifact를 BE 관점에서 정의한다. Legacy `GR-*` Rule Set과 active Runtime Policy를 구분한다.

## Current Scope

| Layer | Status | Scope |
|---|---|---|
| Requirement Classification | READY | 59 Requirement Candidates classified |
| Control | READY / NOT ACTIVE | 22 semantic Controls |
| Test | DEFINED / VALIDATION REQUIRED | 29 Test contracts. VALIDATED 0 |
| Policy Candidate | VALIDATION REQUIRED | 11 candidates. REVIEW 8 / UNRESOLVED 3 |
| Promotable candidate set | NOT ACTIVE | 9 non-blocked candidates. Runtime validation required |
| Promotion blocked | BLOCKED | `PC-006`, `PC-011` |
| Runtime Policy | OUT OF SCOPE | No active Policy Candidate. No PolicyEvaluation Artifact in 03 |

## 1. Source Artifacts

| Artifact | Role | Source of Truth | Runtime Use |
|---|---|---|---|
| `processed/requirement_classification.json` | 59 Requirement classification records | Requirement semantic classification | Direct Runtime use 금지 |
| `processed/controls.json` | 22 Control definitions | **Control contract source** | Policy action 아님. Handoff input |
| `processed/tests.json` | 29 Test definitions | **Test contract source** | Runtime Decision 아님. Validation contract |
| `processed/policy_candidates.json` | 11 Policy Candidates | **Policy Candidate contract source** | 직접 실행 금지. Evaluation input |
| `processed/traceability.json` | 59 lineage records | Official Source → Evidence → Requirement → Control/Test/PC mapping | Audit/provenance resolver input |
| `provisional/project_provisional_rules.json` | `promotion_blocked=false`인 9 candidates의 projection | Convenience handoff set | Active policy 아님. 전부 `VALIDATION_REQUIRED` |
| `review/validation_report.json` | Semantic artifact validation result | Count, schema/reference integrity, PASS result | Ingest gate metadata. Policy 아님 |
| `review/orphan_report.json` | Orphan/dangling inventory | Reference completeness report | Ingest validation 참고 |
| `review/downstream_todo.json` | Deferred design/validation queue | Open handoff items | Runtime consume 금지 |
| `review/review_required_rules.json` | Legacy REVIEW Rule inventory | Review/migration support | Active policy 아님 |
| `migration/legacy_rule_mapping.json` | Legacy GR → Requirement provenance | Migration history | `migration_role=PROVENANCE_ONLY` |
| `schemas/control_schema.json` | Control JSON Schema | Structural contract | Loader validation |
| `schemas/test_schema.json` | Test JSON Schema | Structural contract | Loader validation |
| `schemas/policy_candidate_schema.json` | Policy Candidate JSON Schema | Structural contract | Loader validation |

### Legacy artifacts

- `rules/gateway_rules.json`
- `rules/gateway_rules.csv`
- `mappings/evidence_rule_mapping.json`
- `schemas/gateway_rule.schema.json`

Legacy Rule 22건은 migration provenance다. `ALLOW`, `BLOCK`, `TRANSFORM`, `REVIEW` 값을 현재 Runtime action으로 ingest하면 안 된다.

## 2. Control Contract

Contract: `schemas/control_schema.json`

Cardinality: array of 22 Controls.

ID: `CTRL-[A-Z]+-[0-9]{3}`.

Control = 하나 이상의 Requirement를 시스템 통제 단위로 구조화한 정의. Runtime Action이 아니다.

| Field | Meaning | Required | Runtime Impact |
|---|---|---:|---|
| `control_id` | Control stable reference | Yes | Test/Policy Candidate lineage key |
| `requirement_ids` | Source Requirement references | Yes, min 1 | 모두 02 active Requirement에 resolve 필요 |
| `control_type` | 통제 유형 enum | Yes | Implementation boundary 분류. Action 아님 |
| `control_name` | Human-readable name | Yes | Display/audit metadata |
| `objective` | 통제 목적 | Yes | Implementation intent. Executable expression 아님 |
| `enforcement_point` | 적용 가능한 시스템 경계 목록 | Yes | Runtime binding 후보. 실제 component binding 아님 |
| `processing_phase` | 관련 처리 단계 목록 | Yes | Applicability mapping input |
| `implementation_boundary` | 03이 확정하지 않는 구현 경계 | Yes | Downstream design constraint |
| `validation_requirement` | Control 검증 요구 | Yes | Test/evaluation input |
| `provenance.source` | 생성 근거 | Yes | Audit metadata |
| `provenance.legacy_rule_ids` | Legacy GR references | Yes | Provenance only |
| `provenance.note` | Migration/derivation note | Yes | Audit metadata |
| `maturity` | `PROJECT_PROVISIONAL` / `VALIDATION_REQUIRED` | Yes | Active status 아님 |

`additionalProperties=false`다. Unknown field를 무시하지 않는다.

Control categories:

- Runtime: `CTRL-RUNTIME-001`~`CTRL-RUNTIME-010`
- Evaluation: `CTRL-EVAL-001`
- Governance: `CTRL-GOV-001`~`CTRL-GOV-007`
- Reference: `CTRL-REF-001`~`CTRL-REF-004`

## 3. Test Contract

Contract: `schemas/test_schema.json`

Cardinality: array of 29 Tests.

ID: `TEST-[0-9]{3}`.

Test = Control expected behavior와 failure condition을 검증하는 계약. Runtime Decision이 아니다.

| Field | Meaning | Required | Runtime Impact |
|---|---|---:|---|
| `test_id` | Test stable reference | Yes | Policy Candidate lineage key |
| `control_ids` | 검증 대상 Control references | Yes, min 1 | Active Control set에 resolve 필요 |
| `test_type` | UNIT, CONTRACT, INTEGRATION, GOLDEN, ADVERSARIAL, FAILURE, REPLAY, GOVERNANCE | Yes | Validation execution class |
| `test_name` | Test name | Yes | Human-readable identity |
| `expected_behavior` | 통과 조건 | Yes | Test oracle input. Runtime action 아님 |
| `failure_condition` | 실패 조건 | Yes | Validation failure definition |
| `required_artifact` | 검증에 필요한 fixture/report/trace | Yes | Promotion dependency |
| `status` | DEFINED, VALIDATION_REQUIRED, VALIDATED | Yes | Validation lifecycle |

Current status:

- `VALIDATION_REQUIRED`: 21
- `DEFINED`: 8
- `VALIDATED`: 0

Test가 존재한다는 이유만으로 linked Control 또는 Policy Candidate를 validated로 처리하면 안 된다.

## 4. Policy Candidate Contract

Contract: `schemas/policy_candidate_schema.json`

Cardinality: array of 11 Policy Candidates.

ID: `PC-[0-9]{3}`.

Policy Candidate = Runtime Policy로 승격 가능성을 분석한 DA 후보.

Runtime Policy = evaluation/approval 이후 BE Runtime에서 선택되는 versioned Policy Snapshot.

두 객체는 identity와 lifecycle이 다르다.

| Field | Meaning | Required | Runtime Impact |
|---|---|---:|---|
| `policy_candidate_id` | DA candidate identity | Yes | BE PolicySnapshot identity로 재사용 금지 |
| `requirement_ids` | Source Requirement refs | Yes | Evidence lineage root |
| `control_ids` | Source Control refs | Yes | 모두 resolve 필요 |
| `test_ids` | Required Test refs | Yes | 모두 resolve 필요 |
| `workload_scope` | Candidate workload scope strings | Yes | Runtime workload binding으로 직접 cast 금지 |
| `actor_scope` | Candidate actor scope | Yes | Applicability input |
| `purpose_scope` | Candidate purpose scope | Yes | Runtime purpose binding 전 validation 필요 |
| `processing_phase` | Candidate processing context | Yes | Applicability input |
| `data_class` | DA candidate data classes | Yes | BE Runtime Data Class와 crosswalk 필요 |
| `applicability` | Candidate applicability note | Yes | 현재 자연어. Executable predicate 아님 |
| `conditions` | Source-derived condition strings | Yes | Policy expression 아님 |
| `candidate_action` | ALLOW/BLOCK/TRANSFORM/REVIEW/UNRESOLVED enum | Yes | Candidate disposition. BE Final Action 아님 |
| `candidate_transform` | NONE / UNRESOLVED | Yes | Final Transform가 아님 |
| `candidate_transform_options` | 허용 가능한 평가 후보 목록 | Yes | Resolver가 임의 선택 금지 |
| `reason_codes` | Legacy/provenance reason codes | Yes | Runtime reason code와 동일시 금지 |
| `evidence_maturity` | VERIFIED / REVIEW_REQUIRED | Yes | Promotion gate |
| `policy_maturity` | PROJECT_PROVISIONAL / VALIDATION_REQUIRED | Yes | Lifecycle metadata |
| `validation_dependencies` | 필요한 evaluation/validation 목록 | Yes | Promotion gate input |
| `promotion_blocked` | Promotion 차단 여부 | Yes | `true`이면 snapshot promotion 금지 |
| `status` | PROJECT_PROVISIONAL / VALIDATION_REQUIRED | Yes | Active status 없음 |
| `rationale` | Candidate 선정 근거 | Yes | Human-readable analysis |

Current values:

- Candidate action: `REVIEW` 8, `UNRESOLVED` 3
- Candidate transform: `NONE` 8, `UNRESOLVED` 3
- Status: `VALIDATION_REQUIRED` 11
- Active: 0
- Promotion blocked: `PC-006`, `PC-011`

## 5. Reference & Lineage

Canonical mapping: `processed/traceability.json`.

Fields:

- `official_source_id`
- `evidence_id`
- `requirement_id`
- `control_id`
- `test_ids`
- `policy_candidate_ids`
- `legacy_rule_ids`

59 Requirement 모두 lineage record를 가진다. Orphan Requirement, dangling Requirement/Control/Test reference는 없다.

Examples:

```text
law_pipa
→ EV-00002
→ RC-00002
→ CTRL-RUNTIME-001
→ TEST-001, TEST-002
→ PC-001
```

```text
fsc_ai_guideline_2026
→ EV-00040
→ RC-00040
→ CTRL-RUNTIME-008
→ TEST-021, TEST-022
→ PC-009
```

```text
law_special_financial_info_decree
→ EV-00057
→ RC-00057
→ CTRL-RUNTIME-010
→ TEST-028, TEST-029
→ PC-011
```

Runtime audit에서 lineage를 보존하려면 ID와 reference type을 함께 전달해야 한다. 현재 03 artifact에는 `version`, `digest`, `artifact_id`, `schema_version`, `ref_type` field가 없다. 이를 canonical source field처럼 합성하지 않는다. Typed reference와 artifact identity는 downstream handoff contract에서 정의해야 한다.

## 6. Action Boundary

- Requirement: Evidence에서 추출한 규제 요구 후보.
- Control: Requirement를 시스템 통제 목적과 경계로 구조화한 정의.
- Test: Control의 expected behavior와 failure condition을 검증하는 계약.
- Policy Candidate: Runtime 적용 가능성을 분석한 DA 후보.
- Runtime Policy: 평가·승격 후 BE Policy Snapshot으로 활성화되는 정책.
- Runtime Decision: 고정된 Policy Snapshot과 Runtime Context의 평가 결과.

```text
Requirement
≠ Control
≠ Test
≠ Policy Candidate
≠ Runtime Policy
≠ Runtime Decision
```

`candidate_action`은 DA disposition이다. BE `PolicyAction` 또는 `FinalAction`으로 직접 deserialize하지 않는다.

## 7. Transform Boundary

실제 `candidate_transform_options` enum:

| Strategy | Source Candidate | Runtime 확정 | Required Boundary |
|---|---|---|---|
| `MASK` | PC-004, PC-009, PC-011 | No | Data evaluation + context binding |
| `HMAC-PSEUDO` | PC-004, PC-009 | No | Data evaluation + key/scope contract |
| `VAULT-TOKEN` | PC-003, PC-004, PC-009 | No | Data evaluation + vault/scope contract |
| `GENERALIZE` | PC-004, PC-009 | No | Utility/privacy evaluation |
| `FIELD-SEPARATION` | PC-003, PC-008, PC-011 | No | Data class crosswalk + routing contract |
| `REMOVE` | PC-004, PC-009 | No | Purpose/utility evaluation |
| `KEEP` | PC-004, PC-008, PC-009, PC-011 | No | Explicit evaluated justification |

`candidate_transform_options`는 allowlist가 아니라 evaluation option set이다. BE가 첫 번째 값, 가장 약한 값 또는 local default를 선택하면 안 된다. `candidate_transform=UNRESOLVED`는 evaluation artifact 없이는 fail-closed promotion condition이다.

## 8. Validation Rules

저장된 validator 결과는 PASS다. BE ingest 경계에서도 다음 invariant가 필요하다.

- JSON Schema required field, enum, ID pattern, `additionalProperties=false`를 검증한다.
- Unknown Requirement, Control, Test reference를 차단한다.
- Requirement lineage 없는 Control을 차단한다.
- Control/Test chain 없는 Policy Candidate를 차단한다.
- Runtime 관련 Control에 Policy Candidate가 없으면 promotion을 차단한다.
- `REVIEW_REQUIRED` dependency의 자동 promotion을 차단한다.
- `promotion_blocked=true`를 완화하지 않는다.
- Final Transform 또는 threshold가 evaluation artifact 없이 설정되면 차단한다.
- `status=ACTIVE`는 현재 schema와 artifact에 없으므로 허용하지 않는다.
- Policy Candidate가 Evidence를 직접 참조하는 우회 구조를 차단한다.
- Unknown Data Class는 crosswalk 없이 default allow하지 않는다.
- Conflicting candidates의 우선순위와 결합 규칙이 없으면 fail-closed 또는 review로 보낸다.
- Legacy `GR-*` action을 Candidate 또는 Runtime Final Action으로 복사하지 않는다.

`unsupported version` 검증은 현재 artifact 자체에 version field가 없어 수행할 수 없다. Versioned packaging contract가 정의된 이후 ingest gate에 추가해야 한다.

## 9. Runtime Handoff Boundary

| Stage | Owner | Input | Output |
|---|---|---|---|
| Evidence Ontology | DA / 02 | Official Source | Evidence + Requirement Candidate |
| Requirement Classification | DA / 03 | 59 Requirement Candidates | Classification records |
| Gateway Control | DA / 03 | Classified Requirements | 22 Controls |
| Test | DA / 03 | Controls | 29 Test contracts |
| Policy Candidate | DA / 03 | Runtime/Evaluation Controls + Tests | 11 candidates |
| Data/Policy Evaluation | Downstream DA/Handoff | Candidate + required artifacts | Evaluated candidate result |
| PolicyEvaluation Artifact | Downstream contract | Evaluated result + binding | BE ingest artifact |
| Policy Snapshot | BE | Validated handoff | Versioned Runtime snapshot |
| Runtime Decision | BE | Pinned snapshot + canonical Runtime Context | Decision + audit lineage |

03 repository에는 독립된 `PolicyEvaluation Artifact` 파일이 없다. 이름과 schema는 downstream에서 확정되어야 한다.

## 10. Runtime Consumption Invariants

- `processed/controls.json`, `tests.json`, `policy_candidates.json`, `traceability.json`을 canonical 03 inputs로 사용한다.
- Policy Candidate를 Runtime에서 직접 실행하지 않는다.
- `provisional/project_provisional_rules.json`의 9건도 active policy로 취급하지 않는다.
- DA Policy Candidate identity와 BE PolicySnapshot identity를 분리한다.
- Evidence → Requirement → Control → Test → Policy Candidate lineage를 보존한다.
- `REVIEW`, `UNRESOLVED`, `VALIDATION_REQUIRED`를 default ALLOW로 변환하지 않는다.
- `promotion_blocked=true` 후보는 snapshot build 대상에서 제외한다.
- Runtime Context와 candidate applicability의 binding이 없거나 불일치하면 적용하지 않는다.
- Regulatory `data_class` 문자열을 BE Runtime Data Class로 직접 cast하지 않는다.
- Transform strategy와 강도를 임의 선택하거나 완화하지 않는다.
- Legacy GR action과 DA candidate action, BE PolicyAction, BE FinalAction을 분리한다.
- Policy Snapshot이 생성되면 version/digest/effective identity를 Runtime Decision 동안 pinning한다. 이 identity는 03 artifact에 현재 존재하지 않으며 BE/downstream contract의 책임이다.

## 11. Implementation Impact

| Interface / Boundary | Responsibility |
|---|---|
| Artifact Loader | Active processed artifacts만 load. Legacy/review file 제외 |
| Schema Validator | Control/Test/Policy Candidate schemas 검증 |
| Typed Reference Resolver | Requirement, Control, Test, Candidate lineage resolve |
| Policy Candidate Normalizer | DA candidate action을 BE action type과 분리 |
| Promotion Gate | Validation dependencies와 `promotion_blocked` 강제 |
| Runtime Binding Validator | Workload, actor, purpose, processing phase binding 검증 |
| Data Class Crosswalk | DA candidate data class와 BE Runtime Data Class 분리·mapping |
| Transform Strategy Resolver | Evaluated transform만 선택. UNRESOLVED fail-closed |
| Applicability Evaluator | Canonical Runtime Context와 candidate applicability 비교 |
| Policy Snapshot Builder | Evaluation 완료 artifact를 versioned/digested snapshot으로 생성 |
| Conflict Resolver | Candidate 충돌 시 명시된 policy만 적용. Default allow 금지 |
| Audit Provenance | Policy Snapshot에서 PC/CTRL/TEST/RC/EV까지 lineage 보존 |

## 12. Open Items

- [ ] `PC-006`, `PC-011`의 REVIEW_REQUIRED Evidence backlog를 해소한다.
- [ ] `PC-004`, `PC-009`, `PC-011`의 final Transform을 data evaluation으로 결정한다.
- [ ] `CTRL-EVAL-001`, `CTRL-RUNTIME-008`의 privacy risk, utility, relationship preservation 평가 artifact를 생성한다.
- [ ] 29개 Test의 required artifact를 실행·수집하고 VALIDATED 승격 기준을 적용한다.
- [ ] `GR-0008`에서 분해된 `RC-00026/33/34/49`와 `RC-00038/39`의 promoted policy 필요성을 검토한다.
- [ ] Policy Candidate → PolicyEvaluation Artifact의 schema와 approval lifecycle을 정의한다.
- [ ] Artifact-level `artifact_id`, `version`, `digest`, `schema_version` contract를 정의한다.
- [ ] Workload/Purpose Binding과 Data Class Crosswalk의 versioned contract를 정의한다.
- [ ] Candidate conflict/priority/combination contract를 정의한다.
- [ ] BE 실제 artifact loader 연결은 별도 구현 상태 확인이 필요하다.

## 13. Developer Summary

03 Gateway Rules는 법령을 바로 코드화한 active Rule Set이 아니다. 02의 59개 Requirement를 22개 Control, 29개 Test, 11개 Policy Candidate로 분리한 DA artifact다. 모든 Policy Candidate는 `VALIDATION_REQUIRED`이고 active candidate는 없다. Candidate action은 REVIEW 또는 UNRESOLVED이며 BE Final Action이 아니다. Transform 7종도 평가 옵션일 뿐 최종 선택이 아니다. `PC-006`과 `PC-011`은 Evidence backlog 때문에 promotion이 차단된다. BE는 Policy Candidate를 직접 실행하지 않고 evaluation과 정식 handoff를 거쳐 versioned Policy Snapshot으로 받아야 한다. Runtime Decision에는 pinned snapshot identity와 EV/RC/CTRL/TEST/PC lineage가 함께 보존되어야 한다.
