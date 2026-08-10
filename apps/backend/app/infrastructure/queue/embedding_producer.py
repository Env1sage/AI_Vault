from uuid import UUID

from app.infrastructure.queue.celery_client import get_celery_client
from app.infrastructure.queue.correlation import correlation_headers

# Must match `worker.embedding.run`, registered by
# `apps/worker/worker/tasks/embedding.py`.
_EMBEDDING_TASK_NAME = "worker.embedding.run"


def enqueue_embedding_job(embedding_job_id: UUID) -> None:
    get_celery_client().send_task(
        _EMBEDDING_TASK_NAME, args=[str(embedding_job_id)], headers=correlation_headers()
    )
