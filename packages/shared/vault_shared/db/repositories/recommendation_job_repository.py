import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from vault_shared.db.models import RecommendationJob, RecommendationJobStatus


class RecommendationJobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        organization_id: uuid.UUID,
        triggered_by: str,
        triggered_by_user_id: uuid.UUID | None,
    ) -> RecommendationJob:
        job = RecommendationJob(
            organization_id=organization_id,
            triggered_by=triggered_by,
            triggered_by_user_id=triggered_by_user_id,
        )
        self._session.add(job)
        self._session.flush()
        return job

    def get_by_id(self, recommendation_job_id: uuid.UUID) -> RecommendationJob | None:
        return self._session.get(RecommendationJob, recommendation_job_id)

    def list_for_organization(self, organization_id: uuid.UUID) -> list[RecommendationJob]:
        return (
            self._session.query(RecommendationJob)
            .filter_by(organization_id=organization_id)
            .order_by(RecommendationJob.created_at.desc())
            .all()
        )

    def get_latest_for_organization(
        self, organization_id: uuid.UUID
    ) -> RecommendationJob | None:
        return (
            self._session.query(RecommendationJob)
            .filter_by(organization_id=organization_id)
            .order_by(RecommendationJob.created_at.desc())
            .first()
        )

    def has_active_job(self, organization_id: uuid.UUID) -> bool:
        return (
            self._session.query(RecommendationJob)
            .filter(
                RecommendationJob.organization_id == organization_id,
                RecommendationJob.status.in_(
                    [RecommendationJobStatus.PENDING, RecommendationJobStatus.RUNNING]
                ),
            )
            .first()
            is not None
        )

    def mark_running(self, job: RecommendationJob) -> None:
        job.status = RecommendationJobStatus.RUNNING
        job.started_at = datetime.now(UTC)
        self._session.flush()

    def mark_completed(self, job: RecommendationJob, *, recommendations_active: int) -> None:
        job.status = RecommendationJobStatus.COMPLETED
        job.recommendations_active = recommendations_active
        job.completed_at = datetime.now(UTC)
        self._session.flush()

    def mark_failed(self, job: RecommendationJob, *, error: str) -> None:
        job.status = RecommendationJobStatus.FAILED
        job.error = error[:2048]
        job.completed_at = datetime.now(UTC)
        self._session.flush()
