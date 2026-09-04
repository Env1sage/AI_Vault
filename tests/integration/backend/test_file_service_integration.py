import socket
import uuid
from datetime import UTC, datetime
from urllib.parse import urlparse

import pytest
from app.application.auth_service import AuthService
from app.application.file_service import FileService
from app.infrastructure.auth.google_identity import GoogleUserInfo
from sqlalchemy.orm import Session
from vault_shared import NotFoundError, get_settings
from vault_shared.db.models import ConnectorProvider, DriveType, RelationshipType
from vault_shared.db.repositories import (
    FileClassificationRepository,
    FileMetadataRepository,
    FileRelationshipRepository,
    FileRepository,
    StorageConnectorRepository,
    StorageSourceRepository,
)
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


def _provision_connector(db: Session, *, organization_id: uuid.UUID, user_id: uuid.UUID):
    return StorageConnectorRepository(db).upsert_connected(
        organization_id=organization_id,
        provider=ConnectorProvider.GOOGLE_WORKSPACE,
        connected_by_user_id=user_id,
        account_email="founder@acme.com",
        workspace_domain="acme.com",
    )


def _provision_file(db: Session, *, connector_id: uuid.UUID, name: str):
    source = StorageSourceRepository(db).upsert(
        connector_id=connector_id, provider_drive_id="root", name="My Drive", drive_type=DriveType.MY_DRIVE
    )
    now = datetime.now(UTC)
    file = FileRepository(db).upsert(
        storage_source_id=source.id,
        provider_file_id=str(uuid.uuid4()),
        provider_parent_id=None,
        parent_folder_id=None,
        name=name,
        path=f"/{name}",
        mime_type="application/pdf",
        size_bytes=1024,
        owner_email="founder@acme.com",
        is_shared=False,
        permissions_summary=None,
        version_id=None,
        checksum=None,
        web_view_link=f"https://drive.google.com/file/d/{name}/view",
        provider_created_at=now,
        provider_modified_at=now,
        provider_viewed_at=None,
        scanned_at=now,
    )
    db.commit()
    return file


@requires_infra
def test_list_for_connector_returns_files_and_total_count(db: Session) -> None:
    user = _provision_user(db)
    connector = _provision_connector(db, organization_id=user.organization_id, user_id=user.id)
    _provision_file(db, connector_id=connector.id, name="Report.pdf")
    _provision_file(db, connector_id=connector.id, name="Invoice.pdf")
    service = FileService(db)

    files, total = service.list_for_connector(
        connector.id, organization_id=user.organization_id, limit=10, offset=0
    )

    assert total == 2
    assert {f.name for f in files} == {"Report.pdf", "Invoice.pdf"}


@requires_infra
def test_list_for_connector_rejects_a_connector_from_another_organization(db: Session) -> None:
    user = _provision_user(db)
    other_user = _provision_user(db)
    connector = _provision_connector(db, organization_id=user.organization_id, user_id=user.id)
    service = FileService(db)

    with pytest.raises(NotFoundError):
        service.list_for_connector(
            connector.id, organization_id=other_user.organization_id, limit=10, offset=0
        )


@requires_infra
def test_get_detail_assembles_metadata_classification_and_relationships(db: Session) -> None:
    user = _provision_user(db)
    connector = _provision_connector(db, organization_id=user.organization_id, user_id=user.id)
    file = _provision_file(db, connector_id=connector.id, name="Report_v2.pdf")
    related = _provision_file(db, connector_id=connector.id, name="Report_v1.pdf")

    now = datetime.now(UTC)
    FileMetadataRepository(db).upsert(
        file_id=file.id,
        normalized_extension="pdf",
        mime_type_validated=True,
        mime_mismatch_reason=None,
        naming_pattern="versioned",
        version_label="v2",
        owner_summary="founder@acme.com",
        sharing_summary="private",
        language="en",
        enriched_at=now,
    )
    FileClassificationRepository(db).upsert(
        file_id=file.id,
        document_type="Documentation",
        confidence=0.5,
        method="mime_document_default",
        classified_at=now,
    )
    FileRelationshipRepository(db).upsert(
        connector_id=connector.id,
        file_id=file.id,
        related_file_id=related.id,
        relationship_type=RelationshipType.SEQUENTIAL_VERSION,
        confidence=0.85,
        metadata={"match_reason": "explicit_version_sequence"},
        discovered_at=now,
    )
    db.commit()

    service = FileService(db)
    detail = service.get_detail(file.id, organization_id=user.organization_id)

    assert detail.metadata.version_label == "v2"
    assert detail.classification.document_type == "Documentation"
    assert len(detail.related_files) == 1
    assert detail.related_files[0].file.name == "Report_v1.pdf"
    assert detail.related_files[0].relationship.relationship_type == RelationshipType.SEQUENTIAL_VERSION


@requires_infra
def test_get_detail_rejects_a_file_from_another_organization(db: Session) -> None:
    user = _provision_user(db)
    other_user = _provision_user(db)
    connector = _provision_connector(db, organization_id=user.organization_id, user_id=user.id)
    file = _provision_file(db, connector_id=connector.id, name="Report.pdf")
    service = FileService(db)

    with pytest.raises(NotFoundError):
        service.get_detail(file.id, organization_id=other_user.organization_id)


@requires_infra
def test_get_detail_handles_a_file_with_no_enrichment_yet(db: Session) -> None:
    user = _provision_user(db)
    connector = _provision_connector(db, organization_id=user.organization_id, user_id=user.id)
    file = _provision_file(db, connector_id=connector.id, name="Report.pdf")
    service = FileService(db)

    detail = service.get_detail(file.id, organization_id=user.organization_id)

    assert detail.metadata is None
    assert detail.classification is None
    assert detail.extraction is None
    assert detail.knowledge_attributes == []
    assert detail.related_files == []
