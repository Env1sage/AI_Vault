import uuid

from sqlalchemy.orm import Session

from vault_shared.db.models import EmbeddingEvent


class EmbeddingEventRepository:
    """Append-only, like `EnrichmentEventRepository` — no update/delete
    methods."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def record(
        self,
        *,
        embedding_job_id: uuid.UUID,
        event_type: str,
        message: str | None = None,
        metadata: dict | None = None,
    ) -> EmbeddingEvent:
        event = EmbeddingEvent(
            embedding_job_id=embedding_job_id,
            event_type=event_type,
            # See ScanEventRepository.record — `message` is frequently
            # `str(some_exception)`, which for a SQLAlchemy DataError
            # includes the full failing SQL plus every bound parameter.
            # Truncated defensively so recording a failure can never itself
            # raise a second, uncaught error.
            message=message[:1024] if message else None,
            metadata_=metadata or {},
        )
        self._session.add(event)
        self._session.flush()
        return event

    def list_for_job(self, embedding_job_id: uuid.UUID) -> list[EmbeddingEvent]:
        return (
            self._session.query(EmbeddingEvent)
            .filter_by(embedding_job_id=embedding_job_id)
            .order_by(EmbeddingEvent.created_at)
            .all()
        )
