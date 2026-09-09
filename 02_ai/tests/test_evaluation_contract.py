from __future__ import annotations

import pytest
from adp_da.bundle_validator import (
    BundleValidationError,
    content_digest,
    validate_bundle,
    validate_contract_snapshot,
)
from bundle_fixture_factory import make_bundle
from contract_fixture_factory import with_contract


def test_v2_export_contract_binding() -> None:
    bundle = with_contract(make_bundle(case_count=1, model_count=3))
    result = validate_bundle(bundle)
    assert result


@pytest.mark.parametrize("field", [
    "prompt_version", "policy_version", "transform_version", "rag_version", "dataset_version",
    "temperature", "max_tokens", "seed_control", "reasoning_control",
])
def test_fixed_conditions_tampering_rejected(field: str) -> None:
    bundle = with_contract(make_bundle(case_count=1, model_count=3))
    snapshot = bundle["contract_evidence"]["snapshot"]
    snapshot["fixed_conditions"][field] = 1 if field in {"temperature", "max_tokens"} else "changed"
    with pytest.raises(BundleValidationError):
        validate_contract_snapshot(snapshot)


@pytest.mark.parametrize("field", [
    "eval_case_id", "evaluation_run_id", "fixed_conditions_digest", "model_profile_digest",
    "decision_id", "provider_request_digest", "provider_input_digest",
    "transform_execution_id", "outbound_payload_id", "outbound_guard_status",
])
def test_rehashed_bundle_cannot_hide_broken_execution_binding(field: str) -> None:
    bundle = with_contract(make_bundle(case_count=1, model_count=3))
    bundle["contract_evidence"]["bindings"][0][field] = (
        "sha256:" + "f" * 64 if "digest" in field else "different")
    bundle["manifest"]["content_digest"] = content_digest(bundle)
    with pytest.raises(BundleValidationError):
        validate_bundle(bundle)


def test_v2_requires_contract_evidence() -> None:
    bundle = with_contract(make_bundle(case_count=1, model_count=3))
    del bundle["contract_evidence"]
    bundle["manifest"]["content_digest"] = content_digest(bundle)
    with pytest.raises(BundleValidationError):
        validate_bundle(bundle)


def test_v1_historical_bundle_still_valid() -> None:
    assert validate_bundle(make_bundle())


@pytest.mark.parametrize("artifact", ["prompt_snapshot", "transform_snapshot"])
def test_rehashed_fixed_digest_does_not_hide_artifact_drift(artifact: str) -> None:
    from contract_fixture_factory import digest
    snapshot = with_contract(make_bundle(case_count=1, model_count=3))[
        "contract_evidence"]["snapshot"]
    fixed = snapshot["fixed_conditions"]
    if artifact == "prompt_snapshot":
        fixed[artifact]["version"] = "changed"
    else:
        fixed[artifact].append({"path": "test", "instruction_digest": "a" * 64})
    snapshot["fixed_conditions_digest"] = digest(fixed)
    with pytest.raises(BundleValidationError):
        validate_contract_snapshot(snapshot)


def test_frozen_model_snapshot_mismatch_is_rejected() -> None:
    bundle = with_contract(make_bundle(case_count=1, model_count=3))
    model = bundle["contract_evidence"]["snapshot"]["model_profiles"][0]
    model["provider_model_version"] = "changed"
    bundle["manifest"]["content_digest"] = content_digest(bundle)
    with pytest.raises(BundleValidationError):
        validate_bundle(bundle)
