import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from app.application.auth_service import AuthenticatedSession
from app.infrastructure.auth.google_identity import (
    GoogleUserInfo,
    get_google_identity_verifier,
)
from app.main import app
from app.presentation.api.v1.auth import _login_rate_limit, _refresh_rate_limit
from app.presentation.dependencies.services import get_auth_service
from fastapi.testclient import TestClient
from vault_shared import ConflictError, UnauthorizedError

client = TestClient(app)


def _fake_session(user) -> AuthenticatedSession:
    return AuthenticatedSession(
        access_token="fake-access-token",
        refresh_token="fake-refresh-token",
        refresh_token_id=uuid.uuid4(),
        refresh_token_expires_at=datetime.now(UTC) + timedelta(days=30),
        user=user,
    )


@pytest.fixture(autouse=True)
def _bypass_rate_limits():
    app.dependency_overrides[_login_rate_limit] = lambda: None
    app.dependency_overrides[_refresh_rate_limit] = lambda: None
    yield
    app.dependency_overrides.pop(_login_rate_limit, None)
    app.dependency_overrides.pop(_refresh_rate_limit, None)


@pytest.fixture(autouse=True)
def _reset_client_cookies():
    # TestClient's underlying httpx client persists Set-Cookie responses into
    # its own jar across requests (mirroring real browser behavior) — without
    # this, a cookie set by one test (e.g. login) leaks into a later test that
    # expects no cookie to be present (e.g. refresh-without-a-cookie).
    client.cookies.clear()
    yield
    client.cookies.clear()


@pytest.fixture
def fake_verifier(owner_user) -> MagicMock:
    verifier = MagicMock()
    verifier.verify.return_value = GoogleUserInfo(
        sub="123",
        email=owner_user.email,
        email_verified=True,
        name=owner_user.name,
        picture=None,
    )
    app.dependency_overrides[get_google_identity_verifier] = lambda: verifier
    yield verifier
    app.dependency_overrides.pop(get_google_identity_verifier, None)


@pytest.fixture
def fake_auth_service() -> MagicMock:
    service = MagicMock()
    app.dependency_overrides[get_auth_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_auth_service, None)


def test_login_success_sets_refresh_cookie_and_returns_access_token(
    owner_user, fake_verifier, fake_auth_service
) -> None:
    fake_auth_service.complete_google_login.return_value = _fake_session(owner_user)

    response = client.post("/v1/auth/login", json={"id_token": "whatever"})

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "fake-access-token"
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == owner_user.email
    assert "vault_refresh_token" in response.cookies


def test_login_propagates_conflict_error_from_the_service(
    owner_user, fake_verifier, fake_auth_service
) -> None:
    fake_auth_service.complete_google_login.side_effect = ConflictError(
        "An account with this email already exists under a different sign-in method."
    )

    response = client.post("/v1/auth/login", json={"id_token": "whatever"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_login_requires_an_id_token_in_the_body(fake_verifier, fake_auth_service) -> None:
    response = client.post("/v1/auth/login", json={})
    assert response.status_code == 422


def test_refresh_without_a_cookie_is_unauthorized(fake_auth_service) -> None:
    response = client.post("/v1/auth/refresh")

    assert response.status_code == 401
    fake_auth_service.refresh_session.assert_not_called()


def test_refresh_with_a_cookie_rotates_the_session(owner_user, fake_auth_service) -> None:
    fake_auth_service.refresh_session.return_value = _fake_session(owner_user)
    client.cookies.set("vault_refresh_token", "old-raw-token")

    try:
        response = client.post("/v1/auth/refresh")
    finally:
        client.cookies.clear()

    assert response.status_code == 200
    fake_auth_service.refresh_session.assert_called_once()
    assert fake_auth_service.refresh_session.call_args.kwargs["raw_refresh_token"] == "old-raw-token"


def test_refresh_propagates_unauthorized_for_a_reused_token(fake_auth_service) -> None:
    fake_auth_service.refresh_session.side_effect = UnauthorizedError(
        "Invalid session — please sign in again."
    )
    client.cookies.set("vault_refresh_token", "stolen-token")

    try:
        response = client.post("/v1/auth/refresh")
    finally:
        client.cookies.clear()

    assert response.status_code == 401


def test_logout_is_a_no_op_without_a_cookie_but_still_succeeds(fake_auth_service) -> None:
    response = client.post("/v1/auth/logout")

    assert response.status_code == 204
    fake_auth_service.logout.assert_not_called()


def test_logout_revokes_the_session_when_a_cookie_is_present(fake_auth_service) -> None:
    client.cookies.set("vault_refresh_token", "some-token")

    try:
        response = client.post("/v1/auth/logout")
    finally:
        client.cookies.clear()

    assert response.status_code == 204
    fake_auth_service.logout.assert_called_once()
