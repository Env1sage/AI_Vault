import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from vault_shared import DependencyUnavailableError, get_logger
from vault_shared.connector_service import ConnectorTokenService
from vault_shared.connectors.google_drive import DriveFile, GoogleDriveClient
from vault_shared.connectors.google_workspace import GoogleWorkspaceOAuthClient
from vault_shared.db.models import DriveType, Folder, ScanType, StorageConnector, StorageSource
from vault_shared.db.models.scan_job import ScanJob
from vault_shared.db.repositories import (
    FileRepository,
    FolderRepository,
    ScanEventRepository,
    ScanJobRepository,
    ScanProgressRepository,
    StorageConnectorRepository,
    StorageSourceRepository,
)

logger = get_logger("worker.scanner.scan_service")

# Bounds how much ingest work happens between commits/cancellation checks —
# keeps memory flat on very large drives and caps how much a crash mid-scan
# can lose, without paying a commit's cost on every single item.
_BATCH_COMMIT_SIZE = 200

# `folders.path`/`files.path` is String(4096) — a deeply nested tree of
# long-named folders could in principle still exceed that even with each
# individual name already bounded (google_drive.py's `_MAX_NAME_LENGTH`),
# so the resolved path is capped defensively too rather than trusting the
# math to always stay under the column limit.
_MAX_PATH_LENGTH = 4096


class ScanCancelled(Exception):
    """Internal control-flow signal — unwinds `run()` out of whatever loop
    it's in once cooperative cancellation has been observed, without
    treating cancellation as a failure."""


class ScannerService:
    """Traverses every `StorageSource` a connector exposes and upserts
    provider-neutral `Folder`/`File` inventory rows (Handbook §8.2, §18),
    invoked from the worker's job queue (Handbook §8.15). Read-only against
    the provider: never downloads file content, never writes back to Drive.

    Ingest is two-pass per source (see ADR-016). Pass 1 streams pages from
    the Drive API and upserts each item immediately with a placeholder path
    and no resolved `parent_folder_id` — Drive's `files.list` gives no
    ordering guarantee, so a folder can be returned after its own children,
    making correct materialized paths impossible to compute in a single
    streaming pass. Pass 2 (`_resolve_hierarchy`) re-reads just that
    source's folders from our own database — a small subset of all items
    even at scale — and computes real paths via a memoized walk of each
    folder's provider-parent chain, then applies the same paths to files.
    """

    def __init__(
        self,
        db: Session,
        *,
        drive_client: GoogleDriveClient,
        oauth_client: GoogleWorkspaceOAuthClient,
    ) -> None:
        self._db = db
        self._drive = drive_client
        self._connectors = StorageConnectorRepository(db)
        self._sources = StorageSourceRepository(db)
        self._folders = FolderRepository(db)
        self._files = FileRepository(db)
        self._jobs = ScanJobRepository(db)
        self._progress = ScanProgressRepository(db)
        self._events = ScanEventRepository(db)
        self._tokens = ConnectorTokenService(db, oauth_client=oauth_client)

    def run(self, scan_job_id: uuid.UUID) -> None:
        job = self._jobs.get_by_id(scan_job_id)
        if job is None:
            logger.warning("scan_job_not_found", extra={"scan_job_id": str(scan_job_id)})
            return

        connector = self._connectors.get_by_id(job.connector_id)
        if connector is None:
            self._jobs.mark_failed(job, error="Connector no longer exists.")
            self._db.commit()
            return

        self._jobs.mark_running(job)
        # Idempotent: a retried task (see worker.tasks.scan) re-enters `run`
        # for the same scan_job_id, and `scan_progress.scan_job_id` is a
        # primary key, so re-creating it would raise an IntegrityError.
        if self._progress.get_for_job(job.id) is None:
            self._progress.create_for_job(job.id)
        self._events.record(scan_job_id=job.id, event_type="scan_started")
        self._db.commit()

        try:
            self._check_cancelled(job.id)
            sources = self._discover_sources(job, connector)
            self._progress.set_sources_discovered(job.id, len(sources))
            self._db.commit()

            for source in sources:
                self._check_cancelled(job.id)
                self._progress.set_current_source(job.id, source.name)
                self._db.commit()

                self._scan_source(job, connector, source)

                self._progress.increment_source_completed(job.id)
                self._db.commit()
        except ScanCancelled:
            self._jobs.mark_cancelled(job)
            self._events.record(scan_job_id=job.id, event_type="scan_cancelled")
            self._db.commit()
            return
        except DependencyUnavailableError:
            # Left RUNNING, not FAILED: `worker.tasks.scan.run_scan` retries
            # the whole job on this specific error, and a misleading
            # terminal status shouldn't appear while a retry is still
            # pending. Only once retries are exhausted does the task itself
            # mark the job FAILED.
            logger.warning("scan_job_dependency_unavailable", extra={"scan_job_id": str(job.id)})
            self._db.rollback()
            raise
        except Exception as exc:  # noqa: BLE001 - job execution boundary must never crash the worker
            logger.exception("scan_job_failed", extra={"scan_job_id": str(job.id)})
            self._db.rollback()
            self._jobs.mark_failed(job, error=str(exc))
            self._events.record(scan_job_id=job.id, event_type="scan_failed", message=str(exc))
            self._db.commit()
            return

        connector.last_synced_at = datetime.now(UTC)
        self._jobs.mark_completed(job)
        self._events.record(scan_job_id=job.id, event_type="scan_completed")
        self._db.commit()

    def _discover_sources(self, job: ScanJob, connector: StorageConnector) -> list[StorageSource]:
        access_token = self._tokens.get_valid_access_token(connector)
        sources = [
            self._sources.upsert(
                connector_id=connector.id,
                provider_drive_id="root",
                name="My Drive",
                drive_type=DriveType.MY_DRIVE,
            )
        ]
        for shared_drive in self._drive.list_shared_drives(access_token=access_token):
            sources.append(
                self._sources.upsert(
                    connector_id=connector.id,
                    provider_drive_id=shared_drive.id,
                    name=shared_drive.name,
                    drive_type=DriveType.SHARED_DRIVE,
                )
            )
        self._db.commit()
        return sources

    def _scan_source(
        self, job: ScanJob, connector: StorageConnector, source: StorageSource
    ) -> None:
        if source.change_token is None or job.scan_type == ScanType.FULL:
            self._ingest_full(job, connector, source)
        else:
            self._ingest_incremental(job, connector, source)

    def _ingest_full(
        self, job: ScanJob, connector: StorageConnector, source: StorageSource
    ) -> None:
        drive_id = None if source.drive_type == DriveType.MY_DRIVE else source.provider_drive_id
        page_token: str | None = None
        pending = pending_folders = pending_files = 0

        while True:
            self._check_cancelled(job.id)
            access_token = self._tokens.get_valid_access_token(connector)
            page = self._drive.list_files_page(
                access_token=access_token, drive_id=drive_id, page_token=page_token
            )

            for item in page.files:
                self._ingest_item(source, item)
                pending += 1
                pending_folders += 1 if item.is_folder else 0
                pending_files += 0 if item.is_folder else 1
                if pending >= _BATCH_COMMIT_SIZE:
                    self._progress.increment_counts(
                        job.id, folders=pending_folders, files=pending_files
                    )
                    self._db.commit()
                    pending = pending_folders = pending_files = 0

            page_token = page.next_page_token
            if not page_token:
                break

        if pending:
            self._progress.increment_counts(job.id, folders=pending_folders, files=pending_files)
        self._db.commit()

        self._resolve_hierarchy(source)

        access_token = self._tokens.get_valid_access_token(connector)
        start_page_token = self._drive.get_start_page_token(
            access_token=access_token, drive_id=drive_id
        )
        self._sources.update_change_token(source, change_token=start_page_token)
        self._db.commit()

    def _ingest_incremental(
        self, job: ScanJob, connector: StorageConnector, source: StorageSource
    ) -> None:
        drive_id = None if source.drive_type == DriveType.MY_DRIVE else source.provider_drive_id
        page_token: str | None = source.change_token
        new_start_token: str | None = None
        pending = pending_folders = pending_files = 0
        touched = False

        while page_token:
            self._check_cancelled(job.id)
            access_token = self._tokens.get_valid_access_token(connector)
            page = self._drive.list_changes_page(
                access_token=access_token, page_token=page_token, drive_id=drive_id
            )

            for item in page.changed_files:
                if item.trashed:
                    self._remove_item(source, item.id)
                else:
                    self._ingest_item(source, item)
                    pending_folders += 1 if item.is_folder else 0
                    pending_files += 0 if item.is_folder else 1
                touched = True
                pending += 1
                if pending >= _BATCH_COMMIT_SIZE:
                    self._progress.increment_counts(
                        job.id, folders=pending_folders, files=pending_files
                    )
                    self._db.commit()
                    pending = pending_folders = pending_files = 0

            for removed_id in page.removed_file_ids:
                self._remove_item(source, removed_id)
                touched = True

            if page.new_start_page_token:
                new_start_token = page.new_start_page_token
            page_token = page.next_page_token

        if pending:
            self._progress.increment_counts(job.id, folders=pending_folders, files=pending_files)
        self._db.commit()

        if touched:
            self._resolve_hierarchy(source)

        if new_start_token:
            self._sources.update_change_token(source, change_token=new_start_token)
            self._db.commit()

    def _ingest_item(self, source: StorageSource, item: DriveFile) -> None:
        now = datetime.now(UTC)
        provider_parent_id = item.parents[0] if item.parents else None
        if item.is_folder:
            self._folders.upsert(
                storage_source_id=source.id,
                provider_file_id=item.id,
                provider_parent_id=provider_parent_id,
                parent_folder_id=None,
                name=item.name,
                path=f"/{item.name}",
                owner_email=item.owner_email,
                is_shared=item.shared,
                provider_created_at=item.created_time,
                provider_modified_at=item.modified_time,
                scanned_at=now,
            )
        else:
            self._files.upsert(
                storage_source_id=source.id,
                provider_file_id=item.id,
                provider_parent_id=provider_parent_id,
                parent_folder_id=None,
                name=item.name,
                path=f"/{item.name}",
                mime_type=item.mime_type,
                size_bytes=item.size,
                owner_email=item.owner_email,
                is_shared=item.shared,
                permissions_summary="shared" if item.shared else None,
                version_id=item.version_id,
                checksum=item.checksum,
                provider_created_at=item.created_time,
                provider_modified_at=item.modified_time,
                provider_viewed_at=item.viewed_by_me_time,
                scanned_at=now,
            )

    def _remove_item(self, source: StorageSource, provider_file_id: str) -> None:
        # The Changes API reports only a fileId for a removal, not whether it
        # was a folder or a file — try both; the (source, provider_file_id)
        # unique constraint guarantees at most one ever matches.
        self._folders.delete_by_source_and_provider_id(
            storage_source_id=source.id, provider_file_id=provider_file_id
        )
        self._files.delete_by_source_and_provider_id(
            storage_source_id=source.id, provider_file_id=provider_file_id
        )

    def _resolve_hierarchy(self, source: StorageSource) -> None:
        folders = self._folders.list_for_source(source.id)
        by_provider_id = {folder.provider_file_id: folder for folder in folders}
        resolved_paths: dict[str, str] = {}
        visiting: set[str] = set()

        def resolve_path(folder: Folder) -> str:
            if folder.provider_file_id in resolved_paths:
                return resolved_paths[folder.provider_file_id]
            if folder.provider_file_id in visiting:
                # A parent cycle should never happen in Drive, but an
                # external API's data is never trusted blindly — fall back
                # to treating this folder as its own root rather than
                # recursing forever.
                return f"/{folder.name}"

            visiting.add(folder.provider_file_id)
            parent = (
                by_provider_id.get(folder.provider_parent_id)
                if folder.provider_parent_id
                else None
            )
            path = f"{resolve_path(parent)}/{folder.name}" if parent else f"/{folder.name}"
            path = path[:_MAX_PATH_LENGTH]
            visiting.discard(folder.provider_file_id)

            resolved_paths[folder.provider_file_id] = path
            return path

        for folder in folders:
            parent = (
                by_provider_id.get(folder.provider_parent_id)
                if folder.provider_parent_id
                else None
            )
            folder.path = resolve_path(folder)
            folder.parent_folder_id = parent.id if parent else None
        self._db.commit()

        for file in self._files.list_for_source(source.id):
            parent = (
                by_provider_id.get(file.provider_parent_id) if file.provider_parent_id else None
            )
            if parent is not None:
                parent_path = resolved_paths.get(parent.provider_file_id, parent.path)
                file.path = f"{parent_path}/{file.name}"[:_MAX_PATH_LENGTH]
                file.parent_folder_id = parent.id
            else:
                file.path = f"/{file.name}"[:_MAX_PATH_LENGTH]
                file.parent_folder_id = None
        self._db.commit()

    def _check_cancelled(self, scan_job_id: uuid.UUID) -> None:
        if self._jobs.is_cancel_requested(scan_job_id):
            raise ScanCancelled()
