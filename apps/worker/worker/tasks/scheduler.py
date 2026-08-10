from vault_shared.db.session import get_session_factory
from worker.celery_app import celery_app
from worker.workflow.scheduler_service import SchedulerService


@celery_app.task(name="worker.scheduler.sweep")
def sweep_due_triggers() -> None:
    """Periodic entry point (see `celery_app.py`'s `beat_schedule`) —
    claims and fires every due scheduled workflow trigger. Safe to run
    concurrently with itself (the claim step is atomic) and safe to skip
    a tick entirely (nothing here assumes exactly-once-per-minute)."""
    session = get_session_factory()()
    try:
        SchedulerService(session).run_due()
    finally:
        session.close()
