import uuid

from sqlalchemy.orm import Session

from vault_shared import ValidationError
from vault_shared.db.models import Notification, NotificationChannel
from vault_shared.db.repositories import NotificationRepository, UserRepository
from vault_shared.notifications.providers import EmailProvider


class NotificationDispatcher:
    """The Notification Framework's send path (Phase 9 spec) — creates a
    `Notification` row first, then attempts delivery, mirroring the "record
    before act" discipline `ExecutionService` uses for rollback records.
    `IN_APP` delivery is real and immediate (the row's existence, visible
    via the notifications list API, *is* the delivery); `EMAIL` delivery
    goes through whichever `EmailProvider` `get_email_provider()` wires in
    — the stub this phase, per the founder's binding choice. One call sends
    to one recipient; fanning out to N recipients is N calls, made by the
    caller (`worker.workflow.execution_service`'s notification/approval
    node handling), consistent with `Notification` being "one row per
    actual recipient."""

    def __init__(self, db: Session, *, email_provider: EmailProvider) -> None:
        self._db = db
        self._notifications = NotificationRepository(db)
        self._users = UserRepository(db)
        self._email_provider = email_provider

    def send(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        channel: str,
        subject: str,
        body: str,
        workflow_execution_id: uuid.UUID | None = None,
    ) -> Notification:
        notification = self._notifications.create(
            organization_id=organization_id,
            user_id=user_id,
            channel=channel,
            subject=subject,
            body=body,
            workflow_execution_id=workflow_execution_id,
        )
        try:
            if channel == NotificationChannel.EMAIL:
                user = self._users.get_by_id(user_id)
                if user is None or not user.email:
                    raise ValidationError("Recipient has no email address on file.")
                self._email_provider.send(to_email=user.email, subject=subject, body=body)
            # IN_APP has nothing further to do — the row itself is the
            # delivery, read via the notifications list endpoint.
            self._notifications.mark_sent(notification)
        except Exception as exc:  # noqa: BLE001 - one failed notification must not crash the caller
            self._notifications.mark_failed(notification, error=str(exc))
        self._db.commit()
        return notification
