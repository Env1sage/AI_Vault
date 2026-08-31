import uuid

from celery import Task

from vault_shared import DependencyUnavailableError, get_logger
from vault_shared.ai_gateway import get_ai_gateway
from vault_shared.db.repositories import IntelligenceJobRepository
from vault_shared.db.session import get_session_factory
from worker.celery_app import celery_app
from worker.intelligence.intelligence_service import IntelligenceService

logger = get_logger("worker.tasks.intelligence")

# Same retry policy as worker.tasks.enrichment.run_enrichment — this task,
# unlike embedding's, has a real external-network failure mode (a hosted
# LLM call), so a whole-job retry on DependencyUnavailableError applies
# here too.
_MAX_RETRIES = 5
_RETRY_BACKOFF_SECONDS = 30


@celery_app.task(
    name="worker.intelligence.run",
    bind=True,
    max_retries=_MAX_RETRIES,
    default_retry_delay=_RETRY_BACKOFF_SECONDS,
)
def run_intelligence(self: Task, intelligence_job_id: str) -> None:
    """No downstream chain trigger — nothing currently depends on an
    `IntelligenceJob` completing (see `IntelligenceJob`'s docstring for
    the documented, non-blocking race with `RecommendationJob`)."""
    session = get_session_factory()()
    try:
        service = IntelligenceService(session, ai_gateway=get_ai_gateway())
        service.run(uuid.UUID(intelligence_job_id))
    except DependencyUnavailableError as exc:
        if self.request.retries >= self.max_retries:
            logger.error(
                "intelligence_task_retries_exhausted",
                extra={
                    "intelligence_job_id": intelligence_job_id,
                    "attempt": self.request.retries,
                },
            )
            jobs = IntelligenceJobRepository(session)
            job = jobs.get_by_id(uuid.UUID(intelligence_job_id))
            if job is not None:
                jobs.mark_failed(job, error=f"Completion provider unavailable after retries: {exc}")
                session.commit()
            return
        logger.warning(
            "intelligence_task_retrying_after_dependency_error",
            extra={"intelligence_job_id": intelligence_job_id, "attempt": self.request.retries},
        )
        raise self.retry(exc=exc) from exc
    finally:
        session.close()
