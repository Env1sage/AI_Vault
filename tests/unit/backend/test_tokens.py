import re

from app.infrastructure.auth.tokens import (
    generate_oauth_state,
    generate_refresh_token,
    hash_refresh_token,
)


def test_generate_refresh_token_produces_unique_high_entropy_values() -> None:
    tokens = {generate_refresh_token() for _ in range(100)}

    assert len(tokens) == 100
    assert all(len(token) >= 32 for token in tokens)


def test_hash_refresh_token_is_deterministic_and_looks_like_sha256_hex() -> None:
    token = generate_refresh_token()

    first_hash = hash_refresh_token(token)
    second_hash = hash_refresh_token(token)

    assert first_hash == second_hash
    assert re.fullmatch(r"[0-9a-f]{64}", first_hash)


def test_hash_refresh_token_differs_for_different_tokens() -> None:
    assert hash_refresh_token(generate_refresh_token()) != hash_refresh_token(generate_refresh_token())


def test_generate_oauth_state_produces_unique_values() -> None:
    states = {generate_oauth_state() for _ in range(50)}
    assert len(states) == 50
