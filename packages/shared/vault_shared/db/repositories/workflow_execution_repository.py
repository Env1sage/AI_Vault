import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from vault_shared.db.models import WorkflowExecution, WorkflowExecutionStatus


class WorkflowExecutionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        workflow_id: uuid.UUID,
        workflow_version_id: uuid.UUID,
        organization_id: uuid.UUID,
        trigger_type: str,
        trigger_context: dict,
        triggered_by_user_id: uuid.UUID | None = None,
    ) -> WorkflowExecution:
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            workflow_version_id=workflow_version_id,
            organization_id=organization_id,
            trigger_type=trigger_type,
            trigger_context=trigger_context,
            triggered_by_user_id=triggered_by_user_id,
        )
        self._session.add(execution)
        self._session.flush()
        return execution

    def get_by_id(self, workflow_execution_id: uuid.UUID) -> WorkflowExecution | None:
        return self._session.get(WorkflowExecution, workflow_execution_id)

    def get_owned(
        self, workflow_execution_id: uuid.UUID, *, organization_id: uuid.UUID
    ) -> WorkflowExecution | None:
        return (
            self._session.query(WorkflowExecution)
            .filter_by(id=workflow_execution_id, organization_id=organization_id)
            .first()
        )

    def list_for_workflow(self, workflow_id: uuid.UUID) -> list[WorkflowExecution]:
        return (
            self._session.query(WorkflowExecution)
            .filter_by(workflow_id=workflow_id)
            .order_by(WorkflowExecution.created_at.desc())
            .all()
        )

    def list_for_organization(
        self,
        organization_id: uuid.UUID,
        *,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WorkflowExecution]:
        query = self._session.query(WorkflowExecution).filter_by(organization_id=organization_id)
        if status is not None:
            query = query.filter(WorkflowExecution.status == status)
        return (
            query.order_by(WorkflowExecution.created_at.desc()).limit(limit).offset(offset).all()
        )

    def has_active_execution_for_workflow(self, workflow_id: uuid.UUID) -> bool:
        active_statuses = [
            WorkflowExecutionStatus.PENDING,
            WorkflowExecutionStatus.RUNNING,
            WorkflowExecutionStatus.PAUSED,
        ]
        return (
            self._session.query(WorkflowExecution)
            .filter(
                WorkflowExecution.workflow_id == workflow_id,
                WorkflowExecution.status.in_(active_statuses),
            )
            .first()
            is not None
        )

    def set_current_node(self, execution: WorkflowExecution, *, node_id: uuid.UUID | None) -> None:
        execution.current_node_id = node_id
        self._session.flush()

    def set_context(self, execution: WorkflowExecution, *, context: dict) -> None:
        execution.context = context
        self._session.flush()

    def mark_running(self, execution: WorkflowExecution) -> None:
        execution.status = WorkflowExecutionStatus.RUNNING
        if execution.started_at is None:
            execution.started_at = datetime.now(UTC)
        self._session.flush()

    def mark_paused(self, execution: WorkflowExecution) -> None:
        execution.status = WorkflowExecutionStatus.PAUSED
        execution.pause_requested = False
        self._session.flush()

    def mark_completed(self, execution: WorkflowExecution) -> None:
        execution.status = WorkflowExecutionStatus.COMPLETED
        execution.completed_at = datetime.now(UTC)
        self._session.flush()

    def mark_failed(self, execution: WorkflowExecution, *, error: str) -> None:
        execution.status = WorkflowExecutionStatus.FAILED
        execution.error = error[:2048]
        execution.completed_at = datetime.now(UTC)
        self._session.flush()

    def mark_cancelled(self, execution: WorkflowExecution) -> None:
        execution.status = WorkflowExecutionStatus.CANCELLED
        execution.completed_at = datetime.now(UTC)
        self._session.flush()

    def request_cancel(self, execution: WorkflowExecution) -> None:
        execution.cancel_requested = True
        self._session.flush()

    def request_pause(self, execution: WorkflowExecution) -> None:
        execution.pause_requested = True
        self._session.flush()

    def resume(self, execution: WorkflowExecution) -> None:
        execution.status = WorkflowExecutionStatus.PENDING
        execution.pause_requested = False
        self._session.flush()

    def is_cancel_requested(self, workflow_execution_id: uuid.UUID) -> bool:
        result = (
            self._session.query(WorkflowExecution.cancel_requested)
            .filter(WorkflowExecution.id == workflow_execution_id)
            .scalar()
        )
        return bool(result)

    def is_pause_requested(self, workflow_execution_id: uuid.UUID) -> bool:
        result = (
            self._session.query(WorkflowExecution.pause_requested)
            .filter(WorkflowExecution.id == workflow_execution_id)
            .scalar()
        )
        return bool(result)
