from __future__ import annotations

from adp_da.api import app
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from scripts.regulatory_refresh import RefreshResult, content_digest


class FakeService:
    def refresh(self, source_ids: list[str] | None) -> list[RefreshResult]:
        source_id = (source_ids or ["AI-1"])[0]
        digest = content_digest(b"same")
        return [
            RefreshResult(
                source_id, f"REF-{source_id}", "UNCHANGED", digest, digest,
                (), (), (), 0,
            )
        ]


def test_manual_refresh_uses_shared_engine_and_never_activates(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr("adp_da.api.load_service", lambda: FakeService())
    monkeypatch.setenv("ADP_REGULATORY_REFRESH_TOKEN", "test-token")
    response = TestClient(app).post(
        "/internal/regulatory/refresh",
        json={"source_ids": ["AI-1"]},
        headers={"X-ADP-Internal-Token": "test-token"},
    )

    assert response.status_code == 200
    assert response.json()["automatic_activation"] is False
    assert response.json()["results"][0]["status"] == "UNCHANGED"


def test_refresh_rejects_invalid_internal_token(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("ADP_REGULATORY_REFRESH_TOKEN", "expected")

    response = TestClient(app).post(
        "/internal/regulatory/refresh",
        json={"source_ids": ["AI-1"]},
        headers={"X-ADP-Internal-Token": "wrong"},
    )

    assert response.status_code == 401
