# Policy · Regulation Reference Evidence Handoff

## 책임 경계

Reference Evidence Bundle은 DA 분석 결과를 관리자 보조 조회 계층으로 전달하는 계약이다. 분석 결과를 Runtime Rule로 자동
승격하지 않으며 DA는 Policy Artifact 연결이나 Evidence Governance 상태를 결정하지 않는다. 법규 원문과 Notebook 전체 내용은
Bundle에 포함하지 않고 공식 source reference, DA analysis reference, bounded claim summary, version과 digest만 전달한다.

## 계약

- Schema: `02_ai/contracts/reference-evidence-bundle-v1.schema.json`
- Source: `02_ai/reference_evidence/reference_evidence_source_v1.json`
- Handoff: `02_ai/artifacts/reference_evidence_v1/reference-evidence-bundle.json`
- Schema version: `adp-reference-evidence-bundle/v1`
- Bundle/Evidence version: `1.1.0` — Admin Trace 책임 축소와 Source/Analysis 분리
- Identity: `bundle_id + bundle_version + content_digest`
- Evidence identity: `evidence_id + evidence_version + content_digest`

`content_digest`는 UTF-8, object key 정렬, 공백 없는 JSON을 SHA-256으로 계산한다. 개별 Evidence digest는 해당 Evidence의
`content_digest`를 제외한 필드를 대상으로 하며 Bundle digest는 최상위 `content_digest`를 제외한 전체 Bundle을 대상으로 한다.

## 생성

```bash
python -m adp_da.reference_evidence \
  --source 02_ai/reference_evidence/reference_evidence_source_v1.json \
  --schema 02_ai/contracts/reference-evidence-bundle-v1.schema.json \
  --output 02_ai/artifacts/reference_evidence_v1/reference-evidence-bundle.json
```

이번 v1 세트는 금융규제 샌드박스, 금융위원회 정책자료, 5대 은행 동향, Digital Asset Infrastructure 분석을 포함한다.
모두 `REFERENCE_ONLY`로 고정되며 Runtime 실행 결과에 영향을 주지 않는다. `source_ref/source_url/source_locator`는 공식
원천을, `analysis_ref/analysis_locator/analysis_version`은 해당 원천을 해석한 DA 분석물 위치를 나타낸다.

## BE 소비 Gate

BE는 schema version, strict field set, Evidence/Bundle digest, identity 중복과 기간을 다시 검증해야 한다. 저장 후 목록·상세와
Workload 관련성 조회만 제공하며 Runtime request path, Policy Lifecycle, Current Selection과는 독립적으로 유지한다. 향후
Policy 연결이 필요해지더라도 DA Handoff가 아니라 BE-owned 별도 관리 기능으로 설계한다.
