"""In-memory contract fixtures for validator tests; never real execution evidence."""
from __future__ import annotations

import hashlib
from typing import Any

from adp_da.bundle_validator import canonical_json, content_digest


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode()).hexdigest()


def with_contract(bundle: dict[str, Any]) -> dict[str, Any]:
    config = bundle["execution_config"]
    for model in config["models"]:
        model.setdefault("destination_profile_id", "dest_" + model["profile_id"])
        model.setdefault("provider", "NVIDIA")
        model["profile_digest"] = digest({
            "modelId": model["provider_model_id"], "modelVersion": model["provider_model_version"],
            "maxTokens": model["max_tokens"], "temperature": model["temperature"],
            "providerConnectionProfileId": model["connection_profile_id"],
        })
    retrieval = {"adapter_version": "jdbc-customer-summary/v1", "profile_id": "test",
                 "scopes": [], "fields": [], "as_of_date": "2026-09-10"}
    fixed = {name: config[name] for name in (
        "evaluation_run_id", "dataset_version", "dataset_digest", "policy_snapshot_digest")}
    fixed.update({
        "evaluation_contract_version": "ai-evaluation-contract/1.0.0",
        "workload": "customer_summary", "purpose_code": "CUSTOMER_SUPPORT",
        "prompt_version": "customer-summary-prompt/1.0.0", "policy_version": "test-policy/1",
        "prompt_snapshot": {"version": "customer-summary-prompt/1.0.0"},
        "prompt_snapshot_digest": digest({"version": "customer-summary-prompt/1.0.0"}),
        "transform_snapshot": [], "transform_version": digest([]),
        "transform_scope": "ai-evaluation:" + config["evaluation_run_id"],
        "rag_mode": "PREDEFINED_RETRIEVAL", "rag_version": digest(retrieval),
        "retrieval_config": retrieval, "retrieved_context_digest": digest("retrieved"),
        "temperature": config["models"][0]["temperature"],
        "max_tokens": config["models"][0]["max_tokens"], "stream": False,
        "seed_control": "NOT_CONFIGURABLE", "reasoning_control": "NOT_CONFIGURABLE",
        "case_set_version": config["evaluation_run_version"],
        "destination_contract_digest": digest("destination"),
        "cases": list({row["eval_case_id"]: {
            "caseId": row["eval_case_id"], "datasetRowRef": "synthetic:test",
            "inputSchemaVersion": "ai-evaluation-input/v1",
            "expectedInputDigest": row["expected_input_digest"],
        } for row in bundle["case_results"]}.values()),
    })
    import copy
    snapshot = {"fixed_conditions": fixed, "fixed_conditions_digest": digest(fixed),
                "model_profiles": copy.deepcopy(config["models"])}
    models = {model["profile_id"]: model for model in config["models"]}
    traces = {row["execution_id"]: row for row in bundle["trace_index"]}
    for trace in traces.values():
        trace.update(transform_execution_id="test-transform", outbound_payload_id="test-outbound",
                     outbound_guard_status="PASSED")
        trace["decision_id"] = "test-decision-" + trace["execution_id"]
        trace["provider_request_digest"] = digest("test-request-" + trace["execution_id"])
    bindings = []
    for row in bundle["case_results"]:
        trace = traces[row["execution_id"]]
        bindings.append({
            "execution_id": row["execution_id"], "evaluation_run_id": config["evaluation_run_id"],
            "eval_case_id": row["eval_case_id"], "fixed_conditions_digest": digest(fixed),
            "model_profile_digest": models[row["model_profile_id"]]["profile_digest"],
            "decision_id": trace["decision_id"], "transform_execution_id": "test-transform",
            "outbound_payload_id": "test-outbound",
            "outbound_guard_status": "PASSED",
            "provider_request_digest": trace["provider_request_digest"],
            "provider_input_digest": digest("test-case-input-" + row["eval_case_id"]),
        })
    bundle["contract_evidence"] = {"snapshot": snapshot, "bindings": bindings}
    bundle["manifest"].update(schema_version="adp-ai-evaluation-bundle/v2", bundle_version="2.0.0")
    bundle["manifest"]["content_digest"] = content_digest(bundle)
    return bundle
