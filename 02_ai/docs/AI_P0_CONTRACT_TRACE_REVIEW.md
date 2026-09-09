# AI P0 Contract / Trace Review

> 후속 구현: P0-00 서버 Freeze/Runtime binding/Bundle v2/DA 검증을 추가했다.
> 아래 점검표는 구현 전 상태를 보존한다. 현재 계약과 실측 전 제한은
> [BE P0 Contract Freeze](../../../ADP-BE/docs/ai-eval-p0-contract-freeze.md)를 참조한다.
> 실제 Provider Evidence는 아직 확보하지 않았다.
> 후속 Runtime 준비 점검: [CRLF 해결 및 실제 실행 blocker](AI_P0_RUNTIME_READINESS.md).

점검일: 2026-09-10. DA `c9d474cff632ff00fdef935b6b2744a58d95433f`,
BE `d937f647d73a97913672bc55422ce1aaf97e7ca5` 기준.

목적은 동일 FPG 통제조건에서 3개 외부 AI Runtime의 Quality / Privacy /
Runtime 특성을 비교하는 것이다. Benchmark 우승 모델 선정이나 자동 정책 승격은 하지 않는다.
이 문서는 소스 점검과 실행 준비 결과이며 BE가 발급한 Evaluation Contract나 실측 Bundle이 아니다.

## 현재 상태

- P0-00: **PARTIAL / GAP**. 기존 서버 소유 baseline을 재사용하지만 요청된 모든 버전과
  실행조건을 동결할 Evidence가 없다. 아래 GAP을 임의 값으로 채우지 않는다.
- P0-01: **NOT_MEASURED**. 실행 연결 코드는 있으나 실제 Trace/Bundle을 확보하지 못했다.
- P0-02: 기존 `evaluation_e2e.py`의 1 Case × 3 Model 실행 경로를 재사용한다.
  최신 BE freshness 계약에 필요한 요청별 UTC timestamp 헤더만 보완했다.
- 실제 Provider 호출: 0회. 실제 평가 표본: 미확보. 모델 품질/Privacy/Runtime Rule Candidate:
  `UNRESOLVED` 또는 기존 Consumer 기준 `NOT_EVALUABLE`; 수치를 생성하지 않는다.

## 기존 구조와 재사용 파일

DA의 모든 경로는 `02_ai/` 아래다.

| 영역 | 재사용 파일/폴더 | 역할 |
|---|---|---|
| 정책/근거 | `evidence_ontology/`, `gateway_rules/` | 법적·정책 근거와 provisional rule |
| 분석 | `notebooks/01_evaluation_ai_field_utility_v1.ipynb`부터 기존 4개 분석 Notebook | Workload, Field Utility, Transform, Legal Constraint |
| 평가 Notebook | `notebooks/AI_EVAL_01_bundle_validation.ipynb`부터 `AI_EVAL_04_policy_effect_analysis.ipynb` | Bundle 독립 검증 및 기존 분석 경로 |
| Handoff | `contracts/`, `artifacts/ai_handoff_vNext/` | Workload binding, field contract, policy evaluation, 미결정 후보 |
| Dataset | `data/processed/financial_synthetic/manifest.json` | 기존 합성 금융 데이터 manifest |
| 실행 | `src/adp_da/evaluation_e2e.py` | 고정 Run/Case/Model binding, Runtime POST, readiness, export |
| 소비 | `src/adp_da/evaluation_bundle.py`, `bundle_loader.py`, `bundle_validator.py` | 원본 보존, schema/digest/provenance 검증 |
| 분석 코드 | `src/adp_da/bundle_dataset.py`, `bundle_analysis.py` | 기존 metric 및 후보 상태 출력 |
| 절차 | `docs/AI_EVALUATION_E2E_RUNBOOK.md`, `AI_EVALUATION_CONSUMER.md` | 기존 실행 및 분석 convention |

DA의 `nvidia_nim.py` 직접 호출은 BE Policy/Transform/Guard/Trace를 우회하므로 이 실험 경로로
사용하지 않는다. 기존 합성 fixture와 demo 산출물은 실제 Provider Evidence로 사용하지 않는다.

BE Java 경로는 `src/main/java/com/adp/gateway/` 기준이다.

| 파일/영역 | 역할 |
|---|---|
| `ai/application/AiEvaluationRunCatalog.java` | 서버 소유 Run/Case/Dataset/Input/Policy binding |
| `ai/application/AiModelProfileCatalog.java` | 3개 Model/Version/Sampling/Destination snapshot |
| `ai/infrastructure/AiExternalSchemaMapper.java` | 고정 NVIDIA payload 및 실행 provenance 기록 |
| `ai/application/AiProviderConnectionRegistry.java`, `ai/infrastructure/HttpAiConnector.java` | BE 소유 NVIDIA 연결/credential/HTTP 측정 |
| `runtime/application/RuntimeExecutionService.java` | Authorization → Retrieval → Policy → Transform → Guard → Connector |
| `runtime/api/RuntimeExecutionTraceResponse.java`, `RuntimeExecutionEvidenceResponse.java` | 실행 상세·필드 집합·Guard·Delivery Evidence |
| `runtime/api/RuntimeExecutionTraceEventsResponse.java` | 저장된 trace에서 단계 목록을 구성 |
| `ai/application/AiEvaluationBundleService.java`, `ai/infrastructure/JdbcAiEvaluationBundleAdapter.java` | readiness와 최신 Case×Model Bundle export |
| `ai/domain/AiEvaluationBundle.java`, `docs/contracts/ai-evaluation-bundle.schema.json` | 6개 root section의 v1 전달 계약 |
| `common/trace/RequestFreshnessFilter.java`, `TraceHeaders.java` | POST timestamp/replay-window 검증 |

## P0-00: 기존 고정값과 GAP

| 조건 | 소스에서 확인한 값/상태 |
|---|---|
| workload | `customer_summary` |
| workload_type 요청값 | `CUSTOMER_SUPPORT`; 현재 BE 필드명은 `purposeCode`/`purpose`, 새로운 `workload_type` 필드를 만들지 않음 |
| evaluation run | `ai-eval-baseline-2026-09-07`, version `1.0.0` |
| Case ID | `customer-summary-ko-001`, row ref `synthetic:customer-100` |
| Dataset Version | `financial_synthetic_processed_v1` |
| Dataset digest | catalog의 `sha256:9afdc4bf89c0047a5e90f21e6f8eaffb4f6c148998f1740f30baf666bdae0a44`; 실제 export 재검증 필요 |
| Prompt Version | **GAP**. 고정 input과 expected/actual input digest는 있으나 명시적 prompt version 없음 |
| Policy Version | catalog의 `be-runtime-policy/0.0.0`, provisional policy snapshot digest; 실행 상세 `policyVersion`과 대조 필요 |
| Transform Version | **GAP**. transform execution ID/status/output digest는 version이 아님 |
| RAG KB Version | **GAP**. 승인된 금융 데이터 Retrieval은 있으나 versioned RAG KB/검색 설정 Evidence 없음 |
| Random Seed | **GAP**. 현재 NVIDIA payload에 seed 미전송 |
| temperature | 세 profile 모두 `0.0` |
| max_tokens | 세 profile 모두 `512` |
| reasoning | **GAP**. 현재 payload에 reasoning 제어/증적 없음; 미전송을 off로 해석하지 않음 |
| stream | `false` |
| Model profile version | `2026-09-07` |
| Provider model version | 아래 catalog 등록값. Provider 실제 revision을 확인한 값은 아님 |

| 모델 | provider model ID | catalog model version |
|---|---|---|
| Nemotron 3.5 Lightning | `nvidia/nemotron-3.5-lightning-30b-a3b` | `1.0-preview` |
| Muse Glimmer 30B | `meta/muse-glimmer-30b` | `v1.0` |
| Gemma 4 31B IT | `google/gemma-4-31b-it` | `v1.0` |

### 요청 Evidence와 실제 BE 필드

계약상 출력 가능 여부를 정리한 것이며 실제 수신 완료를 뜻하지 않는다.

| 요청 Evidence | 기존 필드/위치 | 판정 |
|---|---|---|
| evaluation_run_id | Bundle manifest/execution_config의 `evaluation_run_id` | 제공 경로 존재 |
| case_id | `case_results[].eval_case_id`; 상세 `aiModel.evalCaseId` | 기존 명칭으로 제공 |
| model_id | `execution_config.models[].provider_model_id` | profile ID와 구분 |
| model_version | `execution_config.models[].provider_model_version` | catalog snapshot; 실제 Provider revision 검증 GAP |
| dataset_version | `execution_config.dataset_version` | 제공 경로 존재 |
| prompt_version | 없음 | GAP |
| policy_version | 실행 상세 `policyVersion`; Bundle에는 `policy_snapshot_digest` | Bundle 단독으로는 GAP |
| transform_version | 없음 | GAP |
| rag_version | 없음 | GAP |
| execution_config_digest | 정확한 필드 없음 | GAP; `evaluation_contract_digest`/`profile_digest`/`content_digest`를 임의로 같은 의미로 치환하지 않음 |

`evaluation_contract_digest`는 Run/Case/Input/Dataset/Policy/Model binding을 묶지만,
존재하지 않는 Prompt/Transform/RAG version, seed, reasoning 조건의 동결을 보장하지 않는다.
model만 바꿔도 승인·destination·profile digest는 연결된 값으로 바뀐다. 기존 필드 계약과
sampling은 같지만 단순히 "모델 외 모든 조건 동결 완료"로 결론 내릴 수 없다.

## P0-01: Trace Chain 점검

기존 조회 API는 `GET /v1/runtime/executions/{executionId}`와
`GET /v1/runtime/executions/{executionId}/trace`다.
Bundle API는 `GET /api/admin/ai/evaluation-runs/{runId}/readiness` 및 `/bundle`이다.
서버 소유 `executionId`로 join하며 caller가 보낸 trace 문자열을 실행 identity로 사용하지 않는다.

| Chain | 현재 코드상 Evidence | 한계 |
|---|---|---|
| Caller | 인증 principal, institution, approval, request/trace ID | Bundle에 caller principal identity 없음; caller→execution의 완전한 연결은 추가 audit 대조 필요 |
| Workload / Purpose | 상세 `workloadId`, `purposeCode` | Bundle v1에는 없음 |
| Requested Fields | `evidence.requested.fields/digest/count` 및 retrieved/transformed/released 집합 | Bundle v1에는 없음 |
| Policy Evaluation | `decisionId`, `policyVersion`, `snapshotDigest`, policy layer Evidence | Bundle에는 decision ID와 policy snapshot digest 중심 |
| Transform | `transformExecutionId`, `transformStatus`, `transformOutputDigest` | transform version 없음 |
| Outbound Guard | `outboundGuardStatus`, payload ID/digest | 거부 경로는 후속 Provider 증적이 없는 것이 정상일 수 있음 |
| Provider Request | provider request ID/digest, connector execution ID | digest는 원문/전체 field chain이 아님 |
| Provider Response | provider response digest, status/HTTP/error/measurement type | transport 실패에는 응답 digest가 없을 수 있음 |
| Response Guard | status와 reason codes | 원문 응답을 Bundle에 저장하지 않음 |
| Controlled Delivery | status, response digest, reason, deliveredAt | 실행/Guard 결과에 따라 미전달은 정상 통제 결과일 수 있음 |

`/trace`의 stages는 독립적인 append-only event log가 아니라 저장 trace의 필드로 구성된다.
대부분의 observedAt은 공통 updatedAt이며 별도의 Provider Response stage도 없다.
따라서 stage 목록 존재만으로 완전한 시간 순서·단계별 latency를 입증하지 않는다.

### KPI 측정 상태

기존 Bundle consumer의 section identity/Cartesian completeness 검증은 재사용하지만 아래 4개
KPI와 동일하다고 정의하지 않는다. 현 계약에 확정된 KPI 분모·조건부 필수 Evidence 목록이 없어
새 수식을 Runtime Contract로 임의 확정하지 않는다.

| KPI | 현재 결과 | 측정에 필요한 Evidence / GAP |
|---|---|---|
| Trace Completeness Rate | NOT_MEASURED / null | 실제 상세 Trace, terminal-path별 필수 연결 정의; BLOCK/REVIEW 이후 단계를 무조건 누락으로 세지 않음 |
| Orphan Execution Rate | NOT_MEASURED / null | 평가 대상 전체 실행/실패 population과 Trace 대조; 최신 Case×Model만 export한 Bundle은 전체 분모가 아님 |
| Policy → Execution Binding Rate | NOT_MEASURED / null | 실제 decision ID/policy snapshot/execution join과 대상 실행 분모 |
| Missing Evidence Rate | NOT_MEASURED / null | 조건부 필수 항목 목록과 실제 누락 수; NOT_ATTEMPTED/TRANSPORT의 정상 null과 구분 |

현재 확보 표본이 없으므로 0%나 100%를 기입하지 않는다. source 연결 가능성과 실측 completeness는 다르다.

## P0-02: 실제 호출 준비 여부

- BE와 DA `.env`: 모두 없음(호스트에서도 재확인).
- 프로세스 `NVIDIA_API_KEY`, `ADP_RUNTIME_API_KEY`, `ADP_BE_BASE_URL`: 미설정.
- 로컬 `http://127.0.0.1:8080/actuator/health/readiness`: 연결 불가.
- 현재 PATH에서 Docker/Java 실행 도구 미발견. 원격 배포 환경이 없다는 뜻은 아님.
- 세 profile/승인/destination binding 및 NVIDIA `/v1/chat/completions` 경로는 소스에 존재.
- 실제 Provider 모델 제공 여부·계정 entitlement·revision: **미검증**. catalog 등록을 호출 성공으로 보지 않음.
- 기존 preflight: `ready_for_live_execution=false`; 1 Case × 3 Models binding 검사 통과.
  local admin header 구성 가능 판정은 서버 인증 성공 판정이 아니다.
- baseline은 연결 확인용 Case 1개다. 대표성, 반복 관측, 품질 rubric/정답, privacy scoring,
  허용 손실·SLA 기준이 없어 최종 Runtime Rule 후보를 지지할 수 없다.

새 Provider client/실험 디렉터리/합성 결과를 만들지 않는다. BE 배포와 설정이 준비되면 기존
Runbook의 `--execute` 또는 저장된 실행을 재사용하는 `--consume-existing` 경로를 따른다.
이 점검에서는 둘 다 실행하지 않았다. 새로운 version/seed/reasoning 정의는 BE 계약 확장 전 GAP으로 유지한다.

## 최소 변경과 검증

- 추가: 본 문서. 기존 P0 고정값, Evidence 매핑, 실측 불가 사유 기록.
- 수정: `src/adp_da/evaluation_e2e.py`에 각 Runtime POST 시점의
  `X-ADP-Request-Timestamp` 추가. BE의 기본 5분 replay window/30초 future skew 계약을 준수한다.
  timestamp는 요청 freshness 메타데이터이며 누락된 실험 seed/version을 대신하지 않는다.
- 수정: `tests/test_evaluation_e2e.py`의 기존 fake HTTP 실행 검증에 UTC timestamp 범위 검사 추가.
- BE, Runtime schema, Notebook, AI/Digital Asset Artifact와 키 파일은 수정하지 않는다.
- 실제 모델 실행 전후 Trace 수집/4개 KPI 구현은 위 GAP과 실측 데이터가 해결된 후
  기존 loader/validator/analysis 경로에서 확장한다. 현 단계에서 가상 KPI를 생성하지 않는다.

검증 결과: `python -m ruff check .` PASS,
`python -m pytest 02_ai/tests/test_evaluation_e2e.py 02_ai/tests/test_evaluation_bundle.py -q`
70 passed, `python -m mypy 02_ai/src` PASS (21 source files), `git diff --check` PASS.
BE/DA의 `ai-evaluation-bundle.schema.json` SHA-256 바이트 일치 확인.
테스트는 기존 synthetic fixture/fake HTTP 검증이며 실제 Provider 성공 증적이 아니다.
