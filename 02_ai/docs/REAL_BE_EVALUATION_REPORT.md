# 최초 REAL_BE_EVALUATION 확보 점검

점검일: 2026-09-08. BE `5d5f999`, DA base `8b0a9ad` 및 현재 로컬 Consumer 기준.

**실제 Bundle을 확보하지 못해 독립 검증과 성능 분석을 시작하지 않았다.**
등록 Run 정의는 존재하지만 실행 중인 서버나 완료된 Runtime 증적은 확인되지 않았다.
새 합성 fixture나 가상 성능 결과를 만들지 않았으며 commit/push하지 않았다.

## 1. 실제 Evaluation Run 확보 여부

| 구분 | 확인 결과 |
|---|---|
| SYNTHETIC_VALIDATION | 기존 Consumer 검증 산출물. 이번 실측 근거에서 제외 |
| REAL_BE_EVALUATION | NOT_ACQUIRED. 실제 응답/실행 증적 미확보 |
| 등록 Run 정의 | 존재. `AiEvaluationRunCatalog`의 static baseline |
| 실행된 Run | 미확인. Catalog 등록은 실행 완료를 뜻하지 않음 |
| BE readiness | `http://127.0.0.1:8080/actuator/health/readiness` 연결 실패 |
| Bundle API | 로컬 privileged 헤더를 사용한 GET도 연결 실패. HTTP 응답 없음 |
| 재확인 | 샌드박스 밖 호스트에서도 두 요청 모두 연결 실패 |
| 로컬 실행 도구 | Docker 명령 및 기본 Docker 설치 경로에서 설치를 확인하지 못함 |
| 설정 | BE/DA `.env` 없음. 예제만 존재. 호스트 프로세스의 NVIDIA_API_KEY 및 Bundle source/run 설정 없음 |
| 저장된 Bundle | 점검한 BE/DA 저장소에는 기존 Consumer 합성 fixture/산출물만 발견 |

원격 배포 서버가 존재하지 않는다는 뜻은 아니다. 접근 주소나 Export 파일이 제공되지 않아
확인할 수 없다. 인증 실패(401/403)나 Bundle 없음(404)을 관측한 것도 아니다.
현재 실패는 HTTP 응답 이전의 연결 단계다.

### 실제 실행에 부족한 입력

1. **이미 평가가 실행된 BE가 있다면:** 접근 가능한 BE base URL과 해당 배포의 관리자 인증 방식,
   또는 그 서버가 Export한 원본 Bundle JSON 파일. 이미 저장된 Bundle의 Export에는
   DA 측 NVIDIA API key가 필요하지 않다.
2. **새 평가를 실행해야 한다면:** PostgreSQL/Flyway가 준비된 실행 가능한 BE 환경,
   BE에 주입할 유효한 `NVIDIA_API_KEY`, 등록 모델 3종에 대한 Provider 사용 권한,
   Runtime 실행자 인증과 승인/목적지/subject scope fixture 또는 동등한 배포 설정.
3. **로컬 개발 구성 사용 시:** `ADP_LOCAL_USER_AUTH_ENABLED=true`,
   `ADP_LOCAL_FIXTURES_ENABLED=true`, `ADP_AI_CONNECTOR_ENABLED=true`를 확인한다.
   NVIDIA profile은 `ADP_NVIDIA_BASE_URL`을 사용한다. 내부 `mock-ai` 응답을
   실제 NVIDIA 측정으로 대체하지 않는다. 새 모델 실행 전 접근 가능 모델을 확인한다.

이 입력 없이 키 누락 실패나 MOCK 실행을 만들어 최초 실제 모델 평가로 간주하지 않는다.

## 2. 사용한 evaluationRunId

- 발견한 등록 ID: `ai-eval-baseline-2026-09-07`
- 등록 version: `1.0.0`
- 실제 분석에 사용한 ID: **없음**. 위 ID로 API 확보만 시도했고 연결에 실패했다.
- Case: `customer-summary-ko-001`
- Dataset row reference: `synthetic:customer-100`
- Dataset: `financial_synthetic`, version `financial_synthetic_processed_v1`
- Workload / purpose: `customer_summary` / `CUSTOMER_SUPPORT`
- 입력: 서버가 고정한 `{"prompt":"승인된 고객 정보를 간단히 요약하세요"}`

실제 BE를 실행하더라도 이 baseline의 입력 데이터는 합성 금융 데이터다.
실제 서버/Provider 측정을 뜻하는 REAL_BE_EVALUATION과 실제 고객 데이터는 다른 개념이다.
이 Run은 새로 만들어낸 DA Consumer fixture와도 다르다.

Dataset manifest의 LF 파일 바이트 SHA-256은 등록 digest와 일치한다:
`9afdc4bf89c0047a5e90f21e6f8eaffb4f6c148998f1740f30baf666bdae0a44`.
Windows CRLF 작업 사본의 raw SHA-256은
`2e54e595ded98144cc9b57459497768318e9d5616ccd39e9a711e174d7faaee0`이다.
이는 줄바꿈 차이로 설명된다. 이 확인은 전체 CSV 내용의 별도 검증이나 Bundle 검증을 뜻하지 않는다.

### 등록 Model / Destination / Policy

| Profile ID | Provider model ID | Provider version | Destination profile |
|---|---|---|---|
| nvidia-nemotron-3.5-lightning-30b-a3b | nvidia/nemotron-3.5-lightning-30b-a3b | 1.0-preview | dest_nvidia-nemotron-3-5-lightning-30b-a3b |
| meta-muse-glimmer-30b | meta/muse-glimmer-30b | v1.0 | dest_meta-muse-glimmer-30b |
| google-gemma-4-31b-it | google/gemma-4-31b-it | v1.0 | dest_google-gemma-4-31b-it |

모델 이름은 저장소 등록값이며 현재 Provider 제공 여부를 실측 확인한 결과가 아니다.
Profile version은 `2026-09-07`, connection은 `nvidia-nim-hosted`,
`max_tokens=512`, `temperature=0.0`이다. NVIDIA endpoint 기본값은
`https://integrate.api.nvidia.com`이다.

Policy snapshot은 `be-runtime-policy/0.0.0`, action `TRANSFORM`,
`PROJECT_PROVISIONAL_POLICY_EVALUATION:0.0.0:sha256:local-fixture-policy-evaluation` 및
provisional policy/rule/requirement와 `RUNTIME_AUTHORIZATION`, `SUBJECT_SCOPE` controls를
고정한 digest다. 실제 Bundle digest나 측정된 정책 효과로 표현하지 않는다.
승인 참조는 각 profile에 대해 `approval_ai_eval_<profile_id>`다.

## 3. 실제 Bundle 규모

| 항목 | 등록 기대값 | 확보한 실제 Bundle |
|---|---:|---|
| Case 수 | 1 | 미확보 |
| Model 수 | 3 | 미확보 |
| Execution 수 | 완전한 Cartesian Product이면 3 | 미확보 |
| bundle_id / content_digest | Export에서 읽어야 함 | 없음 |
| execution_from / execution_cutoff_at | Export에서 읽어야 함 | 없음 |

관측 표본 수는 0이다. 이는 BE DB에 실행이 0건이라는 뜻이 아니다.
BE는 각 Case×Model의 최신 실행만 Export한다.

## 4. DA 독립 검증 결과

**NOT_RUN_NO_BUNDLE**. JSON Schema, content_digest, Cartesian Product, pair 중복,
Execution ID 집합, provenance, expected/actual input digest, failure summary,
token usage, COMPLETE evidence 중 어떤 항목도 실측 PASS로 표시하지 않는다.

### API 호출 및 인증

현재 BE 소스의 Bundle 경로는 `PRIVILEGED_OPERATOR`를 요구한다.
로컬 개발 모드에서 `UserHeaderAuthenticationFilter`가 아래 헤더를 읽어
`institution_local`, workload `*` principal을 만든다. 조회에는 institution/workload scope가 적용된다.

```powershell
# BE가 실제 기동된 로컬 개발 환경에서만 실행
$bundleHeaders = @{
    'X-ADP-User-Id' = 'da-evaluation-reader'
    'X-ADP-User-Roles' = 'PRIVILEGED_OPERATOR'
}
New-Item -ItemType Directory -Force outputs/real_be_evaluation | Out-Null
Invoke-WebRequest -UseBasicParsing `
    -Uri 'http://127.0.0.1:8080/api/admin/ai/evaluation-runs/ai-eval-baseline-2026-09-07/bundle' `
    -Headers $bundleHeaders `
    -OutFile outputs/real_be_evaluation/bundle.json
python -m adp_da.evaluation_bundle outputs/real_be_evaluation/bundle.json `
    --evaluation-run-id ai-eval-baseline-2026-09-07 `
    --output outputs/real_be_evaluation/analysis
```

위는 후속 재개 방법이며 이번에 성공한 명령이 아니다. 기존 Consumer의 로컬 JSON 경로로
원본 응답을 다시 로드해 모든 검증을 수행한다. 실패 응답을 Bundle로 취급하지 않는다.

**기존 Consumer의 `Authorization: Bearer` 옵션은 이 BE의 관리자 인증 구현과 맞지 않는다.**
현재 소스에는 이를 처리하는 Bearer/JWT 필터가 없고, `ApiKeyAuthenticationFilter`도
`/api/admin/`을 건너뛴다. 배포 환경의 인증 연동은 별도 확인해야 한다.
로컬 사용자 헤더 인증을 원격 운영 환경의 인증 대체 수단으로 사용하지 않는다.

새 Runtime 실행은 `POST /v1/runtime/executions`, `X-ADP-API-Key` 및
`RUNTIME_EXECUTOR` 권한을 사용한다. 로컬 fixture의 `local-dev-api-key`는 개발용이며,
Bundle 관리자 인증용 키가 아니다. 각 profile의 destination/approval을 사용하고
`institution_local`, `customer_summary`, `CUSTOMER_SUPPORT`,
`subjectScope=customer:customer-100`, `processingContexts=[AI_USE]`,
Run/Case ID 및 고정 input을 제공한다. 새 실행마다 idempotency key를 구분한다.
구체적인 기존 request 형식은 BE `AiEvaluationBundleControllerTests.submitEvaluation`에 있다.

## 5. 모델 비교 결과

미수행. 실제 실행 상태·Case별 차이·실패 유형이 없다. 기존 합성 fixture 수치를 인용하지 않는다.

## 6. Runtime 분석 결과

미수행. latency, HTTP/provider failure, token usage 모두 관측값 없음.
계약상 `TRANSPORT`는 timeout 전용 분류가 아니므로 추후 Bundle을 받아도
timeout 비율은 별도 원인 증적 없이는 분리 산출할 수 없다.

## 7. 통계검정 및 효과크기

미수행. p-value와 effect size는 null이다. 등록 baseline은 독립 Case 1개뿐이므로
세 모델의 실행 3건을 독립 표본 3개로 세지 않는다. Bundle이 확보돼도
이 baseline만으로 모델 일반화나 안정적인 P95/P99/SLA를 결정할 수 없다.
Case별 기술 비교는 가능하지만 추론 검정을 억지로 수행하지 않는다.

## 8. SUPPORTED_CANDIDATE

없음. 실제 metric과 표본이 없어 임계값·allowlist 후보를 지지하지 않는다.

## 9. UNRESOLVED

| 항목 | 상태 | 실제 근거 metric | 관측 표본 수 | 부족한 근거 |
|---|---|---|---:|---|
| MODEL_ALLOWLIST | UNRESOLVED | null | 0 | 실제 profile별 실행 결과, 대표 Case 및 독립 품질 기준 |
| LATENCY_THRESHOLD | UNRESOLVED | null | 0 | 실제 유형별 latency, 반복 관측 및 DA/SLA 판단 |
| FAILURE_THRESHOLD | UNRESOLVED | null | 0 | 실제 실패 분모·분류·반복 실행 및 위험 허용수준 |
| REVIEW_CONDITION | UNRESOLVED | null | 0 | 실제 REVIEW 결과와 정답/오차 비용 |

## 10. NOT_EVALUABLE

| 항목 | 상태 | 실제 근거 metric | 관측 표본 수 | 현재 계약의 한계 |
|---|---|---|---:|---|
| MODEL_QUALITY | NOT_EVALUABLE | null | 0 | 정답 라벨/독립 품질 점수 없음. Runtime 완료는 품질이 아님 |
| UTILITY_THRESHOLD | NOT_EVALUABLE | null | 0 | Utility outcome 및 척도 없음 |
| TRANSFORM_POLICY | NOT_EVALUABLE | null | 0 | 처치/대조 arm, transform 강도, privacy/utility outcome 없음 |

## 11. Utility/Transform 검증을 위해 추가로 필요한 실험

**설계만 작성했으며 실행/결과는 없다.**

| 설계 요소 | 요구사항 |
|---|---|
| Control | 승인된 기존 Policy 또는 허용되는 원본 처리 조건 |
| Treatment | FPG Policy/Transform 적용. method와 strength를 명시 |
| Pair | 동일 Case×동일 Model×동일 반복 차수의 control/treatment |
| 통제 | Dataset, 입력, model/profile version, sampling, destination, 실행 환경 고정 |
| 배정 | arm 실행 순서 무작위화/교차배치. 시간대·provider 부하 block 기록 |
| 표본 | 독립적인 대표 Case 확장. 최소 실용 효과와 power 계획으로 크기 결정 |
| 반복 | 각 pair를 반복하고 별도 immutable run/version으로 보존. 최신 실행만 남는 Export 한계 해결 |
| 품질 | 정답/평가 rubric과 scorer version 고정. correctness, completeness, hallucination 등 업무별 점수 |
| Utility | DA가 사전 합의한 척도, 허용 손실 및 비열등성 margin |
| Privacy | 원문 대신 승인된 scorer에서 계산한 노출/재식별 위험·통제 성공 지표 |
| Runtime | measurement type별 latency/token, timeout 전용 원인, HTTP/provider failure |
| 검정 | 구조·가정 충족 시 paired binary 검정 또는 Wilcoxon/Friedman; 효과크기·다중검정 보정 |

현재 static Run은 하나의 policy digest와 고정 input만 허용하므로 임의 request로 policy arm을
바꿀 수 없다. BE와 versioned 실험 계약, case-to-workload mapping, treatment/pair/repeat ID,
score artifact의 execution ID·bundle snapshot 연결을 합의해야 한다.
Provider response 원문이 Bundle에 없으므로 승인된 평가 지점에서 scoring한 결과만
별도 privacy-safe artifact로 제공하도록 설계한다. 누락·실패 결과를 제외하는 규칙도 사전 명시한다.

## 12. DA 담당자가 최종 결정해야 할 항목

1. 기존 실행 서버의 Bundle을 재사용할지, 등록 baseline으로 실제 Provider 실행을 시작할지.
2. API 주소·관리자 인증 또는 원본 Bundle 파일 제공 경로.
3. baseline 1 Case는 연결 확인용으로만 사용할지, 대표 Case와 반복 실험을 확장할지.
4. 품질/Utility 평가 rubric, privacy 지표, 실용 효과·SLA·실패/REVIEW 오차 비용.
5. 통제된 Policy/Transform 실험의 허용 control 조건과 버전 관리 계약.

### 확인한 소스

- BE `src/main/java/com/adp/gateway/ai/application/AiEvaluationRunCatalog.java`
- BE `src/main/java/com/adp/gateway/ai/application/AiModelProfileCatalog.java`
- BE `src/main/java/com/adp/gateway/ai/application/AiProviderConnectionRegistry.java`
- BE `src/main/java/com/adp/gateway/auth/infrastructure/SecurityConfig.java`
- BE `src/main/java/com/adp/gateway/auth/infrastructure/UserHeaderAuthenticationFilter.java`
- BE `src/main/java/com/adp/gateway/auth/infrastructure/ApiKeyAuthenticationFilter.java`
- BE `src/test/java/com/adp/gateway/ai/api/AiEvaluationBundleControllerTests.java`
- BE `docs/ai-eval-0-nvidia-model-profiles.md`, `docs/ai-eval-1-evaluation-run-contract.md`
- BE `docs/ai-eval-3-da-evaluation-bundle.md`, `docs/contracts/ai-evaluation-bundle.schema.json`
- BE `docker-compose.yml`, `.env.example`, `src/main/resources/application.yml`
- DA `02_ai/data/processed/financial_synthetic/manifest.json`, `02_ai/src/adp_da/bundle_loader.py`
