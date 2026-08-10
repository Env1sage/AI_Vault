from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_version_endpoint_returns_api_and_service_version() -> None:
    response = client.get("/v1/version")

    assert response.status_code == 200
    body = response.json()
    assert body["api_version"] == "v1"
    assert "service_version" in body
