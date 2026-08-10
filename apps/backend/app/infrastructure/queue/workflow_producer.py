from uuid import UUID

from app.infrastructure.queue.celery_client import get_celery_client
from app.infrastructure.queue.correlation import correlation_headers

# Must match `worker.workflow.run`, registered by
# `apps/worker/worker/tasks/workflow.py`.
_WORKFLOW_TASK_NAME = "worker.workflow.run"


def enqueue_workflow_execution(workflow_execution_id: UUID) -> None:
    """Starts a fresh run, or resumes a `PAUSED` one — `WorkflowExecutionService.
    run()` in the worker picks up from `current_node_id` either way, so
    this producer never needs to know which case it is."""
    get_celery_client().send_task(
        _WORKFLOW_TASK_NAME, args=[str(workflow_execution_id)], headers=correlation_headers()
    )
