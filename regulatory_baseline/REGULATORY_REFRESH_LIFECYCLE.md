# Regulatory Refresh Lifecycle

The canonical flow is:

`Official Source Registry -> authority adapter -> normalized bytes -> SHA-256 compare -> selective parse -> AI/DA impact -> pending candidates -> replay/shadow -> maker-checker -> Active`.

## Safety boundary

- `UNCHANGED` performs zero parser runs and creates zero candidates.
- `FETCH_FAILED` and `PARSE_FAILED` preserve every active policy and create zero candidates.
- A changed source with no requirement/control impact is recorded as `NO_POLICY_IMPACT`.
- Changed sources create immutable evidence-version, requirement/control, and policy candidates in `PENDING_REVIEW` only.
- Candidate creation never approves, activates, overwrites, or immediately changes a runtime rule.
- A `BOTH` source retains one evidence identity while producing separate AI and Digital Asset impact results.

## Source adapters

`scripts/regulatory_refresh.py` routes the official registry URL through adapters for the National Law Information Center, Financial Services Commission, Korea Financial Intelligence Unit, Personal Information Protection Commission, Financial Security Institute, FATF, and a final HTTPS-only official-source adapter. Adapter output is normalized into one byte model before hashing.

## Invocation

- CLI/manual: `python scripts/regulatory_refresh.py --source-id SOURCE_ID`
- Internal API: `POST /internal/regulatory/refresh` with `{"source_ids":["SOURCE_ID"]}`; omit or set `null` for all sources.
- BE admin API: `POST /api/admin/regulatory-refresh`; restricted to `PRIVILEGED_OPERATOR`.
- Scheduler: `REGULATORY_REFRESH_ENABLED=true` and `REGULATORY_REFRESH_CRON="0 0 3 * * *"`.

Scheduled and manual BE calls use the same service and gateway. BE rejects any downstream response where `automatic_activation` is not explicitly `false`.
The internal DA endpoint also requires the `X-ADP-Internal-Token` header configured by `ADP_REGULATORY_REFRESH_TOKEN`.

## Review queue

`REGULATORY_REVIEW_QUEUE.json` contains all nine `REVIEW_REQUIRED` identities. Every item includes the official source, affected requirement/control/policy scope, recommended maker-checker action, and `PENDING_REVIEW` status. There is no automatic legal judgment.
