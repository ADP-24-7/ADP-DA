# Regulatory Evidence E2E Gap Analysis

연결 기준: `Official Source → DA Evidence → Requirement → Control → Policy Artifact → BE Policy Version/Lifecycle → FE 표시`.

## Domain summary

| Domain | Source | DA Evidence | Control | BE Lifecycle | FE | Gap |
| --- | --- | --- | --- | --- | --- | --- |
| AI | PIPA 법률 제21445호 / `REF-REG-PIPA-2026-09-11` | CONNECTED | CONNECTED | CONNECTED | CONNECTED | exemplar 없음 |
| DIGITAL_ASSET | 가상자산이용자보호법 / `REF-REG-VA-UPA-2024` | CONNECTED | CONNECTED | CONNECTED | CONNECTED | exemplar 없음 |
| BOTH | PIPA 시행령 | PARTIAL | CONNECTED | MISSING | MISSING | 최신 source는 확보했으나 policy binding 미생성 |
| BOTH | 금융회사 지배구조법·시행령 | MISSING | PARTIAL | PARTIAL | PARTIAL | maker-checker 통제는 있으나 source별 binding 미생성 |
| BOTH | 전자금융거래법·시행령 | MISSING | PARTIAL | MISSING | MISSING | 시행본·적용범위 법률 검토 후 materialize 필요 |
| AI | 신용정보법·시행령 | CONNECTED/PARTIAL | CONNECTED | PARTIAL | PARTIAL | 최신 시행령 locator는 확보, lifecycle binding 미생성 |
| AI | AI 기본법·시행령 | PARTIAL/CONNECTED | CONNECTED | PARTIAL | PARTIAL | 단계별 시행 조문 검토 필요 |
| AI | 전자금융감독규정 및 금융 AI guidance | CONNECTED | CONNECTED | PARTIAL | PARTIAL | source identity의 policy binding 확대 필요 |
| AI | PIPC/FSC/FSEC legacy guidance | PARTIAL | CONNECTED | MISSING | MISSING/PARTIAL | 현행 적용범위 legal-owner review 및 materialize 필요 |
| DIGITAL_ASSET | 가상자산법 시행령·감독규정 | CONNECTED/PARTIAL | CONNECTED | PARTIAL | PARTIAL | source별 binding 확대 필요 |
| DIGITAL_ASSET | 특정금융정보법·시행령·FIU 고시 | PARTIAL/MISSING | CONNECTED/PARTIAL | PARTIAL/MISSING | PARTIAL/MISSING | 교정 snapshot을 기존 DA evidence로 materialize 필요 |
| DIGITAL_ASSET | FIU CDD 및 FATF | PARTIAL/CONNECTED | CONNECTED | PARTIAL | PARTIAL | 무버전 guidance 및 국내 적용범위 검토 필요 |

## Status inventory

| Status | Unique sources | 설명 |
| --- | ---: | --- |
| CURRENT | 23 | 공식 원문·식별자·시행일·digest 확보 |
| REVIEW_REQUIRED | 9 | 공식 원문 확보, 법률 해석 또는 적용성 검토 필요 |
| UNRESOLVED | 0 | 공식 원문 미확보 항목 없음 |

세부 source별 상태, 조문, requirement/control 및 policy artifact 목록은 두 registry의 각 entry가 source of truth다.

## Remaining gaps

1. exemplar 두 건 외 30개 unique source/domain mapping은 association을 생성하지 않았다. 자동으로 policy에 연결하지 않고 법률 owner 검토와 maker-checker 절차를 거쳐야 한다.
2. 최신 snapshot을 기존 AI E2 corpus와 Digital Asset evidence master에 materialize하는 별도 승인 작업이 필요하다. frozen 실험 수치는 변경하지 않았다.
3. `REVIEW_REQUIRED` 9건은 시행일 분기, 비구속 guidance 또는 국내 적용범위를 확정해야 한다.
4. BE association은 추적성만 제공하며 Runtime rule, lifecycle 전이, approval 판단을 유발하지 않는다.

## Summary

| 지표 | 결과 |
| --- | ---: |
| AI source | 21 |
| Digital Asset source | 17 |
| Common source | 6 |
| Unique source | 32 |
| DA→BE→FE 완전 연결 | 2 domain mappings |
| Partial/Missing | 30 unique source/domain mappings |
# Implemented refresh closure (2026-09-13)

The registry now drives authority adapters, normalized SHA-256 comparison, selective parsing, AI/Digital Asset impact splitting, pending evidence/requirement/control/policy candidates, and the existing maker-checker lifecycle. Remaining `MISSING` trace values represent real source-to-artifact materialization work and are not reported as connected.
