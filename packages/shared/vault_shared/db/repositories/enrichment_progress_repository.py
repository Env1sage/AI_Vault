import uuid

from sqlalchemy import update
from sqlalchemy.orm import Session

from vault_shared.db.models import EnrichmentProgress


class EnrichmentProgressRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_for_job(self, enrichment_job_id: uuid.UUID) -> EnrichmentProgress:
        progress = EnrichmentProgress(enrichment_job_id=enrichment_job_id)
        self._session.add(progress)
        self._session.flush()
        return progress

    def get_for_job(self, enrichment_job_id: uuid.UUID) -> EnrichmentProgress | None:
        return self._session.get(EnrichmentProgress, enrichment_job_id)

    def set_files_pending(self, enrichment_job_id: uuid.UUID, count: int) -> None:
        self._session.execute(
            update(EnrichmentProgress)
            .where(EnrichmentProgress.enrichment_job_id == enrichment_job_id)
            .values(files_pending=count)
        )

    def set_current_file(self, enrichment_job_id: uuid.UUID, name: str | None) -> None:
        self._session.execute(
            update(EnrichmentProgress)
            .where(EnrichmentProgress.enrichment_job_id == enrichment_job_id)
            .values(current_file_name=name)
        )

    def increment_processed(self, enrichment_job_id: uuid.UUID) -> None:
        self._session.execute(
            update(EnrichmentProgress)
            .where(EnrichmentProgress.enrichment_job_id == enrichment_job_id)
            .values(files_processed=EnrichmentProgress.files_processed + 1)
        )

    def increment_failed(self, enrichment_job_id: uuid.UUID) -> None:
        self._session.execute(
            update(EnrichmentProgress)
            .where(EnrichmentProgress.enrichment_job_id == enrichment_job_id)
            .values(files_failed=EnrichmentProgress.files_failed + 1)
        )
