from sqlalchemy.orm import Session

from vault_shared import get_logger
from vault_shared.db.models import SchedulerJob, WorkflowStatus, WorkflowTriggerType
from vault_shared.db.repositories import (
    AuditLogRepository,
    SchedulerJobRepository,
    WorkflowExecutionRepository,
    WorkflowRepository,
    WorkflowTriggerRepository,
    WorkflowVersionRepository,
)
from vault_shared.scheduling import next_cron_run

logger = get_logger("worker.workflow.scheduler_service")


class SchedulerService:
    """The Trigger Engine's scheduled-trigger sweep (Phase 9 spec) — a
    periodic Celery Beat task (`worker.scheduler.sweep`, registered in
    `celery_app.py`'s `beat_schedule`) calls `run_due()` roughly once a
    minute. Claims every due `SchedulerJob` atomically
    (`SchedulerJobRepository.claim_due` — the mechanism that prevents the
    phase spec's named "trigger duplication" failure mode under more than
    one Beat process), starts a fresh `WorkflowExecution` for each one
    whose workflow is still active and has a published version, and
    recomputes/persists the trigger's next cron occurrence — a claimed row
    that were never rescheduled would silently stop firing forever, so
    this step is not optional cleanup, it always runs even when firing
    itself was skipped or failed."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._scheduler_jobs = SchedulerJobRepository(db)
        self._triggers = WorkflowTriggerRepository(db)
        self._workflows = WorkflowRepository(db)
        self._versions = WorkflowVersionRepository(db)
        self._executions = WorkflowExecutionRepository(db)
        self._audit_logs = AuditLogRepository(db)

    def run_due(self) -> int:
        claimed = self._scheduler_jobs.claim_due()
        fired = 0
        for scheduler_job in claimed:
            try:
                if self._fire(scheduler_job):
                    fired += 1
            except Exception:  # noqa: BLE001 - one trigger's failure must not stop the sweep
                logger.exception(
                    "scheduler_job_fire_failed", extra={"scheduler_job_id": str(scheduler_job.id)}
                )
                self._db.rollback()
            finally:
                self._reschedule(scheduler_job)
        return fired

    def _fire(self, scheduler_job: SchedulerJob) -> bool:
        trigger = self._triggers.get_by_id(scheduler_job.workflow_trigger_id)
        if trigger is None or not trigger.enabled:
            return False
        workflow = self._workflows.get_by_id(trigger.workflow_id)
        if workflow is None or workflow.status != WorkflowStatus.ACTIVE:
            return False
        published = self._versions.get_published(workflow.id)
        if published is None:
            return False
        if self._executions.has_active_execution_for_workflow(workflow.id):
            logger.info(
                "scheduler_skipped_active_execution", extra={"workflow_id": str(workflow.id)}
            )
            return False

        execution = self._executions.create(
            workflow_id=workflow.id,
            workflow_version_id=published.id,
            organization_id=workflow.organization_id,
            trigger_type=WorkflowTriggerType.SCHEDULED,
            trigger_context={"workflow_trigger_id": str(trigger.id)},
        )
        self._audit_logs.record(
            event_type="workflow_triggered_by_schedule",
            organization_id=workflow.organization_id,
            metadata={"workflow_id": str(workflow.id), "workflow_execution_id": str(execution.id)},
        )
        self._scheduler_jobs.record_run(scheduler_job, workflow_execution_id=execution.id)
        self._db.commit()

        from worker.celery_app import celery_app

        celery_app.send_task("worker.workflow.run", args=[str(execution.id)])
        return True

    def _reschedule(self, scheduler_job: SchedulerJob) -> None:
        trigger = self._triggers.get_by_id(scheduler_job.workflow_trigger_id)
        cron = trigger.config.get("cron") if trigger else None
        if trigger is None or not trigger.enabled or not cron:
            self._db.commit()
            return
        next_run_at = next_cron_run(cron)
        self._scheduler_jobs.upsert_for_trigger(trigger.id, next_run_at=next_run_at)
        self._db.commit()
