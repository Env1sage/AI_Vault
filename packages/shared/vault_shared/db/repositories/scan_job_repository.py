import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from vault_shared.db.models import ScanJob, ScanStatus


class ScanJobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self, *, connector_id: uuid.UUID, scan_type: str, triggered_by_user_id: uuid.UUID | None
    ) -> ScanJob:
        job = ScanJob(
            connector_id=connector_id,
            scan_type=scan_type,
            triggered_by_user_id=triggered_by_user_id,
        )
        self._session.add(job)
        self._session.flush()
        return job

    def get_by_id(self, scan_job_id: uuid.UUID) -> ScanJob | None:
        return self._session.get(ScanJob, scan_job_id)

    def list_for_connector(self, connector_id: uuid.UUID) -> list[ScanJob]:
        return (
            self._session.query(ScanJob)
            .filter_by(connector_id=connector_id)
            .order_by(ScanJob.created_at.desc())
            .all()
        )

    def has_active_job(self, connector_id: uuid.UUID) -> bool:
        return (
            self._session.query(ScanJob)
            .filter(
                ScanJob.connector_id == connector_id,
                ScanJob.status.in_([ScanStatus.PENDING, ScanStatus.RUNNING]),
            )
            .first()
            is not None
        )

    def mark_running(self, job: ScanJob) -> None:
        job.status = ScanStatus.RUNNING
        job.started_at = datetime.now(UTC)
        self._session.flush()

    def mark_completed(self, job: ScanJob) -> None:
        job.status = ScanStatus.COMPLETED
        job.completed_at = datetime.now(UTC)
        self._session.flush()

    def mark_failed(self, job: ScanJob, *, error: str) -> None:
        job.status = ScanStatus.FAILED
        job.error = error[:2048]
        job.completed_at = datetime.now(UTC)
        self._session.flush()

    def mark_cancelled(self, job: ScanJob) -> None:
        job.status = ScanStatus.CANCELLED
        job.completed_at = datetime.now(UTC)
        self._session.flush()

    def request_cancel(self, job: ScanJob) -> None:
        job.cancel_requested = True
        self._session.flush()

    def is_cancel_requested(self, scan_job_id: uuid.UUID) -> bool:
        """Queries the single column directly rather than `session.get()` —
        an entity fetch would return the session's identity-mapped object,
        which can be stale relative to a cancel requested by a *different*
        process (the backend, handling the cancel API call) unless this
        session happens to have just expired it via a commit. A column-only
        query always reaches the database, guaranteeing a fresh read."""
        result = (
            self._session.query(ScanJob.cancel_requested).filter(ScanJob.id == scan_job_id).scalar()
        )
        return bool(result)
