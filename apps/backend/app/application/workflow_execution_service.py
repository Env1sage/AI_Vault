import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.infrastructure.queue.workflow_producer import enqueue_workflow_execution
from vault_shared import ConflictError, NotFoundError
from vault_shared.db.models import (
    WorkflowExecution,
    WorkflowExecutionStatus,
    WorkflowNodeExecution,
    WorkflowStatus,
    WorkflowTriggerType,
)
from vault_shared.db.repositories import (
    AuditLogRepository,
    WorkflowExecutionRepository,
    WorkflowNodeExecutionRepository,
    WorkflowRepository,
    WorkflowVersionRepository,
)

_CANCELLABLE_STATUSES = (
    WorkflowExecutionStatus.PENDING,
    WorkflowExecutionStatus.RUNNING,
    WorkflowExecutionStatus.PAUSED,
)


@dataclass(frozen=True)
class WorkflowExecutionDetail:
    execution: WorkflowExecution
    node_executions: list[WorkflowNodeExecution]


class WorkflowExecutionService:
    """Read/control surface for `WorkflowExecution`s (Phase 9's Workflow
    Execution History + manual trigger) — mirrors `ExecutionJobService`'s
    role exactly: every mutating node this service's `trigger_manual`
    eventually causes to run happens in the worker, never here. This class
    only ever flips cooperative flags the worker checks between nodes, or
    enqueues a fresh run."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._workflows = WorkflowRepository(db)
        self._versions = WorkflowVersionRepository(db)
        self._executions = WorkflowExecutionRepository(db)
        self._node_executions = WorkflowNodeExecutionRepository(db)
        self._audit_logs = AuditLogRepository(db)

    def get_owned(
        self, workflow_execution_id: uuid.UUID, *, organization_id: uuid.UUID
    ) -> WorkflowExecution:
        execution = self._executions.get_owned(
            workflow_execution_id, organization_id=organization_id
        )
        if execution is None:
            raise NotFoundError("Workflow execution not found.")
        return execution

    def get_detail(
        self, workflow_execution_id: uuid.UUID, *, organization_id: uuid.UUID
    ) -> WorkflowExecutionDetail:
        execution = self.get_owned(workflow_execution_id, organization_id=organization_id)
        return WorkflowExecutionDetail(
            execution=execution,
            node_executions=self._node_executions.list_for_execution(execution.id),
        )

    def list_for_organization(
        self, organization_id: uuid.UUID, *, status: str | None = None
    ) -> list[WorkflowExecution]:
        return self._executions.list_for_organization(organization_id, status=status)

    def list_for_workflow(
        self, workflow_id: uuid.UUID, *, organization_id: uuid.UUID
    ) -> list[WorkflowExecution]:
        workflow = self._workflows.get_owned(workflow_id, organization_id=organization_id)
        if workflow is None:
            raise NotFoundError("Workflow not found.")
        return self._executions.list_for_workflow(workflow_id)

    def trigger_manual(
        self, workflow_id: uuid.UUID, *, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkflowExecution:
        workflow = self._workflows.get_owned(workflow_id, organization_id=organization_id)
        if workflow is None:
            raise NotFoundError("Workflow not found.")
        if workflow.status != WorkflowStatus.ACTIVE:
            raise ConflictError(f"Cannot trigger a workflow that is {workflow.status}.")

        published = self._versions.get_published(workflow_id)
        if published is None:
            raise ConflictError("This workflow has no published version to run.")
        if self._executions.has_active_execution_for_workflow(workflow_id):
            raise ConflictError("Another run is already in progress for this workflow.")

        execution = self._executions.create(
            workflow_id=workflow.id,
            workflow_version_id=published.id,
            organization_id=organization_id,
            trigger_type=WorkflowTriggerType.MANUAL,
            trigger_context={},
            triggered_by_user_id=user_id,
        )
        self._audit_logs.record(
            event_type="workflow_triggered_manually",
            organization_id=organization_id,
            user_id=user_id,
            metadata={"workflow_id": str(workflow_id), "workflow_execution_id": str(execution.id)},
        )
        self._db.commit()
        enqueue_workflow_execution(execution.id)
        return execution

    def cancel(
        self, execution: WorkflowExecution, *, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkflowExecution:
        if execution.status not in _CANCELLABLE_STATUSES:
            raise ConflictError(f"Cannot cancel a run that is already {execution.status}.")
        self._executions.request_cancel(execution)
        self._record(
            execution,
            organization_id=organization_id,
            user_id=user_id,
            event_type="workflow_cancel_requested",
        )
        return execution

    def pause(
        self, execution: WorkflowExecution, *, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkflowExecution:
        if execution.status != WorkflowExecutionStatus.RUNNING:
            raise ConflictError("Only a running workflow execution can be paused.")
        self._executions.request_pause(execution)
        self._record(
            execution,
            organization_id=organization_id,
            user_id=user_id,
            event_type="workflow_pause_requested",
        )
        return execution

    def resume(
        self, execution: WorkflowExecution, *, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkflowExecution:
        if execution.status != WorkflowExecutionStatus.PAUSED:
            raise ConflictError("Only a paused workflow execution can be resumed.")
        self._executions.resume(execution)
        self._record(
            execution,
            organization_id=organization_id,
            user_id=user_id,
            event_type="workflow_resumed",
        )
        self._db.commit()
        enqueue_workflow_execution(execution.id)
        return execution

    def _record(
        self,
        execution: WorkflowExecution,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        event_type: str,
    ) -> None:
        self._audit_logs.record(
            event_type=event_type,
            organization_id=organization_id,
            user_id=user_id,
            metadata={"workflow_execution_id": str(execution.id)},
        )
        self._db.commit()
