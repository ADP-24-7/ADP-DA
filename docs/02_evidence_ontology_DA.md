# 02 Evidence Ontology — DA Analysis

## 1. 분석 목적

01 Industry Analysis에서는 금융산업에서 AI, SaaS, Cloud, Data, Digital Asset 활용이 실제 승인 과제, 정책자료, 은행 사례로 확장되는 흐름을 확인했다. 02 Evidence Ontology는 그 다음 단계로, 이러한 환경에서 금융 데이터를 처리할 때 어떤 법령·감독규정·가이드라인·공식 정책을 근거로 삼아야 하는지 분석한다.

목표는 법령 문장을 곧바로 실행 규칙으로 바꾸는 것이 아니다. 공식 원문을 추적 가능한 Evidence로 보존하고, 적용 대상·데이터·처리 맥락·조건·요구행위·금지·예외를 분석해 Requirement Candidate로 구조화하는 것이다. 이를 통해 원문 근거와 분석자의 해석을 분리하면서, 후속 Gateway Control·Test·Policy Candidate 설계에 사용할 수 있는 검증 가능한 입력을 만든다.

## 2. 분석 대상

최종 분석 기준은 `processed/evidence_master.json`의 59개 Evidence다. 하나의 Evidence는 하나의 규제 도메인에 속한다.

| 구분 | 분석 대상 | 건수 | 목적 |
|---|---|---:|---|
| PRIVACY | 개인정보 보호법, 신용정보법 시행령, 전자금융감독규정 및 관련 공식 정책 | 32 | 개인정보·가명정보 처리, 제3자 제공, 재식별 방지, 위탁·보안 통제 요구 확인 |
| AI | 금융분야 인공지능 가이드라인 | 8 | 금융 AI 이용 시 데이터 입력·출력, 외부 AI, 개인정보 보호 관련 요구 확인 |
| SAAS_CLOUD | 전자금융감독규정과 금융위원회 SaaS·Cloud 정책자료 | 9 | 내부망 SaaS·Cloud 이용, 망분리 예외, 접근통제·모니터링·보안 요구 확인 |
| DIGITAL_ASSET | 가상자산 이용자보호법·시행령, 특정금융정보법·시행령, 금융위·FIU 자료 | 10 | 가상자산 거래, 고객확인, 자산 분리, 이전정보와 지갑주소 관련 요구 확인 |
| **합계** | 법률·시행령·감독규정·가이드라인·공식 정책 | **59** | Gateway 규칙 설계를 위한 규제 근거와 요구 후보 구조화 |

출처 유형별로는 법률 26건, 가이드라인 15건, 감독규정 10건, 시행령 6건, 공식 정책 2건이다.

## 3. 분석 방법

원문 Evidence 수집 → 문서 정제 → Evidence 단위 구조화 → Requirement Candidate 추출 → 규제 영역·처리 맥락 분류 → 검증 상태 부여 → 후속 Control·Test·Policy Candidate가 참조할 수 있는 형태로 동결

### 3.1 공식 원문 수집

- 무엇을 했는가: 국가법령정보센터, 금융위원회, 금융정보분석원 등 공식 출처의 법령·감독규정·가이드라인·정책자료를 수집하고 출처 manifest를 남겼다.
- 왜 했는가: 분석된 요구사항이 비공식 요약이 아니라 공식 원문과 URL로 역추적될 수 있어야 하기 때문이다.
- 결과물: `raw/official_sources/*`, `official_sources_manifest.json`, Evidence의 `source_id`, `source_url`, `retrieved_at`.

### 3.2 문서 정제와 Evidence 구조화

- 무엇을 했는가: 법령의 조·항과 가이드라인의 페이지·섹션을 기준으로 원문을 Evidence 단위로 나누고, 원문 위치와 기준일을 보존했다.
- 왜 했는가: 긴 문서 전체가 아니라 특정 요구를 담은 근거 단위로 비교·검증하기 위해서다.
- 결과물: `evidence_master.json`의 59개 Evidence. `original_text`가 원문 근거의 Source of Truth다.

### 3.3 규제 요소 추출

- 무엇을 했는가: 각 Evidence에서 적용 대상, 데이터 유형, 처리 맥락, 조건, 요구행위, 금지, 예외를 분리했다.
- 왜 했는가: 같은 데이터라도 위탁, 제3자 제공, AI 이용, SaaS·Cloud 이용, 가상자산 거래 등 처리 맥락에 따라 적용 조건이 달라질 수 있기 때문이다.
- 결과물: Evidence의 `applies_to`, `data_type`, `processing_context`, `condition`, `required_action`, `prohibition`, `exception`.

### 3.4 Requirement Candidate 생성

- 무엇을 했는가: 59개 Evidence 각각에 대응하는 Requirement Candidate를 만들고 `evidence_id`로 연결했다.
- 왜 했는가: 공식 원문과 원문에서 분석한 통제 요구 후보를 분리해, 분석 결과가 법령 원문처럼 취급되는 것을 막기 위해서다.
- 결과물: `requirement_candidates.json`의 59개 후보. 적용성(`actor`, `data`, `processing_context`), 원문 유래 요구, 해석 태그, 후속 단계로 미룬 고려사항을 포함한다.

### 3.5 규제 도메인과 처리 맥락 분류

- 무엇을 했는가: Evidence와 Requirement Candidate를 PRIVACY, AI, SAAS_CLOUD, DIGITAL_ASSET으로 분류하고 processing context와 해석 태그를 부여했다.
- 왜 했는가: 규제 문서의 주제와 실제 데이터 처리 상황을 함께 분석하면서도 두 개념을 혼동하지 않기 위해서다.
- 결과물: 4개 도메인, `processing_context`, `interpretation_tags`. 주요 맥락은 보안통제, 제3자 제공·위탁, 가명정보 처리, 디지털자산 활동, SaaS·Cloud 이용, AI 이용 등이다.

### 3.6 검증과 동결

- 무엇을 했는가: JSON Schema, ID 중복, Evidence 참조, 공식 출처 연결, Runtime 의미의 잔존 여부를 검증하고 VERIFIED와 REVIEW_REQUIRED를 분리했다.
- 왜 했는가: 직접 확인되지 않은 근거가 검증 완료 자료와 섞이거나 Runtime 결정으로 자동 승격되는 것을 방지하기 위해서다.
- 결과물: `review/validation_report.json`, `review/review_required.json`, `processed/evidence_ontology.json`. 최종 02 계층은 `FROZEN` 상태다.

## 4. 주요 분석 결과

### 4.1 Evidence와 Requirement Candidate

| 항목 | 전체 | 확정/후속 분석 가능 | 추가 검토 필요 |
|---|---:|---:|---:|
| Evidence | 59 | VERIFIED 49 | REVIEW_REQUIRED 10 |
| Requirement Candidate | 59 | CANDIDATE 49 | REVIEW_REQUIRED 10 |

공식 출처에서 Evidence로 이어지는 참조와 Evidence에서 Requirement Candidate로 이어지는 참조는 모두 PASS다. Schema 오류, 중복 Evidence·Requirement ID, 누락된 Evidence 참조, Requirement가 없는 Evidence는 없었다.

### 4.2 규제 도메인 분포

- PRIVACY: 32건
- DIGITAL_ASSET: 10건
- SAAS_CLOUD: 9건
- AI: 8건

개인정보 영역이 가장 크지만, AI·SaaS·Cloud·Digital Asset도 별도의 규제 도메인과 처리 맥락으로 구조화되어 있다.

### 4.3 요구 유형

Requirement Candidate의 해석 태그는 중복 부여될 수 있다. 주요 분포는 다음과 같다.

- REVIEW: 26건
- PSEUDONYMIZE: 11건
- THIRD_PARTY_TRANSFER: 10건
- DIGITAL_ASSET: 10건
- LOG: 7건
- MONITOR: 5건
- CLOUD: 5건
- SAAS: 4건
- CROSS_BORDER_TRANSFER: 4건
- ENCRYPT: 3건

이는 가명처리와 제3자 제공뿐 아니라 기록·모니터링, Cloud·SaaS, 국외 이전, 암호화 등 서로 다른 통제 요구가 함께 존재함을 보여준다. 18개 Requirement Candidate에는 기존 분석에서 발견된 `ALLOW`, `BLOCK`, `DETECT`, `MASK` 성격의 태그가 후속 `GATEWAY_POLICY_OR_TRANSFORM_STAGE`에서 결정하도록 deferred consideration으로 분리되어 있다.

### 4.4 REVIEW_REQUIRED

추가 검토가 필요한 Evidence는 PRIVACY 2건, SAAS_CLOUD 3건, DIGITAL_ASSET 5건이며 AI에는 없다.

- PRIVACY: `EV-00025`, `EV-00027`
- SAAS_CLOUD: `EV-00029`, `EV-00046`, `EV-00047`
- DIGITAL_ASSET: `EV-00053`~`EV-00057`

주된 사유는 공식 원문 위치·URL 직접 재확인 미완료, PDF 페이지 위치 검증 미완료, 원문 버전과 effective date 기준시점 불일치 가능성, actor 공백 및 일부 필드 품질 문제다. 이 10건의 검증 방법은 `NOT_VERIFIABLE`로 유지되며 대응 Requirement Candidate도 `REVIEW_REQUIRED`다.

### 4.5 Runtime 경계

모든 Requirement Candidate의 `prohibited_runtime_decision`은 `true`다. 02 단계에서는 `ALLOW`, `BLOCK`, `TRANSFORM`, 변환 방식, 임계값을 결정하지 않는다. 따라서 59개 Requirement Candidate는 Runtime Rule이 아니라 후속 Control·Test·Policy Candidate 설계의 분석 입력이다.

## 5. 분석 결과 해석

### Evidence와 Requirement를 분리한 이유

법령·가이드라인 원문은 근거이고, Requirement Candidate는 그 원문에서 적용 대상과 요구를 분석해 만든 후보이다. 둘을 하나로 합치면 분석자의 분류나 해석이 공식 문구처럼 보일 수 있다. 59개 Evidence와 59개 Requirement Candidate를 `evidence_id`로 연결한 구조는 원문 보존과 분석 가능성을 동시에 확보한다.

### 법령 문구를 곧바로 Runtime Rule로 사용할 수 없는 이유

Evidence에는 조건, 예외, 적용 대상, 처리 맥락이 함께 존재한다. 또한 10건은 원문 위치·기준시점 등을 추가 검토해야 한다. 분석 결과에서도 18개 후보의 실행 관련 고려사항이 후속 단계로 명시적으로 이관되었고, 모든 후보가 직접 Runtime 결정을 금지한다. 따라서 법령의 한 문구만으로 ALLOW·BLOCK·TRANSFORM을 결정할 수 없다.

### 데이터 유형과 processing context를 함께 둔 이유

같은 데이터라도 가명정보 처리, 제3자 제공·위탁, 국외 이전, AI 이용, SaaS·Cloud 이용, 가상자산 거래와 지갑주소 처리에 따라 요구가 달라진다. 02는 Regulatory Domain과 별도로 `data`와 `processing_context`를 구조화해 후속 단계가 적용성을 평가할 수 있게 했다.

### 도메인을 분리한 의미

PRIVACY는 가명처리·제3자 제공·재식별 방지 같은 데이터 보호 요구를 중심으로 한다. AI는 외부 AI 이용과 입력·출력 데이터 보호, SAAS_CLOUD는 내부망·Cloud 이용과 접근통제·모니터링, DIGITAL_ASSET은 거래·고객확인·자산 분리·지갑주소 맥락을 포함한다. 이 차이는 하나의 범용 키워드 규칙보다 도메인과 처리 맥락을 결합한 후속 평가가 필요함을 보여준다.

### VERIFIED와 REVIEW_REQUIRED를 분리한 의미

검증 완료 49건과 추가 검토 10건을 분리함으로써 직접 확인되지 않은 Evidence가 확정 근거로 자동 승격되는 것을 막았다. REVIEW_REQUIRED는 삭제 대상이 아니라 원문 검증과 필드 보완이 필요한 추적 대상이다.

## 6. Gateway와의 연결

02에서 03 이후 단계로 이어지는 경계는 다음과 같다.

```text
Official Source
→ Evidence
→ Requirement Candidate
→ Control
→ Test
→ Policy Candidate
→ downstream evaluation
→ Runtime Policy
```

02는 Official Source, Evidence, Requirement Candidate를 소유한다. 03 Gateway Rules는 59개 Requirement Candidate를 입력으로 받아 요구를 `RUNTIME_ENFORCEABLE`, `GOVERNANCE_CONTROL`, `EVALUATION_DEPENDENT`, `NON_RUNTIME_REFERENCE`로 분류하고 Control·Test·Policy Candidate를 설계한다. Runtime 활성화, 최종 변환 방식과 임계값 선택은 그보다 후속 단계의 책임이다.

따라서 Gateway는 법령 원문을 직접 실행하지 않는다. 원문은 Evidence로 보존되고, 분석 가능한 Requirement Candidate로 정규화된 뒤, Control과 Test를 거쳐 평가된 Policy만 Runtime에서 사용될 수 있다. 이 구조는 각 실행 정책이 어떤 Evidence와 Requirement에서 출발했는지 추적할 수 있게 한다.

## 7. 핵심 결론

02 Evidence Ontology는 공식 규제 자료를 59개 Evidence와 59개 Requirement Candidate로 구조화했다. 각 Evidence는 원문, 출처, 적용 대상, 데이터, 처리 맥락, 조건, 요구행위, 금지와 예외를 보존한다. 49건은 VERIFIED, 10건은 REVIEW_REQUIRED로 분리되어 검증 수준이 명시되었다. PRIVACY뿐 아니라 AI, SAAS_CLOUD, DIGITAL_ASSET을 독립 도메인으로 구성해 변화한 금융 데이터 처리환경을 반영했다. Evidence와 Requirement를 분리하고 모든 Requirement의 직접 Runtime 결정을 금지함으로써 법령과 실행 정책 사이의 분석 경계를 유지했다. 이 결과는 03 단계가 추적 가능한 Control·Test·Policy Candidate를 설계할 수 있는 규제 근거와 적용성 정보를 제공한다.
