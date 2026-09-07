"""Synthetic contract fixture ONLY. Not BE-exported or real provider measurements."""

from __future__ import annotations

from typing import Any

from adp_da.bundle_validator import content_digest, failure_summary


def make_bundle(case_count: int = 8, model_count: int = 2) -> dict[str, Any]:
    digest = "sha256:" + "a" * 64
    start, end = "2026-09-01T00:00:00Z", "2026-09-01T00:01:00Z"
    config = {
        "evaluation_run_id": "SYNTHETIC-DA-CONSUMER-TEST",
        "evaluation_run_version": "1",
        "evaluation_contract_digest": digest,
        "dataset_id": "SYNTHETIC-CASES",
        "dataset_version": "1",
        "dataset_digest": digest,
        "policy_snapshot_digest": digest,
        "models": [
            {
                "profile_id": f"synthetic-profile-{m}",
                "profile_version": "1",
                "profile_digest": digest,
                "provider_model_id": f"synthetic-model-{m}",
                "provider_model_version": "1",
                "connection_profile_id": "synthetic",
                "max_tokens": 100,
                "temperature": 0.0,
                "sampling_profile_version": "1",
                "destination_profile_digest": digest,
            }
            for m in range(model_count)
        ],
    }
    results, metrics, traces = [], [], []
    for case in range(case_count):
        for model in range(model_count):
            identity = {
                "execution_id": f"synthetic-{case}-{model}",
                "eval_case_id": f"case-{case}",
                "model_profile_id": f"synthetic-profile-{model}",
            }
            measurement = (
                ("HTTP_FULL_RESPONSE", "HTTP_ATTEMPT_NO_RESPONSE", "NOT_ATTEMPTED", "MOCK")[
                    case % 4
                ]
                if case >= 4
                else "HTTP_FULL_RESPONSE"
            )
            failed = case % 3 == 0 and model == 0
            provider = "FAILED" if failed else "COMPLETED"
            error = "PROVIDER_SERVER_ERROR" if failed else "NONE"
            if measurement == "NOT_ATTEMPTED":
                provider, error = "NOT_SENT", "NONE"
            elif measurement == "HTTP_ATTEMPT_NO_RESPONSE":
                provider, error = "SENT_UNKNOWN", "TRANSPORT"
            complete = measurement == "HTTP_FULL_RESPONSE" and not failed
            results.append(
                {
                    **identity,
                    "runtime_status": "COMPLETED"
                    if provider == "COMPLETED"
                    else "BLOCKED"
                    if provider == "NOT_SENT"
                    else "FAILED",
                    "final_action": "BLOCK" if provider == "NOT_SENT" else "ALLOW",
                    "response_guard_status": "PASSED" if complete else "NOT_EVALUATED",
                    "controlled_delivery_status": "DELIVERED" if complete else "WITHHELD",
                    "provider_status": provider,
                    "error_category": error,
                    "evidence_status": "COMPLETE",
                    "expected_input_digest": digest,
                    "actual_input_digest": digest,
                }
            )
            metrics.append(
                {
                    **identity,
                    "measurement_type": measurement,
                    "full_response_latency_millis": 100 + case * 11 + model * 20
                    if measurement == "HTTP_FULL_RESPONSE"
                    else 0
                    if measurement == "MOCK"
                    else None,
                    "attempt_elapsed_millis": 500
                    if measurement == "HTTP_ATTEMPT_NO_RESPONSE"
                    else None,
                    "initial_runtime_latency_millis": 10,
                    "input_tokens": 10 if complete else None,
                    "output_tokens": 5 if complete else None,
                    "total_tokens": 15 if complete else None,
                    "token_usage_status": "COMPLETE" if complete else "NOT_PROVIDED",
                    "provider_http_status": (500 if failed else 200)
                    if measurement == "HTTP_FULL_RESPONSE"
                    else None,
                    "provider_status": provider,
                    "error_category": error,
                }
            )
            traces.append(
                {
                    "execution_id": identity["execution_id"],
                    "decision_id": None,
                    "connector_execution_id": None,
                    "provider_request_digest": None,
                    "provider_response_digest": None,
                    "created_at": start,
                    "updated_at": end,
                }
            )
    bundle = {
        "manifest": {
            "schema_version": "adp-ai-evaluation-bundle/v1",
            "bundle_id": "AI-EVAL-BUNDLE:SYNTHETIC-DA-CONSUMER-TEST:1",
            "bundle_version": "1.0.0",
            "content_digest": digest,
            "evaluation_run_id": config["evaluation_run_id"],
            "evaluation_run_version": "1",
            "execution_count": len(results),
            "case_count": case_count,
            "model_count": model_count,
            "generated_at": end,
            "execution_from": start,
            "execution_cutoff_at": end,
        },
        "execution_config": config,
        "case_results": results,
        "runtime_metrics": metrics,
        "failure_summary": failure_summary(metrics),
        "trace_index": traces,
    }
    bundle["manifest"]["content_digest"] = content_digest(bundle)
    return bundle
