# Setup

## Runtime

- Python: 3.12
- Package manager: pip
- Local virtual environment: `.venv`
- Container runtime: Docker Compose
- Command runner: Makefile

## Windows 기준

Windows 팀원은 PowerShell이 아니라 Git Bash를 기준으로 실행합니다.

Git Bash에는 `make`가 기본 포함되지 않을 수 있으므로, 없으면 `winget install GnuWin32.Make` 또는 `choco install make`로 설치합니다.

Makefile은 Windows에서 `.venv/Scripts/python.exe`, macOS에서 `.venv/bin/python`을 사용하도록 분기합니다.

## Local Commands

```bash
make setup
make check
```

개별 실행:

```bash
make test
make lint
make format
make typecheck
```

## Docker Commands

`adp-local` 네트워크는 다른 ADP MSA 레포와 로컬에서 연결하기 위한 공통 네트워크입니다.
DA의 Makefile은 `../ADP-BE/docker-compose.yml`을 통합 Stack의 Source of Truth로 사용하고
이 저장소의 `docker-compose.yml`을 DA 전용 override로 함께 로드합니다. 따라서 BE와 DA에서
기동한 Stack이 동일한 `adp-be-postgres-data` Evidence volume을 사용합니다.

```bash
make docker-up
make docker-down
```

### BE AI Connector / NVIDIA 설정

BE Connector와 실제 NVIDIA credential은 `../ADP-BE/.env`에서만 관리합니다. DA의
`.env`는 Consumer/E2E 설정만 소유합니다. 키는 `.env.example`, 문서, 로그에 기록하지 않습니다.

```dotenv
ADP_AI_CONNECTOR_ENABLED=true
NVIDIA_API_KEY=<local-secret>
ADP_NVIDIA_BASE_URL=https://integrate.api.nvidia.com
ADP_AI_CONNECTOR_READ_TIMEOUT=60s
```

- `NVIDIA_API_KEY`가 비어 있어도 컨테이너 자체는 기동되지만 NVIDIA Provider 호출은
  실패합니다. 실제 3개 모델 실행 전에는 키가 비어 있지 않은지 로컬에서 확인합니다.
- `ADP_NVIDIA_BASE_URL`은 BE Connector용이며 `/v1`을 붙이지 않습니다. BE가 요청
  경로를 조립합니다.
- 위 설정은 `../ADP-BE/.env`에 둡니다. `NVIDIA_BASE_URL`(`/v1` 포함)과
  `NVIDIA_MODEL`은 선택적인 DA Python NIM 클라이언트 전용이며 BE에는 전달되지 않습니다.
- `ADP_AI_CONNECTOR_BASE_URL`의 기본값은 BE Compose와 동일한 내부 mock 주소입니다.
  Compose가 함께 기동하는 `mock-ai` 서비스가 이 주소를 제공합니다. NVIDIA 모델은
  `ADP_NVIDIA_BASE_URL`을 사용하므로 실호출 시 이 값과 구분합니다.
- 타임아웃은 필요할 때 `ADP_AI_CONNECTOR_CONNECT_TIMEOUT` 및
  `ADP_AI_CONNECTOR_READ_TIMEOUT`으로 조정합니다. 실제 세 모델 평가의 로컬 기본값은
  BE 평가 계약과 동일하게 `60s`입니다.

DA override는 컨테이너에서 BE→DA 평가 명령을 실행할 수 있도록
`ADP_BE_BASE_URL=http://adp-be:8080`, Runtime API Key 및 로컬 관리자 Header 값을
전달합니다. `ADP_AI_E2E_CONFIRM_REAL_PROVIDER`는 DA `.env`에서 기본 `NO`이며 실제 Provider
3회 호출 직전에만 명시적으로 `YES`로 설정합니다. 이미 BE에서 실행을 마쳤다면
`make ai-eval-consume`으로 Readiness→Bundle→분석만 수행합니다.

현재 BE는 원격 Bearer/JWT 인증을 제공하지 않습니다. `ADP_BE_TOKEN`과
`ADP_BE_REMOTE_BEARER_AUTH_ENABLED`는 운영 인증 Adapter가 실제 배포·검증되기 전에는 각각
빈 값과 `NO`로 유지합니다.

`docker-compose.yml`은 단독 Stack 파일이 아니므로 직접 `docker compose up`하지 않고
`make docker-up`, `make docker-ps`, `make docker-down`을 사용합니다.
