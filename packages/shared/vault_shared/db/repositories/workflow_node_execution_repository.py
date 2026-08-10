import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from vault_shared.db.models import WorkflowNodeExecution, WorkflowNodeExecutionStatus


class WorkflowNodeExecutionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self, *, workflow_execution_id: uuid.UUID, workflow_node_id: uuid.UUID
    ) -> WorkflowNodeExecution:
        node_execution = WorkflowNodeExecution(
            workflow_execution_id=workflow_execution_id,
            workflow_node_id=workflow_node_id,
            status=WorkflowNodeExecutionStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        self._session.add(node_execution)
        self._session.flush()
        return node_execution

    def get_by_id(self, workflow_node_execution_id: uuid.UUID) -> WorkflowNodeExecution | None:
        return self._session.get(WorkflowNodeExecution, workflow_node_execution_id)

    def get_for_execution_and_node(
        self, *, workflow_execution_id: uuid.UUID, workflow_node_id: uuid.UUID
    ) -> WorkflowNodeExecution | None:
        """The most recent execution record for this node within this run
        — used by the run loop to detect "have we already started/finished
        this node?" on a resume, rather than blindly re-running it (which
        would, e.g., create a second `ApprovalRequest` for an already-
        pending `APPROVAL` node)."""
        return (
            self._session.query(WorkflowNodeExecution)
            .filter_by(
                workflow_execution_id=workflow_execution_id, workflow_node_id=workflow_node_id
            )
            .order_by(WorkflowNodeExecution.created_at.desc())
            .first()
        )

    def list_for_execution(self, workflow_execution_id: uuid.UUID) -> list[WorkflowNodeExecution]:
        return (
            self._session.query(WorkflowNodeExecution)
            .filter_by(workflow_execution_id=workflow_execution_id)
            .order_by(WorkflowNodeExecution.created_at)
            .all()
        )

    def mark_completed(
        self, node_execution: WorkflowNodeExecution, *, output_context: dict
    ) -> None:
        node_execution.status = WorkflowNodeExecutionStatus.COMPLETED
        node_execution.output_context = output_context
        node_execution.completed_at = datetime.now(UTC)
        self._session.flush()

    def mark_skipped(self, node_execution: WorkflowNodeExecution, *, reason: str) -> None:
        node_execution.status = WorkflowNodeExecutionStatus.SKIPPED
        node_execution.output_context = {"reason": reason}
        node_execution.completed_at = datetime.now(UTC)
        self._session.flush()

    def mark_failed(self, node_execution: WorkflowNodeExecution, *, error: str) -> None:
        node_execution.status = WorkflowNodeExecutionStatus.FAILED
        node_execution.error = error[:2048]
        node_execution.completed_at = datetime.now(UTC)
        self._session.flush()

    def mark_waiting_approval(self, node_execution: WorkflowNodeExecution) -> None:
        node_execution.status = WorkflowNodeExecutionStatus.WAITING_APPROVAL
        self._session.flush()

    def mark_waiting_delay(self, node_execution: WorkflowNodeExecution, *, resume_at: str) -> None:
        node_execution.status = WorkflowNodeExecutionStatus.WAITING_DELAY
        node_execution.output_context = {"resume_at": resume_at}
        self._session.flush()
