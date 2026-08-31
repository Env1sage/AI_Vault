import uuid

from sqlalchemy.orm import Session

from vault_shared import DependencyUnavailableError, UnauthorizedError, ValidationError
from vault_shared.ai_gateway.interfaces import Message
from vault_shared.ai_gateway.providers.openai_compatible_completion_provider import (
    OpenAICompatibleCompletionProvider,
)
from vault_shared.db.models import AIProviderConfig
from vault_shared.db.repositories import AIProviderConfigRepository
from vault_shared.security.encryption import decrypt_token, encrypt_token
from vault_shared.settings import get_settings

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_TEST_MAX_TOKENS = 10
_TEST_MESSAGE = "Reply with exactly one word: OK."


class AIProviderConfigService:
    """Per-organization AI completion provider configuration (ADR-024's
    per-org follow-up) — owner/admin-only, OpenRouter-only in this phase.
    Mirrors `ConnectorCredentials`' "only ever handle encrypted values at
    the model/repo layer, encrypt/decrypt at the service layer" split."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._configs = AIProviderConfigRepository(db)

    def get_status(self, organization_id: uuid.UUID) -> AIProviderConfig | None:
        return self._configs.get_by_organization_id(organization_id)

    def set(
        self, organization_id: uuid.UUID, *, api_key: str | None, model_name: str
    ) -> AIProviderConfig:
        """A blank/omitted `api_key` keeps the existing stored key,
        updating only `model_name` — lets an admin change models without
        re-pasting the key every time. Raises if there's no key to fall
        back on at all (nothing stored yet, and none given)."""
        existing = self._configs.get_by_organization_id(organization_id)
        if api_key:
            api_key_encrypted = encrypt_token(api_key)
        elif existing is not None:
            api_key_encrypted = existing.api_key_encrypted
        else:
            raise ValidationError("An API key is required.")

        config = self._configs.upsert(
            organization_id=organization_id,
            api_key_encrypted=api_key_encrypted,
            model_name=model_name,
        )
        self._db.commit()
        return config

    def clear(self, organization_id: uuid.UUID) -> None:
        existing = self._configs.get_by_organization_id(organization_id)
        if existing is not None:
            self._configs.delete(existing)
            self._db.commit()

    def test(
        self, organization_id: uuid.UUID, *, api_key: str | None, model_name: str
    ) -> tuple[bool, str | None]:
        """Tests the *candidate* key/model directly — never the resolver
        (which reads only already-saved config) — so a not-yet-saved key
        can be validated before committing to it. A blank `api_key` tests
        against whatever key is already stored, matching `set()`'s "blank
        means keep/use the existing key" rule. Never persists anything,
        win or lose."""
        if api_key:
            resolved_key = api_key
        else:
            existing = self._configs.get_by_organization_id(organization_id)
            if existing is None:
                return False, "No API key is saved yet — enter one to test."
            resolved_key = decrypt_token(existing.api_key_encrypted)

        provider = OpenAICompatibleCompletionProvider(
            base_url=_OPENROUTER_BASE_URL,
            api_key=resolved_key,
            model_name=model_name,
            timeout_seconds=get_settings().completion_request_timeout_seconds,
        )
        try:
            provider.complete(
                messages=[Message(role="user", content=_TEST_MESSAGE)],
                context=None,
                max_tokens=_TEST_MAX_TOKENS,
            )
        except UnauthorizedError:
            return False, "That API key was rejected."
        except DependencyUnavailableError as exc:
            return False, str(exc)
        return True, None
