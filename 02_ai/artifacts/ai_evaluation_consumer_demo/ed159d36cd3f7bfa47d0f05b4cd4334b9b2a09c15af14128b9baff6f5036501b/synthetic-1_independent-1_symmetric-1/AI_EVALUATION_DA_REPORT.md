# AI Evaluation DA Report

## Evidence

- Data origin: **SYNTHETIC_FIXTURE**
- Bundle: `AI-EVAL-BUNDLE:SYNTHETIC-DA-CONSUMER-TEST:1`
- Snapshot: `sha256:ed159d36cd3f7bfa47d0f05b4cd4334b9b2a09c15af14128b9baff6f5036501b`
- Executions: 16

Synthetic fixture results validate software only. They cannot establish model quality, production latency, failure tolerance or policy effectiveness.

## Independent validation

See `validation.json`: schema, digest, identity, Cartesian product, provenance, failure summary, measurement and token consistency must all pass.

## Hypotheses and statistical results

### model_comparison

- Hypothesis: Equal operational outcome distributions across model profiles.
- Complete cases: 7
- Test: exact McNemar (two-sided binomial on discordant pairs)
- p-value: 0.5
- Holm-adjusted p-value: 0.5
- Effect size: {"name": "paired_rate_difference", "value": -0.2857142857142857, "direction": "first model minus second model"}
- Interpretation: Synthetic fixture: method demonstration only; no evidence of real model performance.

### runtime_analysis

- Hypothesis: Equal operational outcome distributions across model profiles.
- Complete cases: 5
- Test: Wilcoxon signed-rank (two-sided, scipy auto)
- p-value: 0.0625
- Holm-adjusted p-value: 0.125
- Effect size: {"name": "matched_rank_biserial", "value": -1.0, "direction": "first model minus second model"}
- Interpretation: Synthetic fixture: method demonstration only; no evidence of real model performance.

## Findings and limits

- workload_analysis: workload_id is absent; do not infer it from run or case names.
- model_quality: No gold labels, response contents or scored utility/quality outcomes.
- timeout_rate: TRANSPORT is broader than timeout; no timeout reason is exported.
- Policy/Transform: **NOT EVALUABLE WITH CURRENT BUNDLE**.
- Detailed per-model actual status rates, per-case comparisons, measurement strata, tail quantiles, complete token totals and failures are in JSON artifacts.
- No synthetic observations support a BE design threshold.

## BE Handoff Gap

| Item | Existing status / source | Resolvable now | Analysis | Final status | Additional data |
|---|---|---|---|---|---|
| ALLOW / BLOCK / REVIEW | UNRESOLVED / `02_ai/docs/AI_CONTRACT_GAP_ANALYSIS.md#explicit-non-decisions` | No | No ground-truth labels to evaluate REVIEW decisions. | UNRESOLVED | Yes |
| AI Utility Threshold | UNRESOLVED / `02_ai/artifacts/ai_handoff_vNext/ANALYST_DECISION_REQUIRED.md` | No | No gold labels, response contents or scored utility/quality outcomes. | NOT_EVALUABLE | Yes |
| Latency | UNRESOLVED / `02_ai/artifacts/ai_handoff_vNext/ANALYST_DECISION_REQUIRED.md` | No | Observed quantiles are not an approved SLA. | UNRESOLVED | Yes |
| Failure tolerance | UNRESOLVED / `02_ai/artifacts/ai_handoff_vNext/ANALYST_DECISION_REQUIRED.md` | No | Failure rates require risk budget and representative runs. | UNRESOLVED | Yes |
| Model Quality | UNRESOLVED / `02_ai/artifacts/ai_handoff_vNext/ANALYST_DECISION_REQUIRED.md` | No | Operational outcomes do not establish model quality. | UNRESOLVED | Yes |
| Transform criteria | UNRESOLVED / `02_ai/artifacts/ai_handoff_vNext/ANALYST_DECISION_REQUIRED.md` | No | One policy_snapshot_digest per bundle; model profiles are not treatment arms. No privacy outcome, utility score, transform strength or randomized paired experiment. | NOT_EVALUABLE | Yes |

## Decision candidates

| Candidate | Status | Value | Basis |
|---|---|---|---|
| MODEL_ALLOWLIST | UNRESOLVED | Not set | Operational outcomes do not establish model quality. |
| UTILITY_THRESHOLD | NOT_EVALUABLE | Not set | No gold labels, response contents or scored utility/quality outcomes. |
| LATENCY_THRESHOLD | UNRESOLVED | Not set | Observed quantiles are not an approved SLA. |
| FAILURE_THRESHOLD | UNRESOLVED | Not set | Failure rates require risk budget and representative runs. |
| REVIEW | UNRESOLVED | Not set | No ground-truth labels to evaluate REVIEW decisions. |
| TRANSFORM_POLICY | NOT_EVALUABLE | Not set | One policy_snapshot_digest per bundle; model profiles are not treatment arms. No privacy outcome, utility score, transform strength or randomized paired experiment. |

## Next DA decisions

- Export versioned case-to-workload mapping and expected case/model catalog.
- Use identical cases, model, sampling and destination across randomized policy arms.
- Record transform method/strength and independent privacy and utility outcome scores.
- Collect repeated time-separated runs, failures and full-response/attempt timing.
- Pre-register practical margins, SLA/risk budget and sample-size/power plan.
- Confirm independence of cases before enabling inferential tests; confirm symmetric paired differences before Wilcoxon.
- Approve utility labels, practical effect margins and false REVIEW/BLOCK costs.

## Statistical references

- [SciPy binomtest: exact McNemar discordant-pair calculation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binomtest.html)
- [SciPy Wilcoxon assumptions](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wilcoxon.html)
- [SciPy Friedman approximation limits](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.friedmanchisquare.html)
