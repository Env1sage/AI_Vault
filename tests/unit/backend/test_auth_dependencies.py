import uuid
from unittest.mock import MagicMock

import pytest
from app.infrastructure.auth.jwt import AccessTokenClaims, create_access_token
from app.presentation.dependencies.auth import get_current_user, require_role
from factories import make_user
from vault_shared import ForbiddenError, UnauthorizedError
from vault_shared.db.models import RoleName


class _FakeRequest:
    def __init__(self, headers: dict[str, str]) -> None:
        self.headers = headers


def test_get_current_user_rejects_missing_authorization_header() -> None:
    with pytest.raises(UnauthorizedError):
        get_current_user(_FakeRequest({}), db=MagicMock())  # type: ignore[arg-type]


def test_get_current_user_rejects_non_bearer_scheme() -> None:
    request = _FakeRequest({"authorization": "Basic abc123"})
    with pytest.raises(UnauthorizedError):
        get_current_user(request, db=MagicMock())  # type: ignore[arg-type]


def test_get_current_user_rejects_an_invalid_token() -> None:
    request = _FakeRequest({"authorization": "Bearer not-a-real-token"})
    with pytest.raises(UnauthorizedError):
        get_current_user(request, db=MagicMock())  # type: ignore[arg-type]


def test_get_current_user_rejects_a_valid_token_for_a_deleted_user() -> None:
    claims = AccessTokenClaims(
        user_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        role="owner",
    )
    token = create_access_token(claims)
    db = MagicMock()
    db.get.return_value = None

    request = _FakeRequest({"authorization": f"Bearer {token}"})
    with pytest.raises(UnauthorizedError):
        get_current_user(request, db=db)  # type: ignore[arg-type]


def test_get_current_user_returns_the_user_for_a_valid_token() -> None:
    user = make_user()
    claims = AccessTokenClaims(
        user_id=user.id, organization_id=user.organization_id, role="owner"
    )
    token = create_access_token(claims)
    db = MagicMock()
    db.get.return_value = user

    request = _FakeRequest({"authorization": f"Bearer {token}"})
    result = get_current_user(request, db=db)  # type: ignore[arg-type]

    assert result is user


def test_require_role_allows_a_matching_role(owner_user) -> None:
    dependency = require_role(RoleName.OWNER, RoleName.ADMIN)
    assert dependency(user=owner_user) is owner_user


def test_require_role_rejects_a_non_matching_role(member_user) -> None:
    dependency = require_role(RoleName.OWNER, RoleName.ADMIN)
    with pytest.raises(ForbiddenError):
        dependency(user=member_user)
