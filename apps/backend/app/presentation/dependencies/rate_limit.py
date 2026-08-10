from collections.abc import Callable

from fastapi import Request

from app.infrastructure.cache.redis_client import get_redis
from vault_shared import RateLimitExceededError, get_logger

logger = get_logger("app.rate_limit")


def rate_limiter(key_prefix: str, *, limit: int, window_seconds: int) -> Callable[[Request], None]:
    """Fixed-window rate limit keyed by client IP (Handbook §13's "apply rate
    limiting to authentication endpoints"). Fails open on a Redis outage —
    rate limiting is defense-in-depth here, not the primary control (JWT
    validation and OAuth state validation are), so it must never be the
    reason sign-in goes down entirely."""

    def dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{key_prefix}:{client_ip}"

        try:
            redis = get_redis()
            # redis-py's stubs are generic over sync/async clients; get_redis()
            # is always the sync client, so these calls are never awaitable.
            current = int(redis.incr(key))  # type: ignore[arg-type]
            if current == 1:
                redis.expire(key, window_seconds)
        except Exception:
            logger.warning("rate_limit_check_failed", extra={"key_prefix": key_prefix})
            return

        if current > limit:
            raise RateLimitExceededError("Too many requests. Please try again later.")

    return dependency
