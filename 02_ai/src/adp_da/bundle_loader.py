"""Load exact response bytes, preserve every export and validate before use."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from adp_da.bundle_validator import BundleValidationError, validate_bundle


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


def load_bundle(
    source: str | Path,
    archive_dir: Path,
    *,
    evaluation_run_id: str | None = None,
    token: str | None = None,
    timeout: float = 30,
    max_bytes: int = 50_000_000,
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_text = str(source)
    is_api = source_text.startswith(("https://", "http://"))
    if is_api:
        url = urlsplit(source_text)
        if url.username or url.password or url.query or url.fragment:
            raise ValueError("Use a base URL without credentials, query or fragment")
        if url.scheme != "https" and url.hostname not in {"localhost", "127.0.0.1", "::1"}:
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
        if token:
            headers["Authorization"] = "Bearer " + token
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
