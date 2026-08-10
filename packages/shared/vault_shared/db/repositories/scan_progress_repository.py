import uuid

from sqlalchemy import update
from sqlalchemy.orm import Session

from vault_shared.db.models import ScanProgress


class ScanProgressRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_for_job(self, scan_job_id: uuid.UUID) -> ScanProgress:
        progress = ScanProgress(scan_job_id=scan_job_id)
        self._session.add(progress)
        self._session.flush()
        return progress

    def get_for_job(self, scan_job_id: uuid.UUID) -> ScanProgress | None:
        return self._session.get(ScanProgress, scan_job_id)

    def set_sources_discovered(self, scan_job_id: uuid.UUID, count: int) -> None:
        self._session.execute(
            update(ScanProgress)
            .where(ScanProgress.scan_job_id == scan_job_id)
            .values(sources_discovered=count)
        )

    def set_current_source(self, scan_job_id: uuid.UUID, name: str | None) -> None:
        self._session.execute(
            update(ScanProgress)
            .where(ScanProgress.scan_job_id == scan_job_id)
            .values(current_source_name=name)
        )

    def increment_source_completed(self, scan_job_id: uuid.UUID) -> None:
        self._session.execute(
            update(ScanProgress)
            .where(ScanProgress.scan_job_id == scan_job_id)
            .values(sources_completed=ScanProgress.sources_completed + 1)
        )

    def increment_counts(
        self, scan_job_id: uuid.UUID, *, folders: int = 0, files: int = 0
    ) -> None:
        """A single atomic `UPDATE ... SET x = x + n` — safe to call from a
        long-running scan without racing the row's other columns, and
        avoids the identity-map-staleness pitfall a read-then-write would
        have (see `ScanJobRepository.is_cancel_requested`)."""
        if not folders and not files:
            return
        self._session.execute(
            update(ScanProgress)
            .where(ScanProgress.scan_job_id == scan_job_id)
            .values(
                folders_discovered=ScanProgress.folders_discovered + folders,
                files_discovered=ScanProgress.files_discovered + files,
            )
        )
