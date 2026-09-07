# DA-04 Outbound Destination Runtime Validation

현재 vNext의 Field-level 목적지 분리는 성립한다. 다만 Field 집합이 완전하다는 사실은
실제 upstream 값이나 Provider wire schema까지 확보했다는 뜻이 아니다.

## Evidence와 범위

- [실행된 DA-04 Notebook](../../notebooks/runtime_validation/DA_04_outbound_destination.ipynb)
- [분석 및 Artifact 생성기](../../src/da_04_outbound_destination.py)
- [Notebook 생성기](../../src/build_da_04_notebook.py)
- [Master CSV](../../data/processed/da_master_transaction_sample_73410.csv)
- [기존 Regulatory Requirement](../../data/processed/regulatory_outbound_requirements.csv)
- [기존 execution mapping](../../data/processed/outbound_requirement_execution_mapping.csv)
- [권위 있는 vNext matrix](../../artifacts/outbound_design_vNext/outbound_requirement_matrix.json)
- [foundation 04](../../notebooks/foundation/04_regulatory_outbound_design_analysis.ipynb)
- [foundation 05](../../notebooks/foundation/05_fpg_control_boundary_validation.ipynb)

기준 main commit: `25dcdfa8bd742516a5156c04b24a00341c1fedbd`.
PR [#11](https://github.com/ADP-24-7/ADP-DA/pull/11),
[#12](https://github.com/ADP-24-7/ADP-DA/pull/12),
[#13](https://github.com/ADP-24-7/ADP-DA/pull/13),
[#14](https://github.com/ADP-24-7/ADP-DA/pull/14),
[#15](https://github.com/ADP-24-7/ADP-DA/pull/15),
[#16](https://github.com/ADP-24-7/ADP-DA/pull/16),
[#19](https://github.com/ADP-24-7/ADP-DA/pull/19),
[#20](https://github.com/ADP-24-7/ADP-DA/pull/20),
[#21](https://github.com/ADP-24-7/ADP-DA/pull/21)의 본문·merge 정보와 현재 파일을 검토했다.

foundation은 규제·schema gap·Outbound 설계·책임 경계를 이미 정리했다.
DA-04는 이를 복제하거나 법령을 재해석하지 않고 실제 표본 가용성·목적지 partition·
유출/Exact/phase invariant 및 negative control을 검증한다. CSV는
`PROCESSED_ANALYSIS_ARTIFACT`이며 운영 거래 입력이 아니다.

## 실제 계산 결과

18개 Requirement, 12개 unique Field, 6개 Destination, 정규화 35행이다.
requirement_id 및 legal basis 연결은 모두 일치한다. 연결 존재가 법적 완전성을 의미하지는 않는다.
CSV의 legacy exact/transform/destination/missing action과 vNext의 차이는
`analysis_summary.json`의 `legacy_to_vnext`에 남겼다. 현재 Runtime 권위는 vNext다.

실제 Master는 73,410행·고유 hash 73,410개다. `to_address` 결측은 46건이며
임의 주소나 계약 주소로 대체하지 않았다. `value_lossless` 73,410개가 atomic integer
문자열 문법을 만족한다. 이는 원천 Amount ground truth와 일치함을 다시 증명한 결과가 아니다.
FLOAT `value`를 Amount canonical source로 사용하지 않았다.

| 지표 | 결과 | 단위/해석 |
|---|---:|---|
| 안전하게 매핑 가능한 표본 Field | 5/12 (41.67%) | 주소 2종, amount, tx_hash, timestamp |
| legacy ONCHAIN 후보 | 6/12 (50.00%) | transaction_id의 hash 후보 포함, 현재 PRE 입력으로 부적합 |
| 실행 전 off-chain 의존 | 6/12 (50.00%) | identity 2종, KYC, VASP, 승인 Trace ID, asset context |
| POST_EXECUTION 의존 | 3/12 (25.00%) | tx_hash, execution_status, timestamp |

source와 phase는 별도 축이므로 비율을 더하지 않는다. transaction-level 실제 값 가용성은
별도 표에 있으며 beneficiary_address는 73,364/73,410이다.
모든 Master 관측은 POST_EXECUTION 데이터다. 주소·금액이 관측돼도 실행 전 승인/요청
일치가 입증되는 것은 아니다. `receipt_status` 관측값을 provider execution_status/finality
enum으로 자동 변환하지 않는다.

## 목적지별 설계 효과

baseline `EXTERNALIZABLE_SUPERSET`은 최소 한 외부 목적지에 허용된 8개 Field다.
OMIT/NOT_EXTERNALIZED/Internal-only 및 POST 내부 trace-only는 제외한다.
이는 비교용 Field 집합이며 실제 baseline payload를 송신하지 않았다.

| Destination | Superset | Payload Field | 절대 감소 | 상대 감소 | 필수 Field 집합 유지 |
|---|---:|---:|---:|---:|---:|
| BLOCKCHAIN_EXECUTION_SYSTEM | 8 | 4 | 4 | 50.0% | 100% |
| EXTERNAL_VASP | 8 | 2 | 6 | 75.0% | 100% |
| TRAVEL_RULE_PROVIDER | 8 | 5 | 3 | 37.5% | 100% |

목적지와 무관한 Field의 profile 잔존은 0이다. 이 결과는 개인정보 위험의 감소율,
실제 Required Value coverage, Provider 전송 수용률, 실행 성공률이 아니다.
특히 MINIMIZE/MAP_TO_EXTERNAL_SCHEMA의 실제 wire 구현은 미확정이다.

## 정상 Contract와 SIMULATION 분리

정상 vNext 재검증에서 contract 위반·금지 외부화·OMIT 외부화·Exact 손실변환·
POST Field의 외부 PRE payload 혼입은 각각 0건이다.
내부 목적지의 PASS_THROUGH row는 14개로, `PASS_THROUGH != EXTERNALIZE`를 보여준다.

Negative **SIMULATION 9개 중 9개 탐지**, 정상 Field-profile fixture 1개 PASS:

- 내부 KYC Field 유출
- 필수 amount 누락
- EXACT_REQUIRED + MINIMIZE
- POST tx_hash를 PRE payload에 삽입
- 정의되지 않은 Destination
- exact value 변경
- 목적지에 무관한 external identity Field
- FLOAT amount
- contract 자체의 POST requirement를 PRE로 변경

fixture 기호 값을 실제 identity/KYC/approval로 해석하지 않는다.
정상 fixture PASS는 Field-profile 검사에 한정된다. 실제 provider schema가 없으면
모든 기호 값이 있어도 일반 preflight는 REVIEW이며 전체 Runtime PASS를 생성하지 않는다.

## BE Handoff

기존 [vNext pipeline](../../artifacts/outbound_design_vNext/runtime_pipeline.json)을 재사용한다.

`ApprovedTransaction → RegulatoryOutboundRequirement → RequiredFieldResolver →
Source/Availability Resolver → Approved-vs-Requested Validator → Exact Validator →
Transform/Field Separation → Destination Payload Builder → Outbound Decision →
External Execution → POST_EXECUTION Result Binding → Trace/Reconciliation`

이는 기능 책임을 설명하며 새로운 BE class/API/DB field/enum을 강제하지 않는다.

Destination Profile은 `destination`, `allowed_fields`, `required_fields`,
`internal_only_fields`, `required_exact_fields`, `runtime_phase`, `on_missing_action`을
제공한다. `required_input_fields`와 payload 필드는 다르다. KYC status는 내부 입력 존재만
확인하며 OMIT된 원값은 외부뿐 아니라 내부 audit payload에도 넣지 않는다.
최종 status reference/audit wire naming은 BE Contract에 맞춘다.

필수 Runtime 검증은 presence, exact preservation, transform compatibility,
externalization policy, phase validation, destination validation이다.

| 조건 | 처리 |
|---|---|
| mandatory 입력 또는 payload 누락 | 원래 `on_missing_action` 보존, PASS 불가 |
| 승인값/Exact 불일치, 금지 유출, 허용되지 않은 phase 혼입 | BLOCK |
| unsupported Destination, unmapped/ambiguous Provider schema | REVIEW |
| POST missing `REVIEW_AFTER_HANDOFF` | 원래 action 유지 후 기존 BE 상태/복구 계약에 연결 |

`REVIEW_AFTER_HANDOFF`는 source의 action이며 새 Decision enum이 아니다.
`PASS`는 현 handoff 조건 충족이고 거래 승인·AML 적합·Settlement 성공이 아니다.
`REVIEW`는 정보 미확정이며 KYC/AML judgment가 아니다.

FPG는 trusted upstream KYC result를 입력으로 소비할 뿐 판단을 생성하지 않는다.
KYC/AML/Sanctions/Customer Risk/VASP Eligibility/Wallet/Signing/Custody/Settlement Finality는
외부 책임이다. DA-01의 Transaction≠Execution, DA-02 exact-safe representation,
DA-03 Approval→Request→Submission→Execution Trace 및 PRE/POST 분리를 유지한다.

## Artifact 및 재현

- [analysis_summary.json](../../artifacts/da_04_outbound_destination/analysis_summary.json): 집계·가용성·legacy 차이
- [validation_metrics.json](../../artifacts/da_04_outbound_destination/validation_metrics.json): 설계 효과·정상 invariant·SIMULATION
- [destination_payload_profile.json](../../artifacts/da_04_outbound_destination/destination_payload_profile.json): phase별 Field 계약·규제 lineage
- [runtime_requirements.json](../../artifacts/da_04_outbound_destination/runtime_requirements.json): 기존 pipeline·책임·decision 및 fail-closed 요구
- [contract_gaps.json](../../artifacts/da_04_outbound_destination/contract_gaps.json): 9종 GAP 및 requirement 연결
- [Evidence JSON Schema](../../contracts/da_04_evidence.schema.json): 분석 Artifact 구조 검증용

이 Schema/Profile은 VerifyVASP/CODE 등 Provider wire-format이 아니다.
표준 개발 의존성과 `[notebook]` 의존성을 설치한 Python 3.12에서 repo root 기준:

```bash
python 03_digital_asset/src/build_da_04_notebook.py
python -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=180 03_digital_asset/notebooks/runtime_validation/DA_04_outbound_destination.ipynb
python 03_digital_asset/src/da_04_outbound_destination.py --check
python -m pytest 03_digital_asset/tests
python -m ruff check .
python scripts/validate_contracts.py
```

Notebook Run All이 계산과 Artifact 생성을 수행한다. JSON은 결과 dict에서 직렬화한다.
재생성 시 기존 generated_at을 유지하여 check/Run All 간 동일 결과를 비교한다.
Master SHA-256은 raw bytes, 다른 Git text source는 CRLF→LF bytes 기준이다.
Notebook code cell hash 및 저장된 결과 JSON을 독립 재계산 결과와 테스트로 대조한다.
한글 폰트를 탐색하고 없는 환경에서는 영문 graph label을 사용한다.

## 통계 검수와 남은 GAP

추정 대상은 현재 contract Field 집합·partition·invariant다. 무작위 실험이나 독립적인
모집단 평균 비교가 아니므로 추론검정/p-value를 사용하지 않았다.
절대 Field 감소·상대 노출 Field 감소·필수 Field 유지가 설계 효과크기다.

남은 9종 GAP:

1. Provider MINIMIZE/MAP_TO_EXTERNAL_SCHEMA 세부 schema
2. legacy hash와 실행 전 transaction_id 의미 불일치
3. 승인 asset/Token scale context
4. receipt_status와 execution_status/finality mapping
5. 실제 upstream identity/KYC/VASP 입력
6. 기존 법적 candidate/REVIEW_REQUIRED
7. Provider wire 및 실제 BE E2E
8. 실제 approval/request/submission/result Trace
9. 원천 재추출·Amount ground truth provenance

논리 검수는 Notebook에 PASS/GAP으로 별도 기록했다. 실제 approval Trace와 provider
binding은 GAP이며 수행하지 않은 BE 검증이나 규제 확정을 PASS라고 주장하지 않는다.
