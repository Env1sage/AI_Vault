import socket
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

import pytest
from sqlalchemy.orm import Session
from vault_shared import DependencyUnavailableError, get_settings
from vault_shared.connectors.google_drive import DriveFile, DriveFilesPage, SharedDrive
from vault_shared.connectors.google_workspace import GoogleAccountInfo, GoogleTokenSet
from vault_shared.db.models import ConnectorProvider, RoleName, ScanStatus, ScanType
from vault_shared.db.repositories import (
    ConnectorCredentialsRepository,
    FileRepository,
    FolderRepository,
    OrganizationRepository,
    RoleRepository,
    ScanJobRepository,
    ScanProgressRepository,
    StorageConnectorRepository,
    StorageSourceRepository,
    UserRepository,
)
from vault_shared.db.session import get_session_factory
from vault_shared.security.encryption import encrypt_token
from worker.scanner.scan_service import ScannerService


def _reachable(url: str) -> bool:
    parsed = urlparse(url)
    if not parsed.hostname or not parsed.port:
        return False
    try:
        with socket.create_connection((parsed.hostname, parsed.port), timeout=1):
            return True
    except OSError:
        return False


def _infra_available() -> bool:
    settings = get_settings()
    return _reachable(settings.database_url) and _reachable(settings.redis_url)


requires_infra = pytest.mark.skipif(
    not _infra_available(),
    reason="Postgres/Redis not reachable — run against `docker compose up` or CI service containers.",
)


@pytest.fixture
def db():
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


class _FakeGoogleWorkspaceOAuthClient:
    """No real Google credentials in this sandbox — stands in exactly where
    GoogleWorkspaceOAuthClient would via constructor injection, matching
    Phase 3's connector integration test pattern."""

    def exchange_code(self, *, code: str) -> GoogleTokenSet:
        return GoogleTokenSet(
            access_token="access-1",
            refresh_token="refresh-1",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            granted_scopes="https://www.googleapis.com/auth/drive.readonly",
        )

    def refresh_access_token(self, *, refresh_token: str) -> GoogleTokenSet:
        return GoogleTokenSet(
            access_token="access-refreshed",
            refresh_token=refresh_token,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            granted_scopes="https://www.googleapis.com/auth/drive.readonly",
        )

    def fetch_account_info(self, *, access_token: str) -> GoogleAccountInfo:
        return GoogleAccountInfo(email="founder@acme.com", workspace_domain="acme.com")

    def build_authorize_url(self, *, state: str) -> str:
        return f"https://accounts.google.com/o/oauth2/v2/auth?state={state}"

    def revoke(self, *, token: str) -> bool:
        return True


class _FakeGoogleDriveClient:
    """Canned Drive responses, configured per test — never calls the real
    Google Drive API. `files_pages` maps a drive_id (None for My Drive) to a
    list of `DriveFilesPage`s returned in order across successive calls."""

    def __init__(
        self,
        *,
        shared_drives: list[SharedDrive] | None = None,
        files_pages: dict[str | None, list[DriveFilesPage]] | None = None,
    ) -> None:
        self.shared_drives = shared_drives or []
        self._files_pages = {k: list(v) for k, v in (files_pages or {}).items()}
        self.list_files_page_calls = 0
        self._on_call: Callable[[], None] | None = None

    def list_shared_drives(self, *, access_token: str) -> list[SharedDrive]:
        return self.shared_drives

    def list_files_page(
        self, *, access_token: str, drive_id: str | None, page_token: str | None, page_size: int = 1000
    ) -> DriveFilesPage:
        self.list_files_page_calls += 1
        if self._on_call:
            self._on_call()
        pages = self._files_pages.get(drive_id, [])
        index = 0 if page_token is None else int(page_token)
        page = pages[index]
        next_token = str(index + 1) if index + 1 < len(pages) else None
        return DriveFilesPage(files=page.files, next_page_token=next_token)

    def get_start_page_token(self, *, access_token: str, drive_id: str | None) -> str:
        return "start-token-1"

    def list_changes_page(self, *, access_token: str, page_token: str, drive_id: str | None):
        raise NotImplementedError


def _folder(item_id: str, name: str, *, parent_id: str | None) -> DriveFile:
    return DriveFile(
        id=item_id,
        name=name,
        mime_type="application/vnd.google-apps.folder",
        parents=[parent_id] if parent_id else [],
        size=None,
        created_time=None,
        modified_time=None,
        viewed_by_me_time=None,
        owner_email="founder@acme.com",
        shared=False,
        checksum=None,
        version_id=None,
        is_folder=True,
        trashed=False,
    )


def _file(item_id: str, name: str, *, parent_id: str | None) -> DriveFile:
    return DriveFile(
        id=item_id,
        name=name,
        mime_type="application/pdf",
        parents=[parent_id] if parent_id else [],
        size=1024,
        created_time=None,
        modified_time=None,
        viewed_by_me_time=None,
        owner_email="founder@acme.com",
        shared=False,
        checksum="abc123",
        version_id="v1",
        is_folder=False,
        trashed=False,
    )


def _provision_user(db: Session):
    """Provisions a persisted Organization+Role+User directly via
    `vault_shared` repositories rather than the backend's `AuthService` —
    apps/backend and apps/worker are independently deployable (ADR-012), so
    a worker-side test can't import backend application code."""
    unique = uuid.uuid4().hex[:12]
    organization = OrganizationRepository(db).create(name="Acme", slug=f"acme-{unique}")
    role = RoleRepository(db).get_by_name(RoleName.OWNER)
    user = UserRepository(db).create(
        organization_id=organization.id,
        role_id=role.id,
        google_sub=f"sub-{unique}",
        email=f"founder-{unique}@example.com",
        name="Ada Founder",
        avatar_url=None,
    )
    db.commit()
    return user


def _provision_connector(db: Session, *, organization_id: uuid.UUID, user_id: uuid.UUID):
    connector = StorageConnectorRepository(db).upsert_connected(
        organization_id=organization_id,
        provider=ConnectorProvider.GOOGLE_WORKSPACE,
        connected_by_user_id=user_id,
        account_email="founder@acme.com",
        workspace_domain="acme.com",
    )
    ConnectorCredentialsRepository(db).upsert(
        connector_id=connector.id,
        access_token_encrypted=encrypt_token("access-1"),
        refresh_token_encrypted=encrypt_token("refresh-1"),
        granted_scopes="https://www.googleapis.com/auth/drive.readonly",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db.commit()
    return connector


def _create_job(db: Session, *, connector_id: uuid.UUID, scan_type: str = ScanType.FULL):
    job = ScanJobRepository(db).create(
        connector_id=connector_id, scan_type=scan_type, triggered_by_user_id=None
    )
    db.commit()
    return job


@requires_infra
def test_full_scan_ingests_folders_and_files_with_correct_materialized_paths(db: Session) -> None:
    user = _provision_user(db)
    connector = _provision_connector(db, organization_id=user.organization_id, user_id=user.id)
    job = _create_job(db, connector_id=connector.id)

    drive = _FakeGoogleDriveClient(
        files_pages={
            None: [
                DriveFilesPage(
                    files=[
                        _folder("f-reports", "Reports", parent_id=None),
                        _file("file-q1", "Q1.pdf", parent_id="f-reports"),
                    ],
                    next_page_token=None,
                )
            ]
        }
    )
    service = ScannerService(db, drive_client=drive, oauth_client=_FakeGoogleWorkspaceOAuthClient())

    service.run(job.id)

    completed_job = ScanJobRepository(db).get_by_id(job.id)
    assert completed_job.status == ScanStatus.COMPLETED

    source = StorageSourceRepository(db).get_by_connector_and_provider_drive_id(
        connector_id=connector.id, provider_drive_id="root"
    )
    folder = FolderRepository(db).get_by_source_and_provider_id(
        storage_source_id=source.id, provider_file_id="f-reports"
    )
    file = FileRepository(db).get_by_source_and_provider_id(
        storage_source_id=source.id, provider_file_id="file-q1"
    )
    assert folder.path == "/Reports"
    assert file.path == "/Reports/Q1.pdf"
    assert file.parent_folder_id == folder.id

    progress = ScanProgressRepository(db).get_for_job(job.id)
    assert progress.folders_discovered == 1
    assert progress.files_discovered == 1
    assert progress.sources_completed == 1


@requires_infra
def test_full_scan_resolves_hierarchy_even_when_child_arrives_before_parent(db: Session) -> None:
    """Drive's files.list pagination gives no ordering guarantee — this feeds
    the child folder and file in the same page as the parent, in reverse
    order, to prove the two-pass resolve step (not ingest order) determines
    the final materialized path."""
    user = _provision_user(db)
    connector = _provision_connector(db, organization_id=user.organization_id, user_id=user.id)
    job = _create_job(db, connector_id=connector.id)

    drive = _FakeGoogleDriveClient(
        files_pages={
            None: [
                DriveFilesPage(
                    files=[
                        _file("file-old", "old.pdf", parent_id="f-archive"),
                        _folder("f-archive", "Archive", parent_id="f-reports"),
                        _folder("f-reports", "Reports", parent_id=None),
                    ],
                    next_page_token=None,
                )
            ]
        }
    )
    service = ScannerService(db, drive_client=drive, oauth_client=_FakeGoogleWorkspaceOAuthClient())

    service.run(job.id)

    source = StorageSourceRepository(db).get_by_connector_and_provider_drive_id(
        connector_id=connector.id, provider_drive_id="root"
    )
    archive = FolderRepository(db).get_by_source_and_provider_id(
        storage_source_id=source.id, provider_file_id="f-archive"
    )
    old_file = FileRepository(db).get_by_source_and_provider_id(
        storage_source_id=source.id, provider_file_id="file-old"
    )
    assert archive.path == "/Reports/Archive"
    assert old_file.path == "/Reports/Archive/old.pdf"


@requires_infra
def test_cancellation_between_sources_stops_the_scan_cleanly(db: Session) -> None:
    user = _provision_user(db)
    connector = _provision_connector(db, organization_id=user.organization_id, user_id=user.id)
    job = _create_job(db, connector_id=connector.id)

    drive = _FakeGoogleDriveClient(
        shared_drives=[SharedDrive(id="shared-1", name="Team Drive")],
        files_pages={
            None: [DriveFilesPage(files=[_folder("f1", "Folder1", parent_id=None)], next_page_token=None)],
            "shared-1": [DriveFilesPage(files=[], next_page_token=None)],
        },
    )
    jobs = ScanJobRepository(db)

    def _cancel_after_my_drive() -> None:
        if drive.list_files_page_calls == 1:
            jobs.request_cancel(job)
            db.commit()

    drive._on_call = _cancel_after_my_drive
    service = ScannerService(db, drive_client=drive, oauth_client=_FakeGoogleWorkspaceOAuthClient())

    service.run(job.id)

    cancelled_job = jobs.get_by_id(job.id)
    assert cancelled_job.status == ScanStatus.CANCELLED
    # My Drive's single page was ingested before cancellation was observed.
    assert drive.list_files_page_calls == 1


@requires_infra
def test_dependency_unavailable_leaves_the_job_running_for_a_celery_level_retry(
    db: Session,
) -> None:
    user = _provision_user(db)
    connector = _provision_connector(db, organization_id=user.organization_id, user_id=user.id)
    job = _create_job(db, connector_id=connector.id)

    drive = _FakeGoogleDriveClient()

    def _raise() -> None:
        raise DependencyUnavailableError("Google Drive rate limit exceeded.")

    drive._on_call = _raise
    service = ScannerService(db, drive_client=drive, oauth_client=_FakeGoogleWorkspaceOAuthClient())

    with pytest.raises(DependencyUnavailableError):
        service.run(job.id)

    still_running_job = ScanJobRepository(db).get_by_id(job.id)
    assert still_running_job.status == ScanStatus.RUNNING
