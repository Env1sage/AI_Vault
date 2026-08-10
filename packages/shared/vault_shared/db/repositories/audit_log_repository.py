import uuid

from sqlalchemy.orm import Session

from vault_shared.db.models import AuditLog


class AuditLogRepository:
    """Append-only by construction — this class intentionally exposes no
    update/delete methods (Handbook §8.12)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def record(
        self,
        *,
        event_type: str,
        organization_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        metadata: dict | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            event_type=event_type,
            organization_id=organization_id,
            user_id=user_id,
            metadata_=metadata or {},
            ip_address=ip_address,
        )
        self._session.add(entry)
        self._session.flush()
        return entry
