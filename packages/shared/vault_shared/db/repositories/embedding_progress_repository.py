import uuid

from sqlalchemy import update
from sqlalchemy.orm import Session

from vault_shared.db.models import EmbeddingProgress


class EmbeddingProgressRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_for_job(self, embedding_job_id: uuid.UUID) -> EmbeddingProgress:
        progress = EmbeddingProgress(embedding_job_id=embedding_job_id)
        self._session.add(progress)
        self._session.flush()
        return progress

    def get_for_job(self, embedding_job_id: uuid.UUID) -> EmbeddingProgress | None:
        return self._session.get(EmbeddingProgress, embedding_job_id)

    def set_files_pending(self, embedding_job_id: uuid.UUID, count: int) -> None:
        self._session.execute(
            update(EmbeddingProgress)
            .where(EmbeddingProgress.embedding_job_id == embedding_job_id)
            .values(files_pending=count)
        )

    def set_current_file(self, embedding_job_id: uuid.UUID, name: str | None) -> None:
        self._session.execute(
            update(EmbeddingProgress)
            .where(EmbeddingProgress.embedding_job_id == embedding_job_id)
            .values(current_file_name=name)
        )

    def increment_processed(self, embedding_job_id: uuid.UUID) -> None:
        self._session.execute(
            update(EmbeddingProgress)
            .where(EmbeddingProgress.embedding_job_id == embedding_job_id)
            .values(files_processed=EmbeddingProgress.files_processed + 1)
        )

    def increment_failed(self, embedding_job_id: uuid.UUID) -> None:
        self._session.execute(
            update(EmbeddingProgress)
            .where(EmbeddingProgress.embedding_job_id == embedding_job_id)
            .values(files_failed=EmbeddingProgress.files_failed + 1)
        )
