import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from vault_shared.db.models import Notification, NotificationStatus


class NotificationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        channel: str,
        subject: str,
        body: str,
        workflow_execution_id: uuid.UUID | None = None,
    ) -> Notification:
        notification = Notification(
            organization_id=organization_id,
            user_id=user_id,
            workflow_execution_id=workflow_execution_id,
            channel=channel,
            subject=subject,
            body=body,
        )
        self._session.add(notification)
        self._session.flush()
        return notification

    def get_by_id(self, notification_id: uuid.UUID) -> Notification | None:
        return self._session.get(Notification, notification_id)

    def list_for_user(
        self, user_id: uuid.UUID, *, organization_id: uuid.UUID, limit: int = 100
    ) -> list[Notification]:
        return (
            self._session.query(Notification)
            .filter_by(user_id=user_id, organization_id=organization_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .all()
        )

    def mark_sent(self, notification: Notification) -> None:
        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.now(UTC)
        self._session.flush()

    def mark_failed(self, notification: Notification, *, error: str) -> None:
        notification.status = NotificationStatus.FAILED
        notification.error = error[:1024]
        self._session.flush()
