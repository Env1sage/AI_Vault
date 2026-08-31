"""Regression coverage for the message-ordering fix in
`OpenAICompatibleCompletionProvider.complete()` (ADR-024) — a persona/
safety system message must precede retrieved `context`, never follow it,
or the injection defense sits after the untrusted data it's meant to
constrain."""

from unittest.mock import MagicMock, patch

from vault_shared.ai_gateway.interfaces import Message
from vault_shared.ai_gateway.providers.openai_compatible_completion_provider import (
    OpenAICompatibleCompletionProvider,
)


def _response(json_body: dict) -> MagicMock:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = json_body
    return response


def _provider() -> OpenAICompatibleCompletionProvider:
    return OpenAICompatibleCompletionProvider(
        base_url="https://example.test/v1",
        api_key="test-key",
        model_name="test-model",
        timeout_seconds=60,
    )


def test_context_is_inserted_after_a_leading_persona_system_message() -> None:
    body = {"choices": [{"message": {"content": "ok"}}]}
    with patch("requests.post", return_value=_response(body)) as mock_post:
        _provider().complete(
            messages=[
                Message(role="system", content="PERSONA"),
                Message(role="user", content="What's in this file?"),
            ],
            context="DATA",
            max_tokens=100,
        )

    messages = mock_post.call_args.kwargs["json"]["messages"]
    assert [m["role"] for m in messages] == ["system", "system", "user"]
    assert messages[0]["content"] == "PERSONA"
    assert messages[1]["content"] == "DATA"
    assert messages[2]["content"] == "What's in this file?"


def test_context_still_lands_at_index_zero_with_no_leading_system_message() -> None:
    """Backward compatibility: every caller before this fix passed no
    leading system message, so `insert_at` must still resolve to 0."""
    body = {"choices": [{"message": {"content": "ok"}}]}
    with patch("requests.post", return_value=_response(body)) as mock_post:
        _provider().complete(
            messages=[Message(role="user", content="question")],
            context="DATA",
            max_tokens=100,
        )

    messages = mock_post.call_args.kwargs["json"]["messages"]
    assert messages[0] == {"role": "system", "content": "DATA"}
    assert messages[1] == {"role": "user", "content": "question"}


def test_no_context_leaves_messages_untouched() -> None:
    body = {"choices": [{"message": {"content": "ok"}}]}
    with patch("requests.post", return_value=_response(body)) as mock_post:
        _provider().complete(
            messages=[
                Message(role="system", content="PERSONA"),
                Message(role="user", content="question"),
            ],
            context=None,
            max_tokens=100,
        )

    messages = mock_post.call_args.kwargs["json"]["messages"]
    assert messages == [
        {"role": "system", "content": "PERSONA"},
        {"role": "user", "content": "question"},
    ]
