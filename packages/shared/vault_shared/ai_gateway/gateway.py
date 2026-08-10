import time

from vault_shared.ai_gateway.interfaces import (
    CompletionProvider,
    CompletionResult,
    EmbeddingProvider,
    EmbeddingResult,
    Message,
)
from vault_shared.metrics import record_ai_provider_latency


class AIGateway:
    """The sole boundary between this platform and any embedding/LLM
    provider (Handbook §8.14, §12) — every caller uses these capability
    methods only; nothing outside this module and its `providers/`
    adapters imports a provider SDK or calls a provider API directly.

    Provider selection is constructor injection (`get_ai_gateway()`
    decides which adapters to wire), the same pattern already used for
    `GoogleWorkspaceOAuthClient` throughout this codebase — swapping or
    adding a provider is a change to the factory plus a new adapter class,
    never a change to any caller of `embed`/`complete`."""

    def __init__(
        self, *, embedding_provider: EmbeddingProvider, completion_provider: CompletionProvider
    ) -> None:
        self._embedding_provider = embedding_provider
        self._completion_provider = completion_provider

    def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        started_at = time.perf_counter()
        try:
            return self._embedding_provider.embed(texts)
        finally:
            record_ai_provider_latency(
                # `.name` (the provider identifier), not `.model_name` (the
                # specific model version) — matches CompletionProvider's
                # only identity attribute below, keeping the metric's
                # `provider` label shape consistent across both operations.
                provider=self._embedding_provider.name,
                operation="embed",
                duration_seconds=time.perf_counter() - started_at,
            )

    @property
    def embedding_model_name(self) -> str:
        """Lets a caller (e.g. `EmbeddingService`'s pending-files query)
        check whether a stored embedding is current without calling
        `embed()` — the provider exposes its identity as plain
        attributes for exactly this."""
        return self._embedding_provider.model_name

    @property
    def embedding_model_version(self) -> str:
        return self._embedding_provider.model_version

    def complete(
        self, *, messages: list[Message], context: str | None = None, max_tokens: int = 1024
    ) -> CompletionResult:
        started_at = time.perf_counter()
        try:
            return self._completion_provider.complete(
                messages=messages, context=context, max_tokens=max_tokens
            )
        finally:
            record_ai_provider_latency(
                provider=self._completion_provider.name,
                operation="complete",
                duration_seconds=time.perf_counter() - started_at,
            )
