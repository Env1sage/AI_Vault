import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from vault_shared.db.models import FileIntelligence


class FileIntelligenceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_file_id(self, file_id: uuid.UUID) -> FileIntelligence | None:
        return self._session.get(FileIntelligence, file_id)

    def upsert(
        self,
        *,
        file_id: uuid.UUID,
        status: str,
        document_type: str | None,
        summary: str | None,
        entities: list,
        structured_metadata: dict,
        topics: list,
        confidence: float | None,
        provider: str,
        model_name: str,
        error: str | None,
        processed_at: datetime,
    ) -> FileIntelligence:
        intelligence = self.get_by_file_id(file_id)
        if intelligence is None:
            intelligence = FileIntelligence(file_id=file_id)
            self._session.add(intelligence)

        intelligence.status = status
        intelligence.document_type = document_type
        intelligence.summary = summary
        intelligence.entities = entities
        intelligence.structured_metadata = structured_metadata
        intelligence.topics = topics
        intelligence.confidence = confidence
        intelligence.provider = provider
        intelligence.model_name = model_name
        intelligence.error = error
        intelligence.processed_at = processed_at
        self._session.flush()
        return intelligence
