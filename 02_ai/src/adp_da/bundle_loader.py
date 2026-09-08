"""Load exact response bytes, preserve every export and validate before use."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from adp_da.bundle_validator import BundleValidationError, validate_bundle

LOCAL_DEV_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "adp-be"})


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: Any, msg: Any, headers: Any, newurl: Any
    ) -> None:
        return None


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BundleValidationError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise BundleValidationError("non-finite JSON number")


def _validate_header_value(name: str, value: str) -> None:
    if not value.strip():
        raise ValueError(f"{name} must not be empty")
    if "\r" in value or "\n" in value:
        raise ValueError(f"{name} must not contain line breaks")


def load_bundle(
    source: str | Path,
    archive_dir: Path,
    *,
    evaluation_run_id: str | None = None,
    token: str | None = None,
    remote_bearer_enabled: bool = False,
    local_admin_user_id: str | None = None,
    local_admin_roles: str | None = None,
    timeout: float = 30,
    max_bytes: int = 50_000_000,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load and validate a local bundle or an exact export from the BE API.

    API callers may use either a bearer ``token`` or BE's development-only local
    administrator headers. Local administrator values must be supplied together and
    are deliberately never included in returned/archive metadata.
    """
    source_text = str(source)
    is_api = source_text.startswith(("https://", "http://"))
    if is_api:
        url = urlsplit(source_text)
        if url.username or url.password or url.query or url.fragment:
            raise ValueError("Use a base URL without credentials, query or fragment")
        local_api = url.hostname in LOCAL_DEV_HOSTS
        if url.scheme != "https" and not local_api:
            raise ValueError("Remote API requires HTTPS")
        if not evaluation_run_id:
            raise ValueError("API source requires evaluation_run_id")
        endpoint = (
            source_text.rstrip("/")
            + "/api/admin/ai/evaluation-runs/"
            + quote(evaluation_run_id, safe="")
            + "/bundle"
        )
        headers = {"Accept": "application/json"}
        has_local_admin = local_admin_user_id is not None or local_admin_roles is not None
        if has_local_admin and not (local_admin_user_id and local_admin_roles):
            raise ValueError("Local administrator user ID and roles must be provided together")
        if token and has_local_admin:
            raise ValueError("Bearer and local administrator authentication are mutually exclusive")
        if token:
            _validate_header_value("Bearer token", token)
            if not local_api and not remote_bearer_enabled:
                raise ValueError(
                    "Remote Bearer authentication is disabled until the BE authentication "
                    "adapter is deployed and explicitly enabled"
                )
            headers["Authorization"] = "Bearer " + token
        elif has_local_admin:
            assert local_admin_user_id is not None
            assert local_admin_roles is not None
            _validate_header_value("Local administrator user ID", local_admin_user_id)
            _validate_header_value("Local administrator roles", local_admin_roles)
            headers["X-ADP-User-Id"] = local_admin_user_id
            headers["X-ADP-User-Roles"] = local_admin_roles
        with build_opener(_NoRedirect()).open(
            Request(endpoint, headers=headers), timeout=timeout
        ) as response:
            raw = response.read(max_bytes + 1)
    else:
        with Path(source).open("rb") as file:
            raw = file.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise BundleValidationError("bundle exceeds byte limit")
    # Raw-byte hash distinguishes exports whose generated_at differs but content_digest is equal.
    archive_dir.mkdir(parents=True, exist_ok=True)
    raw_path = archive_dir / (hashlib.sha256(raw).hexdigest() + ".json")
    if raw_path.exists():
        if raw_path.read_bytes() != raw:
            raise BundleValidationError("raw archive collision")
    else:
        raw_path.write_bytes(raw)
    bundle = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    validation = validate_bundle(bundle)
    if evaluation_run_id and bundle["manifest"]["evaluation_run_id"] != evaluation_run_id:
        raise BundleValidationError("requested evaluation run mismatch")
    metadata = {
        **bundle["manifest"],
        "evaluated_execution_count": bundle["failure_summary"]["evaluated_execution_count"],
        "source_type": "api" if is_api else "local",
        "raw_path": str(raw_path),
        "validation": validation,
    }
    raw_path.with_suffix(".metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return bundle, metadata
