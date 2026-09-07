# DA-06 Recovery / Idempotency BE Handoff

DA-06의 저장된 분석 결과를 BE 구현 요구사항으로 고정한다. 새로운 분석, 실제 Provider 호출,
BE Recovery 구현 또는 운영 검증을 수행한 문서가 아니다.

## 구현 진입점과 근거

| 파일 | 역할 |
|---|---|
| [analysis_summary.json](../artifacts/da_06_recovery_idempotency/analysis_summary.json) | 관측 Evidence |
| [validation_metrics.json](../artifacts/da_06_recovery_idempotency/validation_metrics.json) | 가상 실험 및 기존 통계 출력 |
| [runtime_requirements.json](../artifacts/da_06_recovery_idempotency/runtime_requirements.json) | 9개 불변조건, 전이, 금지 조건 |
| [runtime_architecture.json](../artifacts/da_06_recovery_idempotency/runtime_architecture.json) | 파이프라인, 기존 BE 필드와 상태 매핑 |
| [contract_gaps.json](../artifacts/da_06_recovery_idempotency/contract_gaps.json) | 관측 및 구현 공백 |
| [da_06_handoff.schema.json](../contracts/da_06_handoff.schema.json) | Artifact 스키마; Provider wire schema 아님 |

원본 [Notebook](../notebooks/runtime_validation/DA_06_recovery_idempotency.ipynb)과
[분석 Markdown](handoff/DA_06_recovery_idempotency.md)은 바이트 그대로 보존한다.
통계 상세·그래프·실험 코드는 Notebook을 참조한다. Artifact의 `evidence_refs`는 두 원본과
기존 Master CSV의 SHA-256을 연결한다. 셀 번호는 0부터 시작한다.

관측값: Ethereum 73,410건, Hash 결측·중복 0, 고유 Hash 73,410,
Hash→Receipt 연결 73,410/73,410(100%), receipt 성공 72,241(98.4076%), 실패 1,169(1.5924%).
Notebook의 `FINALIZED`는 receipt_status=1의 **실험용 표기**이다.
실제 Settlement Finality, 업무 요청의 멱등성 또는 exactly-once 실행 증거가 아니다.

가상 실험은 모든 거래가 제출되고 Hash가 확보된 뒤 응답을 알 수 없다고 가정한다.
NAIVE_RESEND 중복 Submission 위험은 73,410건, 중복 외부효과 위험은 72,241건(98.4076%),
Wilson 95% CI [98.3145%, 98.4956%]이다.
RECONCILIATION_FIRST는 기존 Receipt 연결로 73,410건(100%)의 상태를 복구할 수 있었고,
즉시 재전송 0건, 중복 외부효과 위험 0%이다. 실제 Provider 조회 성공률을 측정한 것이 아니다.
기존 paired 결과는 McNemar exact p<0.001, 절대 위험 차이 98.4076%p, 상대 위험 감소 100%이다.
0%는 상태 확인 전 제출을 금지한 정책의 구조적 결과이며 모집단 추론의 핵심 근거로 사용하지 않는다.

**98.4076%는 실제 SENT_UNKNOWN 발생률이나 실제 중복거래율이 아니다.** 이미 제출한 거래의
상태를 확인하지 않고 재전송한다고 가정했을 때 기존 거래가 이미 성공 상태였던 비율이다.
실제 Ethereum 데이터에 Gateway Timeout, 응답 유실, Retry 로그가 없으므로 실제 장애율을 추정하지 않는다.

## BE가 지켜야 하는 계약

1. INV-1: 같은 업무 요청의 중복을 기존 기관·workload·idempotency_key 범위에서 식별한다.
   전송 전에 키를 정하고 기존 request_hash 일치 여부를 검사한다. 일치하면 기존 실행을 재사용하고,
   다른 요청 내용은 충돌로 처리한다. 진행 중 요청은 새 Submission으로 바꾸지 않는다.
2. INV-2: 외부 실행 ID가 있으면 새 제출보다 기존 실행 조회를 우선한다.
3. INV-3: `UNKNOWN != FAILED`이다. Timeout은 외부 실행의 Terminal Failure 증명이 아니다.
4. INV-4: SENT_UNKNOWN에서 즉시 자동 재전송하지 않는다.
5. INV-5: 기존 외부 실행과 원 요청을 결합하여 Reconciliation한다.
6. INV-6: FINALIZED인 동일 업무 요청을 다시 제출하지 않는다.
7. INV-7: Terminal Failure가 확인된 이후에만 별도 정책으로 Retry eligibility를 평가한다.
8. INV-8: 허용된 Retry에도 원 요청과 자식 요청의 lineage를 보존한다.
9. INV-9: 모든 상태 전이를 Audit Trace에 기록한다.

입력은 내부 요청/멱등성 식별자, 기존 외부 참조, 현재 상태, 외부 조회 결과와 evidence digest,
필드 정합성, BE가 확정한 terminal/finality 근거, Retry 정책 판단이다.
`idempotency_key → external_transaction_id → execution_status` 바인딩을 유지한다.
Asset/Amount/Destination 불일치는 자동 완료를 금지한다. 기존 DA-01~04의 정확 보존·추적·출력 경계를 유지한다.
DA-05의 PRE_EXECUTION 승인조건 PASS와 외부 실행 성공을 구분한다.
최신 main의 DA-05 PR #23까지 검토했으며 기존 DA-01~05 파일을 수정하지 않는다.

## 허용 전이와 판정

아래 이름은 DA 개념 상태이며 BE enum 추가 지시가 아니다.

| 전이 | 필요한 근거 |
|---|---|
| SUBMITTED → SENT_UNKNOWN | 제출 기록과 응답 불확실성 |
| SENT_UNKNOWN → RECONCILING | 기존 실행 조회 우선 |
| RECONCILING → FINALIZED | 참조 바인딩, 필드 일치, BE finality 기준 충족 |
| RECONCILING → FAILED | 참조 바인딩과 외부 Terminal Failure 확인 |
| RECONCILING → RECONCILIATION_REQUIRED | 결과 미확정, 참조/필드 불일치 등 |
| FAILED → RETRY_ELIGIBLE | Terminal Failure 확인 및 별도 Retry 정책 허용 |

모든 전이는 Audit Trace를 요구한다. `SENT_UNKNOWN → RETRY` 및 `FINALIZED → 동일 요청 재제출`은 금지한다.
RETRY_ELIGIBLE은 실제 재전송 명령이 아니다. 정책 한도·원자적 실행 권한·lineage 설계가 필요하다.
Hash가 없는 경우 기존 Provider correlation 조회가 지원되면 활용하고, 그렇지 않으면 미확정 상태와 수동
Reconciliation을 유지한다. 조회 불가를 이유로 blind resend를 허용하지 않는다.

## 기존 BE 필드 재사용

검토 기준: ADP-BE commit `5d5f999310db3854e96bf96661f76438d7def6ff`.
정확한 소스 경로는 runtime_architecture의 `be_source_paths`에 기록했다.

| 필수 의미 | 기존 필드 / 공백 |
|---|---|
| request_id | runtime_execution.request_id; execution_id로 연결 |
| idempotency_key | runtime_execution.idempotency_key; V12의 기관/workload scope 유지 |
| external_transaction_id | digital_asset_transaction.external_transaction_id |
| submission_status | external_interaction_recovery.observed_status (Connector 관측) |
| execution_status | digital_asset_transaction.settlement_status; 내부 runtime status와 분리 |
| reconciliation_status | digital_asset_transaction.reconciliation_result; recovery workflow와 분리 |
| retry_count | 공백: recovery attempt_count는 claim 횟수이므로 실제 재전송 횟수로 대체 불가 |
| parent_request_id | 공백: 최초 요청/Retry 요청 연결 계약 필요 |
| created_at | runtime_execution.created_at |
| last_checked_at | external_interaction_recovery.last_status_queried_at; updated_at으로 대체 불가 |

BE의 SENT_UNKNOWN은 settlement_status=SENT_UNKNOWN, reconciliation_result=WAIT,
runtime=EGRESSING으로 남는다. 기존 완료 기준은 settlementStatus=SETTLED와
reconciliation=MATCH/RECOVERED이다. Connector ACKNOWLEDGED 또는 runtime EXTERNALLY_RECONCILED만으로
결제 완료를 선언하지 않는다. DA의 receipt 성공 표기로 이 기준을 약화하지 않는다.

## 검증과 남은 결정

```bash
python 03_digital_asset/src/build_da_06_handoff.py --check
python -m pytest 03_digital_asset/tests/test_da_06_handoff.py
python -m pytest 03_digital_asset/tests 02_ai/tests
python -m ruff check 03_digital_asset/src/build_da_06_handoff.py 03_digital_asset/tests/test_da_06_handoff.py
```

Builder는 원본 SHA-256 및 저장된 출력과 Artifact를 대조하며 Notebook 실행이나 통계 재계산을 하지 않는다.
테스트는 Artifact 계약/참조 검증이다. 실제 BE 장애 주입·동시성·전송 검증을 수행했다는 의미가 아니다.
원본 Notebook의 Ruff B905 1건(`zip`의 strict 누락)은 바이트 보존을 위해 수정하지 않았다.
기존 analyst evidence convention대로 이 Notebook만 검사 제외하며 신규 생성기와 테스트는 검사한다.
BE는 finality/reorg 근거, 실제 Retry 횟수와 lineage, Retry 한도/권한 및 참조 없는 복구 절차를 결정해야 한다.
원천 데이터에 nonce가 없어 sender+nonce 검증은 불가능했고, 업무 키 바인딩·동시성·crash recovery도
이 분석으로 검증하지 않았다. 새 법령 매핑은 수행하지 않았으며 법적 준수 보장을 주장하지 않는다.
