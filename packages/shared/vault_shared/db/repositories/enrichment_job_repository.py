import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from vault_shared.db.models import EnrichmentJob, EnrichmentJobStatus


class EnrichmentJobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        connector_id: uuid.UUID,
        triggered_by: str,
        triggered_by_user_id: uuid.UUID | None,
        scan_job_id: uuid.UUID | None = None,
    ) -> EnrichmentJob:
        job = EnrichmentJob(
            connector_id=connector_id,
            triggered_by=triggered_by,
            triggered_by_user_id=triggered_by_user_id,
            scan_job_id=scan_job_id,
        )
        self._session.add(job)
        self._session.flush()
        return job

    def get_by_id(self, enrichment_job_id: uuid.UUID) -> EnrichmentJob | None:
        return self._session.get(EnrichmentJob, enrichment_job_id)

    def list_for_connector(self, connector_id: uuid.UUID) -> list[EnrichmentJob]:
        return (
            self._session.query(EnrichmentJob)
            .filter_by(connector_id=connector_id)
            .order_by(EnrichmentJob.created_at.desc())
            .all()
        )

    def has_active_job(self, connector_id: uuid.UUID) -> bool:
        return (
            self._session.query(EnrichmentJob)
            .filter(
                EnrichmentJob.connector_id == connector_id,
                EnrichmentJob.status.in_(
                    [EnrichmentJobStatus.PENDING, EnrichmentJobStatus.RUNNING]
                ),
            )
            .first()
            is not None
        )

    def mark_running(self, job: EnrichmentJob) -> None:
        job.status = EnrichmentJobStatus.RUNNING
        job.started_at = datetime.now(UTC)
        self._session.flush()

    def mark_completed(self, job: EnrichmentJob) -> None:
        job.status = EnrichmentJobStatus.COMPLETED
        job.completed_at = datetime.now(UTC)
        self._session.flush()

    def mark_failed(self, job: EnrichmentJob, *, error: str) -> None:
        job.status = EnrichmentJobStatus.FAILED
        job.error = error[:2048]
        job.completed_at = datetime.now(UTC)
        self._session.flush()

    def mark_cancelled(self, job: EnrichmentJob) -> None:
        job.status = EnrichmentJobStatus.CANCELLED
        job.completed_at = datetime.now(UTC)
        self._session.flush()

    def request_cancel(self, job: EnrichmentJob) -> None:
        job.cancel_requested = True
        self._session.flush()

    def is_cancel_requested(self, enrichment_job_id: uuid.UUID) -> bool:
        """Column-only query, not an entity fetch — same identity-map
        staleness reasoning as `ScanJobRepository.is_cancel_requested`."""
        result = (
            self._session.query(EnrichmentJob.cancel_requested)
            .filter(EnrichmentJob.id == enrichment_job_id)
            .scalar()
        )
        return bool(result)
