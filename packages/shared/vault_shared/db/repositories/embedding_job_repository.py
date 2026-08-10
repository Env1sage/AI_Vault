import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from vault_shared.db.models import EmbeddingJob, EmbeddingJobStatus


class EmbeddingJobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        connector_id: uuid.UUID,
        triggered_by: str,
        triggered_by_user_id: uuid.UUID | None,
        enrichment_job_id: uuid.UUID | None = None,
    ) -> EmbeddingJob:
        job = EmbeddingJob(
            connector_id=connector_id,
            triggered_by=triggered_by,
            triggered_by_user_id=triggered_by_user_id,
            enrichment_job_id=enrichment_job_id,
        )
        self._session.add(job)
        self._session.flush()
        return job

    def get_by_id(self, embedding_job_id: uuid.UUID) -> EmbeddingJob | None:
        return self._session.get(EmbeddingJob, embedding_job_id)

    def list_for_connector(self, connector_id: uuid.UUID) -> list[EmbeddingJob]:
        return (
            self._session.query(EmbeddingJob)
            .filter_by(connector_id=connector_id)
            .order_by(EmbeddingJob.created_at.desc())
            .all()
        )

    def has_active_job(self, connector_id: uuid.UUID) -> bool:
        return (
            self._session.query(EmbeddingJob)
            .filter(
                EmbeddingJob.connector_id == connector_id,
                EmbeddingJob.status.in_([EmbeddingJobStatus.PENDING, EmbeddingJobStatus.RUNNING]),
            )
            .first()
            is not None
        )

    def mark_running(self, job: EmbeddingJob) -> None:
        job.status = EmbeddingJobStatus.RUNNING
        job.started_at = datetime.now(UTC)
        self._session.flush()

    def mark_completed(self, job: EmbeddingJob) -> None:
        job.status = EmbeddingJobStatus.COMPLETED
        job.completed_at = datetime.now(UTC)
        self._session.flush()

    def mark_failed(self, job: EmbeddingJob, *, error: str) -> None:
        job.status = EmbeddingJobStatus.FAILED
        job.error = error[:2048]
        job.completed_at = datetime.now(UTC)
        self._session.flush()

    def mark_cancelled(self, job: EmbeddingJob) -> None:
        job.status = EmbeddingJobStatus.CANCELLED
        job.completed_at = datetime.now(UTC)
        self._session.flush()

    def request_cancel(self, job: EmbeddingJob) -> None:
        job.cancel_requested = True
        self._session.flush()

    def is_cancel_requested(self, embedding_job_id: uuid.UUID) -> bool:
        """Column-only query, not an entity fetch — same identity-map
        staleness reasoning as `ScanJobRepository.is_cancel_requested`."""
        result = (
            self._session.query(EmbeddingJob.cancel_requested)
            .filter(EmbeddingJob.id == embedding_job_id)
            .scalar()
        )
        return bool(result)
