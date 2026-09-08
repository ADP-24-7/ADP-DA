# ADP-DA
## Current Domain Layout

```text
ADP-DA/
├── 01_industry_analysis/        # shared industry analysis only
├── 02_ai/                       # AI analysis, contracts, artifacts, code, tests
└── 03_digital_asset/            # Digital Asset analysis workspace
```

AI notebooks, AI handoff artifacts, AI contracts, and the FastAPI analysis package now live under `02_ai/`. Digital Asset analysis starts under `03_digital_asset/data/raw/crypto_card/` and `03_digital_asset/notebooks/`.
Financial Privacy Gateway 프로젝트의 데이터 분석·평가 레포지토리입니다.

이 레포는 Python 기반 Offline 분석, Detector 평가, Threshold 검증, Versioned Artifact 생성을 담당합니다. Runtime 정책 집행과 Source of Truth는 별도 Gateway Core 레포에서 관리합니다.

## 역할 범위

- 산업 변화 분석과 Evidence 정리
- 데이터 유형, 처리기법, Metric, Threshold 후보 검증
- Privacy, Utility, Performance, Relationship Preservation 실험
- Golden, Failure, Replay용 분석 Artifact 생성
- 개발팀으로 넘길 Handoff Contract 정리

## 기본 구조

```text
ADP-DA/
├── 01_industry_analysis/   # 공통 산업분석
├── 02_ai/                  # AI evidence, gateway, data, notebooks, artifacts, contracts, docs, src, tests
├── 03_digital_asset/       # Digital Asset evidence, gateway, data, notebooks, artifacts, contracts, docs, src, tests
└── scripts/                # repository-level validation/build scripts only
```

## 빠른 시작

macOS와 Windows Git Bash 모두 Makefile을 기준으로 실행합니다.

```bash
make setup
make check
```

### 사전 준비

- macOS: Python 3.12, Docker Desktop, `make`
- Windows: Git Bash, Python 3.12, Docker Desktop, `make`

Windows의 Git Bash에는 `make`가 기본 포함되지 않을 수 있습니다. 없으면 아래 중 하나로 설치합니다.

```bash
winget install GnuWin32.Make
```

또는 Chocolatey 사용 시:

```bash
choco install make
```

Python 실행 명령이 환경마다 다르면 아래처럼 지정할 수 있습니다.

```bash
make setup PYTHON=python3.12
make setup PYTHON="py -3.12"
```

## Docker 실행

ADP-BE의 `docker-compose.yml`이 로컬 통합 개발 스택의 Source of Truth입니다.
ADP-DA의 `docker-compose.yml`은 DA 환경만 추가하는 override이며, Makefile이 두 파일을
결합해 동일한 BE PostgreSQL Evidence volume을 사용합니다.

```bash
make setup
make docker-up
```

NVIDIA Provider를 통한 BE 실호출 전에는 `../ADP-BE/.env`에 `NVIDIA_API_KEY`를
설정해야 합니다. BE Connector 변수와 DA Python 클라이언트 변수의 차이 및 안전한
확인 방법은 [환경 설정](SETUP.md#be-ai-connector--nvidia-설정)을 참고합니다.
BE가 이미 모델 실행을 완료했다면 `make ai-eval-consume`으로 Provider 재호출 없이
Readiness, Bundle 검증 및 DA 분석만 수행할 수 있습니다.

## NCP Object Storage

DA artifact는 Local/NCP 공통 `ArtifactStore` 계약으로 게시하며 upload 전·download 후
SHA-256을 검증합니다. 기본 테스트는 외부 호출을 하지 않고, 실제 QA Bucket 검증은
명시적 opt-in으로만 실행합니다. 설정과 보안 경계는
[NCP Object Storage Integration](02_ai/docs/NCP_OBJECT_STORAGE_INTEGRATION.md)을 참고합니다.

저장소를 pull해도 NCP Key는 전달되지 않습니다. 실제 Bucket을 사용할 팀원은 QA용
Credential을 별도로 발급받아 아래처럼 Git에서 제외된 파일을 준비해야 합니다.

```bash
make ncp-storage-env
chmod 600 .env.ncp.local
# .env.ncp.local에 NCLOUD_ACCESS_KEY / NCLOUD_SECRET_KEY 입력
make ncp-storage-preflight
```

`access_key_present`, `secret_key_present`가 모두 `true`인지 확인한 뒤에만 실제 NCP 명령을
실행합니다. Credential은 Git, PR, Notion, 메신저 및 로그에 첨부하지 않습니다.

일반 Storage Manifest와 BE P0-5용 Digital Asset Bundle Manifest는 서로 다른 계층입니다.
BE로 전달하는 최종 값은 Bundle 게시 결과의 `manifestReference`와
`expectedContentDigest`이며, 실제 명령과 현재 BE 연동 경계는 위 통합 문서에 정리되어
있습니다. Artifact bucket은 명시적 allowlist를 통과해야 하고 `*tfstate*` bucket은 항상
거부됩니다.

## Docker 파일 기준

- `Dockerfile`: CI/NCP 배포용 image build
- `Dockerfile.dev`: 로컬 개발용 FastAPI reload image
- `docker-compose.yml`: BE 통합 Stack에 적용하는 DA 전용 override
- `.env.example`: DA Consumer/E2E 로컬 환경변수 샘플

## Make 명령

```bash
make setup
make docker-up
make docker-logs
make docker-ps
make docker-down
make check
```

## 개발 원칙

- Python은 Runtime 정책을 직접 변경하지 않습니다.
- 승인 전 분석 결과는 `candidate` 상태로만 취급합니다.
- 원문 개인정보, 계좌, Wallet, Secret, Prompt 전문은 git과 로그에 남기지 않습니다.
- 개발팀에 넘기는 산출물은 `02_ai/contracts/evaluation_artifact.schema.json` 구조를 기준으로 작성합니다.

## 참고 문서

- [프로젝트 방향성](02_ai/docs/PROJECT_DIRECTION.md)
- [분석 실행 흐름](02_ai/docs/ANALYSIS_WORKFLOW.md)
- [개발 인수 기준](02_ai/docs/HANDOFF.md)
- [환경 설정](SETUP.md)

## DA to BE Handoff Boundary

ADP-DA separates validation evidence from runtime handoff:

- `02_ai/contracts/evaluation_artifact.schema.json`: actual analysis and experiment
  validation evidence.
- `02_ai/contracts/policy_evaluation_artifact.schema.json`: BE handoff contract for
  policy judgment based on validated Evaluation Artifacts.

Regulatory categories, processing contexts, runtime DataClass crosswalks, and
workload/purpose bindings are defined under `02_ai/contracts/`. BE-owned runtime
values remain `TBD`, `UNMAPPED`, or `UNRESOLVED` until BE publishes them.
