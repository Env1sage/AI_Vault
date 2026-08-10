import socket
import uuid
from urllib.parse import urlparse

import pytest
from app.application.auth_service import AuthService
from app.application.embedding_job_service import EmbeddingJobService
from app.infrastructure.auth.google_identity import GoogleUserInfo
from sqlalchemy.orm import Session
from vault_shared import ConflictError, NotFoundError, get_settings
from vault_shared.db.models import (
    ConnectorProvider,
    EmbeddingJobStatus,
    EmbeddingTrigger,
)
from vault_shared.db.repositories import StorageConnectorRepository
from vault_shared.db.session import get_session_factory


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


def _provision_user(db: Session):
    unique = uuid.uuid4().hex[:12]
    google_user = GoogleUserInfo(
        sub=f"sub-{unique}",
        email=f"founder-{unique}@example.com",
        email_verified=True,
        name="Ada Founder",
        picture=None,
    )
    session = AuthService(db).complete_google_login(google_user=google_user, ip_address=None)
    return session.user


def _provision_connected_connector(db: Session, *, organization_id: uuid.UUID, user_id: uuid.UUID):
    return StorageConnectorRepository(db).upsert_connected(
        organization_id=organization_id,
        provider=ConnectorProvider.GOOGLE_WORKSPACE,
        connected_by_user_id=user_id,
        account_email="founder@acme.com",
        workspace_domain="acme.com",
    )


@requires_infra
def test_start_creates_a_pending_manual_embedding_job(db: Session) -> None:
    user = _provision_user(db)
    connector = _provision_connected_connector(
        db, organization_id=user.organization_id, user_id=user.id
    )
    service = EmbeddingJobService(db)

    job = service.start(connector.id, organization_id=user.organization_id, user_id=user.id)

    assert job.status == EmbeddingJobStatus.PENDING
    assert job.triggered_by == EmbeddingTrigger.MANUAL
    assert job.connector_id == connector.id


@requires_infra
def test_start_rejects_a_second_job_while_one_is_active(db: Session) -> None:
    user = _provision_user(db)
    connector = _provision_connected_connector(
        db, organization_id=user.organization_id, user_id=user.id
    )
    service = EmbeddingJobService(db)
    service.start(connector.id, organization_id=user.organization_id, user_id=user.id)

    with pytest.raises(ConflictError):
        service.start(connector.id, organization_id=user.organization_id, user_id=user.id)


@requires_infra
def test_list_for_connector_rejects_a_connector_from_another_organization(db: Session) -> None:
    user = _provision_user(db)
    other_user = _provision_user(db)
    connector = _provision_connected_connector(
        db, organization_id=user.organization_id, user_id=user.id
    )
    service = EmbeddingJobService(db)

    with pytest.raises(NotFoundError):
        service.list_for_connector(connector.id, organization_id=other_user.organization_id)


@requires_infra
def test_get_owned_rejects_a_job_from_another_organization(db: Session) -> None:
    user = _provision_user(db)
    other_user = _provision_user(db)
    connector = _provision_connected_connector(
        db, organization_id=user.organization_id, user_id=user.id
    )
    service = EmbeddingJobService(db)
    job = service.start(connector.id, organization_id=user.organization_id, user_id=user.id)

    with pytest.raises(NotFoundError):
        service.get_owned(job.id, organization_id=other_user.organization_id)


@requires_infra
def test_cancel_sets_cancel_requested_on_a_pending_job(db: Session) -> None:
    user = _provision_user(db)
    connector = _provision_connected_connector(
        db, organization_id=user.organization_id, user_id=user.id
    )
    service = EmbeddingJobService(db)
    job = service.start(connector.id, organization_id=user.organization_id, user_id=user.id)

    cancelled = service.cancel(job, organization_id=user.organization_id, user_id=user.id)

    assert cancelled.cancel_requested is True


@requires_infra
def test_cancel_rejects_a_job_that_already_completed(db: Session) -> None:
    user = _provision_user(db)
    connector = _provision_connected_connector(
        db, organization_id=user.organization_id, user_id=user.id
    )
    service = EmbeddingJobService(db)
    job = service.start(connector.id, organization_id=user.organization_id, user_id=user.id)
    service._jobs.mark_completed(job)
    db.commit()

    with pytest.raises(ConflictError):
        service.cancel(job, organization_id=user.organization_id, user_id=user.id)
