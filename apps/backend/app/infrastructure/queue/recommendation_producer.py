from uuid import UUID

from app.infrastructure.queue.celery_client import get_celery_client
from app.infrastructure.queue.correlation import correlation_headers

# Must match `worker.recommendation.run`, registered by
# `apps/worker/worker/tasks/recommendation.py`.
_RECOMMENDATION_TASK_NAME = "worker.recommendation.run"


def enqueue_recommendation_job(recommendation_job_id: UUID) -> None:
    get_celery_client().send_task(
        _RECOMMENDATION_TASK_NAME,
        args=[str(recommendation_job_id)],
        headers=correlation_headers(),
    )
