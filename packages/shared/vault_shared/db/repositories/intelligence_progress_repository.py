import uuid

from sqlalchemy import update
from sqlalchemy.orm import Session

from vault_shared.db.models import IntelligenceProgress


class IntelligenceProgressRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_for_job(self, intelligence_job_id: uuid.UUID) -> IntelligenceProgress:
        progress = IntelligenceProgress(intelligence_job_id=intelligence_job_id)
        self._session.add(progress)
        self._session.flush()
        return progress

    def get_for_job(self, intelligence_job_id: uuid.UUID) -> IntelligenceProgress | None:
        return self._session.get(IntelligenceProgress, intelligence_job_id)

    def set_files_pending(self, intelligence_job_id: uuid.UUID, count: int) -> None:
        self._session.execute(
            update(IntelligenceProgress)
            .where(IntelligenceProgress.intelligence_job_id == intelligence_job_id)
            .values(files_pending=count)
        )

    def set_current_file(self, intelligence_job_id: uuid.UUID, name: str | None) -> None:
        self._session.execute(
            update(IntelligenceProgress)
            .where(IntelligenceProgress.intelligence_job_id == intelligence_job_id)
            .values(current_file_name=name)
        )

    def increment_processed(self, intelligence_job_id: uuid.UUID) -> None:
        self._session.execute(
            update(IntelligenceProgress)
            .where(IntelligenceProgress.intelligence_job_id == intelligence_job_id)
            .values(files_processed=IntelligenceProgress.files_processed + 1)
        )

    def increment_failed(self, intelligence_job_id: uuid.UUID) -> None:
        self._session.execute(
            update(IntelligenceProgress)
            .where(IntelligenceProgress.intelligence_job_id == intelligence_job_id)
            .values(files_failed=IntelligenceProgress.files_failed + 1)
        )
