import pytest
from cryptography.fernet import Fernet
from vault_shared import get_settings
from vault_shared.security.encryption import (
    TokenEncryptionError,
    decrypt_token,
    encrypt_token,
)


@pytest.fixture
def encryption_key(monkeypatch):
    """A valid Fernet key for the duration of one test — get_settings() is
    process-wide lru_cached, so it must be cleared both before and after."""
    key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setenv("CONNECTOR_ENCRYPTION_KEY", key)
    get_settings.cache_clear()
    yield key
    get_settings.cache_clear()


def test_round_trips_a_token_through_encrypt_and_decrypt(encryption_key) -> None:
    ciphertext = encrypt_token("my-secret-refresh-token")

    assert ciphertext != "my-secret-refresh-token"
    assert decrypt_token(ciphertext) == "my-secret-refresh-token"


def test_decrypt_raises_token_encryption_error_for_garbage_input(encryption_key) -> None:
    with pytest.raises(TokenEncryptionError):
        decrypt_token("not-a-valid-fernet-token")


def test_decrypt_raises_token_encryption_error_when_the_key_has_changed(
    encryption_key, monkeypatch
) -> None:
    ciphertext = encrypt_token("my-secret-refresh-token")

    other_key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setenv("CONNECTOR_ENCRYPTION_KEY", other_key)
    get_settings.cache_clear()

    with pytest.raises(TokenEncryptionError):
        decrypt_token(ciphertext)


def test_raises_a_clear_error_when_no_encryption_key_is_configured(monkeypatch) -> None:
    monkeypatch.setenv("CONNECTOR_ENCRYPTION_KEY", "")
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="CONNECTOR_ENCRYPTION_KEY"):
            encrypt_token("anything")
    finally:
        get_settings.cache_clear()
