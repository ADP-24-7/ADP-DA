# Analysis Workflow

## 1. 산업 변화 분석

AI, SaaS, Cloud, Digital Asset 변화와 금융 데이터 활용 환경을 정리합니다. 확정되지 않은 정책 해석은 결론 근거에서 제외합니다.

## 2. Evidence Ontology

공식 문서, 논문, 규정, 샌드박스 자료를 수집하고 데이터 유형, 처리기법, Metric, Threshold 후보로 분류합니다.

## 3. 실제 데이터 실험

확보 가능한 데이터에서 Raw, Mask, HMAC, Vault Token 등 처리기법별 Privacy, Utility, Performance를 비교합니다.

## 4. 처리기법 검증

처리기법별 장단점, 실패 사례, 재현성, Runtime 적용 요구사항을 정리합니다.

## 5. Gateway 구현 Handoff

분석 결과는 `contracts/evaluation_artifact.schema.json` 형식으로 정리하고, 개발팀이 구현할 Requirement, Control, Test 후보를 함께 전달합니다.

## 6. Runtime 검증 피드백

개발 Runtime 결과와 Offline 실험 결과를 비교해 False Allow, Review 부담, Drift, Audit Gap을 분석합니다.

## 7. DA to BE Handoff Boundary

The handoff path is:

```text
Official Source
-> Evidence
-> Requirement Candidate
-> Control
-> Test
-> Policy Candidate
-> Evaluation
-> Evaluation Artifact
-> PolicyEvaluation Artifact
-> BE Runtime
```

`02_evidence_ontology` remains the frozen source for Evidence and Requirement
Candidate artifacts. `03_gateway_rules` remains the frozen source for Control,
Test, and Policy Candidate artifacts.

`contracts/evaluation_artifact.schema.json` is validation evidence for actual
analysis and experiment results. `contracts/policy_evaluation_artifact.schema.json`
is the BE handoff contract for policy judgment derived from validated Evaluation
Artifacts. PolicyEvaluation Artifacts reference validation evidence through
`validation_artifact_refs` instead of duplicating experiment metrics.
