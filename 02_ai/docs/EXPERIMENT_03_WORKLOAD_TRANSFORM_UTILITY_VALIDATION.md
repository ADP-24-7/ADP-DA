# Experiment 03 Workload Transform Utility Validation

Status: `VALIDATED / ACTIVATED / E2_EXTERNAL_EXECUTION_PENDING / NO_PROVIDER_CALLS`

## Executive conclusion

E3는 Transform 기술의 일반 순위를 만들지 않았다. 동결된 `customer_summary / CUSTOMER_SUPPORT`의 업무 목적과 20개 Field Requirement를 기준으로 privacy, utility, relation, exactness, Runtime compatibility, destination compatibility를 독립 gate로 평가했다. 필수 gate 하나라도 실패하면 `NOT_FIT`이며 평균점수는 없다.

34개 실험 단위 중 23개가 `FIT`, 11개가 `NOT_FIT`이다. 최종 20-field profile은 `KEEP`, `REMOVE`, `HMAC_PSEUDO`, `VAULT_TOKEN`만 선택한다. BE resolver와 destination field contract가 두 `REQUIRED_EXACT` 금액을 `KEEP`으로 집행하고 Outbound Guard가 원본·변환값과 digest를 provider boundary 전에 검증하므로 상태는 `VALIDATED / ACTIVATED`다. Provider 호출은 0건이다.

## 1. Repository and immutable E2 input

- DA baseline: `77a93d1893fd8da2e56c18b06bf0a3052fe70767`
- BE baseline: `4cbf8dbc74665db7aa819da246926d42542a9851`
- E2 source: `E2_TO_E3_TRANSFORM_REQUIREMENTS.json`
- version/digest: `1.1.1` / `sha256:899cf31a920c1363cfb21b9c7d6f3204819222935bcbb9008a01ccbf9a8ba73e`
- cardinality: 3 cases × 20 fields = 60 immutable requirement rows
- provider authorization: `false`

E3 generator는 위 파일을 읽고 digest와 cardinality를 검증할 뿐 다시 쓰지 않는다. Workload, Purpose, Business Need, Applicability, Field Requirement, Exact/Relation/Release Requirement와 Transform Intent는 E2 소유다. 불일치는 `E3 contradiction -> E2 owner review required`로 fail-close한다.

## 2. E1 → E2 → E3 chain

E1은 Runtime stage enforcement와 traceability를 검증했다. E2는 이를 금융 업무의 Workload/Purpose, 규제·감독·내부통제, applicability와 Field Requirement로 확장했다. E3는 해당 requirement를 만족하는 method가 실제 synthetic tabular data에서 privacy와 업무 utility를 동시에 유지하는지 검증한다.

```text
Workload / Purpose / Business Need
→ Regulatory and Internal Evidence
→ Frozen Field Requirement / Transform Intent
→ Candidate Method / Method Evidence
→ Field-bound Experiment / Independent Gates
→ Validated Method
→ BE Compatibility / Activation Gap
→ Read-only FE Controller Evidence
```

## 3. Evidence method

Method matrix는 결과보다 먼저 freeze한다. 17개 source record 각각은 source type, authority, year, document, method, field type, workload condition, privacy property, utility property, limitation과 evidence strength를 가진다. 구성은 official guidance 4, security standards 3, financial policy/operation references 4, peer-reviewed research 5, vendor reference 1이다.

금융위원회 안내서는 목적·이용환경·정보주체·정보 속성과 위험을 함께 보고 삭제·대체·범주화 후 적정성과 재식별 가능성을 검토하게 한다. 개인정보보호위원회의 2026.03 가이드라인은 준비, 위험성 검토, 가명처리, 적정성 검토, 안전한 관리의 위험기반 체계를 제시한다. method 명칭만으로 안전을 선언하는 근거가 아니다.

신한투자증권 개인전문투자자 심사는 성명과 실명번호가 표시된 unmasked 서류를 요구한다. 이는 exact identity가 필요한 제한된 업무가 있음을 보일 뿐 customer summary의 외부 release를 정당화하지 않는다. 반대로 공개된 개인정보·신용정보 통제에는 가명처리, 암호화, 접근권한·접근통제, DLP, 로그와 모니터링이 결합된다. 공개 정보보호 직무자료의 masking reveal과 외부 반출 검토는 privileged reveal이 독립 권한·감사 통제여야 함을 뒷받침하지만 특정 알고리즘의 안전성 근거로 사용하지 않는다. 신한은행 가족회원 등록 신청서는 BPR 전송 전에 주민등록서류와 신분증의 실명번호 후단을 마스킹하도록 명시한다. 이는 특정 등록 workflow에서 후단 비공개와 업무 utility가 양립하는 금융 현업 사례이며, 다른 본인확인 업무로 일반화하지 않는다.

Vendor Dynamic Data Masking 자료는 role-based `UNMASK`, inference 우회 위험과 audit 필요성을 설명하는 운영 참고일 뿐 법률이나 신한 내부정책으로 표현하지 않는다.

## 4. Candidate review

| Method | Current applicability | BE support | Decision |
|---|---|---|---|
| KEEP | required exact/category facts | SUPPORTED | evaluate |
| REMOVE/SUPPRESS | unnecessary/prohibited fields | SUPPORTED | evaluate |
| MASK | relationship identifiers | SUPPORTED | suffix 2/3/4; safety not assumed |
| HMAC | scoped relationship identifiers | SUPPORTED | evaluate with key/domain limitation |
| VAULT TOKEN | controlled reversible relation | SUPPORTED | evaluate with vault limitation |
| Standard encryption | no provider-readable plaintext contract | NOT_SUPPORTED | not applicable |
| FPE | no legacy format requirement | REQUIRES_EXTENSION | not applicable; no implementation |
| OPE/ORE | no ciphertext range/sort requirement | NOT_SUPPORTED | not applicable; leakage risk |
| GENERALIZE/BIN/ROUND | exact financial facts | SUPPORTED | comparison retained; E2 prohibited |
| AGGREGATE | record-level summary required | NOT_SUPPORTED | not applicable |
| NOISE/RANDOMIZATION | exact record facts required | NOT_SUPPORTED | not applicable |

FPE의 현재 공식 상태는 NIST SP 800-38G Rev.1 second public draft다. FF1 최소 domain은 1,000,000으로 강화됐고 FF3는 제거됐다. 형식 보존은 비식별 보장이 아니다. OPE/ORE는 order/frequency leakage를 이용한 plaintext recovery가 peer-reviewed 연구에서 입증돼 현재 workload에서 후보가 아니다.

## 5. Experiment and metrics

Canonical unit은 `Workload × Purpose × Field × Transform Method`다. 세 identifier field에는 literal exposure, collision, same-entity/false match/non-match, unambiguous relation과 deterministic consistency를 사용했다. 두 exact numeric field에는 exact match, absolute/relative error, strict ordering과 threshold decision preservation을 사용했다. exact metadata에는 exact/schema gate, 제거 field에는 absence와 remaining schema gate를 적용했다.

모든 결과는 transform latency, UTF-8 payload size before/after, schema validity, deterministic consistency, transform failure, retrieval compatibility, outbound compatibility를 기록한다. Provider latency와 LLM token은 생성하지 않았다.

| Gate | PASS | FAIL | N/A |
|---|---:|---:|---:|
| Privacy | 25 | 9 | 0 |
| Utility | 25 | 9 | 0 |
| Relation | 8 | 7 | 19 |
| Exact | 7 | 2 | 25 |
| Overall | 23 FIT | 11 NOT_FIT | 0 |

MASK 기술 자체가 항상 실패한다는 결론이 아니다. 기존 분석에서 특정 account identifier의 `MASK-4`가 relation preservation 가능성을 보인 결과는 관계성 단일 축의 관찰이다. 현재 E3의 MASK 2/3/4는 세 identifier에서 source character를 남기고, 일부 suffix가 우연히 충돌하지 않더라도 현재 workload가 요구하는 privacy·identifier binding·relation gate를 동시에 만족하지 못했으므로 최종 Transform으로 선택하지 않았다. HMAC과 vault token은 세 identifier에서 literal exposure 없이 deterministic relation을 보존했다. 이 결과는 고정 synthetic domain과 key/vault control 안에서만 유효하다.

KEEP은 balance, amount와 다섯 exact contract field에서 exact/utility를 보존했다. GENERALIZE는 balance와 amount의 값을 바꾸므로 두 row 모두 `NOT_FIT`이다. 평균 오차가 작거나 ordering 대부분이 보존되는지와 무관하다. 10개 불필요·금지 field의 REMOVE는 required schema를 훼손하지 않고 absence gate를 통과했다.

## 6. Method-by-method decision

- KEEP — 적용 7 fields, 거절 0. synthetic-only allowlist 안에서 exact facts를 보존한다.
- REMOVE — 적용 10 fields, 거절 0. 이름, 연락처, 주소, 생년월일, 주민번호, 원계좌번호, free text를 제거한다.
- MASK — 적용 0, 거절 9 variants. 세 identifier × suffix 2/3/4 모두 literal exposure로 privacy gate 실패.
- HMAC — 세 identifier 모두 FIT; 최종 profile은 transaction ID에 선택. key custody와 purpose/domain separation이 조건.
- TOKEN — 세 identifier 모두 FIT; 최종 profile은 customer/account ID에 선택. detokenization authorization, vault lifecycle과 audit가 조건.
- FPE — 적용/실행 0. format requirement 없음, BE 미지원, draft/security/domain 제약.
- GENERALIZE — 적용 0, 거절 2. `REQUIRED_EXACT` balance/amount 변경.
- Standard encryption, OPE/ORE, Aggregate, Noise — 적용/실행 0. 현재 record-level provider-readable exact summary 목적과 불일치.

## 7. Validated profile and compatibility

Profile version은 `1.2.0`, digest는 `sha256:788b2da13d17ca13d5e1062ce98dce143d54810ed9dee31976f398b04a03fa0d`이다. 각 field는 E2 requirement, validated/prohibited methods, 독립 결과, E2/E3 evidence, method evidence, profile version과 activation status를 보유한다. 선택은 customer/account ID=`VAULT_TOKEN`, transaction ID=`HMAC_PSEUDO`, exact facts=`KEEP`, unnecessary/prohibited fields=`REMOVE`다. unexplained contradiction은 0이다.

BE TransformEngine은 MASK, HMAC_PSEUDO, VAULT_TOKEN, REMOVE, KEEP, GENERALIZE, FIELD_SEPARATION을 구현한다. 최종 profile method는 모두 supported다. 새 method extension은 현재 필요하지 않다. 별도 handoff는 FPE/OPE/encryption/aggregate/noise를 향후 조건부 검토 대상으로만 기록한다. `account.balance`와 `transaction.amount`의 `GENERALIZE → KEEP` activation과 `REQUIRED_EXACT` outbound 검증이 완료되어 Runtime activation gap은 0이다.

## 8. FE Controller Contract and integration freeze

Read-only API/FE에는 Workload, Purpose, Business Need, Field, Classification, E2 Requirement, Transform Intent, current Runtime method, validated method, Privacy/Utility/Relation/Exact result, Runtime/destination compatibility, activation status, rejected method와 evidence IDs를 표시한다. 실행·모델·prompt 선택, 종합점수나 method ranking은 제공하지 않는다.

`AI_INTEGRATED_VALIDATION_PROFILE.json`은 E1 Runtime enforcement, E2 policy/requirement validation, E3 transform/utility validation을 책임 경계를 유지한 채 순차 결합한다. E3 validation과 Runtime activation은 완료됐다. E2 external execution은 `PENDING_EXTERNAL_EXECUTION`, Provider governance는 `PROVIDER_GOVERNANCE_BLOCKED`, Provider calls는 0이다. Hold-out과 NIST independent final validation은 수행하지 않았다.

## 9. E2 Provider Governance and hold-out baseline

E2 Provider Governance contract `e2-provider-governance/1.2.0`은 Provider/Model/Workload/Destination binding에 Region, Retention, Reuse gate를 추가한다. contract digest는 `sha256:5f591b577fd41993682c732392405fd9329305ec8e6ff1f983913eb5bfe71039`다. Runtime gate는 활성화됐지만 현재 NVIDIA hosted 관측값은 다음 이유로 `BLOCK`이다.

| Model | Destination profile | Frozen destination digest |
|---|---|---|
| Nemotron 3.5 Lightning | `dest_nvidia-nemotron-3-5-lightning-30b-a3b` | `sha256:a6d7fb15ca4da646ca16fb92eb2a7c39327be9cdff21a130012f564749bc922e` |
| Muse Glimmer 30B | `dest_meta-muse-glimmer-30b` | `sha256:35827b9982c8813acef21a321d0bde08d856039a882c09cbf764d72d1cc3b607` |
| Gemma 4 31B IT | `dest_google-gemma-4-31b-it` | `sha256:824292c9ad5bdcd8cd1c502997053243f179782e18402ca380b4c54a0c76f991` |

- Region: requested `KR`, resolved `UNRESOLVED` → `PROVIDER_REGION_REQUIRED`
- Retention: approved `SESSION_ONLY / max 0 days`, provider exception duration unverified → `RETENTION_UNVERIFIED`
- Reuse: approved `REQUEST_EXECUTION` 외 AI model improvement 범위 존재 → `MODEL_TRAINING_NOT_ALLOWED`

NVIDIA API Catalog 문서는 NVIDIA DGX Cloud hosting까지만 확인하며 물리적 처리 region을 특정하지 않는다. API Trial 약관은 원칙적으로 세션 종료 후 content를 저장·사용하지 않지만 개별 서비스 공개와 security/fraud/abuse logging 예외를 둔다. NVIDIA Technology Access Terms의 일반 User Content 조항은 제품·서비스 개선 범위를 포함한다. 그러므로 승인되지 않은 외부 사실을 PASS로 추론하지 않는다.

`AI_E1_E2_E3_HOLDOUT_BASELINE.json`은 E1 frozen, E2 active fail-closed governance, E3 frozen/activated를 하나의 변경금지 baseline으로 묶는다. Runtime gate와 destination contract 재동결은 완료됐지만 외부 조건이 BLOCK이므로 Hold-out은 시작하지 않는다. 새 integrated digest는 `sha256:2e396f6a1482a868397e56f19a68daab5d3c6caea6e2ed800c07bcd69a996f21`이다.

## 10. Limitations / Remaining gaps

- synthetic dataset은 real customer/credit data safety를 입증하지 않는다.
- auxiliary-data re-identification attack을 직접 수행하지 않았다.
- HMAC key와 token vault 운영을 integration 환경에서 측정하지 않았다.

## Sources

- [금융위원회 금융분야 가명·익명처리 안내서](https://www.fsc.go.kr/no010101/77193)
- [개인정보보호위원회 가명정보 처리 가이드라인(2026.03.)](https://www.pipc.go.kr/np/cop/bbs/selectBoardArticle.do?bbsId=BS074&mCode=C020010000&nttId=11928)
- [NIST SP 800-188](https://doi.org/10.6028/NIST.SP.800-188), [NIST IR 8053](https://doi.org/10.6028/NIST.IR.8053)
- [NIST FIPS 198-1](https://doi.org/10.6028/NIST.FIPS.198-1), [NIST SP 800-38G Rev.1 2PD](https://doi.org/10.6028/NIST.SP.800-38Gr1.2pd)
- [신한투자증권 개인전문투자자 신청절차](https://www.shinhansec.com/siw/banking-lending/service/609001/contents.do)
- [신한투자증권 신용정보 활용체제](https://www.shinhansec.com/siw/customer-center/guide/business_guide_terms_tab8/contents.do)
- [신한투자증권 정보보호 직무자료](https://recruit.shinhansec.com/files/interview/7-5.pdf)
- [신한은행 신한 Plus 가족회원 가족합산 신청서](https://img.shinhan.com/sbank2016/form/20200918000000420005WF00001000000001.PDF?1676301714489=)
- [Microsoft SQL Server Dynamic Data Masking](https://learn.microsoft.com/en-us/sql/relational-databases/security/dynamic-data-masking)
- [PCI SSC Tokenization Product Security Guidelines](https://listings.pcisecuritystandards.org/documents/Tokenization_Product_Security_Guidelines.pdf)
- [Grubbs et al., Leakage-Abuse Attacks against ORE](https://doi.org/10.1109/SP.2017.44)
- [Naveed et al., Inference Attacks on Property-Preserving Encrypted Databases](https://doi.org/10.1145/2810103.2813651)
- [Durak and Vaudenay, Breaking FF3 over Small Domains](https://eprint.iacr.org/2017/521)
- [Woo et al., Global Measures of Data Utility](https://doi.org/10.29012/jpc.v1i1.568)
- [Sharma et al., Disclosure Risk and Utility in a Synthetic Dataset](https://doi.org/10.32604/cmc.2021.014984)
- [NVIDIA API Catalog Quickstart](https://docs.api.nvidia.com/nim/docs/api-quickstart)
- [NVIDIA API Trial Terms of Service](https://assets.ngc.nvidia.com/products/api-catalog/legal/NVIDIA%20API%20Trial%20Terms%20of%20Service.pdf)
- [NVIDIA Technology Access Terms of Use](https://developer.nvidia.com/legal/terms)
