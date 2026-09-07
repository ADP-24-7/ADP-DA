# Evidence Coverage Validation Report

Generated at: 2026-08-26T11:45:00+09:00

This report records coverage and validation findings before changing existing evidence records. It does not create policy rules and does not make legal conclusions beyond official source text.

## Coverage Areas

| coverage_area | secured evidence | status |
| --- | ---: | --- |
| 개인정보/가명정보 | 10 | Existing evidence from 개인정보 보호법 제28조의2 through 제28조의5. |
| 개인신용정보 | 3 | Existing evidence from 신용정보의 이용 및 보호에 관한 법률 시행령 제32조. |
| 제3자 제공/위탁 | 1 | Existing evidence from 개인정보 보호법 제28조의2 제2항 only. 개인정보 보호법 제26조 is identified but not yet added. |
| 국외이전 | 0 | 개인정보 보호법 제28조의8 official text identified; not yet added to Evidence Dataset. |
| 금융 AI 이용 | 0 | FSC official 2026 금융분야 인공지능 가이드라인 page and PDF attachment identified; PDF page-level evidence is MANUAL_REQUIRED. |
| SaaS/Cloud 이용 | 0 | FSC/FSEC official SaaS pages and PDF attachments identified; PDF page-level evidence is MANUAL_REQUIRED. |
| 암호화/접근통제/로그 | 0 | 전자금융감독규정 제14조 official text identified; not yet added to Evidence Dataset. |
| 재식별/추가정보 관리 | 5 | Existing evidence from 개인정보 보호법 제28조의4 and 제28조의5. |

## Official Source Checks

### 국가법령정보센터

- 개인정보 보호법 current official page verified as `[시행 2025. 10. 2.] [법률 제20897호, 2025. 4. 1., 일부개정]`.
- 개인정보 보호법 제28조의8 official text was identified for 국외이전 coverage.
- 개인정보 보호법 제26조 official text was identified for 위탁 coverage.
- 전자금융감독규정 제14조 official text was identified for 암호화/접근통제/로그 coverage, with `[시행 2026. 2. 13.] [금융위원회고시 제2026-7호, 2026. 2. 13., 일부개정]`.
- 신용정보의 이용 및 보호에 관한 법률 시행령 current official snippets show `[시행 2026. 8. 13.] [대통령령 제36574호, 2026. 8. 11., 일부개정]`.

### 개인정보보호위원회

- 가명정보 처리 가이드라인(2026.03.) official board page identified.
- 개인정보 처리방침 작성지침(2026.4. 개정) official guide list entry identified.
- PDF originals and page-level extraction are MANUAL_REQUIRED.

### 금융위원회

- 금융분야 인공지능 가이드라인 2026 official announcement identified, including PDF attachments.
- 내부업무망 SaaS 망분리 예외 official announcement identified.
- 금융분야 마이데이터 서비스 가이드라인 and 금융분야 개인정보보호 가이드라인 official pages remain MANUAL_REQUIRED for PDF preservation and page-level parsing.

### 금융감독원

- Direct page-level source for a current privacy/security guide was not collected in this pass.
- FSS materials referenced through FSC/FSEC official notices remain MANUAL_REQUIRED until original FSS-hosted files are preserved.

### 금융보안원

- 내부업무망 SaaS 망분리 예외 적용에 따른 보안 해설서 official guide page identified.
- 금융분야 망분리 개선 로드맵 업무 설명회 자료 page identified.
- PDF originals and page-level extraction are MANUAL_REQUIRED.

## Existing 13 Evidence Validation

| evidence_id | source_id | validation_result | note |
| --- | --- | --- | --- |
| EV-00001 | law_pipa | PASS_WITH_REVIEW | 개인정보 보호법 제28조의2 제1항 text matched official source context; status remains PENDING. |
| EV-00002 | law_pipa | PASS_WITH_REVIEW | 개인정보 보호법 제28조의2 제2항 text matched official source context; status remains PENDING. |
| EV-00003 | law_pipa | PASS_WITH_REVIEW | 개인정보 보호법 제28조의3 제1항 text matched official source context; status remains PENDING. |
| EV-00004 | law_pipa | PASS_WITH_REVIEW | 개인정보 보호법 제28조의3 제2항 text matched official source context; status remains PENDING. |
| EV-00005 | law_pipa | REVIEW_REQUIRED | Existing extractor found no explicit candidate field; keep REVIEW_REQUIRED. |
| EV-00006 | law_pipa | PASS_WITH_REVIEW | 개인정보 보호법 제28조의4 제1항 text matched official source context; amendment/future-enforcement notes should be reviewed against full official article. |
| EV-00007 | law_pipa | REVIEW_REQUIRED | Existing extractor found no explicit candidate field; amendment/future-enforcement notes should be reviewed against full official article. |
| EV-00008 | law_pipa | PASS_WITH_REVIEW | 개인정보 보호법 제28조의4 제3항 text matched official source context; status remains PENDING. |
| EV-00009 | law_pipa | PASS_WITH_REVIEW | 개인정보 보호법 제28조의5 제1항 text matched official source context; status remains PENDING. |
| EV-00010 | law_pipa | PASS_WITH_REVIEW | 개인정보 보호법 제28조의5 제2항 text matched official source context; status remains PENDING. |
| EV-00011 | law_credit_info | REVIEW_REQUIRED | Existing source URL/effective-date pair needs re-verification against current 국가법령정보센터 page before modification. |
| EV-00012 | law_credit_info | REVIEW_REQUIRED | Existing source URL/effective-date pair needs re-verification against current 국가법령정보센터 page before modification. |
| EV-00013 | law_credit_info | REVIEW_REQUIRED | Text appears consistent with 제32조 제3항 context, but existing source URL/effective-date pair needs re-verification before status upgrade. |

## Manual Required Documents

| coverage_area | organization | document_name | official_page | reason |
| --- | --- | --- | --- | --- |
| 개인정보/가명정보 | 개인정보보호위원회 | 가명정보 처리 가이드라인(2026.03.) | https://www.pipc.go.kr/np/cop/bbs/selectBoardArticle.do?bbsId=BS074&mCode=C020010000&nttId=11928 | PDF original and page-level text must be preserved. |
| 개인정보/가명정보 | 개인정보보호위원회 | 개인정보 처리방침 작성지침(2026.4. 개정) | https://pipc.go.kr/np/cop/bbs/selectBoardList.do?bbsId=BS217&mCode=G010030000 | Exact current attachment must be selected and preserved. |
| 개인신용정보 | 금융위원회 | 금융분야 마이데이터 서비스 가이드라인(2021.7.29.) | https://www.fsc.go.kr/po010101/76323 | PDF original and page-level text must be preserved. |
| 제3자 제공/위탁 | 금융위원회 | 금융분야 개인정보보호 가이드라인 개정본 | https://fsc.go.kr/po010106/72612 | PDF original and page-level text must be preserved. |
| 금융 AI 이용 | 금융위원회 | 금융분야 인공지능 가이드라인 | https://www.fsc.go.kr/no010101/87142 | PDF attachment identified; page-level evidence requires manual download/extraction. |
| 금융 AI 이용 | 금융감독원 | 금융분야 AI 위험관리프레임워크 | https://www.fsc.go.kr/no010101/87142 | Referenced by FSC announcement; original FSS document must be preserved before evidence extraction. |
| 금융 AI 이용 | 금융보안원 | 금융분야 인공지능 보안 안내서 | https://www.fsc.go.kr/no010101/87142 | Referenced by FSC announcement; original FSEC guide must be preserved before evidence extraction. |
| SaaS/Cloud 이용 | 금융위원회 | 내부업무망 SaaS 망분리 예외 적용 보도자료 | https://www.fsc.go.kr/no010101/86745?srchKey=sj | PDF original available; preserve before page-based evidence extraction. |
| SaaS/Cloud 이용 | 금융보안원 | 내부업무망 SaaS 망분리 예외 적용에 따른 보안 해설서 | https://www.fsec.or.kr/bbs/detail?bbsNo=11929&menuNo=222 | PDF original and page-level text must be preserved. |
| SaaS/Cloud 이용 | 금융보안원 | 생성형 AI 및 SaaS 이용 규제특례 관련 보안대책 | https://www.fsec.or.kr/bbs/detail?bbsNo=11542&menuNo=66 | PDF original and page-level text must be preserved. |
| 암호화/접근통제/로그 | 금융보안원 | 금융부문 암호기술 활용 가이드(2019) | https://www.fsec.or.kr/bbs/detail?bbsNo=6158&menuNo=222 | PDF original and page-level text must be preserved. |

## Do Not Modify Yet

- Do not update existing evidence source URLs or effective dates until a reviewer approves changes based on the official source checks above.
- Do not mark any existing PENDING evidence as CONFIRMED until human review compares `original_text` with the official raw artifact.
- Do not create `policy_rules.json`.

## Coverage Expansion Update

Generated at: 2026-08-26T12:55:00+09:00

The Evidence Dataset was expanded from 13 to 49 records without deleting the original 13 records and without creating `policy_rules.json`.

New evidence ranges:

| range | source | coverage |
| --- | --- | --- |
| EV-00014 ~ EV-00020 | 개인정보 보호법 제26조 | 제3자 제공/위탁 |
| EV-00021 ~ EV-00024 | 개인정보 보호법 제28조의8 | 국외이전 |
| EV-00025 ~ EV-00034 | 전자금융감독규정 | 외부 서비스 이용, 클라우드, 정보보호, 접근통제, 기록/로그, 암호화 |
| EV-00035 ~ EV-00042 | 금융분야 인공지능 가이드라인 | 금융 AI 이용, 보안성, 개인정보/개인신용정보, 국외이전 점검 |
| EV-00043 ~ EV-00049 | FSC SaaS 공식 보도자료 및 첨부 PDF | SaaS/Cloud 이용, 망분리 대체 정보보호통제 |

Collected raw PDF artifacts:

| source_id | raw_path | status |
| --- | --- | --- |
| fsc_ai_guideline_2026 | data/raw/fsc_ai_guideline_20260618.pdf | COLLECTED |
| fsc_saas_cloud_2026 | data/raw/fsc_saas_cloud_20260417.pdf | COLLECTED |

Still manual-required:

| source | reason |
| --- | --- |
| PIPC 가명정보 처리 가이드라인(2026.03.) | Original PDF and page-level extraction still need preservation. |
| PIPC 개인정보 처리방침 작성지침(2026.4. 개정) | Exact current attachment still needs manual preservation. |
| FSC 금융분야 마이데이터 서비스 가이드라인 | Original PDF and page-level extraction still need preservation. |
| FSC 금융분야 개인정보보호 가이드라인 개정본 | Original PDF and page-level extraction still need preservation. |
| FSS 금융분야 AI 위험관리프레임워크 | Original FSS-hosted artifact still needs preservation. |
| FSEC 금융분야 인공지능 보안 안내서 | Original FSEC-hosted artifact still needs preservation. |
| FSEC 내부업무망 SaaS 망분리 예외 적용 보안 해설서 | Original PDF and page-level extraction still need preservation. |
| FSEC 금융부문 암호기술 활용 가이드(2019) | Original PDF and page-level extraction still need preservation. |
