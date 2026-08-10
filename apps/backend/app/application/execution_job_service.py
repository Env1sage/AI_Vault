import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.infrastructure.queue.execution_producer import enqueue_execution_job
from vault_shared import ConflictError, NotFoundError, get_settings
from vault_shared.db.models import ExecutionJob, ExecutionJobStatus, ExecutionResult
from vault_shared.db.repositories import (
    AuditLogRepository,
    ExecutionAuditRepository,
    ExecutionJobRepository,
    ExecutionPlanRepository,
    ExecutionResultRepository,
    RollbackRecordRepository,
)

_CANCELLABLE_STATUSES = (
    ExecutionJobStatus.PENDING,
    ExecutionJobStatus.RUNNING,
    ExecutionJobStatus.PAUSED,
)


@dataclass(frozen=True)
class ExecutionJobDetail:
    job: ExecutionJob
    results: list[ExecutionResult]


class ExecutionJobService:
    """Read/control surface for `ExecutionJob`s (Phase 8's Execution
    Queue: "Pause execution. Resume execution. Cancel pending jobs.") and
    the Rollback Framework's entry point. Every mutating Drive call this
    service triggers happens in the worker, never here — this class only
    ever flips cooperative flags the worker checks between steps, or
    enqueues a fresh job; see `ExecutionService` for the actual
    execution/rollback logic."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._jobs = ExecutionJobRepository(db)
        self._plans = ExecutionPlanRepository(db)
        self._results = ExecutionResultRepository(db)
        self._rollback_records = RollbackRecordRepository(db)
        self._execution_audits = ExecutionAuditRepository(db)
        self._audit_logs = AuditLogRepository(db)

    def get_owned(self, execution_job_id: uuid.UUID, *, organization_id: uuid.UUID) -> ExecutionJob:
        job = self._jobs.get_owned(execution_job_id, organization_id=organization_id)
        if job is None:
            raise NotFoundError("Execution job not found.")
        return job

    def get_detail(
        self, execution_job_id: uuid.UUID, *, organization_id: uuid.UUID
    ) -> ExecutionJobDetail:
        job = self.get_owned(execution_job_id, organization_id=organization_id)
        return ExecutionJobDetail(job=job, results=self._results.list_for_job(job.id))

    def list_for_organization(
        self, organization_id: uuid.UUID, *, status: str | None = None
    ) -> list[ExecutionJob]:
        return self._jobs.list_for_organization(organization_id, status=status)

    def cancel(
        self, job: ExecutionJob, *, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> ExecutionJob:
        if job.status not in _CANCELLABLE_STATUSES:
            raise ConflictError(f"Cannot cancel a job that is already {job.status}.")
        self._jobs.request_cancel(job)
        self._record(
            job,
            organization_id=organization_id,
            user_id=user_id,
            event_type="execution_cancel_requested",
        )
        return job

    def pause(
        self, job: ExecutionJob, *, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> ExecutionJob:
        if job.status != ExecutionJobStatus.RUNNING:
            raise ConflictError("Only a running job can be paused.")
        self._jobs.request_pause(job)
        self._record(
            job,
            organization_id=organization_id,
            user_id=user_id,
            event_type="execution_pause_requested",
        )
        return job

    def resume(
        self, job: ExecutionJob, *, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> ExecutionJob:
        if job.status != ExecutionJobStatus.PAUSED:
            raise ConflictError("Only a paused job can be resumed.")
        self._jobs.resume(job)
        self._record(
            job, organization_id=organization_id, user_id=user_id, event_type="execution_resumed"
        )
        self._db.commit()
        enqueue_execution_job(job.id)
        return job

    def trigger_rollback(
        self, execution_plan_id: uuid.UUID, *, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> ExecutionJob:
        settings = get_settings()
        if not settings.execution_rollback_enabled:
            raise ConflictError("Rollback is currently disabled for this deployment.")

        plan = self._plans.get_owned(execution_plan_id, organization_id=organization_id)
        if plan is None:
            raise NotFoundError("Execution plan not found.")
        if not plan.rollback_available:
            raise ConflictError("This plan does not support rollback.")
        if not self._rollback_records.list_rollbackable_for_plan(execution_plan_id):
            raise ConflictError("Nothing to roll back for this plan.")
        if self._jobs.has_active_job_for_plan(execution_plan_id):
            raise ConflictError(
                "Another execution or rollback is already in progress for this plan."
            )

        job = self._jobs.create(
            execution_plan_id=execution_plan_id,
            organization_id=organization_id,
            triggered_by_user_id=user_id,
            is_rollback=True,
        )
        self._execution_audits.record(
            organization_id=organization_id,
            execution_plan_id=execution_plan_id,
            execution_job_id=job.id,
            actor_user_id=user_id,
            event_type="execution_rollback_requested",
        )
        self._audit_logs.record(
            event_type="execution_rollback_requested",
            organization_id=organization_id,
            user_id=user_id,
            metadata={"execution_plan_id": str(execution_plan_id)},
        )
        self._db.commit()
        enqueue_execution_job(job.id)
        return job

    def _record(
        self, job: ExecutionJob, *, organization_id: uuid.UUID, user_id: uuid.UUID, event_type: str
    ) -> None:
        self._execution_audits.record(
            organization_id=organization_id,
            execution_plan_id=job.execution_plan_id,
            execution_job_id=job.id,
            actor_user_id=user_id,
            event_type=event_type,
        )
        self._audit_logs.record(
            event_type=event_type,
            organization_id=organization_id,
            user_id=user_id,
            metadata={"execution_job_id": str(job.id)},
        )
        self._db.commit()
