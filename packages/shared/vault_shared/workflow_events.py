import uuid
from collections.abc import Callable

from sqlalchemy.orm import Session

from vault_shared.db.models import WorkflowStatus, WorkflowTriggerType
from vault_shared.db.repositories import (
    AuditLogRepository,
    WorkflowExecutionRepository,
    WorkflowRepository,
    WorkflowTriggerRepository,
    WorkflowVersionRepository,
)


def fire_workflow_event(
    db: Session,
    *,
    organization_id: uuid.UUID,
    event_type: str,
    payload: dict,
    enqueue_workflow_execution: Callable[[uuid.UUID], None],
) -> int:
    """Starts a fresh `WorkflowExecution` for every enabled `EVENT`
    trigger in this organization matching `event_type` (Phase 9's Event
    Triggers: scan/enrichment completed, recommendation generated,
    connector reconnected). Called from both `apps/worker` (the scan/
    enrichment/recommendation completion chains) and `apps/backend` (a
    connector reconnecting) — lives in `packages/shared` for the same
    reason `ExecutionPlanService`/`ApprovalService` do (ADR-021); the
    enqueue callback is injected so this module never imports either
    app's Celery wiring directly. Silently skips a trigger whose workflow
    is paused/disabled, has no published version, or already has a run in
    progress — an event firing is best-effort, not a queued-forever
    guarantee; the next occurrence of the same event will try again.
    Returns how many executions were actually started, for callers that
    want to log it."""
    triggers_repo = WorkflowTriggerRepository(db)
    workflows_repo = WorkflowRepository(db)
    versions_repo = WorkflowVersionRepository(db)
    executions_repo = WorkflowExecutionRepository(db)
    audit_logs = AuditLogRepository(db)

    triggers = triggers_repo.list_enabled_by_event_type(
        organization_id=organization_id, event_type=event_type
    )
    fired = 0
    for trigger in triggers:
        workflow = workflows_repo.get_by_id(trigger.workflow_id)
        if workflow is None or workflow.status != WorkflowStatus.ACTIVE:
            continue
        published = versions_repo.get_published(workflow.id)
        if published is None:
            continue
        if executions_repo.has_active_execution_for_workflow(workflow.id):
            continue

        execution = executions_repo.create(
            workflow_id=workflow.id,
            workflow_version_id=published.id,
            organization_id=organization_id,
            trigger_type=WorkflowTriggerType.EVENT,
            trigger_context={"event_type": event_type, **payload},
        )
        audit_logs.record(
            event_type="workflow_triggered_by_event",
            organization_id=organization_id,
            metadata={
                "workflow_id": str(workflow.id),
                "workflow_execution_id": str(execution.id),
                "source_event": event_type,
            },
        )
        db.commit()
        enqueue_workflow_execution(execution.id)
        fired += 1
    return fired
