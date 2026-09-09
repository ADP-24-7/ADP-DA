# Policy · Regulation Reference Evidence Handoff

## 책임 경계

Reference Evidence Bundle은 DA 분석 결과를 제품 조회 계층으로 전달하는 계약이다. 분석 결과를 Runtime Rule로 자동 승격하지
않으며 `REFERENCE_ONLY` Evidence는 Policy Artifact와 binding할 수 없다. 법규 원문과 Notebook 전체 내용은 Bundle에 포함하지
않고 source reference, bounded claim summary, version과 digest만 전달한다.

## 계약

- Schema: `02_ai/contracts/reference-evidence-bundle-v1.schema.json`
- Source: `02_ai/reference_evidence/reference_evidence_source_v1.json`
- Handoff: `02_ai/artifacts/reference_evidence_v1/reference-evidence-bundle.json`
- Schema version: `adp-reference-evidence-bundle/v1`
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
모두 `REFERENCE_ONLY`이며 Runtime 실행 결과에 영향을 주지 않는다.

## BE 소비 Gate

BE는 schema version, strict field set, Evidence/Bundle digest, identity 중복, 기간, `REFERENCE_ONLY` binding 금지를 다시 검증해야
한다. 저장 후 목록·상세·Workload mapping 조회만 제공하며 Runtime Policy 적용에는 별도의 승인된 Policy Artifact binding이
필요하다.
