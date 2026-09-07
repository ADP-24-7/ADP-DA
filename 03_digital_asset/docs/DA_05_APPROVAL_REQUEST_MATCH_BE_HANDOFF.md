# DA-05 Approval / Request Match BE Handoff

DA-05는 **PRE_EXECUTION 승인조건 검증**이다. Approval Match PASS는 거래 신규 승인이나
Execution Success가 아니다. 기존 pipeline의 `Approved Value vs Requested Value Match`
단계에 연결하며 전체 FPG 아키텍처나 BE enum을 재설계하지 않는다.

## 입력과 판정

원본 [DA-05 입력 문서](handoff/DA_05_approved_requested_match.md)의 Approval/Request
필드를 개념 계약으로 사용한다. 최종 BE naming은 기존 schema로 crosswalk한다.
Approval Resolver와 Request Resolver는 신뢰된 `approval_id ↔ request_id` 관계를 제공해야 한다.
배열 순서·행 위치·같은 index에 의존한 binding은 금지한다. 결측·잘못된 binding·입력은
fail-closed이며 reference validator는 예외를 발생시켜 PASS를 반환하지 않는다.

| Rule | 비교 | 적용 |
|---|---|---|
| Asset | requested_asset == approved_asset | 항상 |
| Amount | requested_amount <= approved_max_amount | 0 금액도 적용 |
| Destination | 검증된 Ethereum 주소를 lowercase로 비교 | Address Transaction |
| Period | valid_from <= requested_at <= valid_until | 양 끝 inclusive |

하나 이상의 applicable violation이면 BLOCK, 모두 일치하면 DA-05 단계 PASS다.
유효기간은 timezone-aware UTC로 비교한다. 잘못된/naive timestamp를 추정하지 않는다.

## Contract Creation과 Exact Amount

Notebook의 `request_type=CONTRACT_CREATION`은 거래 구조이며 숫자 Ethereum
`transaction_type` 0~4와 다른 축이다. BE는 신뢰된 구조 resolver로 생성 요청임을 확인해야 한다.
일반 주소 요청의 destination 결측을 생성 요청으로 간주해 검사를 우회하면 안 된다.
생성 요청의 Destination은 NOT_APPLICABLE, match 결과는 null이며 violation에 포함하지 않는다.
**NOT_APPLICABLE != PASS**. 실행 후 `contract_address`를 PRE 요청주소로 대체하지 않는다.

Amount는 DA-02의 atomic integer/digit string을 사용한다. FLOAT·rounding·표시용 decimal은
canonical comparison에 사용하지 않는다. 최대한도 비교는 DA-02의 approved/outbound **동일값
보존**과 별개다. 한도 이내더라도 승인된 구체 금액을 바꾸는 것은 허용되지 않는다.
숫자 Transaction Type 자체로 PASS/BLOCK하거나 0 Amount 검사를 생략하지 않는다.

## Runtime Architecture / Trace

Approval Resolver → Request Resolver → 명시적 Binding → Transaction Structure Context →
Rule Applicability Resolver → Asset/Exact Amount/Destination/Period Comparator →
Violation Aggregator → Decision → Trace/Evidence Binding.

Trace는 approval_id, request_id, applicability, 네 비교 결과, violation reason/count,
approval_match, decision, evaluated_at, policy/contract version, validation evidence reference를
재구성할 수 있어야 한다. 실제 BE field명은 기존 계약에 연결하며 73,410개 Fixture를 싣지 않는다.

DA-01의 Transaction≠Execution, DA-03의 승인/요청/제출/결과 Trace 구분을 유지한다.
DA-05의 주소 일치 검사는 DA-04의 외부 시스템별 Payload Field 통제와 다르다.
Contract Creation 예외를 DA-04 Unknown Destination 허용으로 확장하지 않는다.
기존 vNext beneficiary_address 필수 조건과의 applicability 연동은 BE가 확정해야 한다.

## Evidence / 재현 / 한계

- [원본 Notebook](../notebooks/runtime_validation/DA_05_approved_requested_match.ipynb)
- [Artifact 7개](../artifacts/da_05_approved_requested_match/analysis_summary.json)
- [Runtime Architecture](../artifacts/da_05_approved_requested_match/runtime_architecture.json)
- [개념 Match Contract](../artifacts/da_05_approved_requested_match/approval_request_match_contract.json)
- [DA-02 Exact](DA_02_EXACT_PRESERVATION_BE_HANDOFF.md)

실제 요청 context 73,410건과 통제된 Approval Fixture 비교의 저장 결과는 PASS 36,514,
BLOCK 36,896, 단일 위반 29,557, 복수 위반 7,339, 일치율 100%, 오분류 0이다.
실제 기관 승인 로그가 아니며 위반 비율은 Runtime threshold나 시장 위반율이 아니다.
통계·그래프·실험 세부는 Notebook을 참조한다.

원본 Notebook/Markdown은 byte 단위 보존했다. 기존 로컬 경로·np 선행 사용·lint 오류는
원본을 수정해 숨기지 않는다. 기존 analyst evidence convention대로 Notebook만 Ruff에서
제외하고 신규 comparator/생성기/테스트는 검사한다. 원본 Run All은 수행하지 않았다.
Artifact는 저장 출력을 추출하고 Master 구조를 대조하여 생성한다.
원본 도입부 Purpose/Counterparty는 최종 실험에 포함되지 않아 구현 근거로 승격하지 않는다.
원본의 위치 기반 fixture 구성은 BE binding 알고리즘으로 복제하지 않는다.

```bash
python 03_digital_asset/src/build_da_05_handoff.py
python 03_digital_asset/src/build_da_05_handoff.py --check
python -m pytest 03_digital_asset/tests -q
python -m ruff check .
```

실제 승인 resolver, 승인된 생성 요청의 구조 증빙, provider/unit/scale/time/address/audit
mapping은 [CONTRACT_GAP](../artifacts/da_05_approved_requested_match/contract_gaps.json)이다.
Reference comparator는 DA Contract 테스트용이며 BE 구현 완료를 의미하지 않는다.
