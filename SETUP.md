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

```bash
make docker-up
make docker-down
```

### BE AI Connector / NVIDIA 설정

DA Compose로 로컬 통합 스택을 실행할 때도 `adp-be`는 BE Compose와 같은 AI
Connector 환경변수를 받습니다. `.env.example`을 복사해 생성한 추적 제외 `.env`에
실제 키를 입력합니다. 키는 `.env.example`, 문서, 로그에 기록하지 않습니다.

```dotenv
ADP_AI_CONNECTOR_ENABLED=true
NVIDIA_API_KEY=<local-secret>
ADP_NVIDIA_BASE_URL=https://integrate.api.nvidia.com
```

- `NVIDIA_API_KEY`가 비어 있어도 컨테이너 자체는 기동되지만 NVIDIA Provider 호출은
  실패합니다. 실제 3개 모델 실행 전에는 키가 비어 있지 않은지 로컬에서 확인합니다.
- `ADP_NVIDIA_BASE_URL`은 BE Connector용이며 `/v1`을 붙이지 않습니다. BE가 요청
  경로를 조립합니다.
- `NVIDIA_BASE_URL`(`/v1` 포함)과 `NVIDIA_MODEL`은 DA Python NIM 클라이언트용이며
  BE에는 전달되지 않습니다.
- `ADP_AI_CONNECTOR_BASE_URL`의 기본값은 BE Compose와 동일한 내부 mock 주소입니다.
  Compose가 함께 기동하는 `mock-ai` 서비스가 이 주소를 제공합니다. NVIDIA 모델은
  `ADP_NVIDIA_BASE_URL`을 사용하므로 실호출 시 이 값과 구분합니다.
- 타임아웃은 필요할 때 `ADP_AI_CONNECTOR_CONNECT_TIMEOUT` 및
  `ADP_AI_CONNECTOR_READ_TIMEOUT`으로 조정합니다. 실제 세 모델 평가의 로컬 기본값은
  BE 평가 계약과 동일하게 `60s`입니다.

DA 컨테이너에서 BE→DA 평가 명령을 실행할 수 있도록 Compose는
`ADP_BE_BASE_URL=http://adp-be:8080`, Runtime API Key 및 로컬 관리자 Header 값을
전달합니다. `ADP_AI_E2E_CONFIRM_REAL_PROVIDER`는 안전을 위해 기본 `NO`이며 실제 Provider
3회 호출 직전에만 `YES`로 설정합니다. 이미 BE에서 실행을 마쳤다면
`make ai-eval-consume`으로 Readiness→Bundle→분석만 수행합니다.

현재 BE는 원격 Bearer/JWT 인증을 제공하지 않습니다. `ADP_BE_TOKEN`과
`ADP_BE_REMOTE_BEARER_AUTH_ENABLED`는 운영 인증 Adapter가 실제 배포·검증되기 전에는 각각
빈 값과 `NO`로 유지합니다.

비밀 값을 출력하지 않고 전달 여부만 확인하려면 다음처럼 변수 이름과 설정 유무만
검사할 수 있습니다.

```bash
docker compose config --format json | python -c '
import json, sys
env = json.load(sys.stdin)["services"]["adp-be"]["environment"]
names = ("ADP_AI_CONNECTOR_ENABLED", "ADP_NVIDIA_BASE_URL", "NVIDIA_API_KEY")
print({name: ("set" if env.get(name) else "empty") for name in names})
'
```
