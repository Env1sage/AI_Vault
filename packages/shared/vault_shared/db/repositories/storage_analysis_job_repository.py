import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from vault_shared.db.models import StorageAnalysisJob, StorageAnalysisJobStatus


class StorageAnalysisJobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        organization_id: uuid.UUID,
        triggered_by: str,
        triggered_by_user_id: uuid.UUID | None,
    ) -> StorageAnalysisJob:
        job = StorageAnalysisJob(
            organization_id=organization_id,
            triggered_by=triggered_by,
            triggered_by_user_id=triggered_by_user_id,
        )
        self._session.add(job)
        self._session.flush()
        return job

    def get_by_id(self, storage_analysis_job_id: uuid.UUID) -> StorageAnalysisJob | None:
        return self._session.get(StorageAnalysisJob, storage_analysis_job_id)

    def list_for_organization(self, organization_id: uuid.UUID) -> list[StorageAnalysisJob]:
        return (
            self._session.query(StorageAnalysisJob)
            .filter_by(organization_id=organization_id)
            .order_by(StorageAnalysisJob.created_at.desc())
            .all()
        )

    def get_latest_for_organization(
        self, organization_id: uuid.UUID
    ) -> StorageAnalysisJob | None:
        return (
            self._session.query(StorageAnalysisJob)
            .filter_by(organization_id=organization_id)
            .order_by(StorageAnalysisJob.created_at.desc())
            .first()
        )

    def has_active_job(self, organization_id: uuid.UUID) -> bool:
        return (
            self._session.query(StorageAnalysisJob)
            .filter(
                StorageAnalysisJob.organization_id == organization_id,
                StorageAnalysisJob.status.in_(
                    [StorageAnalysisJobStatus.PENDING, StorageAnalysisJobStatus.RUNNING]
                ),
            )
            .first()
            is not None
        )

    def mark_running(self, job: StorageAnalysisJob) -> None:
        job.status = StorageAnalysisJobStatus.RUNNING
        job.started_at = datetime.now(UTC)
        self._session.flush()

    def mark_completed(self, job: StorageAnalysisJob) -> None:
        job.status = StorageAnalysisJobStatus.COMPLETED
        job.completed_at = datetime.now(UTC)
        self._session.flush()

    def mark_failed(self, job: StorageAnalysisJob, *, error: str) -> None:
        job.status = StorageAnalysisJobStatus.FAILED
        job.error = error[:2048]
        job.completed_at = datetime.now(UTC)
        self._session.flush()
