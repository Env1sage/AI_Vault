from uuid import UUID

from app.infrastructure.queue.celery_client import get_celery_client
from app.infrastructure.queue.correlation import correlation_headers

# Must match `worker.execution.run`, registered by
# `apps/worker/worker/tasks/execution.py`.
_EXECUTION_TASK_NAME = "worker.execution.run"


def enqueue_execution_job(execution_job_id: UUID) -> None:
    get_celery_client().send_task(
        _EXECUTION_TASK_NAME, args=[str(execution_job_id)], headers=correlation_headers()
    )
