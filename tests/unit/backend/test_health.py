from unittest.mock import MagicMock, patch

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_liveness_returns_ok_without_checking_dependencies() -> None:
    with patch("app.presentation.api.health.get_engine") as mock_engine, patch(
        "app.presentation.api.health.get_redis"
    ) as mock_redis:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_engine.assert_not_called()
    mock_redis.assert_not_called()


def test_readiness_reports_ok_when_all_dependencies_are_reachable() -> None:
    mock_connection = MagicMock()
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_connection
    mock_redis = MagicMock()

    with patch("app.presentation.api.health.get_engine", return_value=mock_engine), patch(
        "app.presentation.api.health.get_redis", return_value=mock_redis
    ):
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": True, "redis": True}}
    mock_redis.ping.assert_called_once()


def test_readiness_degrades_to_503_when_database_is_unreachable() -> None:
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = ConnectionError("boom")
    mock_redis = MagicMock()

    with patch("app.presentation.api.health.get_engine", return_value=mock_engine), patch(
        "app.presentation.api.health.get_redis", return_value=mock_redis
    ):
        response = client.get("/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["database"] is False
    assert body["checks"]["redis"] is True


def test_readiness_degrades_to_503_when_redis_is_unreachable() -> None:
    mock_connection = MagicMock()
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_connection
    mock_redis = MagicMock()
    mock_redis.ping.side_effect = ConnectionError("boom")

    with patch("app.presentation.api.health.get_engine", return_value=mock_engine), patch(
        "app.presentation.api.health.get_redis", return_value=mock_redis
    ):
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"] == {"database": True, "redis": False}
