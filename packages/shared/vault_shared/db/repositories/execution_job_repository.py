import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from vault_shared.db.models import ExecutionJob, ExecutionJobStatus


class ExecutionJobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        execution_plan_id: uuid.UUID,
        organization_id: uuid.UUID,
        triggered_by_user_id: uuid.UUID | None = None,
        is_rollback: bool = False,
    ) -> ExecutionJob:
        job = ExecutionJob(
            execution_plan_id=execution_plan_id,
            organization_id=organization_id,
            triggered_by_user_id=triggered_by_user_id,
            is_rollback=is_rollback,
        )
        self._session.add(job)
        self._session.flush()
        return job

    def get_by_id(self, execution_job_id: uuid.UUID) -> ExecutionJob | None:
        return self._session.get(ExecutionJob, execution_job_id)

    def get_owned(
        self, execution_job_id: uuid.UUID, *, organization_id: uuid.UUID
    ) -> ExecutionJob | None:
        return (
            self._session.query(ExecutionJob)
            .filter_by(id=execution_job_id, organization_id=organization_id)
            .first()
        )

    def list_for_plan(self, execution_plan_id: uuid.UUID) -> list[ExecutionJob]:
        return (
            self._session.query(ExecutionJob)
            .filter_by(execution_plan_id=execution_plan_id)
            .order_by(ExecutionJob.created_at.desc())
            .all()
        )

    def list_for_organization(
        self,
        organization_id: uuid.UUID,
        *,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ExecutionJob]:
        query = self._session.query(ExecutionJob).filter_by(organization_id=organization_id)
        if status is not None:
            query = query.filter(ExecutionJob.status == status)
        return query.order_by(ExecutionJob.created_at.desc()).limit(limit).offset(offset).all()

    def has_active_job_for_plan(self, execution_plan_id: uuid.UUID) -> bool:
        active_statuses = [
            ExecutionJobStatus.PENDING,
            ExecutionJobStatus.RUNNING,
            ExecutionJobStatus.PAUSED,
        ]
        return (
            self._session.query(ExecutionJob)
            .filter(
                ExecutionJob.execution_plan_id == execution_plan_id,
                ExecutionJob.status.in_(active_statuses),
            )
            .first()
            is not None
        )

    def mark_running(self, job: ExecutionJob) -> None:
        job.status = ExecutionJobStatus.RUNNING
        if job.started_at is None:
            job.started_at = datetime.now(UTC)
        self._session.flush()

    def mark_completed(self, job: ExecutionJob) -> None:
        job.status = ExecutionJobStatus.COMPLETED
        job.completed_at = datetime.now(UTC)
        self._session.flush()

    def mark_partially_completed(self, job: ExecutionJob) -> None:
        job.status = ExecutionJobStatus.PARTIALLY_COMPLETED
        job.completed_at = datetime.now(UTC)
        self._session.flush()

    def mark_failed(self, job: ExecutionJob, *, error: str) -> None:
        job.status = ExecutionJobStatus.FAILED
        job.error = error[:2048]
        job.completed_at = datetime.now(UTC)
        self._session.flush()

    def mark_cancelled(self, job: ExecutionJob) -> None:
        job.status = ExecutionJobStatus.CANCELLED
        job.completed_at = datetime.now(UTC)
        self._session.flush()

    def mark_paused(self, job: ExecutionJob) -> None:
        job.status = ExecutionJobStatus.PAUSED
        job.pause_requested = False
        self._session.flush()

    def request_cancel(self, job: ExecutionJob) -> None:
        job.cancel_requested = True
        self._session.flush()

    def request_pause(self, job: ExecutionJob) -> None:
        job.pause_requested = True
        self._session.flush()

    def resume(self, job: ExecutionJob) -> None:
        job.status = ExecutionJobStatus.PENDING
        job.pause_requested = False
        self._session.flush()

    def is_cancel_requested(self, execution_job_id: uuid.UUID) -> bool:
        """Column-only query, not an entity fetch — same identity-map
        staleness reasoning as every prior job's cancellation check."""
        result = (
            self._session.query(ExecutionJob.cancel_requested)
            .filter(ExecutionJob.id == execution_job_id)
            .scalar()
        )
        return bool(result)

    def is_pause_requested(self, execution_job_id: uuid.UUID) -> bool:
        result = (
            self._session.query(ExecutionJob.pause_requested)
            .filter(ExecutionJob.id == execution_job_id)
            .scalar()
        )
        return bool(result)
