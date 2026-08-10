import hashlib
import secrets


def generate_refresh_token() -> str:
    """High-entropy opaque token (256 bits) — not a JWT. Only its hash is
    ever persisted (see RefreshTokenRepository)."""
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    """SHA-256 is deliberately fast here, unlike a password hash — the input
    is already a high-entropy random secret, not a low-entropy user password,
    so there's no brute-force risk a slow hash would defend against."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_oauth_state() -> str:
    return secrets.token_urlsafe(24)
