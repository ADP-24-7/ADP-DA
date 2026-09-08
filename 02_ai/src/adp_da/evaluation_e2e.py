"""Guarded BE execution-to-DA-analysis preflight for the fixed AI baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import ssl
import sys
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPSHandler, Request, build_opener

from adp_da.evaluation_bundle import run_pipeline

RUN_ID = "ai-eval-baseline-2026-09-07"
CASE_ID = "customer-summary-ko-001"
CONFIRMATION_ENV = "ADP_AI_E2E_CONFIRM_REAL_PROVIDER"
API_KEY_ENV = "ADP_RUNTIME_API_KEY"
BUNDLE_TOKEN_ENV = "ADP_BE_TOKEN"
REMOTE_BEARER_ENABLED_ENV = "ADP_BE_REMOTE_BEARER_AUTH_ENABLED"
LOCAL_USER_ENV = "ADP_BE_LOCAL_ADMIN_USER_ID"
LOCAL_ROLES_ENV = "ADP_BE_LOCAL_ADMIN_ROLES"
BASE_URL_ENV = "ADP_BE_BASE_URL"
LOCAL_DEV_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "adp-be"})


@dataclass(frozen=True)
class ModelBinding:
    profile_id: str
    destination_profile_id: str
    approval_reference: str


BASELINE_MODELS = (
    ModelBinding(
        "nvidia-nemotron-3.5-lightning-30b-a3b",
        "dest_nvidia-nemotron-3-5-lightning-30b-a3b",
        "approval_ai_eval_nvidia-nemotron-3.5-lightning-30b-a3b",
    ),
    ModelBinding(
        "meta-muse-glimmer-30b",
        "dest_meta-muse-glimmer-30b",
        "approval_ai_eval_meta-muse-glimmer-30b",
    ),
    ModelBinding(
        "google-gemma-4-31b-it",
        "dest_google-gemma-4-31b-it",
        "approval_ai_eval_google-gemma-4-31b-it",
    ),
)


class Opener(Protocol):
    def open(
        self,
        fullurl: str | Request,
        data: Any = None,
        timeout: float | None = None,
    ) -> Any: ...


class E2EError(RuntimeError):
    """Raised when preflight or a live E2E stage fails closed."""


class NoRedirect:
    """urllib handler mixin is built lazily to keep the public surface small."""

    @staticmethod
    def opener() -> Opener:
        from urllib.request import HTTPRedirectHandler

        class RejectRedirect(HTTPRedirectHandler):
            def redirect_request(self, *args: Any, **kwargs: Any) -> None:
                return None

        return build_opener(HTTPSHandler(context=ssl.create_default_context()), RejectRedirect())


def normalized_base_url(value: str) -> str:
    base_url = value.rstrip("/")
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise E2EError("ADP_BE_BASE_URL must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise E2EError("BE base URL must not contain credentials, query, or fragment")
    if parsed.scheme == "http" and parsed.hostname not in LOCAL_DEV_HOSTS:
        raise E2EError("Plain HTTP is allowed only for loopback or the local Compose BE service")
    return base_url


def safe_session_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,47}", value):
        raise E2EError("session id must be 1-48 safe identifier characters")
    return value


def safe_header(value: str, name: str) -> str:
    if not value.strip() or "\r" in value or "\n" in value:
        raise E2EError(f"{name} must be non-empty and contain no CR/LF")
    return value


def default_session_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def runtime_payload(binding: ModelBinding, session_id: str) -> dict[str, Any]:
    suffix = f"{session_id}_{binding.profile_id}"
    return {
        "institutionId": "institution_local",
        "approvalReference": binding.approval_reference,
        "workloadId": "customer_summary",
        "purposeCode": "CUSTOMER_SUPPORT",
        "subjectScope": "customer:customer-100",
        "destinationProfileId": binding.destination_profile_id,
        "idempotencyKey": f"idem_eval_bundle_{suffix}",
        "evaluationRunId": RUN_ID,
        "evalCaseId": CASE_ID,
        "processingContexts": ["AI_USE"],
        "input": {"prompt": "승인된 고객 정보를 간단히 요약하세요"},
    }


def preflight(environment: Mapping[str, str], base_url: str, session_id: str) -> dict[str, Any]:
    base_url = normalized_base_url(base_url)
    safe_session_id(session_id)
    local = urlsplit(base_url).hostname in LOCAL_DEV_HOSTS
    runtime_key_present = bool(environment.get(API_KEY_ENV))
    token_present = bool(environment.get(BUNDLE_TOKEN_ENV))
    remote_bearer_enabled = environment.get(REMOTE_BEARER_ENABLED_ENV) == "YES"
    local_user = environment.get(LOCAL_USER_ENV, "da-evaluation-reader")
    local_roles = environment.get(LOCAL_ROLES_ENV, "PRIVILEGED_OPERATOR")
    local_headers_safe = True
    try:
        safe_header(local_user, LOCAL_USER_ENV)
        safe_header(local_roles, LOCAL_ROLES_ENV)
    except E2EError:
        local_headers_safe = False
    local_admin_present = (
        local
        and local_headers_safe
        and "PRIVILEGED_OPERATOR" in {role.strip() for role in local_roles.split(",")}
    )
    unique_profiles = len({item.profile_id for item in BASELINE_MODELS}) == 3
    unique_destinations = len({item.destination_profile_id for item in BASELINE_MODELS}) == 3
    checks = {
        "baseline_has_three_unique_profiles": unique_profiles,
        "baseline_has_three_unique_destinations": unique_destinations,
        "runtime_api_key_present": runtime_key_present,
        "bundle_auth_present": local_admin_present or (token_present and remote_bearer_enabled),
        "remote_bearer_adapter_confirmed": local or remote_bearer_enabled,
        "real_provider_execution_confirmed": environment.get(CONFIRMATION_ENV) == "YES",
    }
    return {
        "ready_for_live_execution": all(checks.values()),
        "base_url": base_url,
        "evaluation_run_id": RUN_ID,
        "eval_case_id": CASE_ID,
        "expected_case_count": 1,
        "expected_model_count": 3,
        "expected_execution_count": 3,
        "session_id": session_id,
        "models": [asdict(item) for item in BASELINE_MODELS],
        "checks": checks,
        "credential_values_recorded": False,
    }


def _request_bytes(
    opener: Opener,
    url: str,
    *,
    method: str,
    headers: Mapping[str, str],
    payload: Mapping[str, Any] | None = None,
    timeout: float,
) -> bytes:
    body = None
    request_headers = {"Accept": "application/json", **headers}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    request = Request(url, data=body, headers=request_headers, method=method)
    try:
        with opener.open(request, timeout=timeout) as response:
            return cast(bytes, response.read())
    except HTTPError as error:
        error.read(2048)
        message = f"{method} {urlsplit(url).path} failed with HTTP {error.code}"
        raise E2EError(message) from error
    except URLError as error:
        raise E2EError(f"{method} {urlsplit(url).path} failed: {error.reason}") from error


def _decode_json(raw: bytes, stage: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise E2EError(f"{stage} returned invalid JSON") from error
    if not isinstance(value, dict):
        raise E2EError(f"{stage} response must be a JSON object")
    return value


def bundle_headers(environment: Mapping[str, str], local: bool) -> dict[str, str]:
    token = environment.get(BUNDLE_TOKEN_ENV)
    if not local and environment.get(REMOTE_BEARER_ENABLED_ENV) != "YES":
        raise E2EError(
            "remote Bundle export is blocked until the BE bearer authentication adapter "
            f"is deployed and {REMOTE_BEARER_ENABLED_ENV}=YES is explicitly set"
        )
    if token:
        safe_header(token, BUNDLE_TOKEN_ENV)
        return {"Authorization": f"Bearer {token}"}
    if not local:
        raise E2EError("remote Bundle export requires ADP_BE_TOKEN")
    return {
        "X-ADP-User-Id": safe_header(
            environment.get(LOCAL_USER_ENV, "da-evaluation-reader"), LOCAL_USER_ENV
        ),
        "X-ADP-User-Roles": safe_header(
            environment.get(LOCAL_ROLES_ENV, "PRIVILEGED_OPERATOR"), LOCAL_ROLES_ENV
        ),
    }


def _readiness_diagnostics(readiness: Mapping[str, Any]) -> str:
    diagnostics: list[str] = []
    case_models = readiness.get("case_models")
    if isinstance(case_models, list):
        for item in case_models:
            if not isinstance(item, dict):
                continue
            diagnostics.append(
                "/".join(
                    str(item.get(key) or "MISSING")
                    for key in (
                        "eval_case_id",
                        "profile_id",
                        "runtime_status",
                        "provider_status",
                        "evidence_status",
                    )
                )
            )
    return ", ".join(diagnostics[:10]) or "no incomplete pair detail returned"


def _validate_readiness(readiness: Mapping[str, Any]) -> None:
    if readiness.get("evaluation_run_id") != RUN_ID:
        raise E2EError("readiness evaluation run mismatch")
    ready = readiness.get("status") == "READY"
    available = readiness.get("bundle_available") is True
    counts_match = all(
        readiness.get(name) == expected
        for name, expected in (
            ("expected_execution_count", 3),
            ("observed_execution_count", 3),
            ("complete_evidence_count", 3),
            ("missing_execution_count", 0),
            ("unexpected_execution_count", 0),
        )
    )
    if not (ready and available and counts_match):
        diagnostics = _readiness_diagnostics(readiness)
        raise E2EError(
            "evaluation run is not ready for Bundle export: "
            f"status={readiness.get('status')}, "
            f"bundle_available={readiness.get('bundle_available')}, "
            f"observed={readiness.get('observed_execution_count')}, "
            f"complete={readiness.get('complete_evidence_count')}, "
            f"missing={readiness.get('missing_execution_count')}, "
            f"unexpected={readiness.get('unexpected_execution_count')}, "
            f"pairs={diagnostics}"
        )


def _export_ready_bundle(
    *,
    environment: Mapping[str, str],
    report: dict[str, Any],
    output: Path,
    timeout: float,
    client: Opener,
    execution_ids: list[str],
    operation: str,
) -> dict[str, Any]:
    local = urlsplit(str(report["base_url"])).hostname in LOCAL_DEV_HOSTS
    headers = bundle_headers(environment, local)
    output.mkdir(parents=True)
    raw_readiness = _request_bytes(
        client,
        f"{report['base_url']}/api/admin/ai/evaluation-runs/{quote(RUN_ID, safe='')}/readiness",
        method="GET",
        headers=headers,
        timeout=timeout,
    )
    readiness_path = output / "readiness.json"
    readiness_path.write_bytes(raw_readiness)
    readiness = _decode_json(raw_readiness, "evaluation readiness")
    _validate_readiness(readiness)

    raw_bundle = _request_bytes(
        client,
        f"{report['base_url']}/api/admin/ai/evaluation-runs/{quote(RUN_ID, safe='')}/bundle",
        method="GET",
        headers=headers,
        timeout=timeout,
    )
    digest = hashlib.sha256(raw_bundle).hexdigest()
    incoming = output / "bundle_export"
    incoming.mkdir()
    bundle_path = incoming / f"sha256-{digest}.json"
    bundle_path.write_bytes(raw_bundle)
    analysis_path = run_pipeline(bundle_path, output / "analysis", evaluation_run_id=RUN_ID)
    result = {
        **report,
        "operation": operation,
        "ready_for_bundle_consumption": True,
        "execution_ids": execution_ids,
        "readiness_status": readiness["status"],
        "readiness_path": str(readiness_path),
        "bundle_raw_sha256": f"sha256:{digest}",
        "bundle_path": str(bundle_path),
        "analysis_path": str(analysis_path),
    }
    (output / "e2e-result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def consume_existing(
    *,
    environment: Mapping[str, str],
    base_url: str,
    output: Path,
    session_id: str,
    timeout: float,
    opener: Opener | None = None,
) -> dict[str, Any]:
    report = preflight(environment, base_url, session_id)
    if not report["checks"]["bundle_auth_present"]:
        raise E2EError("existing Bundle consumption blocked by missing supported authentication")
    if output.exists():
        raise E2EError(f"output already exists: {output}")
    return _export_ready_bundle(
        environment=environment,
        report=report,
        output=output,
        timeout=timeout,
        client=opener or NoRedirect.opener(),
        execution_ids=[],
        operation="consume_existing",
    )


def execute_live(
    *,
    environment: Mapping[str, str],
    base_url: str,
    output: Path,
    session_id: str,
    timeout: float,
    opener: Opener | None = None,
) -> dict[str, Any]:
    report = preflight(environment, base_url, session_id)
    if not report["ready_for_live_execution"]:
        failed = [name for name, passed in report["checks"].items() if not passed]
        raise E2EError("live execution blocked by preflight: " + ", ".join(failed))
    if output.exists():
        raise E2EError(f"output already exists: {output}")
    client = opener or NoRedirect.opener()
    runtime_key = environment[API_KEY_ENV]
    execution_ids: list[str] = []
    for index, binding in enumerate(BASELINE_MODELS, start=1):
        suffix = f"{session_id}_{index}"
        raw = _request_bytes(
            client,
            f"{report['base_url']}/v1/runtime/executions",
            method="POST",
            headers={
                "X-ADP-API-Key": runtime_key,
                "X-Request-Id": f"req_eval_bundle_{suffix}",
                "X-Trace-Id": f"trace_eval_bundle_{suffix}",
            },
            payload=runtime_payload(binding, session_id),
            timeout=timeout,
        )
        response = _decode_json(raw, f"runtime execution {index}")
        execution_id = response.get("executionId")
        if not isinstance(execution_id, str) or not execution_id:
            raise E2EError(f"runtime execution {index} omitted executionId")
        execution_ids.append(execution_id)

    return _export_ready_bundle(
        environment=environment,
        report=report,
        output=output,
        timeout=timeout,
        client=client,
        execution_ids=execution_ids,
        operation="execute_live",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--execute", action="store_true", help="perform three real provider calls")
    mode.add_argument(
        "--consume-existing",
        action="store_true",
        help="validate readiness and consume an existing Bundle without provider calls",
    )
    parser.add_argument("--base-url", default=os.environ.get(BASE_URL_ENV, "http://127.0.0.1:8080"))
    parser.add_argument("--session-id", default=default_session_id())
    parser.add_argument("--output", type=Path, default=Path("outputs/real_be_evaluation"))
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()
    try:
        if args.timeout <= 0:
            raise E2EError("timeout must be positive")
        if args.execute:
            result = execute_live(
                environment=os.environ,
                base_url=args.base_url,
                output=args.output,
                session_id=args.session_id,
                timeout=args.timeout,
            )
        elif args.consume_existing:
            result = consume_existing(
                environment=os.environ,
                base_url=args.base_url,
                output=args.output,
                session_id=args.session_id,
                timeout=args.timeout,
            )
        else:
            result = preflight(os.environ, args.base_url, args.session_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except E2EError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()
