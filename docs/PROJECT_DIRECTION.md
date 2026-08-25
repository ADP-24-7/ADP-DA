# Project Direction

## 목적

Financial Privacy Gateway에서 분석팀은 Evidence, Metric, Threshold, Transform 후보를 검증하고 개발팀이 구현 가능한 Artifact로 넘깁니다.

## 책임 경계

Python 분석 레포의 책임:

- Offline 분석과 평가
- Dataset, Experiment, Metric, Threshold 기록
- Detector와 Transform 후보 검증
- Golden, Failure, Replay Artifact 생성
- Policy Candidate와 Handoff Contract 작성

Python 분석 레포의 비책임:

- Runtime 정책 활성화
- 운영 Decision의 Source of Truth
- 원문 고객 데이터, 실자산, Secret 보관
- Java Core, UI, Cloud 인프라의 직접 구현

## 개발팀으로 넘길 핵심 결과물

- 변화 근거와 데이터 문제 정의
- Evidence 구조와 처리기법 후보
- Dataset Version과 실험 결과
- 처리기법별 특성, 한계, Failure Case
- Runtime 검증 요구사항
- 운영 Metric과 장애·복구 검증 관점

## 현재 초기화 범위

지금 단계에서는 분석팀이 바로 들어와 작업할 수 있는 최소 공통 환경만 둡니다.

- Python 3.12 버전 고정
- macOS, Windows 공통 README
- Docker Compose 기반 로컬 실행 구조
- MSA 연결용 `adp-local` Docker 네트워크
- 분석 Artifact JSON Schema 초안
- Handoff와 분석 Workflow 문서 골격
