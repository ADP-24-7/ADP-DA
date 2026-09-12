import hmac
import os
from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel

from adp_da import __version__
from scripts.regulatory_refresh import load_service


class HealthResponse(BaseModel):
    service: str
    status: str
    version: str


class RegulatoryRefreshRequest(BaseModel):
    source_ids: list[str] | None = None


class RegulatoryRefreshResponse(BaseModel):
    automatic_activation: bool
    results: list[dict[str, Any]]


app = FastAPI(title="ADP Data Analysis", version=__version__)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(service="adp-da", status="ok", version=__version__)


@app.post("/internal/regulatory/refresh", response_model=RegulatoryRefreshResponse)
def refresh_regulatory_sources(
    request: RegulatoryRefreshRequest,
    internal_token: str = Header(alias="X-ADP-Internal-Token"),
) -> RegulatoryRefreshResponse:
    """Manual and scheduled callers share the same fail-closed refresh engine."""
    expected_token = os.getenv("ADP_REGULATORY_REFRESH_TOKEN", "")
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Regulatory refresh endpoint is not configured",
        )
    if not hmac.compare_digest(internal_token, expected_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    results = load_service().refresh(request.source_ids)
    return RegulatoryRefreshResponse(
        automatic_activation=False,
        results=[asdict(result) for result in results],
    )
