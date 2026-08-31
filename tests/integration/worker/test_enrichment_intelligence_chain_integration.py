"""Covers `worker.tasks.enrichment._enqueue_intelligence_if_enrichment_completed`
— the parallel trigger wired in Stage 5 of Phase 2. Proves it fires
independently of `_enqueue_embedding_if_enrichment_completed` (both created
from the same `EnrichmentJob` completion, neither gated on the other) and
respects the same has-active-job/only-on-completed guards `EmbeddingJob`'s
trigger already has, mirroring `test_scan_task_integration.py`'s direct
task-function testing style (`.delay` mocked, no real broker needed)."""

import socket
import uuid
from datetime import UTC, datetime
from unittest.mock import patch
from urllib.parse import urlparse

import pytest
from sqlalchemy.orm import Session
from vault_shared import get_settings
from vault_shared.db.models import (
    ConnectorProvider,
    EnrichmentJobStatus,
    EnrichmentTrigger,
    IntelligenceJobStatus,
    IntelligenceTrigger,
    RoleName,
)
from vault_shared.db.repositories import (
    EmbeddingJobRepository,
    EnrichmentJobRepository,
    IntelligenceJobRepository,
    OrganizationRepository,
    RoleRepository,
    StorageConnectorRepository,
    UserRepository,
)
from vault_shared.db.session import get_session_factory
from worker.tasks.enrichment import (
    _enqueue_embedding_if_enrichment_completed,
    _enqueue_intelligence_if_enrichment_completed,
)


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


def _provision_connector(db: Session):
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
    db.commit()
    return connector


def _provision_completed_enrichment_job(db: Session, *, connector_id: uuid.UUID):
    jobs = EnrichmentJobRepository(db)
    job = jobs.create(
        connector_id=connector_id, triggered_by=EnrichmentTrigger.MANUAL, triggered_by_user_id=None
    )
    jobs.mark_completed(job)
    db.commit()
    return job


@requires_infra
def test_intelligence_job_is_created_independently_of_the_embedding_job(db: Session) -> None:
    connector = _provision_connector(db)
    enrichment_job = _provision_completed_enrichment_job(db, connector_id=connector.id)

    with (
        patch("worker.tasks.enrichment.run_embedding") as mock_embedding_task,
        patch("worker.tasks.enrichment.run_intelligence") as mock_intelligence_task,
    ):
        _enqueue_embedding_if_enrichment_completed(db, str(enrichment_job.id))
        _enqueue_intelligence_if_enrichment_completed(db, str(enrichment_job.id))

    embedding_job = EmbeddingJobRepository(db).list_for_connector(connector.id)[0]
    intelligence_job = IntelligenceJobRepository(db).list_for_connector(connector.id)[0]

    assert embedding_job.enrichment_job_id == enrichment_job.id
    assert intelligence_job.enrichment_job_id == enrichment_job.id
    assert intelligence_job.triggered_by == IntelligenceTrigger.ENRICHMENT_COMPLETED
    mock_embedding_task.delay.assert_called_once_with(str(embedding_job.id))
    mock_intelligence_task.delay.assert_called_once_with(str(intelligence_job.id))


@requires_infra
def test_intelligence_job_creation_does_not_depend_on_the_embedding_trigger_running(
    db: Session,
) -> None:
    """The chain hook itself proves the parallel design: calling only the
    intelligence trigger (never the embedding one) still creates a job —
    neither function reads the other's state."""
    connector = _provision_connector(db)
    enrichment_job = _provision_completed_enrichment_job(db, connector_id=connector.id)

    with patch("worker.tasks.enrichment.run_intelligence") as mock_intelligence_task:
        _enqueue_intelligence_if_enrichment_completed(db, str(enrichment_job.id))

    assert EmbeddingJobRepository(db).list_for_connector(connector.id) == []
    intelligence_jobs = IntelligenceJobRepository(db).list_for_connector(connector.id)
    assert len(intelligence_jobs) == 1
    mock_intelligence_task.delay.assert_called_once()


@requires_infra
def test_no_intelligence_job_is_created_when_enrichment_did_not_complete(db: Session) -> None:
    connector = _provision_connector(db)
    job = EnrichmentJobRepository(db).create(
        connector_id=connector.id, triggered_by=EnrichmentTrigger.MANUAL, triggered_by_user_id=None
    )
    db.commit()
    assert job.status != EnrichmentJobStatus.COMPLETED

    with patch("worker.tasks.enrichment.run_intelligence") as mock_intelligence_task:
        _enqueue_intelligence_if_enrichment_completed(db, str(job.id))

    assert IntelligenceJobRepository(db).list_for_connector(connector.id) == []
    mock_intelligence_task.delay.assert_not_called()


@requires_infra
def test_no_duplicate_intelligence_job_when_one_is_already_active(db: Session) -> None:
    connector = _provision_connector(db)
    enrichment_job = _provision_completed_enrichment_job(db, connector_id=connector.id)
    IntelligenceJobRepository(db).create(
        connector_id=connector.id,
        triggered_by=IntelligenceTrigger.MANUAL,
        triggered_by_user_id=None,
    )
    db.commit()

    with patch("worker.tasks.enrichment.run_intelligence") as mock_intelligence_task:
        _enqueue_intelligence_if_enrichment_completed(db, str(enrichment_job.id))

    jobs = IntelligenceJobRepository(db).list_for_connector(connector.id)
    assert len(jobs) == 1  # still just the pre-existing active one
    mock_intelligence_task.delay.assert_not_called()
