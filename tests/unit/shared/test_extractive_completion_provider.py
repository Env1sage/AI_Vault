from vault_shared.ai_gateway.interfaces import Message
from vault_shared.ai_gateway.providers.extractive_completion_provider import (
    ExtractiveCompletionProvider,
)


def test_returns_the_no_context_message_when_nothing_was_retrieved() -> None:
    provider = ExtractiveCompletionProvider()

    result = provider.complete(
        messages=[Message(role="user", content="What files do we have?")],
        context=None,
        max_tokens=100,
    )

    assert "don't have any relevant documents" in result.text
    assert result.provider == "extractive_fallback"
    assert result.model_name == "none"
    assert result.tokens_used is None


def test_echoes_the_retrieved_context_when_present() -> None:
    provider = ExtractiveCompletionProvider()

    result = provider.complete(
        messages=[Message(role="user", content="What's in the budget file?")],
        context="### Budget.xlsx\nQ3 total: $42,000",
        max_tokens=100,
    )

    assert "What's in the budget file?" in result.text
    assert "Q3 total: $42,000" in result.text
    assert "No AI model is configured yet" in result.text


def test_bounds_output_length_to_roughly_four_characters_per_token() -> None:
    provider = ExtractiveCompletionProvider()
    long_context = "x" * 10_000

    result = provider.complete(
        messages=[Message(role="user", content="Summarize")], context=long_context, max_tokens=10
    )

    assert len(result.text) == 40
