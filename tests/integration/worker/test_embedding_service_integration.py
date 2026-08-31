import socket
import uuid
from datetime import UTC, datetime
from urllib.parse import urlparse

import pytest
from sqlalchemy.orm import Session
from vault_shared import get_settings
from vault_shared.ai_gateway import AIGateway
from vault_shared.ai_gateway.interfaces import EmbeddingResult
from vault_shared.ai_gateway.providers import ExtractiveCompletionProvider
from vault_shared.db.models import (
    ConnectorProvider,
    DriveType,
    EmbeddingJobStatus,
    EmbeddingTrigger,
    ExtractionStatus,
    RoleName,
)
from vault_shared.db.repositories import (
    EmbeddingJobRepository,
    EmbeddingRepository,
    FileExtractionRepository,
    FileRepository,
    OrganizationRepository,
    RoleRepository,
    StorageConnectorRepository,
    StorageSourceRepository,
    UserRepository,
)
from vault_shared.db.session import get_session_factory
from worker.embedding.embedding_service import EmbeddingService


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


class _FakeEmbeddingProvider:
    """A deterministic stand-in for `LocalEmbeddingProvider` — no gensim
    download, no dependency on real word vectors. Each call to `embed`
    increments `call_count`, letting a test assert exactly how many texts
    were actually (re-)embedded."""

    name = "fake_embedding_provider"

    def __init__(self, *, model_version: str = "1") -> None:
        self.model_name = "fake"
        self.model_version = model_version
        self.call_count = 0

    def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        self.call_count += len(texts)
        return [
            EmbeddingResult(
                vector=[float(len(text)), 0.0],
                model_name=self.model_name,
                model_version=self.model_version,
                dimensions=2,
            )
            for text in texts
        ]


class _RaisingEmbeddingProvider:
    name = "raising_embedding_provider"
    model_name = "fake"
    model_version = "1"

    def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        raise ValueError("simulated embedding failure")


def _gateway(provider: _FakeEmbeddingProvider) -> AIGateway:
    return AIGateway(embedding_provider=provider, completion_provider=ExtractiveCompletionProvider())


def _provision_user(db: Session):
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
    db.commit()
    return connector


def _provision_extracted_file(
    db: Session, *, connector_id: uuid.UUID, name: str, provider_file_id: str, text: str
):
    source = StorageSourceRepository(db).upsert(
        connector_id=connector_id, provider_drive_id="root", name="My Drive", drive_type=DriveType.MY_DRIVE
    )
    now = datetime.now(UTC)
    file = FileRepository(db).upsert(
        storage_source_id=source.id,
        provider_file_id=provider_file_id,
        provider_parent_id=None,
        parent_folder_id=None,
        name=name,
        path=f"/{name}",
        mime_type="text/plain",
        size_bytes=len(text),
        owner_email="founder@acme.com",
        is_shared=False,
        permissions_summary=None,
        version_id=None,
        checksum=None,
        web_view_link=None,
        provider_created_at=now,
        provider_modified_at=now,
        provider_viewed_at=None,
        scanned_at=now,
    )
    FileExtractionRepository(db).upsert(
        file_id=file.id,
        status=ExtractionStatus.SUCCESS,
        extractor_name="plain_text",
        extracted_text=text,
        char_count=len(text),
        error=None,
        extracted_at=now,
    )
    db.commit()
    return file


def _create_job(db: Session, *, connector_id: uuid.UUID):
    job = EmbeddingJobRepository(db).create(
        connector_id=connector_id, triggered_by=EmbeddingTrigger.MANUAL, triggered_by_user_id=None
    )
    db.commit()
    return job


@requires_infra
def test_embedding_processes_pending_files_and_persists_vectors(db: Session) -> None:
    user = _provision_user(db)
    connector = _provision_connector(db, organization_id=user.organization_id, user_id=user.id)
    file = _provision_extracted_file(
        db, connector_id=connector.id, name="Report.txt", provider_file_id="f-1", text="report body"
    )
    job = _create_job(db, connector_id=connector.id)
    provider = _FakeEmbeddingProvider()
    service = EmbeddingService(db, ai_gateway=_gateway(provider))

    service.run(job.id)

    completed_job = EmbeddingJobRepository(db).get_by_id(job.id)
    assert completed_job.status == EmbeddingJobStatus.COMPLETED

    embedding = EmbeddingRepository(db).get_by_file_id(file.id)
    assert embedding is not None
    assert embedding.model_name == "fake"
    assert embedding.vector == [float(len("report body")), 0.0]


@requires_infra
def test_embedding_is_resumable_and_skips_unchanged_content(db: Session) -> None:
    user = _provision_user(db)
    connector = _provision_connector(db, organization_id=user.organization_id, user_id=user.id)
    _provision_extracted_file(
        db, connector_id=connector.id, name="Report.txt", provider_file_id="f-1", text="report body"
    )
    provider = _FakeEmbeddingProvider()
    service = EmbeddingService(db, ai_gateway=_gateway(provider))

    first_job = _create_job(db, connector_id=connector.id)
    service.run(first_job.id)
    assert provider.call_count == 1

    second_job = _create_job(db, connector_id=connector.id)
    service.run(second_job.id)

    # Nothing changed since the first run, so no file is "pending" and the
    # provider is never called again — cheap to re-trigger when idle.
    assert provider.call_count == 1
    assert EmbeddingJobRepository(db).get_by_id(second_job.id).status == EmbeddingJobStatus.COMPLETED


@requires_infra
def test_a_model_version_change_makes_every_file_pending_again(db: Session) -> None:
    user = _provision_user(db)
    connector = _provision_connector(db, organization_id=user.organization_id, user_id=user.id)
    _provision_extracted_file(
        db, connector_id=connector.id, name="Report.txt", provider_file_id="f-1", text="report body"
    )
    provider_v1 = _FakeEmbeddingProvider(model_version="1")
    service_v1 = EmbeddingService(db, ai_gateway=_gateway(provider_v1))
    first_job = _create_job(db, connector_id=connector.id)
    service_v1.run(first_job.id)
    assert provider_v1.call_count == 1

    # A new EmbeddingService configured with a bumped model_version (as if
    # the embedding algorithm changed, per ADR-018) must treat every
    # already-embedded file as pending again, not silently reuse the old
    # vector — this is the "detect when documents require re-embedding"
    # requirement from the phase spec.
    provider_v2 = _FakeEmbeddingProvider(model_version="2")
    service_v2 = EmbeddingService(db, ai_gateway=_gateway(provider_v2))
    second_job = _create_job(db, connector_id=connector.id)
    service_v2.run(second_job.id)

    assert provider_v2.call_count == 1
    assert EmbeddingJobRepository(db).get_by_id(second_job.id).status == EmbeddingJobStatus.COMPLETED


@requires_infra
def test_a_single_files_embedding_failure_does_not_stop_the_job(db: Session) -> None:
    user = _provision_user(db)
    connector = _provision_connector(db, organization_id=user.organization_id, user_id=user.id)
    _provision_extracted_file(
        db, connector_id=connector.id, name="Good.txt", provider_file_id="f-good", text="good text"
    )
    job = _create_job(db, connector_id=connector.id)
    service = EmbeddingService(db, ai_gateway=_gateway(_RaisingEmbeddingProvider()))  # type: ignore[arg-type]

    service.run(job.id)

    completed_job = EmbeddingJobRepository(db).get_by_id(job.id)
    assert completed_job.status == EmbeddingJobStatus.COMPLETED


@requires_infra
def test_cancellation_stops_the_job_cleanly(db: Session) -> None:
    user = _provision_user(db)
    connector = _provision_connector(db, organization_id=user.organization_id, user_id=user.id)
    _provision_extracted_file(
        db, connector_id=connector.id, name="Report.txt", provider_file_id="f-1", text="report body"
    )
    job = _create_job(db, connector_id=connector.id)
    jobs = EmbeddingJobRepository(db)
    jobs.request_cancel(job)
    db.commit()

    service = EmbeddingService(db, ai_gateway=_gateway(_FakeEmbeddingProvider()))

    service.run(job.id)

    cancelled_job = jobs.get_by_id(job.id)
    assert cancelled_job.status == EmbeddingJobStatus.CANCELLED
