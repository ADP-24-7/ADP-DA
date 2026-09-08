# BE 요청사항: 실제 Evaluation Bundle E2E

현재 DA는 SYNTHETIC_VALIDATION을 완료했으나 REAL_BE_EVALUATION은 미완료입니다.
`localhost:8080` 연결에 실패하여 실제 Bundle을 받지 못했으며 실제 검증 PASS,
모델 성능 비교 또는 threshold 확정으로 보고한 항목이 없습니다.

## 1. 실행 가능한 Runtime

DA에서 접근 가능한 BE base URL 또는 PostgreSQL과 함께 기동하는 로컬 실행 방법을
공유해 주세요. 배포 환경의 네트워크 접근 범위도 확인이 필요합니다.

## 2. 관리자 인증

현재 BE 로컬 개발 구현은 `ADP_LOCAL_USER_AUTH_ENABLED=true`일 때 다음 헤더를 사용합니다.

- `X-ADP-User-Id`: 로컬 DA 조회자 식별값. 예: `da-evaluation-reader`
- `X-ADP-User-Roles`: `PRIVILEGED_OPERATOR`

로컬 principal은 `institution_local`, workload `*` 범위를 사용합니다.
배포 환경에서는 실제 관리자 인증 연동과 institution/workload 권한을 공유해 주세요.
현재 소스의 관리자 경로는 Bearer token이나 Runtime API Key만으로 인증되지 않습니다.

ADP-DA Consumer에서 직접 실행하는 최소 로컬 예시:

```powershell
$env:ADP_BE_LOCAL_ADMIN_USER_ID = 'da-evaluation-reader'
$env:ADP_BE_LOCAL_ADMIN_ROLES = 'PRIVILEGED_OPERATOR'
python -m adp_da.evaluation_bundle http://127.0.0.1:8080 `
  --evaluation-run-id ai-eval-baseline-2026-09-07 `
  --output outputs/real_be_evaluation/analysis
```

Consumer는 두 값을 각각 `X-ADP-User-Id`, `X-ADP-User-Roles`로 전송합니다. 값은
CLI 인자나 archive metadata에 기록하지 않습니다. 두 값은 함께 설정해야 하며 Bearer
token과 동시에 사용할 수 없습니다. 예시는 BE가 기동된 로컬 개발 환경 전용이며 원격
운영 인증을 대체하지 않습니다.

현재 BE에는 JWT/OAuth2 Resource Server Adapter가 없으므로 원격 `ADP_BE_TOKEN`만으로는 이
관리자 API에 접근할 수 없습니다. 운영/NCP 직접 연동 전에는 BE 운영 인증 Adapter를 먼저
구현·검증해야 하며, DA E2E runner는 그때까지 원격 Bearer 실행을 기본 차단합니다.

## 3. 등록 Run 실행 상태

`ai-eval-baseline-2026-09-07`의 실제 실행 완료 여부 및 DB 저장 상태를 확인해 주세요.
등록 기대 규모는 `financial_synthetic`의 **1 Case × 3 Model = 3 Execution**입니다.
Catalog 등록과 실행 완료를 구분하고 각 Case×Model의 최신 실행 증적 존재 여부를 알려 주세요.

## 4. 실제 Bundle 제공

`GET /api/admin/ai/evaluation-runs/{evaluationRunId}/bundle`에 대한 DA 직접 접근을
제공해 주세요. 직접 연결이 어려우면 이 API가 실제 Export한 원본 JSON 파일 1개를
전달해 주세요. 임의 fixture나 요약본은 실제 E2E 입력으로 사용하지 않습니다.

## 5. 기대 조건

- manifest의 case/model/execution count와 실제 Cartesian Product 일치
- 각 실행의 `evidence_status=COMPLETE`
- Runtime metrics와 measurement type별 latency 정합성
- token usage 상태, null 조건, input+output=total 정합성
- Runtime metrics로 재계산 가능한 failure summary
- bundle_id, content_digest, 실행 기간과 Run/Dataset/Policy/Model provenance

Provider 실패가 있더라도 증적이 완전한 Bundle은 실패 분석 대상입니다.
성공 결과를 만들기 위해 실패 실행을 누락하거나 보정하지 않습니다.

## 6. 새 Evaluation이 필요한 경우

PostgreSQL/Flyway, Provider endpoint, Runtime 실행자 권한, 승인·Destination 설정,
NVIDIA credential의 BE 환경변수/Secret Store 주입 방법 및 등록 모델의 접근 가능 상태를
공유해 주세요. credential 값 자체를 PR이나 문서에 넣지 않습니다.
Runtime 실행과 Bundle Export의 인증 방식은 구분해야 합니다.

## 7. DA–BE E2E 완료 기준

1. 실제 Bundle 수신 및 원본 보존
2. DA JSON Schema 검증 PASS
3. content_digest 재계산 PASS
4. Case×Model Cartesian Product 및 중복 검증 PASS
5. Execution identity / 섹션 cardinality / provenance 검증 PASS
6. Expected/Actual Input Digest 및 COMPLETE evidence 검증 PASS
7. Failure Summary 재계산 PASS
8. Token Usage 정합성 PASS

BE의 역할은 실제 Evaluation 실행과 신뢰 가능한 Bundle Producer 제공까지입니다.
분석 결과나 threshold 확정은 BE에 요구하지 않습니다. DA가 실제 근거와 검정 가정을
검토한 뒤 담당자 판단으로 Candidate를 결정합니다.

현재 SUPPORTED_CANDIDATE는 없습니다. MODEL_ALLOWLIST, LATENCY_THRESHOLD,
FAILURE_THRESHOLD, REVIEW_CONDITION은 UNRESOLVED이며 MODEL_QUALITY,
UTILITY_THRESHOLD, TRANSFORM_POLICY는 NOT_EVALUABLE입니다.
