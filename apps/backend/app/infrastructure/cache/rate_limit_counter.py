from app.infrastructure.cache.redis_client import get_redis
from vault_shared import get_logger

logger = get_logger("app.cache")


def check_rate_limit(key: str, *, limit: int, window_seconds: int) -> bool:
    """The fixed-window INCR/EXPIRE primitive `rate_limiter()` (route-level,
    IP-keyed) already used inline — extracted here (ADR-024) so
    `ConversationService`'s service-layer tool-call rate check (keyed by
    org+user, not IP) can call it directly without `application/` importing
    from `presentation/`, which `rate_limiter()`'s `Request`-shaped
    dependency signature would otherwise require. Same fail-open posture as
    `response_cache.py`: returns `True` (not rate-limited) on a Redis
    outage — rate limiting is defense-in-depth, never allowed to be the
    reason a request fails."""
    try:
        redis = get_redis()
        # redis-py's stubs are generic over sync/async clients; get_redis()
        # is always the sync client, so these calls are never awaitable.
        current = int(redis.incr(key))  # type: ignore[arg-type]
        if current == 1:
            redis.expire(key, window_seconds)
    except Exception:
        logger.warning("rate_limit_check_failed", extra={"key": key})
        return True

    return current <= limit
