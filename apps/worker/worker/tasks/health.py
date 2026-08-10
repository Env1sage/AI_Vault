from vault_shared import get_logger
from worker.celery_app import celery_app

logger = get_logger("worker.tasks.health")


@celery_app.task(name="worker.health.ping")
def ping() -> str:
    """Proves the queue round-trip works end to end (Phase 1 has no real
    business jobs yet — Storage Scanner jobs start in Phase 3/4)."""
    logger.info("health_ping_task_executed")
    return "pong"
