import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from vault_shared.db.models import IntelligenceJob, IntelligenceJobStatus


class IntelligenceJobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        connector_id: uuid.UUID,
        triggered_by: str,
        triggered_by_user_id: uuid.UUID | None,
        enrichment_job_id: uuid.UUID | None = None,
    ) -> IntelligenceJob:
        job = IntelligenceJob(
            connector_id=connector_id,
            triggered_by=triggered_by,
            triggered_by_user_id=triggered_by_user_id,
            enrichment_job_id=enrichment_job_id,
        )
        self._session.add(job)
        self._session.flush()
        return job

    def get_by_id(self, intelligence_job_id: uuid.UUID) -> IntelligenceJob | None:
        return self._session.get(IntelligenceJob, intelligence_job_id)

    def list_for_connector(self, connector_id: uuid.UUID) -> list[IntelligenceJob]:
        return (
            self._session.query(IntelligenceJob)
            .filter_by(connector_id=connector_id)
            .order_by(IntelligenceJob.created_at.desc())
            .all()
        )

    def has_active_job(self, connector_id: uuid.UUID) -> bool:
        return (
            self._session.query(IntelligenceJob)
            .filter(
                IntelligenceJob.connector_id == connector_id,
                IntelligenceJob.status.in_(
                    [IntelligenceJobStatus.PENDING, IntelligenceJobStatus.RUNNING]
                ),
            )
            .first()
            is not None
        )

    def mark_running(self, job: IntelligenceJob) -> None:
        job.status = IntelligenceJobStatus.RUNNING
        job.started_at = datetime.now(UTC)
        self._session.flush()

    def mark_completed(self, job: IntelligenceJob) -> None:
        job.status = IntelligenceJobStatus.COMPLETED
        job.completed_at = datetime.now(UTC)
        self._session.flush()

    def mark_failed(self, job: IntelligenceJob, *, error: str) -> None:
        job.status = IntelligenceJobStatus.FAILED
        job.error = error[:2048]
        job.completed_at = datetime.now(UTC)
        self._session.flush()

    def mark_cancelled(self, job: IntelligenceJob) -> None:
        job.status = IntelligenceJobStatus.CANCELLED
        job.completed_at = datetime.now(UTC)
        self._session.flush()

    def request_cancel(self, job: IntelligenceJob) -> None:
        job.cancel_requested = True
        self._session.flush()

    def is_cancel_requested(self, intelligence_job_id: uuid.UUID) -> bool:
        """Column-only query, not an entity fetch — same identity-map
        staleness reasoning as `EmbeddingJobRepository.is_cancel_requested`."""
        result = (
            self._session.query(IntelligenceJob.cancel_requested)
            .filter(IntelligenceJob.id == intelligence_job_id)
            .scalar()
        )
        return bool(result)
