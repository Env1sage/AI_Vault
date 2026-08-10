from functools import lru_cache

from vault_shared.ai_gateway.gateway import AIGateway
from vault_shared.ai_gateway.interfaces import (
    CompletionProvider,
    CompletionResult,
    EmbeddingProvider,
    EmbeddingResult,
    Message,
)
from vault_shared.ai_gateway.providers import ExtractiveCompletionProvider, LocalEmbeddingProvider
from vault_shared.ai_gateway.similarity import rank_by_similarity

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
    chat completion) and `apps/worker` (document embedding) both call this
    rather than constructing `AIGateway` themselves, so provider selection
    lives in exactly one place. Currently always wires the local/free
    embedding provider and the deterministic extractive completion
    fallback (see ADR-018); adding a real LLM provider later means adding
    a new adapter class and changing the two lines below — no caller
    changes."""
    return AIGateway(
        embedding_provider=LocalEmbeddingProvider(),
        completion_provider=ExtractiveCompletionProvider(),
    )
