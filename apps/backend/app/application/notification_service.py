import uuid

from sqlalchemy.orm import Session

from vault_shared.db.models import Notification
from vault_shared.db.repositories import NotificationRepository


class NotificationService:
    """Read-only surface for a user's own notifications (Phase 9's
    Notification Settings/inbox view). Actual dispatch — creating and
    sending a `Notification` — only ever happens from a running workflow
    in `apps/worker` (`vault_shared.notifications.NotificationDispatcher`),
    never from this backend; this class exists purely so the frontend has
    something to poll/list against."""

    def __init__(self, db: Session) -> None:
        self._notifications = NotificationRepository(db)

    def list_for_user(
        self, user_id: uuid.UUID, *, organization_id: uuid.UUID
    ) -> list[Notification]:
        return self._notifications.list_for_user(user_id, organization_id=organization_id)
