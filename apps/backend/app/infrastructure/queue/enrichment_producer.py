from uuid import UUID

from app.infrastructure.queue.celery_client import get_celery_client
from app.infrastructure.queue.correlation import correlation_headers

# Must match `worker.enrichment.run`, registered by
# `apps/worker/worker/tasks/enrichment.py`.
_ENRICHMENT_TASK_NAME = "worker.enrichment.run"


def enqueue_enrichment_job(enrichment_job_id: UUID) -> None:
    get_celery_client().send_task(
        _ENRICHMENT_TASK_NAME, args=[str(enrichment_job_id)], headers=correlation_headers()
    )
