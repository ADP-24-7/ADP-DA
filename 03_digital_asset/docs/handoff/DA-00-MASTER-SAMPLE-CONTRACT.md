# DA-00 Master Transaction Sample Contract

## 목적

Digital Asset 분석 전반에서 동일한 Ethereum 거래 기준점을 사용하기 위해
현재 Ethereum 실행환경을 대표하는 Master Transaction Sample을 고정한다.

DA-01~DA-03은 동일한 Master Sample을 기준으로 분석하며,
후속 분석에서 필요한 Trace, Transfer, Approval Fixture 및 Runtime Fixture는
해당 Transaction 기준점에 추가 결합한다.

## DA 소유 기준선

- Source: Google BigQuery Ethereum Mainnet Public Dataset
- Dataset: `bigquery-public-data.goog_blockchain_ethereum_mainnet_us`
- Analysis Population: Pectra 이후 현재 Ethereum 환경
- Population Start: `2025-06-01`
- Stratification Key: `transaction_type`
- Base Sample Size: `49,290`
- Final Master Sample Size: `73,410`
- Sampling Method: 불비례 층화표본추출

### Transaction Type별 최종 표본

- Type 0: `8,000`
- Type 1: `8,000`
- Type 2: `41,410`
- Type 3: `8,000`
- Type 4: `8,000`

## 표본설계 근거

현재 Ethereum 환경에서 Transaction Type 구성비는 다음과 같이 확인되었다.

- Type 2: `84.013664%`
- Type 0: `14.345667%`
- Type 4: `0.758996%`
- Type 3: `0.588700%`
- Type 1: `0.292973%`

단순 비례추출 시 Type 1, 3, 4가 지나치게 적게 포함되므로
희소 Transaction Type을 최소 8,000건까지 추가 확보하였다.

따라서 Transaction Type별 비교에는 실제 추출 표본을 사용하고,
전체 Ethereum 수준의 통계량을 산출할 때에는 모집단 구성비를 이용한
층화 가중치를 적용한다.

## 데이터 품질 검증

- Master Sample Rows: `73,410`
- Unique Transaction Hash: `73,410`
- Duplicate Transaction Hash: `0`
- Missing Receipt Status: `0`

모든 Transaction은 Receipt와 연결되었으며,
DA-01의 Transaction Record와 Execution Result 비교에 사용할 수 있는 상태로 검증되었다.

## Provenance

Master Sample은 원본 Ethereum Mainnet 데이터를 대체하는 원천 데이터가 아니다.

해당 CSV는 DA 분석을 위해 원본 모집단에서 통계적으로 추출한
`PROCESSED_ANALYSIS_ARTIFACT`이다.

BE Runtime은 해당 CSV를 운영 Transaction Source로 사용하지 않는다.

본 Artifact는 다음 목적에만 사용한다.

- DA 분석 재현
- Runtime Control 설계 근거
- BE Handoff Evidence
- 분석 결과 검증

## Handoff 기준

BE는 Master Sample의 Transaction ID나 Sample 구성 자체를
Runtime 정책으로 하드코딩하지 않는다.

DA가 전달하는 것은 Sample에서 도출된 설계 근거이며,
Runtime ID, Enum, State Machine 및 실제 운영 Source Contract의 최종 권한은 BE가 가진다.

## Evidence Artifact

- [Master Sample Notebook](../../notebooks/runtime_validation/DA_00_master_sample.ipynb)
- [Master Sample CSV](../../data/processed/da_master_transaction_sample_73410.csv)
- [분석 요약](../../artifacts/da_00_master_sample/analysis_summary.json)
- [표본설계 계약](../../artifacts/da_00_master_sample/sampling_contract.json)
- [데이터 provenance](../../artifacts/da_00_master_sample/data_provenance.json)
- [검증 범위·재현 한계·BE Crosswalk](DA-00-DA-01-EVIDENCE-GAPS.md)
