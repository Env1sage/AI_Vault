import uuid

from sqlalchemy.orm import Session

from vault_shared.db.models import StorageAnalysisEvent


class StorageAnalysisEventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record(
        self,
        *,
        storage_analysis_job_id: uuid.UUID,
        event_type: str,
        message: str | None = None,
        metadata: dict | None = None,
    ) -> StorageAnalysisEvent:
        event = StorageAnalysisEvent(
            storage_analysis_job_id=storage_analysis_job_id,
            event_type=event_type,
            message=message[:1024] if message else None,
            metadata_=metadata or {},
        )
        self._session.add(event)
        self._session.flush()
        return event

    def list_for_job(self, storage_analysis_job_id: uuid.UUID) -> list[StorageAnalysisEvent]:
        return (
            self._session.query(StorageAnalysisEvent)
            .filter_by(storage_analysis_job_id=storage_analysis_job_id)
            .order_by(StorageAnalysisEvent.created_at)
            .all()
        )
