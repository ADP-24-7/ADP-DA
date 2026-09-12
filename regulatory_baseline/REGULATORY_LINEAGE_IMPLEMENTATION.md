# Regulatory Lineage Implementation

## 변경한 Repository

- ADP-DA: baseline registry, official snapshot, E2E fixture, validator/test.
- ADP-BE: Reference Evidence와 기존 Policy Lifecycle 사이의 immutable association, 조회/등록 API, migration/test.
- ADP-FE: 기존 Policy Governance 화면의 read-only regulatory lineage projection과 test.

## Canonical Evidence ID

`regulatory_evidence_id`는 DA registry에서 사용하는 도메인 명칭이다. BE에서는 이미 존재하는 `evidence_id`를 동등한 canonical key로 재사용한다. 불변 identity는 `(institution_id, evidence_id, evidence_version, content_digest)`이다.

Policy relation은 `(institution_id, evidence_id, evidence_version, artifact_id, artifact_version, binding_type)`로 고정한다. 공식 원문 `source_digest`는 association에 불변 저장하여 기존 Evidence artifact `content_digest`와 혼용하지 않는다. source version, effective date와 official locator는 Reference Evidence version에 귀속된다. 같은 공통 source라도 AI/DA requirement와 policy artifact binding은 별도로 유지된다.

## DA Mapping

두 registry의 모든 entry에 `regulatory_evidence_id`를 부여했고 기존 requirement, control, policy artifact 목록은 유지했다. `REGULATORY_LINEAGE_E2E_FIXTURES.json`은 AI PIPA와 Digital Asset 가상자산이용자보호법 사례를 고정한다. `scripts/validate_regulatory_lineage.py`가 snapshot/registry/fixture identity와 mapping을 검증한다.

## BE Mapping

V54는 `evidence.reference_evidence_policy_artifact` association table만 추가한다. Reference Evidence와 Policy Lifecycle의 기존 schema/state machine은 수정하지 않는다. association의 양쪽은 기존 version PK를 FK로 참조하고 공식 원문 SHA-256을 별도 보존한다. 등록은 privileged operator만 가능하고 조회는 기존 evidence reader 권한을 따른다.

API:

- `POST /api/admin/reference-evidence/{evidenceId}/versions/{evidenceVersion}/policy-bindings`
- `GET /api/admin/reference-evidence/policy-artifacts/{artifactId}/versions/{artifactVersion}`

등록 API는 lifecycle transition, approval, activation 또는 Runtime policy 변경을 수행하지 않는다.

## FE Mapping

기존 `PolicyGovernancePanel`이 현재 선택된 policy artifact/version으로 lineage API를 조회한다. 법령/조문, Evidence ID/source version, source digest, effective date, policy version 및 lifecycle state를 한 table에 표시한다. FE는 상태를 계산하지 않고 BE 응답을 그대로 projection한다. AI Admin과 Digital Asset Admin은 합치지 않았다.

## E2E Trace

- AI: `PIPA official source → REF-REG-PIPA-2026-09-11 → PIPA requirements → AI controls → AI-POLICY-LOCAL-VALIDATED-001/1.0.0 → VALIDATED → Policy Governance projection`
- Digital Asset: `Virtual Asset User Protection Act official source → REF-REG-VA-UPA-2024 → DA-01~03 requirements → execution controls → DA-DIGITAL-ASSET-RUNTIME-LOCAL-ACTIVE-001/1.0.0 → ACTIVE → Policy Governance projection`

## DB Migration

- `V54__bind_reference_evidence_to_policy_lifecycle.sql`
- 별도 local seed 없음. API contract test가 실제 AI/DA canonical Evidence ID를 ingest·bind·조회한다.

## Test Results

- ADP-DA: registry/snapshot/lineage validator PASS, Ruff PASS, mypy PASS, contract validator PASS. AI suite는 212 PASS / 1 unrelated frozen BE-schema digest drift, Digital Asset suite는 115 PASS / 1 unrelated pre-existing `source_markdown_sha256` drift.
- ADP-BE: compile PASS. Reference Evidence lineage + Flyway migration targeted 65 tests PASS. 전체 565 tests는 562 PASS / 2 FAIL / 1 SKIP이며, 두 failure는 기존 고정 ID DB test-order pollution으로 clean DB 단독 재실행 시 모두 PASS했다.
- ADP-FE: ESLint PASS, TypeScript production build PASS, 37 test files / 115 tests PASS. AI와 Digital Asset lineage projection 사례를 각각 검증했다.

## Remaining Gap

- exemplar 외 source는 legal-owner 확인 및 기존 maker-checker 절차 후 association 생성이 필요하다.
- `REVIEW_REQUIRED` source의 법률 해석은 자동화하지 않았다.
- scheduler, polling, 자동 diff/candidate/approval/activation은 범위 밖이며 구현하지 않았다.
# Refresh and review extension (2026-09-13)

`scripts/regulatory_refresh.py` and the authenticated internal refresh API extend immutable source/evidence lineage without changing runtime decisions. BE scheduler/manual orchestration rejects automatic activation, and FE projects the same regulatory evidence identity, source digest, policy version, lifecycle, domain, and review status.
