# 02 Evidence Ontology — Developer Handoff

02 Evidence Ontology의 frozen artifact를 BE 관점에서 정의한다. 이 계층은 Runtime Policy를 생성하지 않는다.

## Current Scope

| Layer | Status | Scope |
|---|---|---|
| Official Source | READY | 공식 원문과 source manifest 보존 |
| Evidence | FROZEN | 59 records. VERIFIED 49 / REVIEW_REQUIRED 10 |
| Requirement Candidate | FROZEN | 59 records. CANDIDATE 49 / REVIEW_REQUIRED 10 |
| Schema / Reference Validation | PASS | Schema error, duplicate ID, dangling reference 없음 |
| Control / Test / Policy Candidate | DOWNSTREAM | `03_gateway_rules` ownership |
| Runtime Policy / Transform / Threshold | OUT OF SCOPE | 02에서 결정하지 않음 |

## 1. Source Artifacts

### Active artifacts

| Artifact | Role | Source of Truth | Runtime Use |
|---|---|---|---|
| `raw/official_sources/official_sources_manifest.json` | 공식 출처 index | Source discovery 및 원문 위치 | 직접 사용 금지. Evidence provenance 확인용 |
| `processed/evidence_master.json` | Final Evidence master, 59 records | **Evidence object와 `original_text`의 canonical source** | 직접 Policy 실행 금지. Governance/traceability 입력 |
| `processed/evidence_master.csv` | Evidence tabular projection | JSON의 분석·검토용 mirror | Runtime consume 금지 |
| `processed/evidence_ontology.json` | Frozen domain/status index | 59 Evidence의 freeze/index 상태 | Discovery 및 freeze 확인용. Record source 아님 |
| `processed/requirement_candidates.json` | Final DA handoff, 59 records | **Requirement Candidate canonical source** | 03 Control/Test/Policy Candidate 생성 입력. 직접 decision 금지 |
| `review/review_required.json` | Unresolved Evidence queue, 10 records | REVIEW_REQUIRED 대상과 사유 | 자동 ALLOW/BLOCK 근거로 사용 금지 |
| `review/validation_report.json` | Final validation/freeze report | Count, schema/reference integrity, freeze state | Ingest gate metadata로 사용 가능. Runtime Policy 아님 |
| `review/evidence_verification_report.json` | 검증 결과 copy | Evidence verification 결과 | Governance/audit 참고 |
| `review/downstream_todo.json` | Cross-layer issue queue | 03에서 검토할 미확정 항목 | Runtime consume 금지 |
| `config/evidence_schema.json` | Evidence JSON Schema | Evidence structural contract | Loader validation contract |
| `config/requirement_candidate_schema.json` | Requirement Candidate JSON Schema | Requirement structural contract | Loader validation contract |

### Non-active artifacts

- `output/evidence.json`, `output/evidence.csv`, `data/reviewed/evidence_candidates.json`, `notebooks/evidence_review_49*.json`: 49-record intermediate/review artifacts. Final Source of Truth가 아니다.
- `review/archive/*`: reverification 이전 snapshot. Active ingest 대상이 아니다.
- `rules/gateway_rules.*`는 03의 legacy provenance이며 02 artifact가 아니다.

## 2. Evidence Contract

Contract: `config/evidence_schema.json`

Cardinality: array of 59 Evidence objects.

ID format: `EV-00000` pattern.

| Field | Meaning | Required | Runtime Impact |
|---|---|---:|---|
| `evidence_id` | Evidence stable reference | Yes | Requirement lineage key. Policy identity 아님 |
| `domain` | `PRIVACY`, `AI`, `SAAS_CLOUD`, `DIGITAL_ASSET` | Yes | Regulatory taxonomy. Runtime Data Class 아님 |
| `source_id` | 공식 출처 identifier | Yes | Source provenance lookup |
| `source_type` | `law`, `decree`, `regulation`, `guideline`, `official_policy` | Yes | Authority/type metadata. Decision action 아님 |
| `source_name` | 법령·문서명 | Yes | Human-readable provenance |
| `article`, `paragraph`, `page`, `section` | 원문 위치 | Yes | Source verification. Empty string 허용 |
| `original_text` | 보존된 공식 원문 | Yes, non-empty | Evidence Source of Truth. Executable expression 아님 |
| `effective_date` | 효력 기준일 | Yes | `reference_date`와 any-of validation. Runtime effective policy date와 다름 |
| `reference_date` | 분석 기준일 | Yes, non-empty | Source temporal reference |
| `source_url` | 공식 출처 URL | Yes, non-empty | Provenance verification |
| `retrieved_at` | 수집 시각 | Yes, non-empty | Collection provenance |
| `applies_to` | 원문 적용 대상 | Yes | Requirement applicability 분석 입력 |
| `data_type` | 원문 기준 데이터 유형 목록 | Yes | Regulatory data description. Runtime Data Class 아님 |
| `processing_context` | 원문이 적용되는 처리 맥락 목록 | Yes | Downstream applicability 입력 |
| `condition` | 적용 조건 | Yes | Requirement derivation input |
| `required_action` | 요구행위 목록 | Yes | Control candidate input. 직접 action code 아님 |
| `prohibition` | 금지사항 목록 | Yes | Control candidate input. 직접 BLOCK 아님 |
| `exception` | 예외 목록 | Yes | Evaluation input. 자동 ALLOW 아님 |
| `review_status` | `VERIFIED` / `REVIEW_REQUIRED` | Yes | Downstream promotion gate |
| `verification_method` | `DIRECT_OFFICIAL_SOURCE` / `NOT_VERIFIABLE` | Yes | Evidence trust state |
| `verified_at` | 검증 시각 또는 null | Yes | Audit metadata |
| `review_note` | 검증 결과·미확정 사유 | Yes | Review queue context |

`additionalProperties=false`다. Loader는 unknown field를 조용히 버리지 말고 schema validation failure로 처리해야 한다.

## 3. Requirement Candidate Contract

Contract: `config/requirement_candidate_schema.json`

Cardinality: array of 59 Requirement Candidate objects.

ID format: `RC-00000` pattern.

### Semantic boundary

```text
Evidence
= official source text and provenance

Requirement Candidate
= Evidence에서 분석한 applicability와 control requirement 후보

Runtime Policy
= downstream evaluation 이후 선택되는 실행 규칙
```

| Field | Meaning | Required | Runtime Impact |
|---|---|---:|---|
| `requirement_id` | Requirement Candidate stable reference | Yes | Downstream Control/Test lineage key |
| `evidence_id` | Source Evidence reference | Yes | Must resolve to active Evidence master |
| `domain` | Evidence와 동일한 regulatory domain | Yes | Taxonomy metadata. Runtime Data Class 아님 |
| `candidate_status` | `CANDIDATE` / `REVIEW_REQUIRED` | Yes | Promotion eligibility input |
| `applicability.actor` | 적용 주체 | Yes | Downstream applicability input |
| `applicability.data` | 규제상 데이터 범주 목록 | Yes | Runtime Data Class로 직접 cast 금지 |
| `applicability.processing_context` | 적용 처리 맥락 목록 | Yes | Downstream mapping input |
| `source_derived_requirement.condition` | Evidence에서 추출한 조건 | Yes | Control/Test 설계 입력 |
| `source_derived_requirement.required_action` | 원문 유래 요구행위 | Yes | 직접 Runtime action 아님 |
| `source_derived_requirement.prohibition` | 원문 유래 금지 | Yes | 직접 BLOCK 아님 |
| `source_derived_requirement.exception` | 원문 유래 예외 | Yes | 직접 ALLOW 아님 |
| `interpretation_tags` | DA 분류 tag | Yes | Search/classification metadata |
| `deferred_runtime_considerations` | 03 이후로 이관된 실행 관련 고려사항 | Yes | `GATEWAY_POLICY_OR_TRANSFORM_STAGE`에서만 결정 |
| `prohibited_runtime_decision` | Direct runtime decision 금지 flag | Yes, constant `true` | Must never be bypassed |
| `review_note` | Candidate 검토 메모 | Yes | Governance context |

현재 59개 Requirement 모두 `prohibited_runtime_decision=true`다. 18개 Requirement에는 ALLOW 8, BLOCK 9, DETECT 3, MASK 1 성격의 source tag가 deferred consideration으로 남아 있다. 이 값은 action selection이 아니다.

## 4. Verification State

### Evidence state

| State | Count | Downstream handling |
|---|---:|---|
| `VERIFIED` | 49 | Requirement evaluation input으로 사용 가능. Runtime action은 여전히 금지 |
| `REVIEW_REQUIRED` | 10 | 자동 promotion 금지. Review queue 유지 |

### Requirement state

| State | Count | Downstream handling |
|---|---:|---|
| `CANDIDATE` | 49 | 03 classification 및 Control/Test 설계 가능 |
| `REVIEW_REQUIRED` | 10 | 확정 Control 또는 완화된 Runtime action으로 자동 승격 금지 |

### REVIEW_REQUIRED IDs

- PRIVACY: `EV-00025`, `EV-00027`
- SAAS_CLOUD: `EV-00029`, `EV-00046`, `EV-00047`
- DIGITAL_ASSET: `EV-00053`~`EV-00057`
- AI: 없음

`REVIEW_REQUIRED` Evidence의 `verification_method`는 모두 `NOT_VERIFIABLE`이다. 사유는 source URL·원문 위치·PDF 페이지 재검증 미완료, source version/effective date 불일치 가능성, actor 공백 또는 일부 field quality 문제다.

Schema에 `UNKNOWN` state는 없다. Missing 또는 unknown enum은 schema error다. Loader가 임의 default를 적용해서는 안 된다.

## 5. Regulatory Taxonomy

| Regulatory Domain | Count | Scope |
|---|---:|---|
| `PRIVACY` | 32 | 개인정보·가명정보·제3자 제공·위탁·보안통제 |
| `AI` | 8 | 금융 AI·외부 AI·입출력 데이터 보호 |
| `SAAS_CLOUD` | 9 | SaaS·Cloud·내부망·접근통제·모니터링 |
| `DIGITAL_ASSET` | 10 | 가상자산 거래·고객확인·자산 분리·지갑주소 |

Concept boundaries:

```text
Regulatory Domain
≠ Runtime Data Class
≠ Processing Context
≠ Workload
≠ Purpose
```

- `domain`: 규제 근거의 분류다.
- `data_type` / `applicability.data`: 규제 문서에서 추출한 데이터 표현이다.
- `processing_context`: 규제가 적용되는 처리 상황이다.
- Runtime Data Class, Workload, Purpose는 02 schema에 없다.
- Crosswalk 또는 Runtime Binding 없이 문자열을 서로 같은 enum으로 취급하면 안 된다.

## 6. Handoff Boundary

```text
Evidence Ontology
→ Requirement Candidate
→ Gateway Control / Test
→ Policy Candidate
→ downstream evaluation artifact
→ BE Policy Snapshot
→ Runtime Decision
```

| Stage | Owner | Input | Output |
|---|---|---|---|
| Official Source | DA / 02 | 공식 법령·가이드·정책 | Raw source + source manifest |
| Evidence | DA / 02 | Official Source | `evidence_master.json` |
| Requirement Candidate | DA / 02 | Evidence | `requirement_candidates.json` |
| Requirement Classification | DA / 03 | 59 Requirement Candidates | `requirement_classification.json` |
| Control / Test | DA / 03 | Classified Requirement | `controls.json`, `tests.json` |
| Policy Candidate | DA / 03 | Control + Test | `policy_candidates.json` |
| Policy Evaluation / Activation | Downstream | Policy Candidate + evaluation result | Evaluated policy artifact |
| Policy Snapshot | BE | Evaluated DA handoff | Versioned BE runtime snapshot |
| Runtime Decision | BE | Policy Snapshot + canonical runtime context | Runtime decision + audit lineage |

02에는 `PolicyEvaluation`, `runtime_binding`, Workload/Purpose Binding, Runtime Data Class Crosswalk가 없다. 해당 계약을 02 값에서 추론하지 않는다.

## 7. Runtime Consumption Rules

- `processed/evidence_master.json`과 `processed/requirement_candidates.json`만 active record source로 취급한다.
- 49-record intermediate artifact와 `review/archive/*`를 active ingest하지 않는다.
- Evidence `original_text`를 Runtime expression으로 실행하지 않는다.
- Requirement Candidate를 ALLOW/BLOCK/TRANSFORM으로 직접 변환하지 않는다.
- `prohibited_runtime_decision=true` invariant를 강제한다.
- `REVIEW_REQUIRED` Evidence/Requirement를 자동 ALLOW 또는 완화 근거로 사용하지 않는다.
- `requirement.evidence_id`는 active Evidence master의 `evidence_id`로 resolve되어야 한다.
- Regulatory Domain, regulatory data, processing context, Runtime Data Class, Workload, Purpose를 혼합하지 않는다.
- Evidence의 `effective_date`를 BE Policy Snapshot의 activation/effective time으로 재사용하지 않는다.
- DA source reference와 BE Policy Snapshot identity를 같은 identifier로 취급하지 않는다.
- Runtime Decision은 02 Evidence ID가 아니라 downstream에서 선택·활성화된 Policy Snapshot identity를 기준으로 해야 한다. Evidence/Requirement reference는 audit lineage로 보존한다.
- 현재 02 artifact에는 artifact-level `version`, `digest`, `artifact_id`, `schema_version`이 없다. 존재하지 않는 identity를 합성해 canonical field처럼 저장하지 않는다.

## 8. Implementation Impact

02 handoff가 요구하는 인터페이스와 경계다. 현재 BE 구현 완료 여부를 의미하지 않는다.

| Component / Boundary | Required behavior |
|---|---|
| Evidence Artifact Loader | Active JSON만 load. Intermediate/archive 제외 |
| Requirement Artifact Loader | 59 Requirement Candidate load 및 Evidence reference resolve |
| JSON Schema Validator | Draft 2020-12 schema, enum, ID pattern, required field, `additionalProperties=false` 검증 |
| Reference Integrity Validator | Official Source → Evidence → Requirement Candidate lineage 확인 |
| Verification Gate | VERIFIED/CANDIDATE와 REVIEW_REQUIRED 분리. Unknown/missing reject |
| Runtime Decision Guard | `prohibited_runtime_decision=true` 강제. Direct action mapping 거부 |
| Taxonomy Mapping Boundary | Regulatory data/context와 Runtime Data Class/Workload/Purpose 간 versioned crosswalk 분리 |
| Requirement → Policy Boundary | 03 Control/Test/Policy Candidate 및 evaluation artifact를 거치도록 강제 |
| Artifact Identity Boundary | DA source artifact identity와 BE Policy Snapshot identity 분리 |
| Audit Lineage | Policy Snapshot에서 Requirement/Evidence까지 typed reference 보존 |
| Encoding / Data Quality Gate | REVIEW_REQUIRED record의 actor 및 일부 data field 품질 검토 없이 promotion 금지 |

02 artifact는 record-level ID만 제공한다. Artifact version/digest validation을 구현하려면 별도 manifest 또는 downstream packaging contract가 필요하다.

## 9. Open Items

- [ ] REVIEW_REQUIRED 10건의 source URL, 원문 위치, PDF page, version/effective date를 재검증한다.
- [ ] `EV-00055`, `EV-00057` 등의 actor 공백을 검토한다.
- [ ] 일부 REVIEW_REQUIRED record의 손상되거나 불명확한 `data_type` 값을 원문과 대조한다.
- [ ] 18개 deferred runtime consideration을 03 이후 Control/Test/evaluation 단계에서 해소한다.
- [ ] `03_gateway_rules`의 downstream todo인 `GR-0008`과 AI Evidence `EV-00038`, `EV-00039`의 cross-domain reference를 검토한다.
- [ ] 02 artifact-level `artifact_id`, `version`, `digest`, `schema_version` packaging contract를 정의한다.
- [ ] Regulatory data/context → Runtime Data Class/Workload/Purpose crosswalk와 Runtime Binding contract를 downstream에서 정의한다.
- [ ] Requirement Candidate가 evaluated Policy artifact로 승격되는 approval/evaluation contract를 확정한다.

## 10. Developer Summary

02 Evidence Ontology는 Runtime Policy가 아니다. 공식 원문을 59개 Evidence와 59개 Requirement Candidate로 정규화한 frozen DA artifact다. Active Source of Truth는 `processed/evidence_master.json`과 `processed/requirement_candidates.json`이다. 49건은 VERIFIED/CANDIDATE이고 10건은 REVIEW_REQUIRED다. 모든 Requirement는 `prohibited_runtime_decision=true`이므로 직접 ALLOW/BLOCK/TRANSFORM으로 해석할 수 없다. BE는 03의 Control·Test·Policy Candidate와 downstream evaluation을 거친 artifact만 Runtime Policy로 받아야 한다. Evidence와 Requirement reference lineage는 보존하되 DA source identity와 BE Policy Snapshot identity는 분리한다. 현재 02에 없는 artifact version/digest와 Runtime Binding은 별도 contract 없이는 추론하지 않는다.
