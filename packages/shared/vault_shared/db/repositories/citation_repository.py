import uuid

from sqlalchemy.orm import Session

from vault_shared.db.models import Citation


class CitationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        message_id: uuid.UUID,
        file_id: uuid.UUID,
        snippet: str | None,
        confidence: float,
        retrieval_method: str,
    ) -> Citation:
        citation = Citation(
            message_id=message_id,
            file_id=file_id,
            snippet=snippet[:1024] if snippet else None,
            confidence=confidence,
            retrieval_method=retrieval_method,
        )
        self._session.add(citation)
        self._session.flush()
        return citation

    def list_for_message(self, message_id: uuid.UUID) -> list[Citation]:
        return self._session.query(Citation).filter_by(message_id=message_id).all()

    def list_for_messages(self, message_ids: list[uuid.UUID]) -> list[Citation]:
        if not message_ids:
            return []
        return self._session.query(Citation).filter(Citation.message_id.in_(message_ids)).all()
