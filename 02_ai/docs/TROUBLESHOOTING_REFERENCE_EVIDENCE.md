# Reference Evidence Handoff 트러블슈팅

## 기존 Evidence Ontology를 제품 API에 그대로 노출하는 문제

기존 Ontology는 법규 원문과 분석 내부 필드를 보존하기 위한 Source of Truth다. 이를 BE API 계약으로 그대로 사용하면 원문과
Notebook 처리 구조가 제품 경계로 노출된다. 별도 Reference Evidence Bundle은 bounded claim summary, source locator,
version/digest만 전달하고 기존 Ontology와 분석 파일은 변경하지 않는다.

## 분석 결과와 Runtime Policy 의미를 혼합하는 문제

금융규제 샌드박스 군집, 은행 동향, Digital Asset Infrastructure 자료는 정책 판단을 자동화하는 근거가 아니다. 초기 Bundle의
모든 항목을 `REFERENCE_ONLY`로 고정하고 `policy_artifact_refs`가 존재하면 builder가 실패하도록 했다.

## Bundle Digest만 검증하는 문제

Bundle digest만 있으면 Consumer가 개별 Evidence를 독립적으로 식별하기 어렵다. 각 Evidence의 `content_digest`와 Bundle 전체
`content_digest`를 각각 canonical SHA-256으로 계산하고, claim 변조와 manifest 변조를 별도 테스트로 검증한다.

## 생성 시각 때문에 동일 입력의 Digest가 계속 바뀌는 문제

실행할 때마다 현재 시각을 넣으면 동일 분석 Snapshot도 매번 다른 Artifact가 된다. `snapshot_at`을 source manifest에 고정하고
builder는 현재 시각을 주입하지 않아 동일 입력으로 동일 Bundle을 재생성한다.
