from vault_shared.ai_gateway import AIGateway
from vault_shared.ai_gateway.providers import ExtractiveCompletionProvider, LocalEmbeddingProvider


def test_returns_a_new_gateway_with_the_given_completion_provider() -> None:
    embedding_provider = LocalEmbeddingProvider()
    original = AIGateway(
        embedding_provider=embedding_provider, completion_provider=ExtractiveCompletionProvider()
    )
    new_completion_provider = ExtractiveCompletionProvider()

    bound = original.with_completion_provider(new_completion_provider)

    assert bound is not original
    assert bound.completion_provider_name == new_completion_provider.name


def test_shares_the_embedding_provider_by_reference_not_a_new_instance() -> None:
    """The whole point: never reconstruct LocalEmbeddingProvider, since its
    GloVe word-vector load is expensive and meant to happen once per
    process."""
    embedding_provider = LocalEmbeddingProvider()
    original = AIGateway(
        embedding_provider=embedding_provider, completion_provider=ExtractiveCompletionProvider()
    )

    bound = original.with_completion_provider(ExtractiveCompletionProvider())

    assert bound._embedding_provider is original._embedding_provider  # noqa: SLF001
    assert bound._embedding_provider is embedding_provider  # noqa: SLF001


def test_does_not_mutate_the_original_gateway() -> None:
    original = AIGateway(
        embedding_provider=LocalEmbeddingProvider(),
        completion_provider=ExtractiveCompletionProvider(),
    )
    original_provider_name = original.completion_provider_name

    class _OtherProvider:
        name = "other_provider"
        model_name = "other-model"

        def complete(self, *, messages, context, max_tokens):  # noqa: ANN001, ANN201
            raise NotImplementedError

    original.with_completion_provider(_OtherProvider())  # type: ignore[arg-type]

    assert original.completion_provider_name == original_provider_name
