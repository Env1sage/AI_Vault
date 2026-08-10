import uuid

from croniter import croniter
from sqlalchemy.orm import Session

from vault_shared import NotFoundError, ValidationError
from vault_shared.db.models import WorkflowEventType, WorkflowTrigger, WorkflowTriggerType
from vault_shared.db.repositories import (
    AuditLogRepository,
    SchedulerJobRepository,
    WorkflowRepository,
    WorkflowTriggerRepository,
)
from vault_shared.scheduling import next_cron_run

_VALID_EVENT_TYPES = {member.value for member in WorkflowEventType}


class WorkflowTriggerService:
    """The Trigger Engine's CRUD surface (Phase 9 spec: Scheduled/Event/
    Manual triggers). A `SCHEDULED` trigger gets a companion `SchedulerJob`
    row with its first `next_run_at` computed via `croniter`; the periodic
    scheduler sweep (`worker.workflow.scheduler_service`) is what actually
    advances it thereafter. `EVENT`/`MANUAL` triggers need no scheduler
    bookkeeping at all."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._workflows = WorkflowRepository(db)
        self._triggers = WorkflowTriggerRepository(db)
        self._scheduler_jobs = SchedulerJobRepository(db)
        self._audit_logs = AuditLogRepository(db)

    def create(
        self,
        workflow_id: uuid.UUID,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        trigger_type: str,
        config: dict,
    ) -> WorkflowTrigger:
        workflow = self._workflows.get_owned(workflow_id, organization_id=organization_id)
        if workflow is None:
            raise NotFoundError("Workflow not found.")

        if trigger_type == WorkflowTriggerType.SCHEDULED:
            cron = config.get("cron")
            if not cron or not croniter.is_valid(cron):
                raise ValidationError("A scheduled trigger needs a valid cron expression.")
        elif trigger_type == WorkflowTriggerType.EVENT:
            event_type = config.get("event_type")
            if event_type not in _VALID_EVENT_TYPES:
                raise ValidationError(f"Unknown event type: {event_type}")
        elif trigger_type != WorkflowTriggerType.MANUAL:
            raise ValidationError(f"Unknown trigger type: {trigger_type}")

        trigger = self._triggers.create(
            workflow_id=workflow_id, trigger_type=trigger_type, config=config
        )
        if trigger_type == WorkflowTriggerType.SCHEDULED:
            next_run_at = next_cron_run(config["cron"])
            self._scheduler_jobs.upsert_for_trigger(trigger.id, next_run_at=next_run_at)

        self._audit_logs.record(
            event_type="workflow_trigger_created",
            organization_id=organization_id,
            user_id=user_id,
            metadata={"workflow_id": str(workflow_id), "trigger_type": trigger_type},
        )
        self._db.commit()
        return trigger

    def list_for_workflow(
        self, workflow_id: uuid.UUID, *, organization_id: uuid.UUID
    ) -> list[WorkflowTrigger]:
        workflow = self._workflows.get_owned(workflow_id, organization_id=organization_id)
        if workflow is None:
            raise NotFoundError("Workflow not found.")
        return self._triggers.list_for_workflow(workflow_id)

    def set_enabled(
        self,
        workflow_trigger_id: uuid.UUID,
        *,
        workflow_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        enabled: bool,
    ) -> WorkflowTrigger:
        workflow = self._workflows.get_owned(workflow_id, organization_id=organization_id)
        if workflow is None:
            raise NotFoundError("Workflow not found.")
        trigger = self._triggers.get_owned(workflow_trigger_id, workflow_id=workflow_id)
        if trigger is None:
            raise NotFoundError("Workflow trigger not found.")

        self._triggers.set_enabled(trigger, enabled=enabled)
        self._audit_logs.record(
            event_type="workflow_trigger_enabled" if enabled else "workflow_trigger_disabled",
            organization_id=organization_id,
            user_id=user_id,
            metadata={"workflow_trigger_id": str(trigger.id)},
        )
        self._db.commit()
        return trigger
