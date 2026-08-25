from fastapi import FastAPI
from pydantic import BaseModel

from adp_da import __version__


class HealthResponse(BaseModel):
    service: str
    status: str
    version: str


app = FastAPI(title="ADP Data Analysis", version=__version__)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(service="adp-da", status="ok", version=__version__)
