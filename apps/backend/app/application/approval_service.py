"""Thin re-export — ApprovalService moved to packages/shared in Phase 9
(ADR-021) so apps/worker's EXECUTE_ACTION workflow node can call
auto_decide_via_policy() directly, not just this backend's own
POST /v1/approvals/{id}/decide endpoint. See
vault_shared.execution.approval_service for the real implementation."""

from sqlalchemy.orm import Session

from app.infrastructure.queue.execution_producer import enqueue_execution_job
from app.infrastructure.queue.workflow_producer import enqueue_workflow_execution
from vault_shared.execution import ApprovalService as _SharedApprovalService


class ApprovalService(_SharedApprovalService):
    def __init__(self, db: Session) -> None:
        super().__init__(
            db,
            enqueue_execution_job=enqueue_execution_job,
            enqueue_workflow_execution=enqueue_workflow_execution,
        )
