import uuid

from sqlalchemy.orm import Session

from vault_shared.db.models import ScanEvent


class ScanEventRepository:
    """Append-only, like `AuditLogRepository` — no update/delete methods."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def record(
        self,
        *,
        scan_job_id: uuid.UUID,
        event_type: str,
        message: str | None = None,
        metadata: dict | None = None,
    ) -> ScanEvent:
        event = ScanEvent(
            scan_job_id=scan_job_id,
            event_type=event_type,
            # `message` is frequently `str(some_exception)` — a SQLAlchemy
            # DataError's string form includes the full failing SQL plus
            # every bound parameter, easily many KB. Truncated defensively
            # so *recording* a failure can never itself raise a second,
            # uncaught StringDataRightTruncation (which previously escaped
            # all the way to Celery's task boundary, crashing the whole job
            # over what should have been a single isolated failure).
            message=message[:1024] if message else None,
            metadata_=metadata or {},
        )
        self._session.add(event)
        self._session.flush()
        return event

    def list_for_job(self, scan_job_id: uuid.UUID) -> list[ScanEvent]:
        return (
            self._session.query(ScanEvent)
            .filter_by(scan_job_id=scan_job_id)
            .order_by(ScanEvent.created_at)
            .all()
        )
