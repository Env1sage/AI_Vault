import uuid

from sqlalchemy.orm import Session

from vault_shared.db.models import SearchSession


class SearchSessionRepository:
    """Append-only query log — no update/delete methods."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def record(
        self, *, organization_id: uuid.UUID, user_id: uuid.UUID, query_text: str, result_count: int
    ) -> SearchSession:
        session_row = SearchSession(
            organization_id=organization_id,
            user_id=user_id,
            query_text=query_text[:1024],
            result_count=result_count,
        )
        self._session.add(session_row)
        self._session.flush()
        return session_row

    def list_for_user(
        self, *, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[SearchSession]:
        return (
            self._session.query(SearchSession)
            .filter_by(organization_id=organization_id, user_id=user_id)
            .order_by(SearchSession.created_at.desc())
            .all()
        )
