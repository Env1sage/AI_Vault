import uuid

from sqlalchemy.orm import Session

from vault_shared.ai_gateway import get_ai_gateway
from vault_shared.db.models import EmbeddingJobStatus, RecommendationTrigger
from vault_shared.db.repositories import (
    EmbeddingJobRepository,
    RecommendationJobRepository,
    StorageConnectorRepository,
)
from vault_shared.db.session import get_session_factory
from worker.celery_app import celery_app
from worker.embedding.embedding_service import EmbeddingService
from worker.tasks.recommendation import run_recommendation


@celery_app.task(name="worker.embedding.run")
def run_embedding(embedding_job_id: str) -> None:
    """No retry policy, unlike `worker.scan.run`/`worker.enrichment.run` —
    `EmbeddingService.run` has no `DependencyUnavailableError` branch to
    retry around, since the default embedding provider is fully local and
    offline. See `EmbeddingService`'s docstring."""
    session = get_session_factory()()
    try:
        service = EmbeddingService(session, ai_gateway=get_ai_gateway())
        service.run(uuid.UUID(embedding_job_id))
        _enqueue_recommendation_if_embedding_completed(session, embedding_job_id)
    finally:
        session.close()


def _enqueue_recommendation_if_embedding_completed(session: Session, embedding_job_id: str) -> None:
    """Handbook's Architecture Impact: AI Intelligence Engine →
    Recommendation Engine (Phase 7). Mirrors `worker.tasks.enrichment.
    _enqueue_embedding_if_enrichment_completed`, with one difference: a
    `RecommendationJob` is organization-scoped, not connector-scoped (the
    Recommendation Engine and dashboard reason about an org's storage as a
    whole, potentially across multiple connectors), so this resolves the
    completed embedding job's connector back to its organization first."""
    embedding_jobs = EmbeddingJobRepository(session)
    embedding_job = embedding_jobs.get_by_id(uuid.UUID(embedding_job_id))
    if embedding_job is None or embedding_job.status != EmbeddingJobStatus.COMPLETED:
        return

    connector = StorageConnectorRepository(session).get_by_id(embedding_job.connector_id)
    if connector is None:
        return

    recommendation_jobs = RecommendationJobRepository(session)
    if recommendation_jobs.has_active_job(connector.organization_id):
        return

    recommendation_job = recommendation_jobs.create(
        organization_id=connector.organization_id,
        triggered_by=RecommendationTrigger.EMBEDDING_COMPLETED,
        triggered_by_user_id=None,
    )
    session.commit()
    run_recommendation.delay(str(recommendation_job.id))
