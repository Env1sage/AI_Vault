import uuid
from unittest.mock import MagicMock

from app.application.assistant.registry import TOOL_REGISTRY
from app.application.conversation_service import ConversationService
from vault_shared.ai_gateway import AIGateway
from vault_shared.ai_gateway.providers import ExtractiveCompletionProvider, LocalEmbeddingProvider


def _service() -> ConversationService:
    gateway = AIGateway(
        embedding_provider=LocalEmbeddingProvider(), completion_provider=ExtractiveCompletionProvider()
    )
    return ConversationService(MagicMock(), ai_gateway=gateway)


def test_cache_key_always_includes_the_organization_id() -> None:
    service = _service()
    spec = TOOL_REGISTRY["get_storage_overview"]
    org_id = uuid.uuid4()

    key = service._cache_key(spec, org_id, {})  # noqa: SLF001 - testing the cache-key contract directly

    assert str(org_id) in key


def test_cache_key_differs_between_two_organizations() -> None:
    service = _service()
    spec = TOOL_REGISTRY["get_storage_overview"]
    org_a, org_b = uuid.uuid4(), uuid.uuid4()

    key_a = service._cache_key(spec, org_a, {})  # noqa: SLF001
    key_b = service._cache_key(spec, org_b, {})  # noqa: SLF001

    assert key_a != key_b


def test_cache_key_is_identical_for_identical_args() -> None:
    service = _service()
    spec = TOOL_REGISTRY["get_duplicate_summary"]
    org_id = uuid.uuid4()

    key_1 = service._cache_key(spec, org_id, {"limit": 5})  # noqa: SLF001
    key_2 = service._cache_key(spec, org_id, {"limit": 5})  # noqa: SLF001

    assert key_1 == key_2


def test_cache_key_differs_for_different_args() -> None:
    service = _service()
    spec = TOOL_REGISTRY["get_duplicate_summary"]
    org_id = uuid.uuid4()

    key_a = service._cache_key(spec, org_id, {"limit": 5})  # noqa: SLF001
    key_b = service._cache_key(spec, org_id, {"limit": 10})  # noqa: SLF001

    assert key_a != key_b


def test_cache_key_differs_between_tools() -> None:
    service = _service()
    org_id = uuid.uuid4()

    key_a = service._cache_key(  # noqa: SLF001
        TOOL_REGISTRY["get_storage_overview"], org_id, {}
    )
    key_b = service._cache_key(  # noqa: SLF001
        TOOL_REGISTRY["get_storage_statistics"], org_id, {}
    )

    assert key_a != key_b
