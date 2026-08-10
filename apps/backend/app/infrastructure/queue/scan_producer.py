from uuid import UUID

from app.infrastructure.queue.celery_client import get_celery_client
from app.infrastructure.queue.correlation import correlation_headers

# Must match `worker.scan.run`, registered by `apps/worker/worker/tasks/scan.py`.
_SCAN_TASK_NAME = "worker.scan.run"


def enqueue_scan_job(scan_job_id: UUID) -> None:
    get_celery_client().send_task(
        _SCAN_TASK_NAME, args=[str(scan_job_id)], headers=correlation_headers()
    )
