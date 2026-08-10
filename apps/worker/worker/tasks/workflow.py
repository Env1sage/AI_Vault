import uuid

from vault_shared.db.session import get_session_factory
from vault_shared.settings import get_settings
from worker.celery_app import celery_app
from worker.workflow.execution_service import WorkflowExecutionService


@celery_app.task(
    name="worker.workflow.run", soft_time_limit=get_settings().execution_timeout_seconds
)
def run_workflow(workflow_execution_id: str) -> None:
    """Starts a fresh run, resumes a paused one, or continues one waiting
    on a `DELAY` node's countdown — `WorkflowExecutionService.run()` reads
    `WorkflowExecution.current_node_id` and decides which case it is, so
    this task is always the same simple entry point regardless. No
    `self.retry(...)`, same reasoning as `worker.execution.run`: a node's
    own failure is already isolated inside the service (recorded on its
    `WorkflowNodeExecution`, never raised out to here) unless it's a
    genuine structural problem (missing node, missing workflow version),
    which is deliberately terminal rather than blindly retried."""
    session = get_session_factory()()
    try:
        service = WorkflowExecutionService(session)
        service.run(uuid.UUID(workflow_execution_id))
    finally:
        session.close()
