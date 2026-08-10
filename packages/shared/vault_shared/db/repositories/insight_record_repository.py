import uuid

from sqlalchemy.orm import Session

from vault_shared.db.models import InsightRecord


class InsightRecordRepository:
    """Append-only — insights are observational snapshots, not open issues
    to resolve, so there's no update/upsert method here (contrast with
    `RecommendationRepository.upsert`)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        organization_id: uuid.UUID,
        recommendation_job_id: uuid.UUID | None,
        insight_type: str,
        title: str,
        description: str,
        confidence: float,
        related_file_ids: list[str],
    ) -> InsightRecord:
        insight = InsightRecord(
            organization_id=organization_id,
            recommendation_job_id=recommendation_job_id,
            insight_type=insight_type,
            title=title,
            description=description,
            confidence=confidence,
            related_file_ids=related_file_ids,
        )
        self._session.add(insight)
        self._session.flush()
        return insight

    def list_recent_for_organization(
        self, organization_id: uuid.UUID, *, limit: int = 20
    ) -> list[InsightRecord]:
        return (
            self._session.query(InsightRecord)
            .filter_by(organization_id=organization_id)
            .order_by(InsightRecord.created_at.desc())
            .limit(limit)
            .all()
        )
