# P0 Runtime 준비 점검 — 2026-09-10

결과: **BLOCKED / FAIL-CLOSED**. Contract 구조 변경 없음. Provider HTTP 호출 0회,
새 execution ID 없음, 실제 Freeze/Bundle/Trace 생성 없음. 테스트 fixture를 실측 Evidence로 사용하지 않았다.

## 1. CRLF 해결

`03_digital_asset/contracts/be_loader_v1/`의 schema 6개는 BE schema와 JSON semantic이 모두
같다. DA 파일의 CRLF를 LF로 바꾼 바이트는 Git HEAD와 정확히 같았다. 의미/expected hash를
수정하지 않고 HEAD 원본 바이트로 복원했다. `.gitattributes`에 해당 schema의 `-text`를 추가해
기존 SHA-256 Evidence 원본 보존 convention을 적용했다. Schema 내용 diff는 없다.

`python -m pytest -q`: **170 passed**, 기존 Starlette deprecation warning 1개.

## 2. PostgreSQL / migration

| 항목 | 코드/환경 점검 결과 |
|---|---|
| Host 직접 실행 기본값 | `localhost:5432`, database `adp` |
| 기존 Compose BE 내부 | `postgres:5432`, database `adp` |
| Username 설정 소스 | `SPRING_DATASOURCE_USERNAME`; Compose DB 초기화는 `POSTGRES_USER` |
| Password 설정 소스 | `SPRING_DATASOURCE_PASSWORD`; Compose DB 초기화는 `POSTGRES_PASSWORD`; 값은 기록하지 않음 |
| URL/port override | `SPRING_DATASOURCE_URL`, `POSTGRES_PORT`, `POSTGRES_DB` |
| Migration | Spring Boot Flyway, `classpath:db/migration`, enabled=true |
| Local fixture | `ADP_LOCAL_FIXTURES_ENABLED=true`일 때 `LocalAuthFixtureLoader`가 ApplicationReadyEvent에서 `db/local/` SQL 적재 |
| 기존 실행 방식 | BE Makefile `postgres-up`: shared `adp-local` network + `docker compose up -d postgres` |
| 기존 DB image/storage | `postgres:16-alpine`, 기존 named volume `adp-be-postgres-data` |
| 호스트 접속 확인 | `127.0.0.1:5432` connection refused, WinError 10061 |
| 실행 도구 | PATH의 docker/psql/postgres, Docker Desktop 표준 설치 경로, PostgreSQL 표준 설치 경로, 해당 Windows service 미발견 |
| WSL | distro 목록 명령 exit 1, 설치 안내 반환; 사용 가능한 distro 확인 불가 |

호스트 권한에서도 동일한 연결 거부를 확인했다. 샌드박스 네트워크 제한으로 오인하지 않는다.
현재 도구 상태로는 기존 Compose DB를 시작할 수 없다. 임의 native/embedded DB나 별도 DB 환경을
만들지 않았다. Docker가 준비되면 기존 BE `make postgres-up` 절차를 사용할 수 있다.
이 점검에서 machine-level Docker/WSL 설치는 수행하지 않았다.

V40 파일과 세 구조 (`runtime.ai_evaluation_contract`, `ai_evaluation_case_input`,
`ai_evaluation_contract_binding`)는 존재한다. **실 DB migration 적용, Flyway history,
테이블 생성, 기존 데이터 regression은 미검증**이다. 실제 적용 성공으로 보고하지 않는다.

## 3. 실제 Freeze

Baseline: `ai-eval-baseline-2026-09-07` / `customer-summary-ko-001`.
BE `127.0.0.1:8080` 역시 호스트에서 connection refused(10061)다. 실제 Freeze API를 호출할
서버가 없으므로 실행하지 않았다. evaluation_contract_version, dataset/prompt/policy/transform/
retrieval version, sampling, seed/reasoning의 **실제 Snapshot 값은 모두 미확보**다.
`fixed_conditions_digest`도 미생성이다. 테스트용 digest를 대신 기재하지 않는다.

## 4. Dataset provenance

- DA manifest dataset version: `financial_synthetic_processed_v1`.
- manifest가 선언한 CSV 11개 파일의 SHA-256: **11/11 일치**.
- 현재 manifest 원본 바이트 SHA-256:
  `sha256:2e54e595ded98144cc9b57459497768318e9d5616ccd39e9a711e174d7faaee0`.
- BE baseline의 등록 dataset digest:
  `sha256:9afdc4bf89c0047a5e90f21e6f8eaffb4f6c148998f1740f30baf666bdae0a44`.
  두 값은 같지 않다. 등록 digest의 산출 규칙/적재 증명이 없으므로 임의로 같은 의미라고
  해석하거나 catalog 값을 바꾸지 않는다.
- `customers.csv` 1,057행에서 literal `CustomerID=customer-100`은 없다. 숫자 문자열 `100`도 없다.
- BE `db/local/V2__local_data_access_fixture.sql`은 `customer-100`과 `acct-100-1`을 직접
  삽입하고 transaction 날짜를 `current_date` 기준으로 생성한다. DA CSV를 읽는 loader가 아니다.
- 해당 fixture와 DA manifest 사이의 승인된 row mapping/적재 provenance를 확인하지 못했다.
  **DB의 실제 적재값 자체는 연결 불가로 읽지 못했다.** 동일 provenance PASS로 판정할 수 없다.

따라서 DB가 시작되더라도 적재/row-reference provenance 확인 전에는 Provider를 실행하지 않는다.

## 5. Readiness

| 검사 | 판정 |
|---|---|
| BE health/readiness | BLOCKED: 8080 connection refused |
| Evaluation Run readiness API | 미호출: BE 없음 |
| Contract Freeze 존재 | 미확인: DB/BE 없음 |
| 3 Model Profile / Destination / approval reference | 코드 등록 3개 확인; 실제 DB 승인 상태 미검증 |
| Runtime API authentication | 현재 실행 process와 BE/DA `.env`에서 `ADP_RUNTIME_API_KEY` 미확인; 서버 인증 미검증 |
| NVIDIA credential | 현재 host process와 BE/DA `.env`에서 `NVIDIA_API_KEY` 미확인 |
| Outbound host TLS | `integrate.api.nvidia.com:443` 연결 및 인증서 검증 성공; HTTP 요청 없음 |
| BE outbound guard/실제 egress | 서버 미기동으로 미검증; host TLS 성공으로 대체하지 않음 |
| Dataset provenance | NOT_VERIFIED / FAIL-CLOSED |

기존 `evaluation_e2e.py --session-id p0-runtime-readiness-20260910` preflight 결과도
`ready_for_live_execution=false`. 로컬 header 설정의 형식 검사는 서버 인증 성공을 의미하지 않는다.
사용자는 조건부 실호출을 승인했지만, 필수 조건이 실패해 실행 확인 환경변수를 활성화하거나
`--execute`를 호출하지 않았다. 승인 부재를 blocker로 삼지 않았다.

## 6. Provider / P0-01 Evidence

- Nemotron / Muse Glimmer / Gemma: 모두 **NOT_ATTEMPTED**.
- execution ID / Provider Request·Response / Guard·Delivery Trace: 새 Evidence 없음.
- Evaluation Bundle v2: 실제 export 없음.
- 이 문서는 CRLF 회귀 테스트, 환경 probe, manifest integrity 및 provenance blocker의 점검 기록이다.
  P0-01 실제 Trace Completeness 분석 입력은 아직 없다.
- Quality/Privacy 점수 및 Runtime Rule Candidate는 생성하지 않았다.

재개 조건은 기존 Docker/PostgreSQL 실행 기반, 실제 데이터 적재 provenance, BE 기동/인가,
credential 주입, 실제 Freeze 및 readiness PASS다. API key 값은 문서/출력/commit에 포함하지 않았다.
