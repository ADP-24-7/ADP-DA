from fastapi.testclient import TestClient

from adp_da.api import app


def test_health() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["service"] == "adp-da"
    assert response.json()["status"] == "ok"
