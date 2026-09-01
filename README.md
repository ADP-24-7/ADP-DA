# ADP-DA

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
├── artifacts/          # 버전 고정된 실험·정책 후보 산출물
├── contracts/          # 개발팀 인수용 JSON Schema와 계약 문서
├── data/
│   ├── processed/      # 정제·파생 데이터. 원문 복제 금지
│   └── raw/            # 로컬 원천 데이터. 기본적으로 git 제외
├── docs/               # 분석 방향, 실행 흐름, 인수인계 기준
├── notebooks/          # 탐색 분석 노트북
├── scripts/            # 반복 실행 스크립트
├── src/adp_da/         # 재사용 가능한 Python 코드와 FastAPI 헬스체크
└── tests/              # 최소 테스트와 분석 유틸 검증
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

다른 ADP MSA 레포와 같은 Docker 네트워크에서 붙일 수 있도록 `adp-local` 외부 네트워크를 사용합니다.

```bash
make docker-up
```

헬스체크:

```bash
curl http://localhost:8010/health
```

## Make 명령

```bash
make help
make setup
make test
make lint
make format
make typecheck
make check
make docker-up
make docker-down
```

## 개발 원칙

- Python은 Runtime 정책을 직접 변경하지 않습니다.
- 승인 전 분석 결과는 `candidate` 상태로만 취급합니다.
- 원문 개인정보, 계좌, Wallet, Secret, Prompt 전문은 git과 로그에 남기지 않습니다.
- 개발팀에 넘기는 산출물은 `contracts/evaluation_artifact.schema.json` 구조를 기준으로 작성합니다.

## 참고 문서

- [프로젝트 방향성](docs/PROJECT_DIRECTION.md)
- [분석 실행 흐름](docs/ANALYSIS_WORKFLOW.md)
- [개발 인수 기준](docs/HANDOFF.md)
- [환경 설정](docs/SETUP.md)

## DA to BE Handoff Boundary

ADP-DA separates validation evidence from runtime handoff:

- `contracts/evaluation_artifact.schema.json`: actual analysis and experiment
  validation evidence.
- `contracts/policy_evaluation_artifact.schema.json`: BE handoff contract for
  policy judgment based on validated Evaluation Artifacts.

Regulatory categories, processing contexts, runtime DataClass crosswalks, and
workload/purpose bindings are defined under `contracts/`. BE-owned runtime
values remain `TBD`, `UNMAPPED`, or `UNRESOLVED` until BE publishes them.
