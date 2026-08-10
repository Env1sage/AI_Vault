from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_every_response_has_the_baseline_security_headers() -> None:
    response = client.get("/health/live")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in response.headers["permissions-policy"]


def test_api_responses_use_a_locked_down_content_security_policy() -> None:
    response = client.get("/health/live")

    assert response.headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"


def test_the_docs_route_gets_a_csp_that_allows_its_own_cdn_assets() -> None:
    response = client.get("/v1/docs")

    csp = response.headers["content-security-policy"]
    assert "cdn.jsdelivr.net" in csp
    assert "default-src 'none'" in csp


def test_hsts_is_absent_by_default_since_local_dev_is_plain_http() -> None:
    # cookie_secure defaults to false for local dev (Settings) — sending
    # Strict-Transport-Security over plain HTTP would be a lie the browser
    # ignores anyway, so this app doesn't send it until cookie_secure=true.
    response = client.get("/health/live")

    assert "strict-transport-security" not in response.headers
