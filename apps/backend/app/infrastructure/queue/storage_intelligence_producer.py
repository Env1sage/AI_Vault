from uuid import UUID

from app.infrastructure.queue.celery_client import get_celery_client
from app.infrastructure.queue.correlation import correlation_headers

# Must match `worker.storage_intelligence.run`, registered by
# `apps/worker/worker/tasks/storage_intelligence.py`.
_STORAGE_INTELLIGENCE_TASK_NAME = "worker.storage_intelligence.run"


def enqueue_storage_analysis_job(storage_analysis_job_id: UUID) -> None:
    get_celery_client().send_task(
        _STORAGE_INTELLIGENCE_TASK_NAME,
        args=[str(storage_analysis_job_id)],
        headers=correlation_headers(),
    )
