"""Independent, fail-closed consumer checks for BE AI-EVAL-3 v1."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from datetime import datetime
from decimal import Decimal
from itertools import product
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "contracts/ai-evaluation-bundle.schema.json"


class BundleValidationError(ValueError):
    """An untrusted bundle must not enter analysis."""


def canonical_json(value: Any) -> str:
    """Compact JSON with Jackson/Java floating-point exponent notation.

    The only floating-point v1 field is model temperature. Preserve its numeric
    type and shortest round-trip digits, with Java's scientific notation boundary.
    """
    if isinstance(value, dict):
        keys = sorted(value, key=lambda key: key.encode("utf-16-be"))
        return (
            "{"
            + ",".join(canonical_json(key) + ":" + canonical_json(value[key]) for key in keys)
            + "}"
        )
    if isinstance(value, list):
        return "[" + ",".join(canonical_json(item) for item in value) + "]"
    if isinstance(value, float):
        if not math.isfinite(value):
            raise BundleValidationError("non-finite number in canonical JSON")
        if value == 0:
            return "-0.0" if math.copysign(1, value) < 0 else "0.0"
        decimal = Decimal(repr(value))
        if 1e-3 <= abs(value) < 1e7:
            rendered = format(decimal, "f")
            return rendered if "." in rendered else rendered + ".0"
        mantissa, exponent = format(decimal.normalize(), "E").split("E")
        if "." not in mantissa:
            mantissa += ".0"
        return mantissa + "E" + str(int(exponent))
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def content_digest(bundle: dict[str, Any]) -> str:
    """BE hashes five sections plus manifest.schema_version, not manifest."""
    content = {key: value for key, value in bundle.items() if key != "manifest"}
    content["schema_version"] = bundle["manifest"]["schema_version"]
    encoded = canonical_json(content).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def failure_summary(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "evaluated_execution_count": len(metrics),
        "failed": sum(row["provider_status"] == "FAILED" for row in metrics),
        "sent_unknown": sum(row["provider_status"] == "SENT_UNKNOWN" for row in metrics),
        "not_attempted": sum(row["measurement_type"] == "NOT_ATTEMPTED" for row in metrics),
        "by_error_category": dict(
            sorted(
                Counter(
                    row["error_category"] for row in metrics if row["error_category"] != "NONE"
                ).items()
            )
        ),
    }


def validate_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, Any] = {}

    def require(condition: bool, name: str) -> None:
        if not condition:
            raise BundleValidationError(name)
        checks[name] = "PASS"

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(bundle))
    if errors:
        # Do not echo potentially private values from invalid payloads.
        paths = ["/".join(map(str, error.absolute_path)) for error in errors]
        raise BundleValidationError("schema: " + ", ".join(paths))
    checks["schema"] = "PASS"
    manifest, config = bundle["manifest"], bundle["execution_config"]
    results, metrics, traces = (
        bundle[key] for key in ("case_results", "runtime_metrics", "trace_index")
    )
    calculated = content_digest(bundle)
    require(calculated == manifest["content_digest"], "content_digest")
    count = manifest["execution_count"]
    indexes = []
    for name, rows in zip(
        ("case_results", "runtime_metrics", "trace_index"), (results, metrics, traces), strict=True
    ):
        index = {row["execution_id"]: row for row in rows}
        require(len(index) == len(rows) == count, name + "_cardinality")
        indexes.append(index)
    require(indexes[0].keys() == indexes[1].keys() == indexes[2].keys(), "execution_identity")
    models = {row["profile_id"] for row in config["models"]}
    cases = {row["eval_case_id"] for row in results}
    pairs = {(row["eval_case_id"], row["model_profile_id"]) for row in results}
    require(len(models) == len(config["models"]) == manifest["model_count"], "model_count")
    require(len(cases) == manifest["case_count"], "case_count")
    require(len(pairs) == count, "case_model_uniqueness")
    require(pairs == set(product(cases, models)), "cartesian_completeness")
    require(
        all(
            manifest[key] == config[key] for key in ("evaluation_run_id", "evaluation_run_version")
        ),
        "run_provenance",
    )
    require(
        manifest["bundle_id"]
        == "AI-EVAL-BUNDLE:" + config["evaluation_run_id"] + ":" + config["evaluation_run_version"],
        "bundle_identity",
    )
    case_digests: dict[str, str] = {}
    for result in results:
        metric = indexes[1][result["execution_id"]]
        require(
            all(
                result[key] == metric[key]
                for key in ("eval_case_id", "model_profile_id", "provider_status", "error_category")
            ),
            "case_model_execution_relationship",
        )
        require(result["expected_input_digest"] == result["actual_input_digest"], "input_digest")
        expected = case_digests.setdefault(result["eval_case_id"], result["expected_input_digest"])
        require(expected == result["expected_input_digest"], "cross_model_input_provenance")
        require(result["evidence_status"] == "COMPLETE", "complete_evidence")
        tokens = [metric[key] for key in ("input_tokens", "output_tokens", "total_tokens")]
        if metric["token_usage_status"] == "COMPLETE":
            require(tokens[2] == tokens[0] + tokens[1], "token_usage")
        else:
            require(all(value is None for value in tokens), "token_usage")
    require(failure_summary(metrics) == bundle["failure_summary"], "failure_summary")
    checks["measurement_enum_and_latency"] = "PASS (schema conditional validation)"
    parse_time = datetime.fromisoformat
    require(
        all(parse_time(row["created_at"]) <= parse_time(row["updated_at"]) for row in traces),
        "trace_time_order",
    )
    require(
        parse_time(manifest["execution_from"])
        == min(parse_time(row["created_at"]) for row in traces),
        "execution_from",
    )
    require(
        parse_time(manifest["execution_cutoff_at"])
        == max(parse_time(row["updated_at"]) for row in traces),
        "execution_cutoff_at",
    )
    require(
        parse_time(manifest["generated_at"]) >= parse_time(manifest["execution_cutoff_at"]),
        "generated_at",
    )
    return {
        "status": "PASS",
        "checks": checks,
        "calculated_digest": calculated,
        "execution_count": count,
        "recomputed_failure_summary": failure_summary(metrics),
        "complete_token_total": sum(
            row["total_tokens"] for row in metrics if row["token_usage_status"] == "COMPLETE"
        ),
        "provenance_scope": "Internal consistency only; no independent catalog or signature. "
        "An entirely omitted case with adjusted manifest cannot be detected without a catalog.",
    }
