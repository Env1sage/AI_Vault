"""Covers `worker.tasks.scan.run_scan` — the Celery-bound wrapper around
`ScannerService`. `test_scan_service_integration.py` already proves
`ScannerService.run()` leaves a job RUNNING on a `DependencyUnavailableError`
so a Celery-level retry can re-enter it; this file proves the *task's own*
retry bookkeeping on top of that — that it retries while attempts remain and
marks the job FAILED once `max_retries` is exhausted, per the two-tier retry
design documented in `apps/worker/worker/tasks/scan.py`.
"""

import socket
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from urllib.parse import urlparse

import pytest
from sqlalchemy.orm import Session
from vault_shared import DependencyUnavailableError, get_settings
from vault_shared.db.models import ConnectorProvider, RoleName, ScanStatus, ScanType
from vault_shared.db.repositories import (
    ConnectorCredentialsRepository,
    OrganizationRepository,
    RoleRepository,
    ScanJobRepository,
    StorageConnectorRepository,
    UserRepository,
)
from vault_shared.db.session import get_session_factory
from vault_shared.security.encryption import encrypt_token
from worker.tasks.scan import _MAX_RETRIES, run_scan


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


def _provision_job(db: Session):
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
    connector = StorageConnectorRepository(db).upsert_connected(
        organization_id=organization.id,
        provider=ConnectorProvider.GOOGLE_WORKSPACE,
        connected_by_user_id=user.id,
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
    job = ScanJobRepository(db).create(
        connector_id=connector.id, scan_type=ScanType.FULL, triggered_by_user_id=None
    )
    db.commit()
    return job


@requires_infra
def test_run_scan_retries_when_attempts_remain(db: Session) -> None:
    job = _provision_job(db)

    with patch("worker.tasks.scan.ScannerService") as scanner_cls:
        scanner_cls.return_value.run.side_effect = DependencyUnavailableError("rate limited")
        run_scan.push_request(retries=0)
        try:
            # Celery's own `Task.retry()` docs: when the task is invoked
            # directly (`request.called_directly`, true for a plain function
            # call like this rather than `.apply_async()`/a live worker), it
            # re-raises the original exception rather than enqueueing a real
            # retry — that enqueue-and-requeue behavior only happens inside
            # an actual worker/broker dispatch, which is exactly what we
            # don't want a test to trigger against the real Redis broker.
            # The meaningful assertion here is that the task does NOT catch
            # this and mark the job FAILED while retries remain.
            with pytest.raises(DependencyUnavailableError):
                run_scan(str(job.id))
        finally:
            run_scan.pop_request()

    db.expire_all()
    job_after = ScanJobRepository(db).get_by_id(job.id)
    # The task didn't touch the job itself — bookkeeping on a still-retryable
    # failure is ScannerService's job (proven separately), not the task
    # wrapper's; the job is left exactly as ScannerService's mock left it.
    assert job_after.status == ScanStatus.PENDING


@requires_infra
def test_run_scan_marks_job_failed_once_retries_are_exhausted(db: Session) -> None:
    job = _provision_job(db)

    with patch("worker.tasks.scan.ScannerService") as scanner_cls:
        scanner_cls.return_value.run.side_effect = DependencyUnavailableError("rate limited")
        run_scan.push_request(retries=_MAX_RETRIES)
        try:
            # Exhausted retries: the task must swallow the error and mark the
            # job FAILED rather than raising `self.retry(...)` again.
            run_scan(str(job.id))
        finally:
            run_scan.pop_request()

    db.expire_all()
    job_after = ScanJobRepository(db).get_by_id(job.id)
    assert job_after.status == ScanStatus.FAILED
    assert "Google Drive unavailable after retries" in job_after.error
