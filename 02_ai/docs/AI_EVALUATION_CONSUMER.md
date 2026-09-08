# AI-EVAL-3 DA Consumer

## Placement and source contract

Existing `ai_handoff_vnext.py`, `fpg_be_handoff_final.py`, EVAL-AI-001–004 notebooks,
handoff artifacts and regulatory analysis are retained. These handoff builders
do not consume runtime evaluation exports; the new modules handle that boundary.

`02_ai/contracts/ai-evaluation-bundle.schema.json` is an unchanged copy of
ADP-BE `docs/contracts/ai-evaluation-bundle.schema.json` at commit
`5d5f999310db3854e96bf96661f76438d7def6ff` (PR #23). Changes to the producer schema
require explicit review and parity checking. No sibling BE checkout is required
at runtime. This runtime snapshot schema is not a replacement for a DA handoff
release manifest schema discussed in the historical gap report.

## Run

From ADP-DA with Python 3.12:

```powershell
python -m pip install -e ".[dev,notebook]"
python -m adp_da.evaluation_bundle 02_ai/tests/fixtures/evaluation_bundle.synthetic.json --output outputs/ai_evaluation_demo --synthetic
```

For a real export, use a new output directory and omit `--synthetic`:

```powershell
python -m adp_da.evaluation_bundle path/to/export.json --output outputs/ai_evaluation
python -m adp_da.evaluation_bundle https://be.example --evaluation-run-id RUN_ID --output outputs/ai_evaluation
```

The API client supports one authentication mode at a time:

- Bearer: `ADP_BE_TOKEN` (or the environment variable named by `--token-env`). This is a
  generic client capability; the current BE does not yet provide a JWT/OAuth2 bearer Adapter.
- BE local development administrator: `ADP_BE_LOCAL_ADMIN_USER_ID` and
  `ADP_BE_LOCAL_ADMIN_ROLES` (or variables selected with
  `--local-admin-user-id-env` and `--local-admin-roles-env`). Both local values are
  required together. Do not also set the Bearer token.

For the local BE route with `ADP_LOCAL_USER_AUTH_ENABLED=true`:

```powershell
$env:ADP_BE_LOCAL_ADMIN_USER_ID = 'da-evaluation-reader'
$env:ADP_BE_LOCAL_ADMIN_ROLES = 'PRIVILEGED_OPERATOR'
python -m adp_da.evaluation_bundle http://127.0.0.1:8080 `
  --evaluation-run-id ai-eval-baseline-2026-09-07 `
  --output outputs/real_be_evaluation/analysis
```

These environment variables map to `X-ADP-User-Id` and `X-ADP-User-Roles`; the
values are not accepted as command-line arguments and are not written to archived
metadata. This authentication mode is only for BE local development.
For a deployed server, implement and confirm its admin authentication integration first. The E2E
runner blocks remote Bearer by default and additionally requires
`ADP_BE_REMOTE_BEARER_AUTH_ENABLED=YES` after that Adapter is deployed.
Privileged operator role and permitted institution/workload scope are required.
Tokens are never CLI arguments or archived metadata. Redirects are rejected. Localhost HTTP
is accepted for development; remote endpoints require HTTPS. BE 404/authorization
and network failures propagate without manufacturing an empty bundle.

Raw JSON bytes are archived by their own SHA-256 before validation. Invalid JSON
is retained for diagnosis but never converted to a dataset. Treat the raw archive
as untrusted input, since a malformed producer could violate the privacy contract.
No raw archive is committed automatically.

Analysis outputs are under `<output>/<content_digest>/<analysis-options>/`.
Existing analysis directories are never overwritten. To rerun, choose a new output
directory. `bundle_id + content_digest` is always retained; exact raw-byte hashes
also distinguish identical snapshots with different `generated_at` values.

## Independent checks

Schema uses Draft 2020-12 with date-time assertions. Validation rejects duplicate
JSON keys, non-finite values, unknown fields, incomplete evidence, invalid enum or
measurement/latency combinations, token-status/null contradictions and token sums.
It recomputes content digest, Cartesian completeness and failure summary, and
checks section identity/cardinality, run identity, cross-model case input digest,
profile uniqueness, provider/error consistency and execution-window bounds.

The digest input includes `schema_version` from manifest and the other five root
sections. It excludes manifest itself, preserves arrays and nulls, and sorts object
keys before compact UTF-8 SHA-256. Floating-point temperature uses Java exponent
notation and its 1e-3/1e7 boundaries instead of Python's default JSON notation.
The current baseline and numeric boundary vectors are tested. An unexpected
cross-runtime numeric representation mismatch fails closed; it never disables
digest validation. Producer-owned canonical fixtures should accompany new model
profiles, especially extreme/subnormal floating-point settings.

Internal provenance consistency is not external catalog verification or authenticity.
Without an independent versioned case catalog, an entirely missing case plus
consistently altered counts cannot be detected. The digest cannot prove that
an attacker has not changed both payload and digest. No such stronger claim is made.

## Dataset and analysis limits

Producer names remain intact: `eval_case_id`, `model_profile_id`, `provider_model_id`,
`runtime_status`, `error_category`. Model config and snapshot metadata are flattened
onto each execution row. Nullable integer tokens/latencies preserve unknowns.
Parquet is preferred, with explicit JSONL fallback if no Parquet engine is installed.

There is no `workload_id`, quality/utility score, timeout-specific reason, transform
strength, treatment arm or scored privacy outcome in v1. No placeholder columns or
inferred workload IDs are created. `COMPLETED` measures operational completion,
not PASS on a quality benchmark. `model_profile_id` comparisons can confound model,
sampling and destination settings. A `final_action` distribution is not a causal
comparison of policies. A single `policy_snapshot_digest` does not identify a
before/after intervention.

Real full-response timings, failed full responses, attempts, not-attempted and MOCK
measurements remain separate. Missing usage is not zero. Failure dimensions overlap;
TRANSPORT is not synonymous with timeout. Latest-per-pair exports omit rerun variance.

## Statistical assumptions

All defaults are descriptive. `--independent-cases` explicitly asserts the analyst's
case-sampling assumption. McNemar compares paired binary operational completion
for two profiles; Cochran Q requires at least 20 informative blocks for the chosen
conservative asymptotic guard. For two latency profiles, also provide
`--symmetric-differences` only if a symmetric paired-difference distribution is
defensible. Wilcoxon reports matched rank-biserial effect. Friedman is deferred
unless >10 complete cases and >6 profiles (SciPy approximation guidance), and
reports Kendall W. Missing full-response pairs are excluded with counts, never
imputed. No independent-sample Chi-square is applied to repeated cases.

Performed model/runtime tests form one Holm family. Raw and adjusted p-values,
effect sizes, sample sizes, hypotheses, references and reasons for skipped tests
are retained. Exploratory statistical significance never sets a BE threshold.
Synthetic fixture tests demonstrate algorithms only.

- [SciPy exact binomial test](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binomtest.html)
- [SciPy Wilcoxon](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wilcoxon.html)
- [SciPy Friedman](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.friedmanchisquare.html)

## Notebooks and artifacts

Run `scripts/build_ai_eval_notebooks.py` only to regenerate notebook sources.
The four `AI_EVAL_0*.ipynb` notebooks default to the explicitly labelled synthetic
fixture. Set `ADP_AI_BUNDLE_SOURCE` to a file/base URL and, for API use,
`ADP_AI_EVALUATION_RUN_ID`. `ADP_AI_INDEPENDENT_CASES=1` and
`ADP_AI_SYMMETRIC_DIFFERENCES=1` provide the explicit statistical assumptions.
For external synthetic inputs set `ADP_AI_SYNTHETIC=1`.

Execute all four notebooks against the test fixture using the current interpreter:

```powershell
python scripts/verify_ai_eval_notebooks.py --write-outputs
```

This verification command clears API source/token variables in its own child
process and stores Jupyter runtime state under ignored `.tmp/`.

The pipeline produces `evaluation_summary.json`, `model_comparison.json`,
`runtime_analysis.json`, `failure_analysis.json`, `policy_effect_analysis.json`,
`validation.json`, dataset and `AI_EVALUATION_DA_REPORT.md`.

Decision candidates and the six Handoff Gap rows are included in the summary and
report. No candidate is automatically promoted: missing utility/transform evidence
is `NOT_EVALUABLE`; missing representative runs, risk budget or analyst decisions
remain `UNRESOLVED`. `SUPPORTED_CANDIDATE` requires evidence and approved criteria
absent from the current inputs; sample quantiles alone never qualify.

Existing vNext analyst decisions and historical explicit non-decisions are cited
without rewriting them. Next work is actual BE export validation, versioned
workload/catalog binding, independent quality labels, controlled policy arms,
representative repeated runs, and analyst-defined SLA/quality/risk margins.
