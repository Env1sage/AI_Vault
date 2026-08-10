import json
import uuid
from dataclasses import dataclass

from app.infrastructure.auth.tokens import generate_oauth_state
from app.infrastructure.cache.redis_client import get_redis
from vault_shared import UnauthorizedError, get_settings


@dataclass(frozen=True)
class OAuthStateClaim:
    organization_id: uuid.UUID
    user_id: uuid.UUID


def _key(provider: str, state: str) -> str:
    return f"oauth-state:{provider}:{state}"


def issue_state(*, provider: str, organization_id: uuid.UUID, user_id: uuid.UUID) -> str:
    state = generate_oauth_state()
    settings = get_settings()
    payload = json.dumps({"organization_id": str(organization_id), "user_id": str(user_id)})
    get_redis().set(_key(provider, state), payload, ex=settings.oauth_state_ttl_seconds)
    return state


def consume_state(*, provider: str, state: str) -> OAuthStateClaim:
    """Single-use: the state is deleted on first successful read, so a
    replayed callback with the same state fails (Handbook §13's "prevent
    replay attacks during OAuth")."""
    redis = get_redis()
    key = _key(provider, state)
    raw = redis.get(key)
    if raw is None:
        raise UnauthorizedError("Invalid or expired OAuth state — please try connecting again.")
    redis.delete(key)
    # redis-py's stubs are generic over sync/async clients; get_redis() is
    # always the sync client, so this is never actually an Awaitable.
    payload = json.loads(raw)  # type: ignore[arg-type]
    return OAuthStateClaim(
        organization_id=uuid.UUID(payload["organization_id"]),
        user_id=uuid.UUID(payload["user_id"]),
    )
