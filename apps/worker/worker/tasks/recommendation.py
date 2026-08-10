import uuid

from sqlalchemy.orm import Session

from vault_shared.db.models import RecommendationJobStatus, WorkflowEventType
from vault_shared.db.repositories import RecommendationJobRepository
from vault_shared.db.session import get_session_factory
from vault_shared.workflow_events import fire_workflow_event
from worker.celery_app import celery_app
from worker.recommendation.recommendation_service import RecommendationService


@celery_app.task(name="worker.recommendation.run")
def run_recommendation(recommendation_job_id: str) -> None:
    """No retry policy, same reasoning as `worker.embedding.run` —
    `RecommendationService.run` has no external-connectivity dependency
    (it only reads already-stored data), so there's nothing a Celery-level
    retry would recover from that a fresh manual "refresh" wouldn't."""
    session = get_session_factory()()
    try:
        service = RecommendationService(session)
        service.run(uuid.UUID(recommendation_job_id))
        _fire_recommendation_generated_if_completed(session, recommendation_job_id)
    finally:
        session.close()


def _fire_recommendation_generated_if_completed(
    session: Session, recommendation_job_id: str
) -> None:
    """Phase 9's `recommendation_generated` event trigger — the simplest
    of the four wired this phase, since `RecommendationJob` is already
    organization-scoped (Phase 7, ADR-019), no connector→organization
    resolution needed unlike scan/enrichment. Skipped for a failed run."""
    jobs = RecommendationJobRepository(session)
    job = jobs.get_by_id(uuid.UUID(recommendation_job_id))
    if job is None or job.status != RecommendationJobStatus.COMPLETED:
        return

    def _enqueue(workflow_execution_id: uuid.UUID) -> None:
        celery_app.send_task("worker.workflow.run", args=[str(workflow_execution_id)])

    fire_workflow_event(
        session,
        organization_id=job.organization_id,
        event_type=WorkflowEventType.RECOMMENDATION_GENERATED,
        payload={"recommendation_job_id": str(job.id)},
        enqueue_workflow_execution=_enqueue,
    )
