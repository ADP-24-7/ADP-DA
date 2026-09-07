# DA-00 / DA-01 Evidence 및 BE Contract Crosswalk

## Evidence 범위와 재현 방법

분석의 권위 있는 입력은 담당자가 작성한 아래 Notebook의 **저장된 코드·출력**과 CSV다.
Notebook을 다시 실행하거나 코드·분석·출력값을 수정하지 않았다.

- [DA-00 Notebook](../../notebooks/runtime_validation/DA_00_master_sample.ipynb)
- [DA-01 Notebook](../../notebooks/runtime_validation/DA_01_external_execution.ipynb)
- [Master CSV](../../data/processed/da_master_transaction_sample_73410.csv)

CSV는 `PROCESSED_ANALYSIS_ARTIFACT`이며 BE 운영 Transaction Source가 아니다.
독립적인 CSV 검산은 기존 Notebook의 집계·가중비율·카이제곱·두 비율 Z 검정·Bonferroni
결과를 같은 방법으로 확인하는 작업이다. 새로운 분석이나 인과 추정을 추가하지 않는다.

ADP-DA 루트에서:

```bash
python 03_digital_asset/src/build_da_00_01_handoff.py
python 03_digital_asset/src/build_da_00_01_handoff.py --check
python -m pytest 03_digital_asset/tests
```

첫 명령은 현재 원본 bytes의 SHA-256과 생성시각으로 6개 Artifact를 생성한다.
`--check`는 파일을 변경하지 않고 CSV↔Notebook↔Handoff 수치, JSON 내용,
원본 SHA-256 및 cell evidence reference를 재검증한다. source_notebook_sha256에는
분석 출력과 줄바꿈까지 포함한다. `.gitattributes`로 해당 원본 bytes를 보존한다.

분석 Notebook 2개는 기록된 Evidence이므로 lint 자동 수정 대상에서 제외한다.
대신 생성기와 검증 테스트를 CI에서 실행하며 기존 foundation Notebook과 production
Python lint 범위는 유지한다. GitHub Actions에서 원본 Notebook 전체 실행 PASS를 주장하지 않는다.

## Machine-readable Artifact

| Artifact | BE 사용 목적 |
|---|---|
| [da_00_master_sample/analysis_summary.json](../../artifacts/da_00_master_sample/analysis_summary.json) | 현재 모집단을 선택한 근거와 Master 품질 |
| [da_00_master_sample/sampling_contract.json](../../artifacts/da_00_master_sample/sampling_contract.json) | Type별 불비례 표본배분·모집단 비중·가중치 |
| [da_00_master_sample/data_provenance.json](../../artifacts/da_00_master_sample/data_provenance.json) | 실제 파일 hash·출처의 검증 범위·재현 한계 |
| [da_01_external_execution/analysis_summary.json](../../artifacts/da_01_external_execution/analysis_summary.json) | receipt 기준 Type별 결과와 가중 실패율 |
| [da_01_external_execution/statistical_validation.json](../../artifacts/da_01_external_execution/statistical_validation.json) | 기존 카이제곱·효과크기·10쌍 사후검정 Evidence |
| [da_01_external_execution/runtime_requirements.json](../../artifacts/da_01_external_execution/runtime_requirements.json) | BE 설계 반영사항과 Runtime Boundary |

Artifact의 보고 수치는 Notebook 출력의 반올림 정밀도를 그대로 사용한다.
사후검정 출력의 `0.000000`은 반올림 표시이며 정확한 p=0이 아니다.
기존 Notebook은 Bonferroni를 사용하므로 다른 보정법으로 바꾸지 않는다.

## 확인한 BE 구현과 의미 Crosswalk

기준 BE commit: `5d5f999310db3854e96bf96661f76438d7def6ff`.
다음 표는 소스 검토 결과이며 실제 Provider/Runtime E2E 검증 결과가 아니다.

| DA 의미 요구 | 확인한 기존 BE 구조 | 연결 상태 / 확인사항 |
|---|---|---|
| Outbound 요청/전송 결과 | `ConnectorStatus`의 `NOT_SENT`, `SENT_UNKNOWN`, `ACKNOWLEDGED`, `COMPLETED`, `FAILED` | connector 상태만으로 settlement 성공을 의미하지 않음 |
| Transaction 제출 상태 | `DigitalAssetResponseGuard`의 `settlementStatus`, 허용값 `SUBMITTED`, `SETTLING` 등 | 기존 provider response contract를 재사용. 새로운 Runtime enum으로 승격하지 않음 |
| Transaction hash | `DigitalAssetTransactionPersistencePort.externalTransactionId`, DB `external_transaction_id` | provider ID와 blockchain tx_hash의 동등성은 미확정. BE mapping 필요 |
| 실제 Execution 결과 | `settlementStatus=SETTLED` 및 reconciliation `MATCH`/`RECOVERED` 조건 | `DigitalAssetSettlementOutcomeHandler`는 두 조건 충족 시 `RuntimeExecutionStatus.COMPLETED` 반환 |
| 결과 확인 시점 | `digital_asset_transaction.created_at`, `updated_at`은 DB 기록 시점 | receipt 확인 시점/chain finality 시점과 동일하다고 간주하지 않음. 별도 의미 mapping 미확정 |
| 최종 Runtime Decision | `RuntimeExecutionStatus`, `RuntimeExecutionResponse.policyAction` | 정책 action과 최종 execution completion은 별개. 문서의 PASS는 새 enum 아님 |
| Approval / Policy trace | 요청 `approvalReference`, 응답 `policyVersion`, `policyAction`, 실행별 `execution_id` 연결 | DA-03 Trace Binding에서 정확한 evidence lineage와 필드 Crosswalk 검증 예정 |
| 미확정 결과 / Recovery | `ExternalStatusQueryPort`, `SENT_UNKNOWN`, `EXTERNALLY_RECONCILED` | 전송 확인만으로 `SETTLED`로 승격하지 않는 기존 BE Recovery 원칙과 연결 |

`SUBMITTED / SENT != EXECUTION_CONFIRMED`는 DA의 **의미적 요구**다.
여기서 SENT, EXECUTION_CONFIRMED 또는 PASS를 새로운 BE enum/DB field로 정의하지 않는다.
최종 naming과 state machine은 BE Contract가 권위 있는 기준이다.

확인한 BE 소스:

- [ConnectorStatus.java](https://github.com/ADP-24-7/ADP-BE/blob/5d5f999310db3854e96bf96661f76438d7def6ff/src/main/java/com/adp/gateway/connector/domain/ConnectorStatus.java)
- [DigitalAssetResponseGuard.java](https://github.com/ADP-24-7/ADP-BE/blob/5d5f999310db3854e96bf96661f76438d7def6ff/src/main/java/com/adp/gateway/digitalasset/infrastructure/DigitalAssetResponseGuard.java)
- [DigitalAssetSettlementOutcomeHandler.java](https://github.com/ADP-24-7/ADP-BE/blob/5d5f999310db3854e96bf96661f76438d7def6ff/src/main/java/com/adp/gateway/digitalasset/application/DigitalAssetSettlementOutcomeHandler.java)
- [JdbcDigitalAssetTransactionPersistence.java](https://github.com/ADP-24-7/ADP-BE/blob/5d5f999310db3854e96bf96661f76438d7def6ff/src/main/java/com/adp/gateway/digitalasset/infrastructure/JdbcDigitalAssetTransactionPersistence.java)
- [BE-8 Recovery](https://github.com/ADP-24-7/ADP-BE/blob/5d5f999310db3854e96bf96661f76438d7def6ff/docs/be-8-digital-asset-recovery.md)

## 남은 CONTRACT_GAP

1. DA-00에서 `client`, `DATASET`, 실제 추출 SQL `query_da01_sample`의 초기화/정의가
   저장돼 있지 않다. BigQuery job ID, 고정 조회 종료시점, random seed/정렬 기준도 없다.
   표본 CSV의 동일 bytes 재분석은 가능하지만 원천 재추출을 완전히 재현했다고 할 수 없다.
2. 원천 dataset 이름은 기존 Handoff의 명시값이다. 전체 역사/현재 모집단 raw 집계가 없어
   DA-00의 모집단 통계는 저장 출력 검증 범위에 한정된다. 모집단 비중과 DA-01 가중치의
   정합성은 저장된 Type별 count와 코드 상수로 확인한다.
3. Notebook의 로컬 절대경로·BigQuery 세션 의존성은 그대로 보존했다. 재현 환경 이전은
   담당자 관리 대상이며, 이 PR에서 원본 분석 코드를 임의 수정하지 않는다.
4. `externalTransactionId`와 tx_hash의 mapping, receipt 확인시각, chain finality와
   settlement 상태의 대응은 BE Contract에서 확정해야 한다.
5. 실제 Provider Receipt/Status Query·Recovery 및 Audit/Trace E2E는 실행하지 않았다.
   기존 BE 소스에 pending/finality 구분이 있음을 확인한 것이 구현 완료 인증은 아니다.
6. 표본에는 receipt가 있는 block 포함 거래만 있으므로 미포함·pending·전송실패의 비율은
   이 분석으로 추정할 수 없다. Type 3의 관측 실패 2건 등 희소 사건의 해석 한계를 유지한다.

## BE 확인 요청

1. tx_hash 확보 후 바로 최종 PASS/성공으로 승격되는 경로가 있는지
2. 제출·전송과 Execution 확인의 의미가 분리되어 있는지
3. Receipt / External Status 결과가 최종 Runtime Decision에 연결되는지
4. 미확정 결과가 기존 SENT_UNKNOWN / Recovery 흐름에 연결되는지
5. Audit/Trace에 제출 상태와 Execution Result가 별도로 보존되는지
6. DA Requirement와 기존 BE enum/field의 Crosswalk를 추가 확정해야 하는지

## Runtime Boundary 및 다음 단계

KYC / AML / Sanctions / Wallet Risk / VASP Risk / Customer Risk Score /
신규 거래 승인 판단을 Active Runtime에 추가하지 않는다. 이미 승인된 Transaction의
외부 실행이 승인조건과 실제 결과를 유지·검증·증명하는 범위다.

후속 Handoff: DA-02 Exact Preservation → DA-03 Trace Binding →
DA-04 Outbound Destination → DA-05 Approved vs Requested Match → DA-06 Recovery / Idempotency.

같은 bytes의 `da_master_transaction_sample_73410 - 복사본.csv`는 중복 파일로 PR에서 제외한다.
`artifacts/analysis_01/figures/`의 이미지 2개는 현재 DA-00/DA-01 Notebook에서 생성/참조가
확인되지 않아 이 Evidence 패키지에서 제외하고 로컬 원본을 보존한다.
