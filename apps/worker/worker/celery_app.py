from celery import Celery
from celery.signals import setup_logging

from vault_shared import configure_logging, get_settings

settings = get_settings()

celery_app = Celery(
    "vault_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "worker.tasks.health",
        "worker.tasks.scan",
        "worker.tasks.enrichment",
        "worker.tasks.embedding",
        "worker.tasks.recommendation",
        "worker.tasks.execution",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Redelivers a task if the worker process dies mid-execution rather than
    # silently dropping it — required for Handbook §8.15's "no lost job state".
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    broker_connection_retry_on_startup=True,
    worker_max_tasks_per_child=1000,
)


@setup_logging.connect
def _configure_worker_logging(**_: object) -> None:
    # Takes over Celery's own logging setup so every worker log line is the
    # same structured JSON format the backend emits (Handbook §26).
    configure_logging(settings.service_name, settings.log_level)
