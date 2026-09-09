# 04. Digital Asset Infrastructure Reference

## Purpose

본 문서는 국내외 디지털자산 시장의 구조 변화와 금융 인프라 확장 방향을 확인하기 위한 참고자료이다.

국내에서는 한국은행의 `프로젝트 한강`, 해외에서는 CFTC의 디지털자산 시장 관련 자료를 통해
금융 인프라가 기존 계좌·내부 시스템 중심에서 토큰화 자산과 외부 네트워크 기반 가치이동까지 확장되는 흐름을 확인한다.

본 자료는 개별 Gateway Rule의 직접적인 법적 판단 근거가 아니라,
Financial Privacy Gateway에서 Digital Asset을 분석 범위에 포함하는 산업적 배경과 구조적 근거로 사용한다.


## 1. Korea — Project Hangang

### Deposit Token 기반 실거래

한국은행의 `프로젝트 한강`은 CBDC 시스템을 기반으로 은행이 발행하는 예금토큰을
일반 이용자가 실제 지급에 사용하는 형태의 디지털화폐 활용성 테스트이다.

2025년 1차 실거래에서는 국민·신한·하나·우리·농협을 포함한 7개 은행이 참여하였으며,
이용자는 해당 은행의 예금계좌와 연결된 전자지갑을 통해 예금토큰을 발행·사용하는 구조로 테스트에 참여하였다.

이는 디지털자산이 단순 투자자산이나 거래소 내 자산을 넘어
은행의 예금·지급결제 인프라와 직접 연결되는 방향으로 확장되고 있음을 보여준다.


### From Pilot to Infrastructure

프로젝트 한강은 2025년 일반 이용자 실거래 테스트 이후 2026년 2단계로 확대되었다.

따라서 국내에서도 Digital Asset 관련 논의가
`기술 검증 → 실제 이용자 거래 → 은행 지급결제 인프라 확대`
방향으로 이동하고 있음을 확인할 수 있다.


## 2. Global — CFTC Reference

### 24/7 Digital Asset Market

디지털자산 시장은 전통 금융시장과 달리 24시간 연속적으로 운영될 수 있다.

시장 운영시간의 확대는 거래뿐 아니라 리스크 관리, 데이터 처리,
상태 모니터링 및 사후 대사 시스템 역시 지속적으로 작동할 수 있는 구조를 요구한다.


### Tokenized Collateral

블록체인 기반 토큰화 자산과 담보의 활용 확대는
금융자산이 온체인 환경에서 이동하고 활용되는 새로운 금융 인프라를 형성하고 있다.

이에 따라 금융기관이 관리해야 할 범위도 기존 계좌 및 금융 데이터에서
Wallet, Asset, Transaction, Counterparty, Settlement State 등
외부 가치이동과 관련된 정보로 확대될 수 있다.


### AI and Autonomous Systems

CFTC는 향후 AI 기반 시스템과 자율 소프트웨어가
토큰화된 금융환경 및 디지털자산 인프라와 직접 상호작용할 가능성을 제시하고 있다.

이는 AI 활용 확대와 Digital Asset 인프라 변화가
장기적으로 독립된 기술 흐름에 머무르지 않을 가능성을 보여주는 참고 근거이다.


## 3. Project Interpretation

본 프로젝트에서는 금융 인프라 변화를 두 개의 외부 실행 영역으로 구분한다.

- **AI · SaaS · Cloud**
  - 내부 데이터와 업무가 외부 기술환경에서 처리되는 `External Data Execution`

- **Digital Asset**
  - 승인된 자산과 가치가 Wallet·Network·Settlement 인프라를 통해 이동하는 `External Value Execution`

두 영역의 실행 대상과 위험은 서로 다르다.

그러나 금융기관 내부에서 승인된 조건이 외부 실행환경으로 넘어간다는 공통점이 존재한다.

따라서 Financial Privacy Gateway는 두 영역을 동일하게 처리하는 것이 아니라,
**동일한 Policy-Execution 구조에서 각각 필요한 실행조건을 통제하고 Trace를 남기는 것**을 목표로 한다.

AI에서는 Role, Purpose, Data, Transform, Model, Destination을 확인하고,
Digital Asset에서는 Purpose, Asset, Amount, Counterparty, Destination, Period, State를 확인한다.


## 4. Next Evidence

프로젝트 한강에서 국민·신한·하나·우리·농협 등 주요 은행이
예금토큰 기반 지급결제 실증에 직접 참여했다는 점을 기준으로,
다음 분석에서는 5대 은행의 공식 사업자료를 확인한다.

이를 통해 금융기관의 사업 영역이

`AI·Data → SaaS·Cloud → Blockchain·Digital Asset → Token Infrastructure`

방향으로 실제 확장되고 있는지를 분석한다.


## Scope Limitation

프로젝트 한강과 CFTC 자료는 Digital Asset을 프로젝트 분석 범위에 포함하는
산업·인프라 변화의 Evidence로 사용한다.

개별 거래의 법적 허용·금지 또는 Gateway Rule의 직접적인 판단은
별도의 Evidence Ontology에서 검증된 국내 법령, 금융당국 자료 및 공식 가이드라인을 기준으로 한다.