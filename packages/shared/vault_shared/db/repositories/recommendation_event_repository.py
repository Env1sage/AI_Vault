import uuid

from sqlalchemy.orm import Session

from vault_shared.db.models import RecommendationEvent


class RecommendationEventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record(
        self,
        *,
        recommendation_job_id: uuid.UUID,
        event_type: str,
        message: str | None = None,
        metadata: dict | None = None,
    ) -> RecommendationEvent:
        event = RecommendationEvent(
            recommendation_job_id=recommendation_job_id,
            event_type=event_type,
            message=message[:1024] if message else None,
            metadata_=metadata or {},
        )
        self._session.add(event)
        self._session.flush()
        return event

    def list_for_job(self, recommendation_job_id: uuid.UUID) -> list[RecommendationEvent]:
        return (
            self._session.query(RecommendationEvent)
            .filter_by(recommendation_job_id=recommendation_job_id)
            .order_by(RecommendationEvent.created_at)
            .all()
        )
