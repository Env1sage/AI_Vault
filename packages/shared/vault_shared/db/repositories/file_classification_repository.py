import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from vault_shared.db.models import FileClassification


class FileClassificationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_file_id(self, file_id: uuid.UUID) -> FileClassification | None:
        return self._session.get(FileClassification, file_id)

    def upsert(
        self,
        *,
        file_id: uuid.UUID,
        document_type: str,
        confidence: float,
        method: str,
        classified_at: datetime,
    ) -> FileClassification:
        classification = self.get_by_file_id(file_id)
        if classification is None:
            classification = FileClassification(file_id=file_id)
            self._session.add(classification)

        classification.document_type = document_type
        classification.confidence = confidence
        classification.method = method
        classification.classified_at = classified_at
        self._session.flush()
        return classification
