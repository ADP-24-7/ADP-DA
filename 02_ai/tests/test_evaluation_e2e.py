from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from adp_da import evaluation_e2e
from bundle_fixture_factory import make_bundle


class Response(BytesIO):
    def __enter__(self) -> Response:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class FakeOpener:
    def __init__(self, bundle: dict[str, Any]) -> None:
        self.bundle = bundle
        self.requests: list[Any] = []

    def open(self, request: Any, timeout: float) -> Response:
        self.requests.append(request)
        if request.get_method() == "GET":
            return Response(json.dumps(self.bundle).encode())
        return Response(json.dumps({"executionId": f"exec-{len(self.requests)}"}).encode())


def live_environment() -> dict[str, str]:
    return {
        evaluation_e2e.API_KEY_ENV: "runtime-secret",
        evaluation_e2e.CONFIRMATION_ENV: "YES",
        evaluation_e2e.LOCAL_USER_ENV: "da-reader",
        evaluation_e2e.LOCAL_ROLES_ENV: "PRIVILEGED_OPERATOR",
    }


def test_preflight_is_secret_safe_and_requires_confirmation() -> None:
    environment = {evaluation_e2e.API_KEY_ENV: "must-not-appear"}
    report = evaluation_e2e.preflight(environment, "http://127.0.0.1:8080/", "test-1")
    assert not report["ready_for_live_execution"]
    assert report["expected_execution_count"] == 3
    assert report["checks"]["runtime_api_key_present"]
    assert not report["checks"]["real_provider_execution_confirmed"]
    assert "must-not-appear" not in json.dumps(report)


@pytest.mark.parametrize(
    "url",
    ["example.invalid", "http://example.invalid", "https://user:secret@example.invalid"],
)
def test_preflight_rejects_unsafe_base_urls(url: str) -> None:
    with pytest.raises(evaluation_e2e.E2EError):
        evaluation_e2e.preflight({}, url, "test")


def test_live_flow_posts_three_bindings_exports_and_analyzes(
    tmp_path: Path, monkeypatch: Any
) -> None:
    bundle = make_bundle(case_count=1, model_count=3)
    bundle["manifest"]["evaluation_run_id"] = evaluation_e2e.RUN_ID
    bundle["execution_config"]["evaluation_run_id"] = evaluation_e2e.RUN_ID
    for section in ("case_results", "runtime_metrics"):
        for row in bundle[section]:
            row["evaluation_run_id"] = evaluation_e2e.RUN_ID
    # The fixture factory's synthetic profiles are valid DA input; this test verifies orchestration.
    from adp_da.bundle_validator import content_digest

    bundle["manifest"]["content_digest"] = content_digest(bundle)
    fake = FakeOpener(bundle)
    analysis = tmp_path / "analysis-result"
    monkeypatch.setattr(evaluation_e2e, "run_pipeline", lambda *args, **kwargs: analysis)

    result = evaluation_e2e.execute_live(
        environment=live_environment(),
        base_url="http://localhost:8080",
        output=tmp_path / "e2e",
        session_id="pytest",
        timeout=1,
        opener=fake,
    )

    assert len(fake.requests) == 4
    posts = fake.requests[:3]
    assert all(request.get_method() == "POST" for request in posts)
    payloads = [json.loads(request.data) for request in posts]
    assert {item["destinationProfileId"] for item in payloads} == {
        binding.destination_profile_id for binding in evaluation_e2e.BASELINE_MODELS
    }
    assert all(item["evaluationRunId"] == evaluation_e2e.RUN_ID for item in payloads)
    assert fake.requests[3].get_header("X-adp-user-id") == "da-reader"
    assert result["execution_ids"] == ["exec-1", "exec-2", "exec-3"]
    assert Path(result["bundle_path"]).exists()
    saved = json.loads((tmp_path / "e2e" / "e2e-result.json").read_text())
    assert "runtime-secret" not in json.dumps(saved)


def test_live_flow_fails_before_network_without_explicit_confirmation(tmp_path: Path) -> None:
    fake = FakeOpener(make_bundle())
    with pytest.raises(evaluation_e2e.E2EError, match="confirmed"):
        evaluation_e2e.execute_live(
            environment={evaluation_e2e.API_KEY_ENV: "secret"},
            base_url="http://localhost:8080",
            output=tmp_path / "e2e",
            session_id="pytest",
            timeout=1,
            opener=fake,
        )
    assert not fake.requests


def test_remote_bundle_export_requires_bearer_token() -> None:
    environment = {
        evaluation_e2e.API_KEY_ENV: "secret",
        evaluation_e2e.CONFIRMATION_ENV: "YES",
    }
    report = evaluation_e2e.preflight(environment, "https://be.example", "pytest")
    assert not report["checks"]["bundle_auth_present"]
    with pytest.raises(evaluation_e2e.E2EError, match="ADP_BE_TOKEN"):
        evaluation_e2e.bundle_headers(environment, local=False)


@pytest.mark.parametrize("value", ["", "operator\rX-Evil: yes", "operator\nX-Evil: yes"])
def test_local_admin_headers_reject_empty_and_crlf(value: str) -> None:
    environment = {
        evaluation_e2e.LOCAL_USER_ENV: value,
        evaluation_e2e.LOCAL_ROLES_ENV: "PRIVILEGED_OPERATOR",
    }
    report = evaluation_e2e.preflight(environment, "http://localhost:8080", "pytest")
    assert not report["checks"]["bundle_auth_present"]
    with pytest.raises(evaluation_e2e.E2EError, match="CR/LF"):
        evaluation_e2e.bundle_headers(environment, local=True)
