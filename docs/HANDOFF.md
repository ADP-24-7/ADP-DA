# Handoff

## 분석팀 산출물의 개발 인수 기준

개발팀에 넘기는 분석 산출물은 다음 항목을 최소로 포함합니다.

- `workload_id`, `experiment_id`, `dataset_version`
- 데이터 출처와 수집 기준
- Privacy, Utility, Performance, Relationship Preservation Metric
- Baseline, Threshold, Threshold Basis
- 처리기법 후보: Raw, Mask, HMAC, Vault Token 등
- Failure Case와 적용 한계
- 개발팀이 구현해야 할 Requirement, Control, Test 후보
- 재현 가능한 실행 명령 또는 Notebook 경로

## 승격 상태

- `candidate`: 분석팀 후보. Runtime 적용 불가
- `validated`: 리뷰 완료. 개발팀 인수 가능
- `hold`: 근거, Metric, 데이터 품질, 보안 검토 부족
- `rejected`: 현재 범위에서 사용하지 않음

## 현재 초기 상태

- Python 3.12 분석 환경만 고정
- FastAPI 헬스체크만 제공
- 실제 데이터, 실험 코드, 정책값은 아직 없음
