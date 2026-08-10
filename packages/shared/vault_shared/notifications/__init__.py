from functools import lru_cache

from vault_shared.notifications.dispatcher import NotificationDispatcher
from vault_shared.notifications.providers import EmailProvider, StubEmailProvider


@lru_cache
def get_email_provider() -> EmailProvider:
    """The one place that decides which `EmailProvider` backs the
    Notification Framework's email channel — currently always the stub
    (the founder's binding Phase 9 choice, mirroring ADR-018's `AIGateway`
    factory pattern). Swapping in a real provider later is a change here
    plus a new adapter class, never a change to any caller."""
    return StubEmailProvider()


__all__ = ["EmailProvider", "NotificationDispatcher", "StubEmailProvider", "get_email_provider"]
