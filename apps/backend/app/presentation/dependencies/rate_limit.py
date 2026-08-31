from collections.abc import Callable

from fastapi import Request

from app.infrastructure.cache.rate_limit_counter import check_rate_limit
from vault_shared import RateLimitExceededError


def rate_limiter(key_prefix: str, *, limit: int, window_seconds: int) -> Callable[[Request], None]:
    """Fixed-window rate limit keyed by client IP (Handbook §13's "apply rate
    limiting to authentication endpoints"). Fails open on a Redis outage —
    rate limiting is defense-in-depth here, not the primary control (JWT
    validation and OAuth state validation are), so it must never be the
    reason sign-in goes down entirely. Thin wrapper over `check_rate_limit`
    (`infrastructure/cache/rate_limit_counter.py`) — the primitive lives
    there, not here, so a service-layer caller (e.g.
    `ConversationService`'s tool-call rate check, keyed by org+user rather
    than IP) can use it without `application/` importing from
    `presentation/`."""

    def dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{key_prefix}:{client_ip}"
        if not check_rate_limit(key, limit=limit, window_seconds=window_seconds):
            raise RateLimitExceededError("Too many requests. Please try again later.")

    return dependency
