import uuid

from sqlalchemy.orm import Session

from vault_shared.db.models import IntelligenceEvent


class IntelligenceEventRepository:
    """Append-only, like `EmbeddingEventRepository` — no update/delete
    methods."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def record(
        self,
        *,
        intelligence_job_id: uuid.UUID,
        event_type: str,
        message: str | None = None,
        metadata: dict | None = None,
    ) -> IntelligenceEvent:
        event = IntelligenceEvent(
            intelligence_job_id=intelligence_job_id,
            event_type=event_type,
            # Defensively truncated — `message` is frequently
            # `str(some_exception)`, which can be arbitrarily long.
            message=message[:1024] if message else None,
            metadata_=metadata or {},
        )
        self._session.add(event)
        self._session.flush()
        return event

    def list_for_job(self, intelligence_job_id: uuid.UUID) -> list[IntelligenceEvent]:
        return (
            self._session.query(IntelligenceEvent)
            .filter_by(intelligence_job_id=intelligence_job_id)
            .order_by(IntelligenceEvent.created_at)
            .all()
        )
