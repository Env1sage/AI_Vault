from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
import requests
from vault_shared import (
    DependencyUnavailableError,
    ReauthRequiredError,
    UnauthorizedError,
)
from vault_shared.connectors.google_workspace import GoogleWorkspaceOAuthClient


def _client() -> GoogleWorkspaceOAuthClient:
    return GoogleWorkspaceOAuthClient(
        client_id="test-client-id",
        client_secret="test-client-secret",
        redirect_uri="http://localhost:5173/connectors/google/callback",
        scopes="openid email profile https://www.googleapis.com/auth/drive.readonly",
    )


def _response(status_code: int, json_body: dict) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_body
    return response


class TestBuildAuthorizeUrl:
    def test_includes_the_expected_oauth_parameters(self) -> None:
        url = _client().build_authorize_url(state="abc123")

        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        assert params["client_id"] == ["test-client-id"]
        assert params["state"] == ["abc123"]
        assert params["response_type"] == ["code"]
        assert params["access_type"] == ["offline"]
        assert params["prompt"] == ["consent"]
        assert "drive.readonly" in params["scope"][0]


class TestExchangeCode:
    def test_returns_a_token_set_on_success(self) -> None:
        payload = {
            "access_token": "access-123",
            "refresh_token": "refresh-456",
            "expires_in": 3600,
            "scope": "openid email",
        }
        with patch("requests.post", return_value=_response(200, payload)):
            token_set = _client().exchange_code(code="auth-code")

        assert token_set.access_token == "access-123"
        assert token_set.refresh_token == "refresh-456"
        assert token_set.granted_scopes == "openid email"

    def test_raises_unauthorized_when_google_rejects_the_code(self) -> None:
        with (
            patch("requests.post", return_value=_response(400, {"error": "invalid_grant"})),
            pytest.raises(UnauthorizedError),
        ):
            _client().exchange_code(code="bad-code")

    def test_raises_dependency_unavailable_on_a_network_error(self) -> None:
        with (
            patch("requests.post", side_effect=requests.ConnectionError("boom")),
            pytest.raises(DependencyUnavailableError),
        ):
            _client().exchange_code(code="auth-code")

    def test_tolerates_a_missing_refresh_token_in_the_response(self) -> None:
        payload = {"access_token": "access-123", "expires_in": 3600, "scope": "openid"}
        with patch("requests.post", return_value=_response(200, payload)):
            token_set = _client().exchange_code(code="auth-code")

        assert token_set.refresh_token is None


class TestRefreshAccessToken:
    def test_keeps_the_original_refresh_token_since_google_does_not_reissue_one(self) -> None:
        payload = {"access_token": "new-access", "expires_in": 3600, "scope": "openid"}
        with patch("requests.post", return_value=_response(200, payload)):
            token_set = _client().refresh_access_token(refresh_token="original-refresh")

        assert token_set.access_token == "new-access"
        assert token_set.refresh_token == "original-refresh"

    def test_raises_reauth_required_when_google_reports_invalid_grant(self) -> None:
        """The real-world root cause of a "token refresh failed" scan
        blocker: a revoked/expired refresh token — Google's authoritative
        `invalid_grant` response — must be classified distinctly from a
        transient or misconfigured auth failure, since only this one is
        permanent and needs a user-facing reconnect action."""
        with (
            patch(
                "requests.post",
                return_value=_response(
                    400, {"error": "invalid_grant", "error_description": "Token has been expired or revoked."}
                ),
            ),
            pytest.raises(ReauthRequiredError),
        ):
            _client().refresh_access_token(refresh_token="revoked-token")

    def test_raises_plain_unauthorized_for_a_non_invalid_grant_refresh_failure(self) -> None:
        """A different Google error (e.g. a misconfigured client) must NOT
        be misclassified as "needs reconnect" — reconnecting wouldn't fix a
        client_id/secret problem, so it stays a generic auth failure."""
        with (
            patch("requests.post", return_value=_response(400, {"error": "unauthorized_client"})),
            pytest.raises(UnauthorizedError) as exc_info,
        ):
            _client().refresh_access_token(refresh_token="some-token")
        assert not isinstance(exc_info.value, ReauthRequiredError)

    def test_raises_unauthorized_on_a_malformed_200_response(self) -> None:
        """Google returning 200 with no `access_token` field must not leak a
        raw KeyError past this boundary."""
        with (
            patch("requests.post", return_value=_response(200, {"expires_in": 3600})),
            pytest.raises(UnauthorizedError),
        ):
            _client().refresh_access_token(refresh_token="some-token")


class TestFetchAccountInfo:
    def test_returns_email_and_workspace_domain(self) -> None:
        payload = {"email": "founder@acme.com", "hd": "acme.com"}
        with patch("requests.get", return_value=_response(200, payload)):
            info = _client().fetch_account_info(access_token="access-123")

        assert info.email == "founder@acme.com"
        assert info.workspace_domain == "acme.com"

    def test_workspace_domain_is_none_for_a_personal_gmail_account(self) -> None:
        payload = {"email": "someone@gmail.com"}
        with patch("requests.get", return_value=_response(200, payload)):
            info = _client().fetch_account_info(access_token="access-123")

        assert info.workspace_domain is None

    def test_raises_unauthorized_when_the_token_cannot_fetch_account_info(self) -> None:
        with (
            patch("requests.get", return_value=_response(401, {})),
            pytest.raises(UnauthorizedError),
        ):
            _client().fetch_account_info(access_token="expired")

    def test_raises_dependency_unavailable_on_a_network_error(self) -> None:
        with (
            patch("requests.get", side_effect=requests.ConnectionError("boom")),
            pytest.raises(DependencyUnavailableError),
        ):
            _client().fetch_account_info(access_token="access-123")


class TestRevoke:
    def test_returns_true_on_a_successful_revoke(self) -> None:
        with patch("requests.post", return_value=_response(200, {})):
            assert _client().revoke(token="some-token") is True

    def test_returns_false_without_raising_on_a_failed_revoke(self) -> None:
        with patch("requests.post", return_value=_response(400, {})):
            assert _client().revoke(token="some-token") is False

    def test_returns_false_without_raising_on_a_network_error(self) -> None:
        with patch("requests.post", side_effect=requests.ConnectionError("boom")):
            assert _client().revoke(token="some-token") is False
