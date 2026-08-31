import uuid

from vault_shared.db.session import get_session_factory
from worker.celery_app import celery_app
from worker.storage_intelligence.storage_intelligence_service import StorageIntelligenceService


@celery_app.task(name="worker.storage_intelligence.run")
def run_storage_intelligence(storage_analysis_job_id: str) -> None:
    """No retry policy, same reasoning as `worker.recommendation.run` —
    `StorageIntelligenceService.run` has no external-connectivity
    dependency (it only reads already-stored data), so there's nothing a
    Celery-level retry would recover from that a fresh manual re-analysis
    wouldn't."""
    session = get_session_factory()()
    try:
        service = StorageIntelligenceService(session)
        service.run(uuid.UUID(storage_analysis_job_id))
    finally:
        session.close()
