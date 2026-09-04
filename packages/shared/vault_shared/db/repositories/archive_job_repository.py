import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from vault_shared.db.models import ArchiveJob, ArchiveJobStatus


class ArchiveJobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        organization_id: uuid.UUID,
        execution_plan_id: uuid.UUID,
        name: str,
        created_by_user_id: uuid.UUID,
    ) -> ArchiveJob:
        archive_job = ArchiveJob(
            organization_id=organization_id,
            execution_plan_id=execution_plan_id,
            name=name,
            status=ArchiveJobStatus.PENDING,
            created_by_user_id=created_by_user_id,
        )
        self._session.add(archive_job)
        self._session.flush()
        return archive_job

    def get_by_id(self, archive_job_id: uuid.UUID) -> ArchiveJob | None:
        return self._session.get(ArchiveJob, archive_job_id)

    def get_owned(self, archive_job_id: uuid.UUID, *, organization_id: uuid.UUID) -> ArchiveJob | None:
        return (
            self._session.query(ArchiveJob)
            .filter_by(id=archive_job_id, organization_id=organization_id)
            .first()
        )

    def get_by_plan_id(self, execution_plan_id: uuid.UUID) -> ArchiveJob | None:
        return (
            self._session.query(ArchiveJob)
            .filter_by(execution_plan_id=execution_plan_id)
            .first()
        )

    def list_for_organization(
        self, organization_id: uuid.UUID, *, limit: int = 100, offset: int = 0
    ) -> tuple[list[ArchiveJob], int]:
        query = self._session.query(ArchiveJob).filter_by(organization_id=organization_id)
        total = query.count()
        items = query.order_by(ArchiveJob.created_at.desc()).limit(limit).offset(offset).all()
        return items, total

    def mark_creating(self, archive_job: ArchiveJob) -> None:
        archive_job.status = ArchiveJobStatus.CREATING
        self._session.flush()

    def mark_completed(
        self,
        archive_job: ArchiveJob,
        *,
        object_storage_key: str,
        original_size_bytes: int,
        compressed_size_bytes: int,
        file_count: int,
        manifest: list[dict],
    ) -> None:
        archive_job.status = ArchiveJobStatus.COMPLETED
        archive_job.object_storage_key = object_storage_key
        archive_job.original_size_bytes = original_size_bytes
        archive_job.compressed_size_bytes = compressed_size_bytes
        archive_job.file_count = file_count
        archive_job.manifest = manifest
        archive_job.completed_at = datetime.now(UTC)
        self._session.flush()

    def mark_failed(self, archive_job: ArchiveJob) -> None:
        archive_job.status = ArchiveJobStatus.FAILED
        self._session.flush()

    def mark_deleted(self, archive_job: ArchiveJob) -> None:
        archive_job.status = ArchiveJobStatus.DELETED
        self._session.flush()
