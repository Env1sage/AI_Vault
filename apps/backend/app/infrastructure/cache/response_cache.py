from app.infrastructure.cache.redis_client import get_redis
from vault_shared import get_logger

logger = get_logger("app.cache")


def get_cached_json(key: str) -> str | None:
    """Read-through cache for expensive, read-heavy aggregation endpoints
    (Phase 10, ADR-022 — the phase spec explicitly names "Dashboard
    aggregation" as a caching target). Fails open on a Redis outage, the
    same defensive posture as `rate_limit.py` — a cache is a performance
    optimization, never allowed to be the reason an endpoint goes down."""
    try:
        # redis-py's stubs are generic over sync/async clients; get_redis()
        # is always the sync client, so this is never actually awaitable —
        # same rationale as rate_limit.py's identical ignore comment.
        return get_redis().get(key)  # type: ignore[return-value]
    except Exception:
        logger.warning("response_cache_read_failed", extra={"key": key})
        return None


def set_cached_json(key: str, value: str, *, ttl_seconds: int) -> None:
    try:
        get_redis().set(key, value, ex=ttl_seconds)
    except Exception:
        logger.warning("response_cache_write_failed", extra={"key": key})
