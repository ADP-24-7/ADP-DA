# DA-01 External Execution Result Contract

## 목적

Ethereum Transaction이 생성되거나 블록에 기록되었다는 사실과
실제 Execution 성공 결과를 동일한 상태로 처리하지 않도록
Digital Asset Runtime의 Execution Result Contract를 정의한다.

DA-01의 핵심 명제는 다음과 같다.

`Transaction Record != Execution Result`

## 분석 기준선

- Master Sample: `da_master_transaction_sample_73410.csv`
- Sample Size: `73,410`
- Transaction Hash Duplicate: `0`
- Receipt Status Missing: `0`

Transaction Type별 Execution 실패율:

- Type 0: `1.5000%`
- Type 1: `1.0250%`
- Type 2: `1.4055%`
- Type 3: `0.0250%`
- Type 4: `4.7875%`

현재 Ethereum 모집단 구성비를 반영한 가중 결과:

- Weighted Execution Failure Rate: `1.4354%`
- Weighted Execution Success Rate: `98.5646%`

## 통계 검증

### 가설

H0:
Transaction Type과 Execution Result는 서로 독립이다.

H1:
Transaction Type과 Execution Result는 서로 독립이 아니다.

### 결과

- Chi-square: `672.6848`
- df: `4`
- p-value: `2.8604e-144`
- Cramér's V: `0.0957`
- Minimum Expected Frequency: `127.39`
- Expected Frequency < 5: `0%`

H0는 기각되었다.

Transaction Type별 Execution 실패율은 동일하지 않았지만,
본 분석의 Runtime 설계 결론은 특정 Transaction Type의 실패 원인을
BE가 판단하도록 만드는 것이 아니다.

핵심 설계 결론은 모든 주요 Transaction Type에서
Transaction 기록 이후 Execution 실패가 실제로 존재한다는 점이다.

## Runtime Contract 요구사항

BE Runtime은 다음 상태를 동일하게 처리해서는 안 된다.

- External Request 생성
- Transaction 전송
- Transaction Hash 확보
- Blockchain Transaction 기록
- Execution Result 확인
- 최종 Runtime Decision

특히 다음 조건만으로 최종 `PASS`를 확정해서는 안 된다.

- Transaction 생성 성공
- 외부 Provider 응답 성공
- `transaction_hash` 확보
- Transaction이 블록에 포함됨

실제 Receipt 또는 이에 준하는 Execution Result Evidence가 확인된 이후에
최종 실행 결과를 확정해야 한다.

## 상태 분리 요구

Runtime에는 최소한 다음 의미적 상태가 분리되어야 한다.

1. Outbound Request 생성
2. External Transaction 제출
3. Execution Result 대기
4. Execution 성공 확인
5. Execution 실패 확인
6. Result 미확정 / Recovery 대상

정확한 Enum 이름과 State Machine 구현은 BE 소유로 유지한다.

DA는 다음 의미 분리만 Contract Requirement로 전달한다.

`SUBMITTED / SENT != EXECUTION_CONFIRMED`

## PASS 의미

Digital Asset Runtime에서 `PASS`는
Transaction이 생성되거나 외부에 전달되었다는 의미가 아니다.

최종 PASS가 Execution Result까지 포함하는 Runtime 단계라면,
Receipt 등 실제 실행 성공 Evidence가 확인된 이후에만 확정할 수 있다.

Execution 확인 이전의 요청은 중간 상태로 유지한다.

## Failure 및 Unknown 처리

Execution Result가 실패로 확인된 경우
Transaction이 이미 기록되어 있더라도 성공 상태로 승격하지 않는다.

Execution Result를 확인할 수 없는 경우에는 성공 또는 실패로 임의 판정하지 않고
기존 BE Recovery / SENT_UNKNOWN 흐름과 연결한다.

DA-01은 Recovery 전략 자체를 정의하지 않는다.

Recovery 및 Idempotency 상세 검증은 `DA-06`에서 수행한다.

## Trace / Audit 요구사항

Audit 및 Trace에서는 최소한 다음 의미를 분리하여 기록해야 한다.

- Transaction 식별자
- Outbound 제출 상태
- Transaction Hash
- Execution Result
- Execution Result 확인 시점
- Runtime 최종 Decision
- 관련 Policy / Approval Trace Reference

전송 성공과 Execution 성공을 하나의 상태 필드로 합치지 않는다.

정확한 Field Name 및 Schema는 BE Contract에 맞춰 Crosswalk한다.

## Runtime Boundary

DA-01은 다음 판단을 수행하지 않는다.

- KYC
- AML
- Sanctions
- Wallet Risk
- VASP Risk
- 고객 위험등급
- 거래 승인 여부

해당 판단은 FPG 이전 단계에서 이미 완료된 것으로 본다.

FPG의 역할은 승인된 Transaction의 외부 실행과
실제 Execution Result 사이의 상태를 통제하고 증명하는 것이다.

## BE 반영 결론

DA-01 분석에 따라 BE Runtime은

`Transaction Record != Execution Result`

원칙을 강제해야 한다.

외부 Transaction 제출 또는 Transaction Hash 확보를
최종 Execution 성공으로 취급하지 않으며,

`Submitted/Sent`
→ `Execution Pending`
→ `Execution Confirmed / Execution Failed`

의 의미적 상태 분리를 유지한다.

본 요구사항은 기존 Common Runtime,
External Status Query,
SENT_UNKNOWN,
Recovery,
Observability,
Audit/Trace 구조와 연결하여 구현한다.

## Evidence Artifact

- [External Execution Notebook](../../notebooks/runtime_validation/DA_01_external_execution.ipynb)
- [분석 요약](../../artifacts/da_01_external_execution/analysis_summary.json)
- [통계검증 및 Notebook의 10쌍 Bonferroni 사후검정](../../artifacts/da_01_external_execution/statistical_validation.json)
- [Runtime 요구사항](../../artifacts/da_01_external_execution/runtime_requirements.json)
- [기존 BE Crosswalk·CONTRACT_GAP·검증 범위](DA-00-DA-01-EVIDENCE-GAPS.md)
