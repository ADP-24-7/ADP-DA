# 03 Gateway Rules — DA Analysis

## 1. 분석 목적

02 Evidence Ontology는 공식 법령·가이드라인을 59개 Evidence와 59개 Requirement Candidate로 구조화했다. 03 Gateway Rules는 그 Requirement를 실제 Gateway 설계에서 다룰 수 있는 Control, Test, Policy Candidate로 변환하는 단계다.

이 과정의 목적은 법령 문구를 곧바로 ALLOW·BLOCK 규칙으로 바꾸는 것이 아니다. Requirement가 요구하는 보호 목적을 시스템 통제 단위로 정리하고, 그 통제가 지켜졌는지를 확인할 Test를 분리한 뒤, Runtime 적용 가능성이 있는 항목만 Policy Candidate로 제시하는 것이다.

```text
Evidence → Requirement Candidate → Control → Test → Policy Candidate
```

Policy Candidate는 법령 자체가 아니며 최종 Runtime Policy도 아니다. 데이터 평가와 Runtime policy validation을 거쳐 승격할 수 있는 DA 분석 후보다.

## 2. 분석 대상

| 분석 대상 | 건수 | 역할 |
|---|---:|---|
| Requirement Candidate | 59 | 02 Evidence에서 추출된 규제 요구와 적용성 정보 |
| Control | 22 | 여러 Requirement를 공통 통제 목적과 enforcement point로 구조화 |
| Test | 29 | Control의 기대 동작, 실패 조건, 필요한 검증 산출물 정의 |
| Policy Candidate | 11 | Runtime 관련 또는 평가 의존 Control의 적용 후보 |

Requirement 59건은 22건의 `RUNTIME_ENFORCEABLE`, 22건의 `GOVERNANCE_CONTROL`, 10건의 `NON_RUNTIME_REFERENCE`, 5건의 `EVALUATION_DEPENDENT`로 분류되었다. 이는 각 Requirement의 primary classification이며 전체 59건을 중복 없이 집계한 결과다.

기존 `GR-0001`~`GR-0022` 22개 규칙은 migration provenance로 보존되지만 active Runtime Policy가 아니다. 현재 Control·Test·Policy Candidate는 legacy Rule을 1:1로 옮긴 것이 아니라 Requirement의 의미와 통제 목적을 다시 묶어 만든 산출물이다.

## 3. 분석 방법

Requirement 분석 → 통제 목적 추출 → Control 구조화 → 검증조건을 Test로 분리 → Runtime 적용 가능성을 Policy Candidate로 분리 → schema·mapping·lineage 검증

### 3.1 Requirement 분석과 분류

- 무엇을 분석했는가: 02의 59개 Requirement Candidate에서 domain, 적용 주체, 데이터 범위, 처리 맥락, 요구행위, 금지, 조건, Evidence 검증 상태를 읽었다.
- 왜 분리했는가: 모든 규제 요구가 Runtime에서 자동 실행될 수 있는 것은 아니기 때문이다.
- 산출물: `requirement_classification.json`. 각 Requirement를 Runtime 실행 가능, 거버넌스 통제, 평가 의존, 비Runtime 참고로 분류했다.

### 3.2 Control 구조화

- 무엇을 분석했는가: 공통 기술·거버넌스 목적을 공유하는 Requirement를 묶고 통제 유형, 목적, enforcement point, 처리 단계, 구현 경계, 검증 요구를 정의했다.
- 왜 분리했는가: 법령의 문장 단위와 시스템의 통제 단위가 항상 1:1로 대응하지 않기 때문이다.
- 산출물: 22개 Control. 하나의 Control이 여러 Requirement를 참조할 수 있다.

### 3.3 Test 분리

- 무엇을 분석했는가: Control별 기대 동작과 실패 조건, 검증에 필요한 artifact를 정의했다.
- 왜 분리했는가: 통제의 존재와 통제가 실제로 작동한다는 증거는 다른 문제이기 때문이다.
- 산출물: 29개 Test. Contract, Unit, Integration, Golden, Adversarial, Failure, Replay, Governance 유형으로 구성했다.

### 3.4 Policy Candidate 생성

- 무엇을 분석했는가: Runtime 관련 Control과 평가 의존 Control 중 후속 정책 평가가 필요한 항목을 선별했다.
- 왜 분리했는가: Control의 목적을 유지하면서도 action, transform, applicability를 검증 전 후보 상태로 보존하기 위해서다.
- 산출물: 11개 Policy Candidate. 모두 `VALIDATION_REQUIRED`이며 active policy는 없다.

### 3.5 검증과 추적성 확인

- 무엇을 분석했는가: Schema, ID 중복, 누락 참조, orphan Requirement, Test가 없는 Control, Policy가 없는 Runtime Control, REVIEW_REQUIRED 자동 승격, final transform·threshold의 조기 확정을 검사했다.
- 왜 분리했는가: 중간 참조가 끊기거나 검증되지 않은 후보가 Runtime 정책처럼 취급되는 것을 방지하기 위해서다.
- 산출물: `traceability.json`, `validation_report.json`, `orphan_report.json`, `downstream_todo.json`. 최종 validation 결과는 PASS다.

## 4. Control 분석

Control은 Requirement를 Gateway의 시스템 통제 단위로 구조화한 정의다. Control 자체는 Runtime Action이 아니다.

### 4.1 Runtime 관련 통제

`CTRL-RUNTIME-001`~`CTRL-RUNTIME-010` 10개가 해당한다.

- 데이터 접근·외부 전송: 목적과 수신자에 따른 외부 반출, 국외 이전, 내부망 경계를 통제한다.
- 데이터 처리·보호: 가명정보 mapping 분리, 비밀번호·규제 데이터 보호, AI 입력의 민감정보 탐지를 다룬다.
- 외부 제공자: 외부 AI의 데이터 재사용 제한과 SaaS·Cloud 환경의 계정·접근 경계를 다룬다.
- Digital Asset: 지갑주소, 고객확인 정보와 거래 필드의 분리·routing을 다룬다.

이 Control들은 Runtime 관련성이 있지만 모두 후속 validation을 요구한다. 예를 들어 `CTRL-RUNTIME-008`은 `RC-00040`에서 파생된 AI 입력 민감정보 탐지 Control이며, 탐지와 transform 평가가 완료되기 전에는 최종 action을 정하지 않는다.

### 4.2 평가 의존 통제

`CTRL-EVAL-001`은 가명처리의 개인정보 보호 수준과 데이터 효용을 비교하도록 설계된 Transform 평가 Control이다. `RC-00001`, `RC-00003`, `RC-00004`, `RC-00010`, `RC-00044`를 묶는다. 구체적인 변환 방식은 이 Control에서 선택하지 않는다.

### 4.3 거버넌스·참고 통제

`CTRL-GOV-001`~`CTRL-GOV-007`과 `CTRL-REF-001`~`CTRL-REF-004` 11개는 기록, 동의 요청 처리, 위탁업체 검토, 모니터링, AI 사용 관리, SaaS 제공자 검토, 디지털자산 보호 검토와 Evidence backlog를 다룬다.

이 11개에는 Test가 존재하지만 Policy Candidate는 없다. Runtime 자동 판단보다 문서화, 사람의 검토, 공급자 평가, Evidence 검증이 중심이기 때문이다. 이 구조는 모든 규제 요구를 억지로 Runtime 정책으로 만들지 않았음을 보여준다.

### 4.4 Control 유형 분포

22개 Control은 HUMAN_REVIEW 5건, PROVIDER_CONTROL 3건, EGRESS_CONTROL·AUDIT·MONITORING 각 2건, 그 밖에 AUTHORIZATION, PURPOSE_LIMITATION, SENSITIVE_DETECTION, TRANSFORM, VAULT_MAPPING, ENCRYPTION, NETWORK_CONTROL, DIGITAL_ASSET_FIELD_SEPARATION 각 1건으로 구성된다.

Control maturity는 `PROJECT_PROVISIONAL` 8건, `VALIDATION_REQUIRED` 14건이다. 이는 구현 또는 검증 수준을 표시하며 Runtime 활성 상태를 뜻하지 않는다.

## 5. Test 분석

Control은 지켜야 할 통제 목적이고, Test는 그 통제가 실제로 지켜졌는지를 판별하기 위한 검증 계약이다.

29개 Test는 다음과 같이 구성된다.

- Governance 12건
- Contract 5건
- Unit 3건
- Golden·Adversarial·Failure·Integration 각 2건
- Replay 1건

Runtime 관련 Test는 허용되지 않은 필드의 외부 반출, 목적·수신자 불일치 시 fail-closed, 재식별 목적 탐지, vault mapping의 외부 유출, 국외 이전 근거, 관리자 계정 allowlist, 네트워크 경계, 민감정보 탐지, 외부 AI 제공자 조건, 지갑·CDD 필드 분리 등을 검증하도록 정의되었다.

Governance Test는 검토 기록, 공급자 계약 근거, 모니터링 로그, Evidence backlog와 같은 문서·감사 artifact의 존재를 확인한다. 이 Test들은 Runtime Decision이 아니라 Control의 검증조건이다.

현재 Test 상태는 `VALIDATION_REQUIRED` 21건, `DEFINED` 8건이다. 실제 validation artifact가 없어 `VALIDATED`로 표시된 Test는 없다. 따라서 Test 정의가 있다는 사실만으로 Control이 검증 완료되었다고 볼 수 없다.

## 6. Policy Candidate 분석

11개 Policy Candidate는 10개 Runtime Control과 1개 평가 의존 Control에서 생성되었다. 거버넌스·참고 Control은 Policy Candidate로 만들지 않았다.

### 6.1 Action과 상태

- `REVIEW`: 8건
- `UNRESOLVED`: 3건
- `VALIDATION_REQUIRED`: 11건
- Active Policy Candidate: 0건

Schema는 ALLOW, BLOCK, TRANSFORM을 허용하지만 현재 semantic redesign 결과에서는 legacy 결정을 최종 action으로 복사하지 않았다. 11개 중 legacy action과 같은 candidate action은 1건뿐이며, 그것도 active policy가 아니다.

### 6.2 Runtime 적용 후보

- 외부 반출 목적·수신자 gate: `PC-001`
- 재식별 목적 guard: `PC-002`
- 가명정보 mapping 분리: `PC-003`
- 가명처리 Transform 평가: `PC-004`
- 국외 이전·외부 반출 gate: `PC-005`
- 관리자 계정 접근통제: `PC-006`
- 내부망 경계: `PC-007`
- 자격증명·규제 데이터 보호: `PC-008`
- AI 입력 민감정보 탐지: `PC-009`
- 외부 AI 재사용 제한: `PC-010`
- Digital Asset 지갑·CDD 필드 분리: `PC-011`

이 목록은 적용 가능성 분석 결과이며 최종 Runtime Policy 목록이 아니다.

### 6.3 Transform 후보

실제 후보에 존재하는 옵션은 다음 7개다.

- `MASK`
- `HMAC-PSEUDO`
- `VAULT-TOKEN`
- `GENERALIZE`
- `FIELD-SEPARATION`
- `REMOVE`
- `KEEP`

`PC-004`와 `PC-009`는 여러 Transform 옵션을 비교해야 하므로 `candidate_transform=UNRESOLVED`다. `PC-011`도 지갑·CDD 필드에 대해 `FIELD-SEPARATION`, `MASK`, `KEEP`을 후보로 두고 Transform을 확정하지 않았다. `PC-003`과 `PC-008`에도 선택 가능한 옵션은 기록되어 있지만 `candidate_transform=NONE`이며, 어느 옵션도 최종 선택으로 해석할 수 없다.

### 6.4 승격 차단 후보

`PC-006`과 `PC-011`은 Evidence maturity가 `REVIEW_REQUIRED`이고 `promotion_blocked=true`다.

- `PC-006`: 관리자 계정 접근 Control. Evidence backlog 해소와 Runtime policy validation이 필요하다.
- `PC-011`: Digital Asset 지갑·CDD 필드 분리 Control. 데이터 평가, Evidence backlog 해소, Runtime policy validation이 필요하다.

나머지 9개는 `provisional/project_provisional_rules.json`에 포함되지만 모두 `VALIDATION_REQUIRED`다. 해당 파일명이나 포함 여부가 정책 활성화를 의미하지 않는다.

## 7. 주요 분석 결과

| 항목 | 결과 |
|---|---:|
| Requirement Candidate | 59 |
| Control | 22 |
| Test | 29 |
| Policy Candidate | 11 |
| Runtime 관련·평가 의존 Control 중 Policy Candidate 보유 | 11 |
| Governance·Reference Control 중 Policy Candidate 없음 | 11 |
| Policy Candidate `REVIEW` | 8 |
| Policy Candidate `UNRESOLVED` | 3 |
| Promotion blocked | 2 |
| Active Policy Candidate | 0 |
| Test `VALIDATION_REQUIRED` | 21 |
| Test `DEFINED` | 8 |
| Test `VALIDATED` | 0 |

Validation에서는 schema 오류, 중복 ID, dangling Requirement·Control·Test 참조, orphan Requirement, Test 없는 Control, Policy 없는 Runtime Control이 발견되지 않았다. 59개 Requirement 모두 traceability chain에 포함되었다.

## 8. 분석 결과 해석

### 법령 문구를 바로 ALLOW·BLOCK으로 만들지 않은 이유

Requirement에는 적용 대상, 데이터, 처리 맥락, 조건, 예외와 Evidence maturity가 함께 존재한다. 같은 요구도 Runtime에서 자동 검증할 수 있는 부분, 거버넌스 절차가 필요한 부분, 데이터 평가가 필요한 부분으로 나뉜다. 그래서 legacy Rule의 action을 그대로 새 Policy Candidate에 복사하지 않았다.

### Requirement와 Control을 분리한 이유

Requirement는 법령 Evidence에서 추출한 요구이고, Control은 같은 기술·거버넌스 목적을 공유하는 여러 Requirement를 시스템 통제 단위로 묶은 것이다. 예를 들어 외부 반출 Control `CTRL-RUNTIME-001`은 `RC-00002`, `RC-00015`, `RC-00019`를 함께 참조한다.

### Control과 Test를 분리한 이유

통제 목적을 정의하는 것만으로는 그 통제가 작동했음을 증명할 수 없다. Test는 expected behavior, failure condition, required artifact를 별도로 정의해 Control의 검증 가능성을 만든다. 현재 VALIDATED Test가 없는 것은 정의와 실제 검증 완료를 구분한 결과다.

### 모든 Control이 Policy Candidate가 아닌 이유

거버넌스 기록, 계약 검토, 사람의 판단, Evidence backlog 관리는 중요하지만 Runtime request에 자동 action을 내리는 규칙은 아니다. 11개 Governance·Reference Control에 Test는 있지만 Policy Candidate가 없는 이유다.

### Policy Candidate 단계를 둔 이유

Runtime 관련성이 있는 Control도 applicability, action, transform, evaluation artifact가 확정되지 않았다. Policy Candidate는 이러한 미확정 값을 보존하면서 후속 검증 대상으로 전달한다. 현재 11개 모두 validation이 필요하고 active 후보는 없다.

### Transform과 REVIEW의 의미

Transform은 데이터의 privacy risk와 utility, 업무상 관계 보존을 평가한 뒤 선택해야 한다. 따라서 여러 옵션은 후보로만 남았다. REVIEW와 UNRESOLVED는 분석 실패가 아니라 Evidence·데이터 평가·Runtime validation이 끝나기 전 자동 결정을 막는 상태다.

## 9. Runtime으로의 연결

Repository에서 확정된 DA chain은 다음과 같다.

```text
Official Source
→ Evidence
→ Requirement Candidate
→ Control
→ Test
→ Policy Candidate
```

03에는 별도의 `PolicyEvaluation Artifact` 파일이 존재하지 않는다. README도 Runtime activation, 최종 Transform과 threshold 선택을 03 범위 밖으로 둔다. 따라서 Runtime 연결은 다음 경계를 전제로 한다.

```text
Policy Candidate
→ downstream data/policy evaluation
→ evaluated handoff artifact
→ BE Policy Snapshot
→ Runtime Decision
```

대표 lineage는 실제 ID로 다음과 같이 추적된다.

- 개인정보 외부 반출: `EV-00002 → RC-00002 → CTRL-RUNTIME-001 → TEST-001/TEST-002 → PC-001`
- AI 입력 민감정보: `EV-00040 → RC-00040 → CTRL-RUNTIME-008 → TEST-021/TEST-022 → PC-009`
- Digital Asset 지갑정보: `EV-00057 → RC-00057 → CTRL-RUNTIME-010 → TEST-028/TEST-029 → PC-011`

BE는 Policy Candidate를 직접 Runtime action으로 실행하지 않고, 평가와 승격을 거친 Policy Snapshot을 사용해야 한다.

## 10. 핵심 결론

03 Gateway Rules는 59개 Requirement Candidate를 22개 Control과 29개 Test로 구조화했다. 그중 Runtime 관련성과 평가 필요성이 있는 Control에서 11개 Policy Candidate를 만들었다. 거버넌스와 참고 성격의 11개 Control은 Test만 두고 Runtime 후보로 승격하지 않았다. 모든 Policy Candidate는 validation이 필요하며 active 후보는 없다. Transform 옵션은 7종이 제시되었지만 최종 방식은 선택되지 않았다. REVIEW_REQUIRED Evidence에 의존하는 2개 후보는 promotion이 차단되었다. 이 구조는 규제 Requirement를 통제 목적, 검증조건, Runtime 적용 후보로 분리하면서 Evidence부터 Policy Candidate까지 추적 가능한 근거를 제공한다.
