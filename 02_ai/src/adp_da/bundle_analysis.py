"""Case-paired operational analysis; never interpret delivery as model quality."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


def finding(
    metric: str,
    estimate: Any,
    n: int,
    evidence: dict[str, Any],
    *,
    test: str | None = None,
    p: float | None = None,
    effect: Any = None,
    reason: str | None = "Descriptive statistic; no population inference.",
    interpretation: str = "Observed snapshot only.",
) -> dict[str, Any]:
    return {
        "metric": metric,
        "estimate": estimate,
        "statistical_test": test,
        "p_value": p,
        "effect_size": effect,
        "sample_size": n,
        "interpretation": interpretation,
        "test_not_performed_reason": reason,
        "evidence": evidence,
    }


def paired_test(
    frame: pd.DataFrame,
    variable: str,
    evidence: dict[str, Any],
    *,
    binary: bool,
    independent_cases: bool,
    symmetric_differences: bool,
    synthetic: bool,
) -> dict[str, Any]:
    pivot = frame.pivot(index="eval_case_id", columns="model_profile_id", values=variable)
    paired = pivot.dropna().astype(float)
    n, k = paired.shape
    result = finding(variable + "_paired_comparison", None, n, evidence)
    result.update(
        {
            "models": list(paired.columns),
            "excluded_case_count": len(pivot) - n,
            "hypothesis": "Equal operational outcome distributions across model profiles.",
        }
    )

    def skip(reason: str) -> dict[str, Any]:
        result["test_not_performed_reason"] = reason
        result["interpretation"] = "No inferential conclusion: " + reason
        return result

    if n < 2 or k < 2:
        return skip("At least two complete cases and two model profiles are required.")
    x = paired.to_numpy()
    if k == 2:
        difference = x[:, 0] - x[:, 1]
        result["estimate"] = float(np.mean(difference) if binary else np.median(difference))
        result["effect_size"] = {
            "name": "paired_rate_difference" if binary else "median_paired_difference_millis",
            "value": result["estimate"],
            "direction": "first model minus second model",
        }
    if not independent_cases:
        return skip("Case independence is not in the bundle; analyst confirmation is required.")
    test: Any
    if binary and k == 2:
        b = int(np.sum((x[:, 0] == 1) & (x[:, 1] == 0)))
        c = int(np.sum((x[:, 0] == 0) & (x[:, 1] == 1)))
        result["discordant_pairs"] = b + c
        if b + c == 0:
            return skip("No discordant pairs; exact McNemar has no information.")
        test = stats.binomtest(b, b + c, p=0.5)
        name = "exact McNemar (two-sided binomial on discordant pairs)"
    elif binary:
        # Cochran Q chi-square approximation requires sufficient informative blocks.
        informative = int(np.sum((x.sum(axis=1) > 0) & (x.sum(axis=1) < k)))
        if informative < 20:
            return skip("Fewer than 20 informative cases; Cochran Q approximation deferred.")
        columns, rows, total = x.sum(axis=0), x.sum(axis=1), x.sum()
        q = float((k - 1) * (k * np.sum(columns**2) - total**2) / (k * total - np.sum(rows**2)))
        result.update(
            {
                "statistical_test": "Cochran Q (asymptotic)",
                "test_statistic": q,
                "p_value": float(stats.chi2.sf(q, k - 1)),
                "effect_size": {
                    "name": "max_minus_min_paired_success_rate",
                    "value": float(np.ptp(x.mean(axis=0))),
                },
            }
        )
        return _tested(result, synthetic)
    elif k == 2:
        if not symmetric_differences:
            return skip("Wilcoxon requires defensible symmetric paired differences; not confirmed.")
        difference = x[:, 0] - x[:, 1]
        nonzero = difference[difference != 0]
        if len(nonzero) < 2:
            return skip("Fewer than two nonzero paired differences.")
        ranks = stats.rankdata(np.abs(nonzero))
        effect = float(np.sum(ranks * np.sign(nonzero)) / np.sum(ranks))
        test = stats.wilcoxon(difference, zero_method="wilcox", method="auto")
        name = "Wilcoxon signed-rank (two-sided, scipy auto)"
        result["effect_size"] = {
            "name": "matched_rank_biserial",
            "value": effect,
            "direction": "first model minus second model",
        }
    else:
        if n <= 10 or k <= 6:
            return skip("Friedman asymptotic p-value deferred: require >10 cases and >6 profiles.")
        if np.all(np.ptp(x, axis=1) == 0):
            return skip("All within-case values tied; Friedman is undefined.")
        test = stats.friedmanchisquare(*[x[:, i] for i in range(k)])
        name = "Friedman (asymptotic)"
        result["effect_size"] = {
            "name": "Kendall W",
            "value": float(test.statistic / (n * (k - 1))),
        }
    result.update(
        {
            "statistical_test": name,
            "p_value": float(test.pvalue),
            "test_statistic": float(test.statistic),
        }
    )
    return _tested(result, synthetic)


def _tested(result: dict[str, Any], synthetic: bool) -> dict[str, Any]:
    result["test_not_performed_reason"] = None
    result["interpretation"] = (
        "Synthetic fixture: method demonstration only; no evidence of real model performance."
        if synthetic
        else "Exploratory case-paired operational comparison, not utility/quality. "
        "Use Holm-adjusted p-values across performed tests; significance does not set policy."
    )
    return result


def analyze_bundle(
    frame: pd.DataFrame,
    *,
    synthetic: bool = False,
    independent_cases: bool = False,
    symmetric_differences: bool = False,
) -> dict[str, Any]:
    first = frame.iloc[0]
    evidence = {key: first[key] for key in ("evaluation_run_id", "bundle_id", "content_digest")}
    evidence["execution_ids"] = frame["execution_id"].tolist()
    evidence["data_origin"] = "SYNTHETIC_FIXTURE" if synthetic else "USER_SUPPLIED_BUNDLE"
    n = len(frame)
    model_findings = []
    runtime_findings = []
    failure_findings = []
    for model, group in frame.groupby("model_profile_id", sort=True):
        reference = {
            **evidence,
            "execution_ids": group.execution_id.tolist(),
            "model_profile_id": model,
        }
        for column in (
            "runtime_status",
            "final_action",
            "response_guard_status",
            "controlled_delivery_status",
            "provider_status",
            "error_category",
        ):
            counts = group[column].value_counts().sort_index()
            model_findings.append(
                finding(
                    column + "_distribution",
                    {
                        status: {"count": int(count), "rate": float(count / len(group))}
                        for status, count in counts.items()
                    },
                    len(group),
                    reference,
                    interpretation="Producer enums; runtime completion does not measure quality.",
                )
            )
        # Never mix mock zeros, full response latency, attempts and initial gateway time.
        for measurement, measured in group.groupby("measurement_type", sort=True):
            for column in (
                "full_response_latency_millis",
                "attempt_elapsed_millis",
                "initial_runtime_latency_millis",
            ):
                values = measured[column].dropna().astype(float)
                estimate = (
                    None
                    if values.empty
                    else {
                        "mean": float(values.mean()),
                        "median": float(values.median()),
                        "p95": float(values.quantile(0.95)),
                        "p99": float(values.quantile(0.99)),
                    }
                )
                runtime_findings.append(
                    finding(
                        column,
                        estimate,
                        len(values),
                        {
                            **reference,
                            "measurement_type": measurement,
                            "execution_ids": measured.execution_id.tolist(),
                        },
                        reason="Descriptive quantiles; small samples do not establish tail SLA.",
                        interpretation="MOCK zeros do not measure provider latency."
                        if measurement == "MOCK"
                        else "Latency in milliseconds within measurement type.",
                    )
                )
            for status, subset in measured.groupby("provider_status", sort=True):
                for column in ("full_response_latency_millis", "attempt_elapsed_millis"):
                    values = subset[column].dropna().astype(float)
                    runtime_findings.append(
                        finding(
                            column + "_by_provider_status",
                            None
                            if values.empty
                            else {"mean": float(values.mean()), "median": float(values.median())},
                            len(values),
                            {
                                **reference,
                                "measurement_type": measurement,
                                "provider_status": status,
                                "execution_ids": subset.execution_id.tolist(),
                            },
                        )
                    )
        complete = group[group.token_usage_status == "COMPLETE"]
        runtime_findings.append(
            finding(
                "token_usage",
                {
                    "status_counts": {
                        str(key): int(value)
                        for key, value in group.token_usage_status.value_counts().items()
                    },
                    "complete_execution_count": len(complete),
                    "totals": {
                        key: int(complete[key].sum())
                        for key in ("input_tokens", "output_tokens", "total_tokens")
                    },
                },
                len(group),
                reference,
                interpretation="Totals include COMPLETE records only; unknown usage is not zero.",
            )
        )
        observed_failures = {
            "provider_failed": group.provider_status.eq("FAILED"),
            "sent_unknown": group.provider_status.eq("SENT_UNKNOWN"),
            "not_attempted": group.measurement_type.eq("NOT_ATTEMPTED"),
            "http_failure": group.provider_http_status.ge(400).fillna(False),
            "transport_error": group.error_category.eq("TRANSPORT"),
        }
        for label, mask in observed_failures.items():
            failure_findings.append(
                finding(
                    label + "_rate",
                    float(mask.mean()),
                    len(group),
                    {
                        **reference,
                        "matching_execution_ids": group.loc[mask, "execution_id"].tolist(),
                    },
                    interpretation="Overlapping failure dimensions; rates must not be summed.",
                )
            )
        categories = group.error_category.value_counts().sort_index()
        failure_findings.append(
            finding(
                "error_category_distribution",
                {
                    str(key): {"count": int(value), "rate": float(value / len(group))}
                    for key, value in categories.items()
                },
                len(group),
                reference,
            )
        )
    binary_frame = frame.copy()
    binary_frame["operational_completion"] = pd.array(
        binary_frame.runtime_status.eq("COMPLETED").astype(int), dtype="Int64"
    )
    binary_frame.loc[binary_frame.measurement_type == "MOCK", "operational_completion"] = pd.NA
    options = {
        "independent_cases": independent_cases,
        "symmetric_differences": symmetric_differences,
        "synthetic": synthetic,
    }
    model_test = paired_test(
        binary_frame, "operational_completion", evidence, binary=True, **options
    )
    latency_frame = frame.copy()
    latency_frame.loc[
        latency_frame.measurement_type != "HTTP_FULL_RESPONSE", "full_response_latency_millis"
    ] = pd.NA
    runtime_test = paired_test(
        latency_frame, "full_response_latency_millis", evidence, binary=False, **options
    )
    performed = [row for row in (model_test, runtime_test) if row["p_value"] is not None]
    previous = 0.0
    for i, row in enumerate(sorted(performed, key=lambda row: row["p_value"])):
        previous = max(previous, min(1.0, (len(performed) - i) * row["p_value"]))
        row["p_value_holm"] = previous
        row["multiplicity_family"] = "All performed model and runtime omnibus comparisons"
    policy = finding(
        "policy_transform_effect",
        None,
        n,
        evidence,
        reason="One policy_snapshot_digest per bundle; model profiles are not treatment arms. "
        "No privacy outcome, utility score, transform strength or randomized paired experiment.",
        interpretation="NOT EVALUABLE WITH CURRENT BUNDLE",
    )
    policy["status"] = "NOT_EVALUABLE"
    policy["additional_experiment"] = [
        "Export versioned case-to-workload mapping and expected case/model catalog.",
        "Use identical cases, model, sampling and destination across randomized policy arms.",
        "Record transform method/strength and independent privacy and utility outcome scores.",
        "Collect repeated time-separated runs, failures and full-response/attempt timing.",
        "Pre-register practical margins, SLA/risk budget and sample-size/power plan.",
    ]
    unavailable = {
        "workload_analysis": "workload_id is absent; do not infer it from run or case names.",
        "model_quality": "No gold labels, response contents or scored utility/quality outcomes.",
        "timeout_rate": "TRANSPORT is broader than timeout; no timeout reason is exported.",
    }
    candidates = []
    for name, status, reason in [
        ("MODEL_ALLOWLIST", "UNRESOLVED", "Operational outcomes do not establish model quality."),
        ("UTILITY_THRESHOLD", "NOT_EVALUABLE", unavailable["model_quality"]),
        ("LATENCY_THRESHOLD", "UNRESOLVED", "Observed quantiles are not an approved SLA."),
        (
            "FAILURE_THRESHOLD",
            "UNRESOLVED",
            "Failure rates require risk budget and representative runs.",
        ),
        ("REVIEW", "UNRESOLVED", "No ground-truth labels to evaluate REVIEW decisions."),
        ("TRANSFORM_POLICY", "NOT_EVALUABLE", policy["test_not_performed_reason"]),
    ]:
        candidate = finding(
            name,
            None,
            n,
            evidence,
            reason=reason,
            interpretation="No automatic BE policy promotion.",
        )
        candidate.update({"status": status, "candidate_value": None})
        candidates.append(candidate)
    gaps = []
    for label, candidate in zip(
        (
            "ALLOW / BLOCK / REVIEW",
            "AI Utility Threshold",
            "Latency",
            "Failure tolerance",
            "Model Quality",
            "Transform criteria",
        ),
        (candidates[4], candidates[1], candidates[2], candidates[3], candidates[0], candidates[5]),
        strict=True,
    ):
        gaps.append(
            {
                "item": label,
                "previous_status": "UNRESOLVED",
                "source": "02_ai/docs/AI_CONTRACT_GAP_ANALYSIS.md#explicit-non-decisions"
                if label == "ALLOW / BLOCK / REVIEW"
                else "02_ai/artifacts/ai_handoff_vNext/ANALYST_DECISION_REQUIRED.md",
                "resolvable_with_bundle": False,
                "analysis_result": candidate["test_not_performed_reason"],
                "final_status": candidate["status"],
                "additional_data_required": True,
            }
        )
    return {
        "evaluation_summary": {
            **finding("evaluated_execution_count", n, n, evidence),
            "data_origin": evidence["data_origin"],
            "unavailable": unavailable,
            "assumptions": options,
            "candidate_policy": "Promote only with representative real "
            "data, quality outcomes and analyst-approved decision criteria; none are supplied.",
            "decision_candidates": candidates,
            "handoff_gaps": gaps,
            "limitations": [
                "Latest execution per case/model only; no rerun variance estimate.",
                "Digest is integrity, not authenticity or external catalog validation.",
                "Model profiles include sampling/destination confounders.",
            ],
        },
        "model_comparison": {
            "findings": model_findings,
            "paired_test": model_test,
            "case_comparison": frame[
                [
                    "eval_case_id",
                    "model_profile_id",
                    "execution_id",
                    "runtime_status",
                    "final_action",
                ]
            ].to_dict("records"),
            "workload_analysis": finding(
                "workload_model_comparison",
                None,
                n,
                evidence,
                reason=unavailable["workload_analysis"],
            ),
        },
        "runtime_analysis": {"findings": runtime_findings, "paired_test": runtime_test},
        "failure_analysis": {
            "findings": failure_findings,
            "timeout": finding(
                "timeout_rate", None, n, evidence, reason=unavailable["timeout_rate"]
            ),
        },
        "policy_effect_analysis": policy,
    }
