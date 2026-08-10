from cryptography.fernet import Fernet, InvalidToken

from vault_shared.settings import get_settings


class TokenEncryptionError(Exception):
    """Raised when a stored token can't be decrypted — a corrupted row or a
    rotated encryption key. Deliberately not a `vault_shared` typed HTTP
    error: the application layer decides how this should surface (e.g. as a
    connector-in-error-state, not a generic 500) rather than this leaf module
    assuming an HTTP context exists."""


def _fernet() -> Fernet:
    key = get_settings().connector_encryption_key
    if not key:
        raise RuntimeError(
            "CONNECTOR_ENCRYPTION_KEY is not set — required before any OAuth "
            "token can be encrypted or decrypted. See .env.example."
        )
    return Fernet(key.encode("utf-8"))


def encrypt_token(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_token(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise TokenEncryptionError("Stored token could not be decrypted.") from exc
