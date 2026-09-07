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
