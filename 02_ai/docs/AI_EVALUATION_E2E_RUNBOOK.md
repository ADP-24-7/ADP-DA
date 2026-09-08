# AI Evaluation BE→DA E2E Runbook

이 자동화는 고정 baseline `ai-eval-baseline-2026-09-07`에 대해 다음 순서를 재현한다.

1. BE Runtime API에 1 Case × 3 Model Profile을 각각 제출
2. 관리자 Bundle API에서 원본 JSON export
3. DA의 Schema, digest, Cartesian Product, provenance 검증
4. 검증을 통과한 Bundle만 DA 분석 산출물로 변환

실제 NVIDIA 호출은 비용과 외부 전송을 수반하므로 기본 명령은 preflight만 수행한다.
스크립트는 NVIDIA key를 직접 사용하지 않는다. Provider credential은 BE에만 주입되어야 한다.

## 1. BE가 준비되기 전: 로컬 preflight

```bash
ADP_RUNTIME_API_KEY=local-dev-api-key \
python -m adp_da.evaluation_e2e --session-id preflight-001
```

출력의 `ready_for_live_execution=false`는 정상이다. 실제 호출 승인 환경변수를 설정하지 않은
상태이기 때문이다. 이 단계는 URL 정책, 고정 3개 binding, Runtime key 존재 여부와 Bundle
인증 설정을 검사하며 네트워크 요청을 보내지 않는다. credential 값은 출력하지 않는다.

## 2. BE 완료 후: 로컬 E2E 실행

BE에 Flyway V25, AI connector, NVIDIA credential, local fixtures/auth가 준비된 것을 확인한 뒤:

```bash
export ADP_BE_BASE_URL=http://127.0.0.1:8080
export ADP_RUNTIME_API_KEY=local-dev-api-key
export ADP_BE_LOCAL_ADMIN_USER_ID=da-evaluation-reader
export ADP_BE_LOCAL_ADMIN_ROLES=PRIVILEGED_OPERATOR
export ADP_AI_E2E_CONFIRM_REAL_PROVIDER=YES

python -m adp_da.evaluation_e2e \
  --execute \
  --session-id be-v25-smoke-001 \
  --output outputs/real_be_evaluation/be-v25-smoke-001
```

`--session-id`는 재실행마다 새 값으로 지정한다. 같은 값은 BE idempotency replay가 목적일 때만
재사용한다. 출력 디렉터리가 이미 존재하면 덮어쓰지 않고 실패한다.

원격 HTTPS 배포에서는 local 관리자 Header 대신 `ADP_BE_TOKEN`을 설정한다. 로컬 Header를
운영 인증 대체로 사용하지 않는다. 원격 plain HTTP와 URL 내 credential은 거부된다.

## 3. 성공 산출물과 완료 조건

- `bundle_export/sha256-<raw digest>.json`: BE 응답 원본 바이트
- `analysis/raw/`: DA Consumer가 별도로 보존한 content-addressed 원본
- `analysis/<content digest>/<options>/validation.json`: 독립 검증 결과
- 같은 분석 디렉터리의 `evaluation_summary.json`, 분석 JSON, dataset, DA report
- `e2e-result.json`: 세 execution ID, raw digest, 분석 경로를 담은 secret-free 실행 기록

명령 성공은 세 POST가 HTTP 성공하고 execution ID를 반환했으며, Bundle export와 모든 DA
검증·분석이 완료됐음을 뜻한다. Provider 실패 실행도 BE가 COMPLETE evidence로 Bundle에
포함하면 분석 대상이다. 모델 품질, utility, SLA 또는 policy threshold의 승인을 뜻하지 않는다.

## 4. 실패 해석

- `runtime_api_key_present`: Runtime API key가 DA 실행 프로세스에 없음
- `bundle_auth_present`: 로컬 privileged Header 또는 원격 Bearer token이 없음
- `real_provider_execution_confirmed`: 외부 실호출 명시 승인이 없음
- Runtime HTTP 실패: BE fixture/approval/destination/provider 설정 및 모델 접근 권한 확인
- Bundle 404: 1×3 최신 실행 증적 완성 여부와 institution/workload scope 확인
- DA validation 실패: 원본을 보존하고 producer 계약/데이터 불일치를 수정하며 우회하지 않음

테스트는 fake HTTP transport를 사용하므로 NVIDIA 또는 실행 중인 BE를 호출하지 않는다.

```bash
python -m pytest 02_ai/tests/test_evaluation_e2e.py
```
