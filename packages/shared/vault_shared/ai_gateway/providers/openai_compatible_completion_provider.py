import requests

from vault_shared import DependencyUnavailableError, UnauthorizedError, get_logger
from vault_shared.ai_gateway.interfaces import CompletionResult, Message

logger = get_logger("vault_shared.ai_gateway.openai_compatible_completion_provider")


class OpenAICompatibleCompletionProvider:
    """A real, hosted LLM behind `AIGateway.complete()` — any provider that
    speaks the OpenAI chat-completions shape (Moonshot's Kimi by default,
    GLM or others via `base_url`/`model_name` alone, no code change).

    Error handling mirrors `GoogleDriveClient._request` deliberately — this
    is this codebase's one other outbound-HTTP-to-an-external-service
    pattern, and the same failure taxonomy applies (network/timeout and
    429 are transient and retried at the Celery task level; 401 is a
    permanent auth problem the caller must surface, not retry)."""

    name = "openai_compatible"

    def __init__(
        self, *, base_url: str, api_key: str, model_name: str, timeout_seconds: int
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self.model_name = model_name
        self._timeout = timeout_seconds

    def complete(
        self, *, messages: list[Message], context: str | None, max_tokens: int
    ) -> CompletionResult:
        chat_messages = [{"role": m.role, "content": m.content} for m in messages]
        if context:
            # OpenAI-compatible APIs have no separate "context" concept —
            # fold it into a system message, same treatment
            # `ExtractiveCompletionProvider` gives `context` today. Inserted
            # AFTER any leading system message(s) already in `messages`,
            # not unconditionally at index 0: a caller's persona/safety
            # system prompt must precede untrusted retrieved content, not
            # follow it — an injection defense placed after the data it's
            # meant to constrain isn't a defense. When `messages` has no
            # leading system message (every caller before this one),
            # `insert_at` is 0 and behavior is unchanged.
            insert_at = 0
            while insert_at < len(chat_messages) and chat_messages[insert_at]["role"] == "system":
                insert_at += 1
            chat_messages.insert(insert_at, {"role": "system", "content": context})

        try:
            response = requests.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model_name,
                    "messages": chat_messages,
                    "max_tokens": max_tokens,
                    "temperature": 0,
                },
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise DependencyUnavailableError("Could not reach the completion provider.") from exc

        if response.status_code == 401:
            raise UnauthorizedError("Completion provider rejected the API key.")
        if response.status_code == 429:
            raise DependencyUnavailableError("Completion provider rate limit exceeded.")
        if response.status_code != 200:
            logger.warning(
                "completion_provider_request_failed",
                extra={"status_code": response.status_code},
            )
            raise DependencyUnavailableError(
                f"Completion provider request failed ({response.status_code})."
            )

        body = response.json()
        text = body["choices"][0]["message"]["content"]
        return CompletionResult(
            text=text,
            provider=self.name,
            model_name=body.get("model", self.model_name),
            tokens_used=body.get("usage", {}).get("total_tokens"),
        )
