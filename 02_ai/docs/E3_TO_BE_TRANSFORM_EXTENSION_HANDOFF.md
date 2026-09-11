# E3 to BE Transform Extension Handoff

Status: `NO_CURRENT_EXTENSION_REQUIRED / VALIDATED_ACTIVATED`

## Current workload decision

`customer_summary / CUSTOMER_SUPPORT`의 동결 E2 계약을 만족하는 최종 20-field profile은 BE가 이미 지원하는 `KEEP`, `REMOVE`, `HMAC_PSEUDO`, `VAULT_TOKEN`만 사용한다. 따라서 현재 E3 profile을 표현하기 위한 새 Transform 구현은 필요하지 않다.

`account.balance`와 `transaction.amount`는 BE resolver와 destination field contract에서 `KEEP / REQUIRED_EXACT`로 활성화됐다. TransformEngine은 KEEP의 source/transformed digest를 동일하게 보존하고 Outbound Guard는 원본·변환값·strategy·digest를 외부 실행 경계 전에 검증한다. 실패 시 machine-readable `REQUIRED_EXACT_*` reason code로 BLOCK한다.

## Reviewed but not handed off for implementation

| Method | Required field | Workload | Decision | Evidence | Activation condition |
|---|---|---|---|---|---|
| Standard encryption | none | customer_summary | `NOT_APPLICABLE / NOT_SUPPORTED` | Shinhan protection controls | Provider가 복호화할 수 없는 보호 경계와 명시적 복호 권한 계약이 별도 정의될 때 재검토 |
| FPE (FF1) | none | customer_summary | `NOT_APPLICABLE / REQUIRES_EXTENSION` | NIST SP 800-38G Rev.1 2PD; Durak–Vaudenay | legacy format 보존이 실제 업무 필수이고 domain·key·tweak·leakage gate가 승인될 때만 별도 설계 |
| OPE/ORE | none | customer_summary | `NOT_APPLICABLE / NOT_SUPPORTED` | Grubbs et al.; Naveed et al. | 외부 ciphertext range/sort가 필수이며 leakage-abuse threat model을 승인한 경우에만 재검토 |
| Aggregate | none | customer_summary | `NOT_APPLICABLE / NOT_SUPPORTED` | NIST SP 800-188; financial synthetic-data study | record-level summary가 아닌 population statistic workload가 동결될 때 재검토 |
| Noise/randomization | none | customer_summary | `NOT_APPLICABLE / NOT_SUPPORTED` | NIST SP 800-188; financial synthetic-data study | 명시적 privacy budget과 허용 오차가 있는 통계 workload가 동결될 때 재검토 |

## E2 Provider Governance freeze

E3 activation does not authorize an external call. The independent E2 governance boundary is frozen as `e2-provider-governance/1.2.0` with digest `sha256:5f591b577fd41993682c732392405fd9329305ec8e6ff1f983913eb5bfe71039`. Provider, model, workload, destination, region, retention, and reuse are evaluated before retrieval and transform. The current NVIDIA-hosted observation remains `BLOCK` because physical region is unresolved, exception-log retention is unverified, and model-improvement reuse is outside the approved execution-only scope. The aggregate hold-out baseline digest is `sha256:0ce91807505042ebba1f8f5059da2f60cdabeab8c9285d304feaf8f1d66ef274`; the integrated validation digest is `sha256:2e396f6a1482a868397e56f19a68daab5d3c6caea6e2ed800c07bcd69a996f21`.

## Expected Runtime contract if a future E2 owner approves an extension

승인된 method만 기존 순서 `Policy → Retrieval → Transform → Outbound Guard → Provider`에 추가한다. Transform instruction/version/key or mapping metadata, field result digest, failure reason, duration, released schema, Outbound Guard decision과 audit trace를 생성해야 한다. reversible method는 reveal/decrypt 권한, vault 또는 key custody, purpose/domain separation, privileged access audit가 필수다.

현재 E3 activation condition은 충족됐다. 다만 E2 Provider Governance는 독립 경계로 계속 `PROVIDER_GOVERNANCE_BLOCKED`이며 Provider authorization은 `false`, Provider calls는 `0`이다.
