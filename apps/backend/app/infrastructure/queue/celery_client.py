from functools import lru_cache

from celery import Celery

from vault_shared import get_settings


@lru_cache
def get_celery_client() -> Celery:
    """A bare Celery client, shared by every queue producer in the backend
    (`scan_producer.py`, `enrichment_producer.py`) — the backend only ever
    calls `.send_task(name, ...)` by task-name string, never importing
    `apps/worker`'s task modules directly, so the two apps stay
    independently deployable (ADR-012)."""
    settings = get_settings()
    return Celery(
        "vault_backend_queue_producer", broker=settings.redis_url, backend=settings.redis_url
    )
