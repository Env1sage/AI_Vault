import os
import socket

import httpx
import pytest

BACKEND_URL = os.environ.get("E2E_BACKEND_URL", "http://localhost:8000")
FRONTEND_URL = os.environ.get("E2E_FRONTEND_URL", "http://localhost:5173")


def _reachable(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


requires_running_stack = pytest.mark.skipif(
    not _reachable("localhost", 8000),
    reason="Full stack not running — start it with `docker compose up` first (Phase 1 manual QA checklist).",
)


@requires_running_stack
def test_backend_health_and_version_are_reachable() -> None:
    assert httpx.get(f"{BACKEND_URL}/health/live", timeout=5).status_code == 200
    assert httpx.get(f"{BACKEND_URL}/v1/version", timeout=5).status_code == 200


@requires_running_stack
def test_frontend_serves_html_and_the_stack_is_wired_together() -> None:
    response = httpx.get(FRONTEND_URL, timeout=5)

    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
