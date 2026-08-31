from unittest.mock import MagicMock, patch

import pytest
import requests
from vault_shared import DependencyUnavailableError, UnauthorizedError
from vault_shared.ai_gateway.interfaces import Message
from vault_shared.ai_gateway.providers.openai_compatible_completion_provider import (
    OpenAICompatibleCompletionProvider,
)


def _response(status_code: int, json_body: dict) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_body
    return response


def _provider() -> OpenAICompatibleCompletionProvider:
    return OpenAICompatibleCompletionProvider(
        base_url="https://api.moonshot.ai/v1",
        api_key="test-key",
        model_name="kimi-k2-0711-preview",
        timeout_seconds=60,
    )


def test_maps_a_successful_response_to_a_completion_result() -> None:
    body = {
        "choices": [{"message": {"content": '{"summary": "A contract."}'}}],
        "model": "kimi-k2-0711-preview",
        "usage": {"total_tokens": 123},
    }
    with patch("requests.post", return_value=_response(200, body)) as mock_post:
        result = _provider().complete(
            messages=[Message(role="user", content="Summarize this.")],
            context=None,
            max_tokens=500,
        )

    assert result.text == '{"summary": "A contract."}'
    assert result.provider == "openai_compatible"
    assert result.model_name == "kimi-k2-0711-preview"
    assert result.tokens_used == 123

    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["json"]["model"] == "kimi-k2-0711-preview"
    assert call_kwargs["json"]["messages"] == [{"role": "user", "content": "Summarize this."}]
    assert call_kwargs["json"]["max_tokens"] == 500
    assert call_kwargs["headers"]["Authorization"] == "Bearer test-key"


def test_folds_context_into_a_leading_system_message() -> None:
    body = {"choices": [{"message": {"content": "ok"}}]}
    with patch("requests.post", return_value=_response(200, body)) as mock_post:
        _provider().complete(
            messages=[Message(role="user", content="What is this?")],
            context="### Contract.pdf\nParty A and Party B agree...",
            max_tokens=100,
        )

    messages = mock_post.call_args.kwargs["json"]["messages"]
    assert messages[0] == {
        "role": "system",
        "content": "### Contract.pdf\nParty A and Party B agree...",
    }
    assert messages[1] == {"role": "user", "content": "What is this?"}


def test_401_raises_unauthorized() -> None:
    with (
        patch("requests.post", return_value=_response(401, {})),
        pytest.raises(UnauthorizedError),
    ):
        _provider().complete(messages=[], context=None, max_tokens=100)


def test_429_raises_dependency_unavailable() -> None:
    with (
        patch("requests.post", return_value=_response(429, {})),
        pytest.raises(DependencyUnavailableError),
    ):
        _provider().complete(messages=[], context=None, max_tokens=100)


def test_other_non_200_raises_dependency_unavailable() -> None:
    with (
        patch("requests.post", return_value=_response(500, {})),
        pytest.raises(DependencyUnavailableError),
    ):
        _provider().complete(messages=[], context=None, max_tokens=100)


def test_connection_error_raises_dependency_unavailable() -> None:
    with (
        patch("requests.post", side_effect=requests.ConnectionError("boom")),
        pytest.raises(DependencyUnavailableError),
    ):
        _provider().complete(messages=[], context=None, max_tokens=100)


def test_falls_back_to_configured_model_name_when_response_omits_it() -> None:
    body = {"choices": [{"message": {"content": "ok"}}]}  # no "model" key
    with patch("requests.post", return_value=_response(200, body)):
        result = _provider().complete(messages=[], context=None, max_tokens=100)

    assert result.model_name == "kimi-k2-0711-preview"
