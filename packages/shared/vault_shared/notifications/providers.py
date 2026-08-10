from typing import Protocol

from vault_shared import get_logger

logger = get_logger("vault_shared.notifications")


class EmailProvider(Protocol):
    name: str

    def send(self, *, to_email: str, subject: str, body: str) -> None: ...


class StubEmailProvider:
    """The founder's binding Phase 9 choice: build the full email-channel
    interface, but never actually send anywhere until a real provider is
    configured — the same "adapter built, external call stubbed" pattern
    ADR-018 used for the still-stubbed LLM completion provider. A
    `Notification` row is still created and marked `SENT` (in-app delivery
    is always real; only the outbound email itself is a no-op), so the
    rest of the system behaves identically to a real provider being
    wired in later — swapping this for a real `EmailProvider` is a change
    to `get_email_provider()` alone, no caller changes."""

    name = "stub"

    def send(self, *, to_email: str, subject: str, body: str) -> None:
        logger.info(
            "stub_email_not_sent",
            extra={"to_email": to_email, "subject": subject, "body_length": len(body)},
        )
