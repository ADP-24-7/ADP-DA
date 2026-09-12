# Regulatory Baseline Audit

기준일은 2026-09-12이며, ADP-DA·ADP-BE·ADP-FE의 코드, 계약, schema, migration, API, test, 문서, artifact, notebook 및 workflow를 추적했다. 공식 원문은 `OFFICIAL_REGULATORY_SNAPSHOT_2026-09-12.json`에 URL/API 식별자와 HTTP 응답 SHA-256으로 고정했다. 검색결과·뉴스·민간 요약은 근거로 사용하지 않았다.

## 판정 기준

- `CURRENT`: 기준일에 유효한 공식 원문 또는 공식 발행본을 snapshot으로 확보했다.
- `REVIEW_REQUIRED`: 공식 원문은 확보했으나 적용범위, 시행일 분기 또는 비구속적 guidance의 법적 해석이 필요하다.
- `UNRESOLVED`: 공식 발행기관 원문을 확보하지 못했다.
- `repository_reference`는 교체 전 legacy 근거를 보존한다. 최신 baseline 판정과 legacy artifact의 연결 완전성은 별개다.

## 보정 결과

- 개인정보 보호법은 법률 제21445호, 시행 2026-09-11을 canonical source로 고정했다.
- 개인정보 보호법 시행령, 금융회사 지배구조법·시행령, 신용정보법 시행령의 최신 공식 locator를 확보했다.
- FSS AI 위험관리 프레임워크는 공식 금융감독원 배포 근거로 교정했다.
- 특정금융정보법·시행령, FIU 보고·감독규정과 AML/CFT 업무규정은 공식 국가법령정보센터 식별자로 교정했다.
- 손상되거나 `NOT_VERIFIABLE`이던 Digital Asset source는 snapshot의 UTF-8 metadata와 digest로 대체했다. 원래 artifact의 손상 기록은 감사 이력으로 남겼다.
- 기관 홈페이지 root만 있던 설정은 source로 인정하지 않았다. 식별 가능한 PIPC·FSC·FSEC 문서는 개별 공식 게시물로 교체했고, 식별 불가능한 FSS root 항목은 registry source에서 제외했다.

## 법률 검토 유지 항목

전자금융거래법·시행령의 현행/예정 시행본 구분, AI 기본법 일부 조문의 단계적 시행, SaaS 가이드의 개정 이력, MyData·금융 개인정보·암호기술 legacy guidance의 현재 적용범위, FIU CDD 웹가이드의 무버전성, FATF Recommendations의 국내 적용범위는 `REVIEW_REQUIRED`로 유지했다.

## Repository 연결 감사

- DA에는 AI E2의 source→requirement→control과 Digital Asset DA-01~06 evidence/control이 존재한다.
- BE에는 Reference Evidence의 immutable identity (`evidence_id`, `evidence_version`, `content_digest`)와 독립적인 Policy Lifecycle이 이미 존재한다.
- FE에는 Reference Evidence와 Policy Governance projection이 각각 존재한다.
- 이번 변경은 BE에 두 기존 aggregate를 잇는 immutable association을 추가하고, FE 기존 Policy Governance 화면에서 그 association을 read-only로 표시한다. 자동 candidate, 자동 approval, 자동 activation 또는 Runtime decision 변경은 없다.

## Summary

| 항목 | 결과 |
| --- | ---: |
| AI registry | 21 |
| Digital Asset registry | 17 |
| BOTH source | 6 |
| Unique source | 32 |
| CURRENT | 23 |
| REVIEW_REQUIRED | 9 |
| UNRESOLVED | 0 |
| AI 완전 연결 | 1 / 21 |
| Digital Asset 완전 연결 | 1 / 17 |

`CURRENT`/`REVIEW_REQUIRED` 합계는 공통 source를 한 번만 센 unique source 기준이다. E2E 완전 연결은 실제 fixture와 API/UI contract test로 증명한 domain mapping만 센다.
# Refresh lifecycle completion (2026-09-13)

- Canonical sources: 32 (`AI` 15, `DIGITAL_ASSET` 11, `BOTH` 6).
- Repository status: `CURRENT` 23, `REVIEW_REQUIRED` 9, `UNRESOLVED` 0.
- Trace vocabulary is normalized to `CONNECTED`, `PENDING_REVIEW`, and `MISSING`.
- The nine legal-owner decisions are materialized in `REGULATORY_REVIEW_QUEUE.json`; automatic approval and activation are disabled.
- Scheduled and manual refresh share one fail-closed service. Unchanged/fetch-failed/parse-failed sources produce no candidates.
