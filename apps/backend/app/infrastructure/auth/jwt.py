import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

from vault_shared import UnauthorizedError, get_settings

ACCESS_TOKEN_TYPE = "access"


@dataclass(frozen=True)
class AccessTokenClaims:
    user_id: uuid.UUID
    organization_id: uuid.UUID
    role: str


def create_access_token(claims: AccessTokenClaims) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(claims.user_id),
        "org": str(claims.organization_id),
        "role": claims.role,
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> AccessTokenClaims:
    """Raises UnauthorizedError (never a raw jwt/library exception) so the
    presentation layer never needs to know which JWT library issued it."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid or expired access token.") from exc

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise UnauthorizedError("Invalid or expired access token.")

    try:
        return AccessTokenClaims(
            user_id=uuid.UUID(payload["sub"]),
            organization_id=uuid.UUID(payload["org"]),
            role=payload["role"],
        )
    except (KeyError, ValueError) as exc:
        raise UnauthorizedError("Invalid or expired access token.") from exc
