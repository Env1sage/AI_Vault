import uuid

import jwt as pyjwt
import pytest
from app.infrastructure.auth.jwt import (
    AccessTokenClaims,
    create_access_token,
    decode_access_token,
)
from vault_shared import UnauthorizedError, get_settings


def _claims() -> AccessTokenClaims:
    return AccessTokenClaims(user_id=uuid.uuid4(), organization_id=uuid.uuid4(), role="owner")


def test_round_trips_claims_through_encode_and_decode() -> None:
    claims = _claims()
    token = create_access_token(claims)

    decoded = decode_access_token(token)

    assert decoded == claims


def test_rejects_a_token_signed_with_a_different_secret() -> None:
    claims = _claims()
    forged = pyjwt.encode(
        {
            "sub": str(claims.user_id),
            "org": str(claims.organization_id),
            "role": claims.role,
            "type": "access",
        },
        "wrong-secret",
        algorithm="HS256",
    )

    with pytest.raises(UnauthorizedError):
        decode_access_token(forged)


def test_rejects_an_expired_token() -> None:
    import datetime

    settings = get_settings()
    claims = _claims()
    now = datetime.datetime.now(datetime.UTC)
    expired = pyjwt.encode(
        {
            "sub": str(claims.user_id),
            "org": str(claims.organization_id),
            "role": claims.role,
            "type": "access",
            "iat": now - datetime.timedelta(hours=1),
            "exp": now - datetime.timedelta(minutes=1),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )

    with pytest.raises(UnauthorizedError):
        decode_access_token(expired)


def test_rejects_a_token_of_the_wrong_type() -> None:
    settings = get_settings()
    claims = _claims()
    wrong_type = pyjwt.encode(
        {
            "sub": str(claims.user_id),
            "org": str(claims.organization_id),
            "role": claims.role,
            "type": "refresh",
        },
        settings.jwt_secret,
        algorithm="HS256",
    )

    with pytest.raises(UnauthorizedError):
        decode_access_token(wrong_type)


def test_rejects_malformed_garbage() -> None:
    with pytest.raises(UnauthorizedError):
        decode_access_token("not-a-jwt-at-all")
