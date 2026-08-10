import uuid
from unittest.mock import patch

import pytest
from app.infrastructure.connectors.oauth_state import consume_state, issue_state
from vault_shared import UnauthorizedError


class _FakeRedis:
    """Enough of Redis's API (set/get/delete with a TTL argument accepted
    but not enforced) to exercise oauth_state.py without a real Redis."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._store[key] = value

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


@pytest.fixture
def fake_redis():
    redis = _FakeRedis()
    with patch("app.infrastructure.connectors.oauth_state.get_redis", return_value=redis):
        yield redis


def test_issue_then_consume_returns_the_original_claim(fake_redis) -> None:
    organization_id = uuid.uuid4()
    user_id = uuid.uuid4()

    state = issue_state(provider="google_workspace", organization_id=organization_id, user_id=user_id)
    claim = consume_state(provider="google_workspace", state=state)

    assert claim.organization_id == organization_id
    assert claim.user_id == user_id


def test_consuming_an_unknown_state_raises_unauthorized(fake_redis) -> None:
    with pytest.raises(UnauthorizedError):
        consume_state(provider="google_workspace", state="never-issued")


def test_state_is_single_use(fake_redis) -> None:
    state = issue_state(
        provider="google_workspace", organization_id=uuid.uuid4(), user_id=uuid.uuid4()
    )

    consume_state(provider="google_workspace", state=state)

    with pytest.raises(UnauthorizedError):
        consume_state(provider="google_workspace", state=state)


def test_states_are_scoped_per_provider(fake_redis) -> None:
    state = issue_state(
        provider="google_workspace", organization_id=uuid.uuid4(), user_id=uuid.uuid4()
    )

    with pytest.raises(UnauthorizedError):
        consume_state(provider="onedrive", state=state)
