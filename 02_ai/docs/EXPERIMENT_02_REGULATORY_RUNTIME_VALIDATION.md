# AI Experiment 02 — Regulatory Runtime Validation

Status: `OPEN / PRE_PROVIDER_VALIDATED / PROVIDER_GOVERNANCE_BLOCKED`

Provider calls: `0`

## 1. Objective

Experiment 02의 질문은 다음과 같다.

> 어떤 금융업무에서 왜 특정 데이터가 필요하며, 금융 규제·감독·보안·내부통제 기준에 따라 각 Field를 어떻게 통제해야 하고, 그 통제가 기존 FPG Runtime에서 실제 집행 가능한가?

E2는 단순 Regulatory RAG 실험이나 모델 성능대회가 아니다. 동일 Workload / Purpose / Regulatory Context / Internal Policy / Runtime Contract 아래에서 3개 모델을 실행하고, 출력 차이가 있더라도 FPG 통제가 일관되게 유지되는지를 검증한다. 최종 분석의 주체는 모델이 아니라 `FPG Control Consistency`다.

현재 NVIDIA destination governance가 미해소되어 Provider 실행은 승인되지 않았다. 따라서 pre-provider 결과만 관측 사실로 기록하고 3 Case × 3 Model 응답, latency, token과 response finding을 생성하거나 추정하지 않는다.

## 2. E1 Baseline

E1 canonical 문서 [AI_EXPERIMENT_01_MODEL_ONLY_RUNTIME_VALIDATION.md](AI_EXPERIMENT_01_MODEL_ONLY_RUNTIME_VALIDATION.md)는 목적/질문 → 독립변수·고정조건·provenance → Runtime chain과 fail-closed → 실행 결과·Response Guard → Bundle/DA 검증 → 관측 사실/설계 해석 → 한계 → 다음 실험의 흐름을 사용했다.

E1은 1 Case × 3 Model을 실제 실행했다. 세 모델 모두 Provider HTTP 200을 받았지만 Response Guard가 `RAW_VALUE_REFLECTION`을 탐지해 `REJECTED`, Controlled Delivery는 `WITHHELD`였다. 이는 Provider 성공과 Delivery 성공이 별도 상태임을 증명했다.

E2는 이 Runtime 의미와 E1 frozen data를 변경하지 않는다. E1 finding, token, latency 또는 모델 특성을 E2 결과로 재사용하지 않는다.

## 3. E1 → E2 Expansion

| 분석 범위 | E1 | E2 |
|---|---|---|
| 핵심 | Runtime 작동성 | 현업 규제·통제 근거와 Runtime 집행 가능성 |
| Workload / Purpose | 고정조건 | applicability와 business need의 시작점 |
| Regulatory RAG | 비교 대상 아님 | 10 source / 39 requirement / 13 gold query |
| Guidance / Internal Control | Runtime 조건 | 법령과 분리된 evidence layer |
| Field Requirement | 결과 field 중심 | 20 field의 필요·정확성·관계·release 계약 |
| Provider Governance | destination | region/retention/reuse 선행 gate |
| Provenance | source row | synthetic non-linkage와 temporal consistency 포함 |
| Runtime cases | 1 positive case | 3 positive + N1~N4 defense cases |
| Model comparison | 1 × 3 실제 실행 | 목표 3 × 3; 현재 0 Provider execution |

E2의 canonical evidence chain은 다음과 같다.

```text
Workload → Purpose → Subject / Action → Business Need → Requested Field
→ Regulatory Evidence → Supervisory / Security Guidance → Internal Policy / Control
→ Applicability → Field Requirement → Transform Intent → Runtime Enforcement
→ Model Execution → Response Guard → Delivery → Execution Evidence
```

## 4. Regulatory Evidence

[FINANCIAL_AI_REGULATORY_EVIDENCE_V2.json](../artifacts/experiment_02/FINANCIAL_AI_REGULATORY_EVIDENCE_V2.json)은 official source 10건과 runtime-mapped requirement 39건을 보존한다.

| Source type | 수 | 범위 |
|---|---:|---|
| LAW | 3 | 개인정보 보호법, 신용정보법, AI 기본법 |
| REGULATION | 2 | AI 기본법 시행령, 전자금융감독규정 |
| SUPERVISORY_GUIDELINE | 2 | 금융위원회 AI 가이드라인, 금융감독원 AI 위험관리 프레임워크 |
| SECURITY_GUIDANCE | 3 | 금융보안원 AI 보안, 프런티어 AI, SaaS 보안 해설 |

39개 requirement는 `APPLICABLE` 20, `CONDITIONAL` 5, `NOT_APPLICABLE` 14다. `UNMAPPED`와 requirement-level `UNRESOLVED`는 0이다.

각 requirement는 source identity, authority, effective date, article/section, applicability condition, FPG control, Runtime stage, expected decision, evidence field와 content digest를 가진다. Internal Control은 법령과 합치지 않고 별도 evidence layer로 유지한다.

## 5. Internal Policy / Control

최종 field/case contract에서 직접 사용되는 internal controls는 다음 6건이다.

- `CTRL-EVAL-001`: transform suitability evaluation
- `CTRL-RUNTIME-001`: purpose/recipient outbound gate
- `CTRL-RUNTIME-003`: pseudonym mapping separation
- `CTRL-RUNTIME-008`: AI input sensitive-data detection
- `CTRL-GOV-003`: provider governance
- `CTRL-RUNTIME-009`: external AI reuse restriction

Project control catalog는 19건이다. 법적 결론이 아니라 FPG 운영 evidence이며 법령 applicability와 독립적으로 표시한다.

[E2_INTERNAL_CONTROL_ROLE_CLASSIFICATION_V1.json](../artifacts/experiment_02/E2_INTERNAL_CONTROL_ROLE_CLASSIFICATION_V1.json)은 19건을 누락 없이 분류한다. Direct 6건은 E2 field/case의 Runtime decision 또는 evidence에 직접 결합되고, Indirect 5건은 Policy/Applicability 입력이지만 독립 final allow/block 근거는 아니다. Governance 8건은 audit, provider assurance 또는 human review를 소유하며 Runtime 직접 binding 대상이 아닌 이유와 적용 위치를 각각 보존한다. `UNMAPPED = 0`이다.

| Role family | 수 | 역할 |
|---|---:|---|
| DIRECT | 6 | `DIRECT_RUNTIME_CONTROL` |
| INDIRECT | 5 | `POLICY_INPUT` |
| GOVERNANCE | 8 | `AUDIT_ONLY`, `GOVERNANCE_ONLY`, `PROVIDER_GOVERNANCE`, `HUMAN_REVIEW` |

### Current BE Runtime semantics

최신 BE `origin/main`의 Runtime과 calibration contract를 병합 후 재검토했다. E2 artifact와 문서는 다음 production 의미를 바꾸지 않는다.

```text
Authentication
→ Authorization
→ Workload / Purpose / Subject / Action binding
→ Policy
→ Retrieval
→ Transform
→ Outbound Guard
→ Provider
→ Response Guard
→ Controlled Delivery
→ Evaluation Bundle
→ Stage Timing / Trace
```

Policy와 Authorization은 별도 decision이다. Outbound Guard `PASSED`는 Provider governance 승인과 같지 않다. Provider HTTP 성공은 Response Guard나 Delivery 성공과 같지 않다.

최신 V50은 `RAW_VALUE_REFLECTION`에 source data class, transform strategy, field treatment와 hashed outbound field path를 추가하는 additive migration이다. 기존 V49 finding을 추정 backfill하지 않으며 metadata가 없으면 calibration readiness는 `REFLECTION_METADATA_MISSING`으로 fail-closed 한다.

Repository V50은 기존 `adp_exp02_v49`에 정상 Spring Boot/Flyway 경로로 1회 적용됐다. applied latest는 V50, failed migration과 checksum mismatch는 0이며 BE readiness는 `UP`이다. DB 삭제·재생성, Flyway repair, image rebuild는 수행하지 않았다.

## 6. Workload / Purpose

| Context | Frozen value |
|---|---|
| Evaluation run | `ai-experiment-02-financial-regulatory-v5` |
| Workload | `customer_summary` — Synthetic customer account and recent-transaction summary |
| Business domain | `BANKING_CUSTOMER_SUPPORT` |
| Purpose | `CUSTOMER_SUPPORT` — authorized internal factual summary |
| Subject scope | `ONE_AUTHORIZED_SYNTHETIC_CUSTOMER` |
| Action | `GENERATE_INTERNAL_SUPPORT_SUMMARY` |
| Requester | authorized support operator or evaluation harness |
| Dataset | `financial_synthetic_processed_v1` |
| Data scope | `SYNTHETIC_NON_PERSONAL` / real-person linkage `NONE` |

Workload/Purpose는 직원이 FE에서 입력해 업무를 수행하는 값이 아니다. 관리자가 어떤 업무·목적·요청자·field·control·외부 승인조건이 적용됐는지 추적하는 read-only governance context다. FE에 Prompt/Chat/Run/Model 선택 기능을 추가하지 않는다.

### Synthetic Data Provenance

[E2_SYNTHETIC_TEMPORAL_PROVENANCE_V1.json](../artifacts/experiment_02/E2_SYNTHETIC_TEMPORAL_PROVENANCE_V1.json)은 평가 기준일 `2026-09-11`, retrieval window 90일과 여섯 transaction의 original/normalized timestamp를 보존한다. 최신 row는 기준일 -14일, 이전 row는 -28일로 정규화했다.

customer/account 관계, amount, transaction type, balance 관계, regulatory trigger, workload/purpose, transform obligation과 destination contract는 바꾸지 않았다. `temporal_consistency_status = VERIFIED`이며 실고객·실거래 data로 대체하지 않았다.

## 7. RAG Validation

| Metric | 결과 |
|---|---:|
| Query | 13 |
| Hit@1 | `13/13 = 1.0` |
| Hit@3 | `13/13 = 1.0` |
| Hit@5 | `13/13 = 1.0` |

이전 Q04와 Q06 Top1 miss는 [E2_RAG_TOP1_MISS_ANALYSIS_V1.json](../artifacts/experiment_02/E2_RAG_TOP1_MISS_ANALYSIS_V1.json)에서 별도 분석했다. Q04의 `EFSR-CLOUD-IMPORTANCE`는 cloud 중요도 평가로 해외이전 법적 조건을 직접 답하지 않았고, Q06의 `AI-ACT-HIGH-IMPACT-CHECK`는 고영향 AI 해당성으로 신용정보 자동화평가 권리를 직접 답하지 않았다. 두 건 모두 단순 family 내 동률이 아니라 requirement-specific ranking 오류이므로 gold requirement를 Top1으로 교정했다. Applicability는 retrieval과 독립 평가되므로 현재 Runtime decision 영향은 없다. 재계산 결과 Hit@1/3/5는 모두 1.0이다.

RAG Retrieval Correctness는 evidence discovery 결과다. Hit@k를 Runtime enforcement, legal compliance 또는 model response grounding으로 해석하지 않는다.

## 8. Applicability

Applicability는 source가 corpus에 있다는 이유만으로 `APPLICABLE`을 부여하지 않는다. requirement의 workload, data, provider와 destination scope를 frozen E2 조건과 대조해 `APPLICABLE` 20, `CONDITIONAL` 5, `NOT_APPLICABLE` 14로 분리했다.

PIPA/신용정보법의 실제 개인·신용정보 제공 의무는 synthetic non-linkable 조건에서 자동 적용하지 않고 production real-data 확장 시 재평가한다. 반면 processing region처럼 실제로 확인되지 않은 destination 조건은 억지로 PASS시키지 않고 Provider Governance에서 `UNRESOLVED / REVIEW_REQUIRED`로 유지한다.

## 9. Field Requirement

최종 handoff [E2_TO_E3_TRANSFORM_REQUIREMENTS.json](../artifacts/experiment_03/E2_TO_E3_TRANSFORM_REQUIREMENTS.json)은 contract version `1.1.1`, digest `sha256:899cf31a920c1363cfb21b9c7d6f3204819222935bcbb9008a01ccbf9a8ba73e`다. 3 case × 20 field, 총 60 row이며 각 row는 다음 30개 필수 속성과 content digest를 가진다.

`case_id`, workload ID/name/domain, purpose code/description, subject/action, field/classification, business need/necessity, regulatory/guidance/internal IDs, applicability, requirement/intent/utility, candidate/prohibited methods, exact/relation/reversibility/release flags, destination, Runtime control/stage, reason과 evidence IDs.

### Field Requirement Summary

| Field group | Requirement | Final transform intent/method |
|---|---|---|
| customer/account/transaction ID | `RELATION_PRESERVE` | identity hide; stable HMAC/token; raw ID 금지 |
| `account.balance` | `REQUIRED_EXACT` | `KEEP` only |
| `transaction.amount` | `REQUIRED_EXACT` | `KEEP` only |
| prompt/category/time metadata | `REQUIRED_EXACT` | `KEEP` |
| 불필요 개인정보·raw account·free text | `REMOVE` / `PROHIBITED_EXTERNAL` | `REMOVE` |

### E2 Requirement Revision `E2-FIELD-REQ-REV-001`

E2 requirement consistency review는 `REQUIRED_EXACT`와 GENERALIZE candidate 사이의 contradiction을 확인했다.

E2 requirement owner는 두 field 각각에 previous requirement, revision reason, measured error evidence, business need, exact gate, approved requirement, prohibited transform, revision version과 revision digest를 기록하여 revision `1.1.1`을 `APPROVED`했다. 승인 결과는 `KEEP_ONLY`, `GENERALIZE prohibited`이며 Runtime activation을 자동 변경하지 않는다.

- `account.balance`: GENERALIZE exact match `0.0`, max absolute error `998.84`, ordering preservation 약 `0.0632`.
- `transaction.amount`: GENERALIZE exact match `0.0`, max absolute error `999.95`, threshold preservation 약 `0.9401`.
- 두 field 모두 `CUSTOMER_SUPPORT`의 사실 요약과 threshold 판단에 정확값이 필요하다.
- PIPA minimization은 불필요 field 제거를 요구하지만 필요한 synthetic financial fact의 부정확화를 요구하지 않는다.
- `FSC-RELIABILITY`, `FSC-GOOD-FAITH`, `CTRL-EVAL-001`, `CTRL-RUNTIME-001`, `CTRL-RUNTIME-008`과 synthetic-only destination constraint 아래에서 KEEP은 허용 가능하다.

따라서 GENERALIZE를 candidate에서 제거하고 prohibited method로 이동했으며 KEEP만 유지했다. 이 revision은 workload utility와 evidence에 기반한 E2 결정이다. current Runtime profile은 여전히 GENERALIZE이며 자동 변경·활성화하지 않았다.

## 10. Positive Runtime

| Case | Execution ID | Authorization | Policy | Retrieval | Transform | Outbound | Provider |
|---|---|---|---|---:|---|---|---|
| P1 | `exec_6ecfbcda-6e7d-4eba-a778-cae92571e850` | ALLOWED | TRANSFORM | 2 tx | APPLIED / 14 fields | PASSED | NOT_SENT |
| P2 | `exec_de6a4ea9-b08f-4b84-899b-7ee1f2042f68` | ALLOWED | TRANSFORM | 2 tx | APPLIED / 17 fields | PASSED | NOT_SENT |
| P3 | `exec_08d6c0b0-158a-42c3-a15f-3046f3f810c9` | ALLOWED | TRANSFORM | 2 tx | APPLIED / 14 fields | PASSED | NOT_SENT |

required transaction context가 존재하고 Transform과 Outbound Guard가 통과했다. 그러나 결과는 “외부 실행 성공”이 아니라 `PASS_TO_PROVIDER_GOVERNANCE_GATE`다.

## 11. Negative Runtime N1~N4

| Case | 방어 대상 | 앞 단계 | 목표 stage | Provider | 판정 |
|---|---|---|---|---|---|
| N1 | Authorization scope | Authentication PASS | Authorization DENIED | NOT_CALLED | PASS |
| N2 | Authorization subject | Authentication PASS | Authorization DENIED | NOT_CALLED | PASS |
| N3 | Policy | Authorization ALLOWED | Policy BLOCK | NOT_CALLED | PASS |
| N4 | Outbound | Auth ALLOWED, Policy TRANSFORM, Retrieval/Transform PASS | Outbound BLOCKED | NOT_CALLED | PASS |

N3는 REVIEW를 강제 BLOCK으로 바꾸지 않고 기존 Policy BLOCK 조건을 사용했다. N4는 request validation이나 required field 완화가 아니라 기존 Outbound Guard 소유 조건에서 차단했다. 각 fixture는 정확히 한 defense stage를 증명하며 Provider 증가량은 0이다.

Positive와 Negative를 함께 보면 허용 가능한 payload는 Provider governance 직전까지 조건부 통과하고, 위반 요청은 올바른 stage에서 fail-closed 한다.

## 12. Provider Governance

| Risk | Evidence | Decision |
|---|---|---|
| Processing region | `UNRESOLVED` | 승인 불가 |
| Retention | session end default; security/fraud/abuse 예외 기간 미명시 | REVIEW_REQUIRED |
| Training/reuse | product/service 및 AI model improvement reuse 허용 | FPG restriction과 미해소 |
| Synthetic minimization | fully synthetic, non-linkable, allowlisted | privacy exposure 감소; destination risk 해소 아님 |

Provider baseline은 request `0`, connector execution `0`, AI model execution evidence `0`이다. Manual override는 없다.

향후 Human Review가 예외 승인하더라도 `Provider Risk = REVIEW_REQUIRED`와 `Human Review = APPROVED_WITH_EXCEPTION`을 별도 보존한다. 위험 자체를 `PASS`로 덮지 않는다.

## 13. Model별 Validation Contract

### 13.1 Nemotron 3.5 Lightning

| 항목 | 현재 evidence |
|---|---|
| Case별 Runtime Result | 3 case 모두 Provider `NOT_EXECUTED` |
| Regulatory / Internal Policy Grounding | contract binding 존재; response grounding 미관측 |
| Response Finding / Guard / Delivery | `NOT_AVAILABLE / NOT_EXECUTED / NOT_DELIVERED` |
| Evidence Completeness | model-specific execution 없음 |
| Provider / E2E Latency | `NOT_AVAILABLE` |
| Input / Output / Total Token | `NOT_AVAILABLE` |
| Error / Failure | model failure 없음; governance gate에서 미전송 |
| 모델 특이사항 | 관측 가능한 특이사항 없음 |

결과 원인은 Nemotron response가 아니라 공통 destination governance다.

### 13.2 Muse Glimmer 30B

| 항목 | 현재 evidence |
|---|---|
| Case별 Runtime Result | 3 case 모두 `NOT_EXECUTED` |
| Regulatory / Internal Policy Grounding | 동일 frozen contract 예정; model response 미관측 |
| Response Finding / Guard / Delivery | `NOT_AVAILABLE / NOT_EXECUTED / NOT_DELIVERED` |
| Evidence Completeness | model-specific execution 없음 |
| Provider / E2E Latency | `NOT_AVAILABLE` |
| Input / Output / Total Token | `NOT_AVAILABLE` |
| Error / Failure | model failure 아님; 실행 미승인 |
| 모델 특이사항 | 관측 가능한 특이사항 없음 |

### 13.3 Gemma 4 31B IT

| 항목 | 현재 evidence |
|---|---|
| Case별 Runtime Result | 3 case 모두 `NOT_EXECUTED` |
| Regulatory / Internal Policy Grounding | 동일 frozen contract 예정; model response 미관측 |
| Response Finding / Guard / Delivery | `NOT_AVAILABLE / NOT_EXECUTED / NOT_DELIVERED` |
| Evidence Completeness | model-specific execution 없음 |
| Provider / E2E Latency | `NOT_AVAILABLE` |
| Input / Output / Total Token | `NOT_AVAILABLE` |
| Error / Failure | model failure 아님; 실행 미승인 |
| 모델 특이사항 | 관측 가능한 특이사항 없음; E1 Gemma 결과를 복제하지 않음 |

### Case × Model execution matrix

| Case | Nemotron | Muse | Gemma |
|---|---|---|---|
| P1 | NOT_EXECUTED | NOT_EXECUTED | NOT_EXECUTED |
| P2 | NOT_EXECUTED | NOT_EXECUTED | NOT_EXECUTED |
| P3 | NOT_EXECUTED | NOT_EXECUTED | NOT_EXECUTED |

## 14. Cross-Model Metrics Contract

동일 Case, Workload, Purpose, RAG, Internal Policy, Prompt, Runtime Contract, Destination과 Generation Condition을 고정하고 Model만 변경한다.

| Metric | Nemotron | Muse Glimmer | Gemma |
|---|---|---|---|
| Regulatory Grounding | NOT_AVAILABLE | NOT_AVAILABLE | NOT_AVAILABLE |
| Internal Policy Grounding | NOT_AVAILABLE | NOT_AVAILABLE | NOT_AVAILABLE |
| Response Findings | NOT_AVAILABLE | NOT_AVAILABLE | NOT_AVAILABLE |
| Response Guard | NOT_EXECUTED | NOT_EXECUTED | NOT_EXECUTED |
| Delivery | NOT_DELIVERED | NOT_DELIVERED | NOT_DELIVERED |
| Provider Latency | NOT_AVAILABLE | NOT_AVAILABLE | NOT_AVAILABLE |
| E2E Latency | NOT_AVAILABLE | NOT_AVAILABLE | NOT_AVAILABLE |
| Input / Output / Total Tokens | NOT_AVAILABLE | NOT_AVAILABLE | NOT_AVAILABLE |
| Evidence Completeness | NOT_EXECUTED | NOT_EXECUTED | NOT_EXECUTED |
| Failure | governance blocked | governance blocked | governance blocked |

현재 비교 가능한 것은 공통 Provider governance gate가 모델과 무관하게 fail-closed 했다는 점뿐이다. 출력 차이, grounding, completeness 또는 운영 성능을 비교할 수 없다. 종합점수와 ranking은 만들지 않는다.

### Latency / Token / Response Finding

[E2_CROSS_MODEL_OPERATIONAL_METRICS_CONTRACT_V1.json](../artifacts/experiment_02/E2_CROSS_MODEL_OPERATIONAL_METRICS_CONTRACT_V1.json)은 9개 Case×Model cell과 operational metric source를 digest `sha256:9383da5850e957007c63c7debade14ff5a7259b54192a3e7537a746440459e43`로 사전 고정한다.

| Metric | BE evidence source | 현재 값 |
|---|---|---|
| provider latency | Bundle `full_response_latency_millis` | null / NOT_AVAILABLE |
| response guard latency | Trace `RESPONSE_GUARD.duration_millis` | null / NOT_AVAILABLE |
| FPG runtime stage latency | non-provider stage duration sum | null / NOT_AVAILABLE |
| total execution latency | Trace `updated_at - created_at` | null / NOT_AVAILABLE |
| input/output/total tokens | Bundle runtime metrics | null / NOT_AVAILABLE |

`null`은 NOT_EXECUTED 또는 NOT_AVAILABLE이고 `0`은 실제 측정값이다. 모델별 tokenizer가 다르므로 token 수를 전역 효율 순위로 해석하지 않는다.

최신 BE native `responseFindingTypes`는 `RAW_VALUE_REFLECTION`, EMAIL/PHONE/ACCOUNT/RRN, key/token/credential/secret/seed 계열이다. V50 calibration API는 finding type을 source data class, transform strategy와 field treatment별 privacy-safe count로 제공하고 raw response/value/path를 노출하지 않는다.

요청된 `UNSUPPORTED_CLAIM`, `REGULATORY_GROUNDING_MISSING`, `REQUIRED_EVIDENCE_MISSING`, `POLICY_CONFLICT`, `INCOMPLETE_RESPONSE`는 현재 BE native finding이 아니다. 중복 enum을 생성하지 않고 `NOT_IMPLEMENTED_AS_NATIVE_BE_FINDING` GAP으로 mapping한다. `RESPONSE_GUARD_REJECTED`는 finding enum이 아니라 guard status/reason이다.

Stage timing은 현재 in-process recorder와 exported sidecar 계약이므로 process restart 이후 DB 기반 재구성이 보장되지 않는다. 최종 Bundle 전 restart-safe persistence를 확인해야 한다.

## 15. E1 ↔ E2 Comparison

- E1은 실제 1×3 Provider response, latency, token, Response Guard와 Delivery evidence를 보유한다.
- E2는 regulatory/control/field/positive-negative pre-provider 분석 범위가 E1보다 넓다.
- E2는 Provider 실행 0이므로 post-provider evidence 깊이는 아직 E1보다 낮다.
- E1 결과를 E2 cell에 복제하지 않고 미관측은 NOT_EXECUTED/NOT_AVAILABLE로 남겼다.
- E1과 E2 모두 관측 사실, 설계 해석, limitation과 handoff를 분리한다.

분석 구조는 퇴보하지 않았지만 실제 model execution evidence가 없으므로 E2를 FINAL로 닫을 수 없다.

## 16. FE Controller Contract

FE는 관리자/보안/AI Governance용 read-only Console이다. 실제 BE API가 제공하는 값만 표시하며 prompt/chat/run/model selection, transform 선택, 임의 score와 ranking을 제공하지 않는다.

| Group | 표시 contract |
|---|---|
| Workload Context | Workload, Purpose, Domain, Subject Scope, Requester Role |
| Regulation / Policy | Regulation, Guidance, Internal Policy, Applicability, Policy Version |
| Field Control | Field, Classification, Need, Requirement, Intent, Applied Transform, Utility, Release |
| Runtime | Authorization, Policy, Retrieval, Transform, Outbound, Provider, Response Guard, Delivery |
| Model Execution | Model, separated latency, token usage, finding, guard, delivery, evidence status |
| Governance | Provider Risk, Human Review, Exception Scope |
| Audit | Execution ID, Contract Version, Evidence Digest, Stage Timing |

FE는 Bundle/Trace metric을 분리 표시하고 null을 `NOT_AVAILABLE`로 표시한다. Bundle이 complete일 때만 최신 BE `/calibration-evidence` API를 호출해 privacy-safe finding group을 표시한다. E2처럼 Bundle이 없으면 `NOT_EXECUTED`를 표시하고 0ms/0token/빈 finding을 실제 결과처럼 표현하지 않는다.

Governance/field projection은 E2 handoff version `1.1.1`과 digest `sha256:899cf31a920c1363cfb21b9c7d6f3204819222935bcbb9008a01ccbf9a8ba73e`를 사용한다. 상태는 `E2_POLICY_REQUIREMENT_VALIDATED`, `PROVIDER_GOVERNANCE_BLOCKED`, `PENDING_EXTERNAL_EXECUTION`으로 각각 분리한다.

현재 BE↔FE schema/type consistency는 test 대상이다. 9개 actual execution의 BE API ↔ Bundle ↔ FE value consistency는 evidence가 없어 `PENDING`이다.

## 17. E3 Handoff

E2 final requirement chain은 다음과 같다.

```text
Workload → Purpose → Regulatory / Internal Policy → Field Requirement
→ Transform Intent → Utility Requirement
```

[E2_TO_E3_TRANSFORM_REQUIREMENTS.json](../artifacts/experiment_03/E2_TO_E3_TRANSFORM_REQUIREMENTS.json)은 E2가 소유하는 유일한 E3 입력이다. version은 `1.1.1`, digest는 `sha256:899cf31a920c1363cfb21b9c7d6f3204819222935bcbb9008a01ccbf9a8ba73e`이며 20 field × 3 case = 60 row를 고정한다.

E3의 후속 질문은 “E2에서 현업·규제 기준으로 결정한 Transform Requirement를 적용했을 때 해당 업무에 필요한 Utility·정확값·관계성이 유지되는가?”다. E3는 E2 requirement를 임의 변경할 수 없으며 변경 필요성이 발견되면 E2 requirement owner에게 돌려보내야 한다.

이 작업에서는 Experiment 03 실행, 결과 생성, validation 또는 완료 판정을 수행하지 않았다. E2 종료점은 E3 input handoff freeze까지다.

## 18. Limitations / Remaining Gap

1. NVIDIA processing region, exceptional retention duration과 model-improvement reuse가 미해소다.
2. Provider 0건으로 3×3 response, grounding, unsupported claim, latency, token과 finding 비교가 없다.
3. repository와 대상 E2 DB latest는 모두 V50이며 BE readiness는 UP이다. 별도 `postgres-test`는 V41 checksum mismatch가 있어 일부 calibration integration test가 application context 시작 전에 중단되는 Known Test Environment Gap이다. Flyway repair와 기존 migration 수정은 수행하지 않는다.
4. V50 이전 response finding은 metadata backfill이 없으므로 calibration-ready로 간주할 수 없다.
5. Stage timing은 in-process evidence라 restart-safe persistence가 확인되지 않았다.
6. Unsupported claim/regulatory grounding/completeness는 BE native response finding으로 구현되지 않았다.
7. current Runtime `GENERALIZE`와 revised E2 `KEEP` 사이 두 profile gap이 남아 있다.
8. 9개 execution Bundle validation과 BE API ↔ Bundle ↔ FE actual-value consistency가 미완료다.
9. synthetic-only 결과를 실제 개인정보·신용정보 workload로 일반화할 수 없다.
10. Hit@k는 retrieval correctness이며 compliance나 response correctness의 증명이 아니다.

### Logical inference audit

| 질문 | Evidence 상태 | 결론 |
|---|---|---|
| 왜 이 AI 업무를 수행하는가 | workload/purpose/business need | PASS |
| 왜 해당 Field가 필요한가 | 60 field rows의 need/necessity/reason | PASS |
| 어떤 규제/내부통제가 적용되는가 | 39 requirement와 control binding | PASS |
| 왜 Transform이 필요한가 | transform intent와 release constraint | PASS |
| 왜 그 Transform Method인가 | E2 candidate/prohibited method와 utility requirement | PASS |
| Transform 후 업무 정보가 유지되는가 | E3 입력 contract만 freeze; E3 미수행 | PENDING_E3 |
| 외부 Provider로 전송 가능한가 | region/retention/reuse unresolved | NO / GOVERNANCE_BLOCKED |
| 모델별 출력 차이는 무엇인가 | Provider response 없음 | GAP / NOT_EXECUTED |
| 출력 차이에도 통제가 동일하게 작동하는가 | pre-provider만 관측 | GAP / POST_PROVIDER_PENDING |
| 관리자가 근거와 결과를 추적할 수 있는가 | BE/FE contract PASS, 9 actual rows 없음 | PARTIAL / ACTUAL_VALUE_PENDING |

### Closure decision

#### Validated

Validated 범위는 Source Coverage, Regulatory RAG, Applicability, Internal Control, Workload/Purpose, 60-row Field Requirement, positive pre-provider, N1~N4, E3 input handoff와 FE Controller Contract다. E2 Policy/Requirement 상태는 `E2_POLICY_REQUIREMENT_VALIDATED`이며 실제 미실행 값은 모두 NOT_EXECUTED/NOT_AVAILABLE/null semantics로 유지한다.

#### Pending

Pending 범위는 NVIDIA Provider Governance, 3×3 Provider execution, 실제 latency/token/response finding과 Cross-model Execution Bundle이다. external execution은 `PENDING_EXTERNAL_EXECUTION`, governance는 `PROVIDER_GOVERNANCE_BLOCKED`다. 따라서 E2 전체를 `FINAL EXECUTION COMPLETE`로 선언하지 않으며 Experiment 03 완료도 판정하지 않는다.
