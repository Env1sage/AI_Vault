from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EmbeddingResult:
    """Provider-neutral embedding output — the vector plus enough model
    identity to detect a re-embedding need later (Handbook §8.5:
    "embedding-model changes must not silently corrupt comparisons against
    previously-generated vectors"). `vector` is unit-normalized, but
    ranking still needs `vault_shared.ai_gateway.similarity`'s
    mean-centering correction, not a plain dot product — see that
    module's docstring."""

    vector: list[float]
    model_name: str
    model_version: str
    dimensions: int


class EmbeddingProvider(Protocol):
    """Handbook §8.14: only the AI Gateway and its adapters know a provider
    exists at all — everything else calls `AIGateway.embed(...)`.
    `model_name`/`model_version` are exposed as attributes (not just
    fields on each `EmbeddingResult`) so a caller can check "would this
    provider consider file X's stored embedding current?" without
    actually calling `embed()`."""

    name: str
    model_name: str
    model_version: str

    def embed(self, texts: list[str]) -> list[EmbeddingResult]: ...


@dataclass(frozen=True)
class Message:
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass(frozen=True)
class CompletionResult:
    text: str
    provider: str
    model_name: str
    tokens_used: int | None


class CompletionProvider(Protocol):
    name: str
    model_name: str

    def complete(
        self, *, messages: list[Message], context: str | None, max_tokens: int
    ) -> CompletionResult: ...
