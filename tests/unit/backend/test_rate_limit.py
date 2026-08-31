from unittest.mock import MagicMock, patch

import pytest
from app.presentation.dependencies.rate_limit import rate_limiter
from vault_shared import RateLimitExceededError


class _FakeRequest:
    class _Client:
        host = "203.0.113.5"

    client = _Client()


def test_allows_requests_under_the_limit() -> None:
    fake_redis = MagicMock()
    fake_redis.incr.return_value = 1

    with patch(
        "app.infrastructure.cache.rate_limit_counter.get_redis", return_value=fake_redis
    ):
        dependency = rate_limiter("test", limit=5, window_seconds=60)
        dependency(_FakeRequest())  # type: ignore[arg-type]

    fake_redis.expire.assert_called_once_with("ratelimit:test:203.0.113.5", 60)


def test_raises_once_the_limit_is_exceeded() -> None:
    fake_redis = MagicMock()
    fake_redis.incr.return_value = 6

    with patch(
        "app.infrastructure.cache.rate_limit_counter.get_redis", return_value=fake_redis
    ):
        dependency = rate_limiter("test", limit=5, window_seconds=60)
        with pytest.raises(RateLimitExceededError):
            dependency(_FakeRequest())  # type: ignore[arg-type]


def test_does_not_reset_expiry_after_the_first_increment() -> None:
    fake_redis = MagicMock()
    fake_redis.incr.return_value = 2

    with patch(
        "app.infrastructure.cache.rate_limit_counter.get_redis", return_value=fake_redis
    ):
        dependency = rate_limiter("test", limit=5, window_seconds=60)
        dependency(_FakeRequest())  # type: ignore[arg-type]

    fake_redis.expire.assert_not_called()


def test_fails_open_when_redis_is_unreachable() -> None:
    with patch(
        "app.infrastructure.cache.rate_limit_counter.get_redis",
        side_effect=ConnectionError("redis down"),
    ):
        dependency = rate_limiter("test", limit=1, window_seconds=60)
        dependency(_FakeRequest())  # type: ignore[arg-type] — must not raise
