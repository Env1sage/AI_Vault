from functools import lru_cache

from vault_shared.ai_gateway.gateway import AIGateway
from vault_shared.ai_gateway.interfaces import (
    CompletionProvider,
    CompletionResult,
    EmbeddingProvider,
    EmbeddingResult,
    Message,
)
from vault_shared.ai_gateway.providers import (
    ExtractiveCompletionProvider,
    LocalEmbeddingProvider,
    OpenAICompatibleCompletionProvider,
)
from vault_shared.ai_gateway.similarity import rank_by_similarity
from vault_shared.settings import get_settings

__all__ = [
    "AIGateway",
    "CompletionProvider",
    "CompletionResult",
    "EmbeddingProvider",
    "EmbeddingResult",
    "Message",
    "get_ai_gateway",
    "rank_by_similarity",
]


@lru_cache
def get_ai_gateway() -> AIGateway:
    """The factory every caller uses — `apps/backend` (query embedding +
    chat completion) and `apps/worker` (document embedding + Phase 2's
    file intelligence) both call this rather than constructing `AIGateway`
    themselves, so provider selection lives in exactly one place. Always
    wires the local/free embedding provider (see ADR-018). The completion
    provider is `OpenAICompatibleCompletionProvider` only when BOTH
    `completion_provider="openai_compatible"` AND `completion_api_key` is
    set — the key check is deliberate: flipping the provider setting alone
    (forgetting the key) must still fall back to today's deterministic
    stub, not fail every `complete()` call across the app (RAG chat
    included). Swapping providers again later is a new adapter class plus
    a change here — no caller changes."""
    settings = get_settings()
    completion_provider: CompletionProvider
    if settings.completion_provider == "openai_compatible" and settings.completion_api_key:
        completion_provider = OpenAICompatibleCompletionProvider(
            base_url=settings.completion_api_base_url,
            api_key=settings.completion_api_key,
            model_name=settings.completion_model_name,
            timeout_seconds=settings.completion_request_timeout_seconds,
        )
    else:
        completion_provider = ExtractiveCompletionProvider()
    return AIGateway(
        embedding_provider=LocalEmbeddingProvider(),
        completion_provider=completion_provider,
    )
