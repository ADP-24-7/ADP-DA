"""Run with python -m adp_da.evaluation_bundle --help."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from adp_da.bundle_analysis import analyze_bundle
from adp_da.bundle_dataset import execution_dataframe, save_dataset
from adp_da.bundle_loader import load_bundle


def write_report(artifacts: dict[str, Any], output: Path) -> None:
    summary = artifacts["evaluation_summary"]
    evidence = summary["evidence"]
    lines = [
        "# AI Evaluation DA Report",
        "",
        "## Evidence",
        "",
        f"- Data origin: **{summary['data_origin']}**",
        f"- Bundle: `{evidence['bundle_id']}`",
        f"- Snapshot: `{evidence['content_digest']}`",
        f"- Executions: {summary['sample_size']}",
        "",
        "Synthetic fixture results validate software only. They cannot establish model "
        "quality, production latency, failure tolerance or policy effectiveness.",
        "",
        "## Independent validation",
        "",
        "See `validation.json`: schema, digest, identity, Cartesian product, provenance, "
        "failure summary, measurement and token consistency must all pass.",
        "",
        "## Hypotheses and statistical results",
        "",
    ]
    for key in ("model_comparison", "runtime_analysis"):
        result = artifacts[key]["paired_test"]
        lines.extend(
            [
                f"### {key}",
                "",
                f"- Hypothesis: {result['hypothesis']}",
                f"- Complete cases: {result['sample_size']}",
                f"- Test: {result['statistical_test']}",
                f"- p-value: {result['p_value']}",
                f"- Holm-adjusted p-value: {result.get('p_value_holm')}",
                f"- Effect size: {json.dumps(result['effect_size'])}",
                f"- Interpretation: {result['interpretation']}",
                "",
            ]
        )
    lines.extend(["## Findings and limits", ""])
    lines.extend(f"- {key}: {value}" for key, value in summary["unavailable"].items())
    lines.extend(
        [
            "- Policy/Transform: **NOT EVALUABLE WITH CURRENT BUNDLE**.",
            "- Detailed per-model actual status rates, per-case comparisons, measurement "
            "strata, tail quantiles, complete token totals and failures are in JSON artifacts.",
            "- No synthetic observations support a BE design threshold.",
            "",
            "## BE Handoff Gap",
            "",
            "| Item | Existing status / source | Resolvable now | Analysis | Final status "
            "| Additional data |",
            "|---|---|---|---|---|---|",
        ]
    )
    for gap in summary["handoff_gaps"]:
        lines.append(
            f"| {gap['item']} | {gap['previous_status']} / `{gap['source']}` | No | "
            f"{gap['analysis_result']} | {gap['final_status']} | Yes |"
        )
    lines.extend(
        [
            "",
            "## Decision candidates",
            "",
            "| Candidate | Status | Value | Basis |",
            "|---|---|---|---|",
        ]
    )
    for candidate in summary["decision_candidates"]:
        lines.append(
            f"| {candidate['metric']} | {candidate['status']} | Not set | "
            f"{candidate['test_not_performed_reason']} |"
        )
    lines.extend(["", "## Next DA decisions", ""])
    lines.extend(
        f"- {item}" for item in artifacts["policy_effect_analysis"]["additional_experiment"]
    )
    lines.extend(
        [
            "- Confirm independence of cases before enabling inferential tests; confirm "
            "symmetric paired differences before Wilcoxon.",
            "- Approve utility labels, practical effect margins and false REVIEW/BLOCK costs.",
            "",
            "## Statistical references",
            "",
            "- [SciPy binomtest: exact McNemar discordant-pair calculation]"
            "(https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binomtest.html)",
            "- [SciPy Wilcoxon assumptions]"
            "(https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wilcoxon.html)",
            "- [SciPy Friedman approximation limits]"
            "(https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.friedmanchisquare.html)",
            "",
        ]
    )
    (output / "AI_EVALUATION_DA_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def run_pipeline(
    source: str | Path,
    output: Path,
    *,
    evaluation_run_id: str | None = None,
    token: str | None = None,
    local_admin_user_id: str | None = None,
    local_admin_roles: str | None = None,
    synthetic: bool = False,
    independent_cases: bool = False,
    symmetric_differences: bool = False,
) -> Path:
    bundle, metadata = load_bundle(
        source,
        output / "raw",
        evaluation_run_id=evaluation_run_id,
        token=token,
        local_admin_user_id=local_admin_user_id,
        local_admin_roles=local_admin_roles,
    )
    # Output is immutable and identified by snapshot plus explicit analysis assumptions.
    digest = str(bundle["manifest"]["content_digest"]).split(":", 1)[1]
    variant = f"synthetic-{int(synthetic)}_independent-{int(independent_cases)}"
    variant += f"_symmetric-{int(symmetric_differences)}"
    destination = output / digest / variant
    destination.mkdir(parents=True, exist_ok=False)
    frame = execution_dataframe(bundle)
    artifacts = analyze_bundle(
        frame,
        synthetic=synthetic,
        independent_cases=independent_cases,
        symmetric_differences=symmetric_differences,
    )
    artifacts["evaluation_summary"]["dataset"] = save_dataset(frame, destination)
    artifacts["evaluation_summary"]["loader_metadata"] = metadata
    artifacts["validation"] = metadata["validation"]
    for name, artifact in artifacts.items():
        (destination / (name + ".json")).write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
        )
    write_report(artifacts, destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="Bundle JSON file or BE API base URL")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evaluation-run-id")
    parser.add_argument(
        "--token-env", default="ADP_BE_TOKEN", help="Read bearer token from env only"
    )
    parser.add_argument(
        "--local-admin-user-id-env",
        default="ADP_BE_LOCAL_ADMIN_USER_ID",
        help="Read the BE development-only X-ADP-User-Id value from this env var",
    )
    parser.add_argument(
        "--local-admin-roles-env",
        default="ADP_BE_LOCAL_ADMIN_ROLES",
        help="Read the BE development-only X-ADP-User-Roles value from this env var",
    )
    parser.add_argument("--synthetic", action="store_true", help="Label fixture-only evidence")
    parser.add_argument(
        "--independent-cases", action="store_true", help="Analyst confirms case independence"
    )
    parser.add_argument(
        "--symmetric-differences",
        action="store_true",
        help="Analyst confirms Wilcoxon paired-difference assumption",
    )
    args = parser.parse_args()
    print(
        run_pipeline(
            args.source,
            args.output,
            evaluation_run_id=args.evaluation_run_id,
            token=os.environ.get(args.token_env),
            local_admin_user_id=os.environ.get(args.local_admin_user_id_env),
            local_admin_roles=os.environ.get(args.local_admin_roles_env),
            synthetic=args.synthetic,
            independent_cases=args.independent_cases,
            symmetric_differences=args.symmetric_differences,
        )
    )


if __name__ == "__main__":
    main()
