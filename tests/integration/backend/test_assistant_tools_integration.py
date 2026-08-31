"""Exact-numeric-correctness tests for the AI Storage Assistant's tool
layer (ADR-024) — the real anti-fabrication test: every tool's returned
figures must equal the seeded data exactly, and every tool must be
isolated to the calling organization even when a foreign org has data of
its own."""

import socket
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

import pytest
from app.application.assistant.tools import (
    ToolContext,
    get_cleanup_candidates,
    get_duplicate_group,
    get_duplicate_summary,
    get_file,
    get_inactive_files,
    get_large_files,
    get_old_files,
    get_storage_overview,
    get_storage_statistics,
)
from sqlalchemy.orm import Session
from vault_shared import get_settings
from vault_shared.ai_gateway import AIGateway
from vault_shared.ai_gateway.providers import ExtractiveCompletionProvider, LocalEmbeddingProvider
from vault_shared.db.models import ConnectorProvider, DriveType, RoleName, StorageAnalysisTrigger
from vault_shared.db.repositories import (
    DuplicateGroupRepository,
    FileRepository,
    OrganizationRepository,
    RoleRepository,
    StorageAnalysisJobRepository,
    StorageAnalysisSnapshotRepository,
    StorageConnectorRepository,
    StorageSourceRepository,
    UserRepository,
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


def _provision_org(db: Session):
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
    return organization, user, connector


def _provision_file(
    db: Session,
    *,
    connector_id: uuid.UUID,
    name: str,
    provider_file_id: str,
    size_bytes: int | None = 1024,
    checksum: str | None = None,
    modified_at: datetime | None = None,
    viewed_at: datetime | None = None,
):
    source = StorageSourceRepository(db).upsert(
        connector_id=connector_id,
        provider_drive_id="root",
        name="My Drive",
        drive_type=DriveType.MY_DRIVE,
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
        size_bytes=size_bytes,
        owner_email="founder@acme.com",
        is_shared=False,
        permissions_summary=None,
        version_id=None,
        checksum=checksum,
        web_view_link=None,
        provider_created_at=now,
        provider_modified_at=modified_at or now,
        provider_viewed_at=viewed_at,
        scanned_at=now,
    )
    db.commit()
    return file


def _seed_snapshot(db: Session, *, organization_id: uuid.UUID, **overrides):
    job = StorageAnalysisJobRepository(db).create(
        organization_id=organization_id,
        triggered_by=StorageAnalysisTrigger.MANUAL,
        triggered_by_user_id=None,
    )
    StorageAnalysisJobRepository(db).mark_completed(job)
    defaults = dict(
        organization_id=organization_id,
        storage_analysis_job_id=job.id,
        total_size_bytes=3_000,
        total_files=3,
        total_folders=0,
        breakdown_by_type_bytes={"documents": 2_000, "images": 1_000},
        breakdown_by_size_bucket_bytes={"< 1 MB": 3_000},
        breakdown_by_source_bytes={"src-1": {"name": "My Drive", "bytes": 3_000}},
        duplicate_group_count=1,
        duplicate_file_count=2,
        duplicate_recoverable_bytes=500,
        large_file_count=1,
        large_file_bytes=2_000,
        old_file_count=1,
        old_file_bytes=1_000,
        inactive_file_count=1,
        inactive_file_bytes=1_000,
        temporary_candidate_count=0,
        temporary_candidate_bytes=0,
        total_potential_savings_bytes=500,
    )
    defaults.update(overrides)
    snapshot = StorageAnalysisSnapshotRepository(db).create(**defaults)
    db.commit()
    return snapshot, job


def _seed_duplicate_group(db: Session, *, organization_id: uuid.UUID, file_a, file_b):
    job = StorageAnalysisJobRepository(db).create(
        organization_id=organization_id,
        triggered_by=StorageAnalysisTrigger.MANUAL,
        triggered_by_user_id=None,
    )
    repo = DuplicateGroupRepository(db)
    group = repo.upsert_group(
        organization_id=organization_id,
        storage_analysis_job_id=job.id,
        checksum="checksum-abc123",
        file_count=2,
        total_size_bytes=(file_a.size_bytes or 0) + (file_b.size_bytes or 0),
        recoverable_size_bytes=file_b.size_bytes or 0,
        recommended_keep_file_id=file_a.id,
        recommended_keep_reason="Most recently modified.",
        recommended_keep_confidence=0.9,
    )
    repo.replace_members(group, [(file_a.id, True), (file_b.id, False)])
    db.commit()
    return group


def _ctx(db: Session, *, organization_id: uuid.UUID, user_id: uuid.UUID) -> ToolContext:
    gateway = AIGateway(
        embedding_provider=LocalEmbeddingProvider(), completion_provider=ExtractiveCompletionProvider()
    )
    return ToolContext(db=db, organization_id=organization_id, user_id=user_id, ai_gateway=gateway)


@requires_infra
def test_get_storage_overview_reports_unavailable_when_no_snapshot_exists(db: Session) -> None:
    org, user, _connector = _provision_org(db)

    result = get_storage_overview(_ctx(db, organization_id=org.id, user_id=user.id), {})

    assert result["available"] is False
    assert result["as_of"] is None


@requires_infra
def test_get_storage_overview_matches_the_seeded_snapshot_exactly(db: Session) -> None:
    org, user, _connector = _provision_org(db)
    snapshot, _job = _seed_snapshot(db, organization_id=org.id)

    result = get_storage_overview(_ctx(db, organization_id=org.id, user_id=user.id), {})

    assert result["available"] is True
    assert result["total_files"] == snapshot.total_files
    assert result["total_size_bytes"] == snapshot.total_size_bytes
    assert result["duplicate_group_count"] == snapshot.duplicate_group_count
    assert result["duplicate_recoverable_bytes"] == snapshot.duplicate_recoverable_bytes
    assert result["total_potential_savings_bytes"] == snapshot.total_potential_savings_bytes
    assert result["total_size_human"] == "2.9 KB"


@requires_infra
def test_get_storage_overview_never_sees_another_organizations_snapshot(db: Session) -> None:
    org_a, user_a, _ = _provision_org(db)
    org_b, _user_b, _ = _provision_org(db)
    _seed_snapshot(db, organization_id=org_b.id, total_files=999_999)

    result = get_storage_overview(_ctx(db, organization_id=org_a.id, user_id=user_a.id), {})

    assert result["available"] is False


@requires_infra
def test_get_storage_statistics_percentages_sum_correctly(db: Session) -> None:
    org, user, _connector = _provision_org(db)
    _seed_snapshot(db, organization_id=org.id)

    result = get_storage_statistics(_ctx(db, organization_id=org.id, user_id=user.id), {})

    by_type = {row["category"]: row for row in result["by_type"]}
    assert by_type["documents"]["bytes"] == 2_000
    assert by_type["documents"]["percent"] == 66.7
    assert by_type["images"]["percent"] == 33.3


@requires_infra
def test_get_duplicate_summary_reports_exact_recoverable_bytes(db: Session) -> None:
    org, user, connector = _provision_org(db)
    file_a = _provision_file(
        db, connector_id=connector.id, name="report.pdf", provider_file_id="f-1",
        size_bytes=5_000, checksum="dup-1",
    )
    file_b = _provision_file(
        db, connector_id=connector.id, name="report (copy).pdf", provider_file_id="f-2",
        size_bytes=5_000, checksum="dup-1",
    )
    _seed_duplicate_group(db, organization_id=org.id, file_a=file_a, file_b=file_b)

    result = get_duplicate_summary(_ctx(db, organization_id=org.id, user_id=user.id), {})

    assert result["total_groups"] == 1
    group = result["groups"][0]
    assert group["file_count"] == 2
    assert group["recoverable_size_bytes"] == 5_000
    assert group["recommended_keep_name"] == "report.pdf"
    assert "report.pdf" in group["sample_file_names"]


@requires_infra
def test_get_duplicate_group_cross_org_id_is_not_found(db: Session) -> None:
    org_a, user_a, _ = _provision_org(db)
    org_b, _user_b, connector_b = _provision_org(db)
    file_a = _provision_file(
        db, connector_id=connector_b.id, name="a.pdf", provider_file_id="f-a", checksum="x"
    )
    file_b = _provision_file(
        db, connector_id=connector_b.id, name="b.pdf", provider_file_id="f-b", checksum="x"
    )
    group = _seed_duplicate_group(db, organization_id=org_b.id, file_a=file_a, file_b=file_b)

    result = get_duplicate_group(
        _ctx(db, organization_id=org_a.id, user_id=user_a.id), {"group_id": str(group.id)}
    )

    assert "error" in result


@requires_infra
def test_get_large_files_echoes_the_applied_threshold(db: Session) -> None:
    org, user, connector = _provision_org(db)
    _provision_file(
        db, connector_id=connector.id, name="huge.zip", provider_file_id="f-1",
        size_bytes=200 * 1024 * 1024,
    )
    _provision_file(
        db, connector_id=connector.id, name="small.txt", provider_file_id="f-2", size_bytes=1_024
    )

    result = get_large_files(
        _ctx(db, organization_id=org.id, user_id=user.id), {"min_size_bytes": 100 * 1024 * 1024}
    )

    assert result["total"] == 1
    assert result["threshold"]["value"] == 100 * 1024 * 1024
    assert result["files"][0]["name"] == "huge.zip"


@requires_infra
def test_get_large_files_min_size_is_clamped_to_the_configured_ceiling(db: Session) -> None:
    org, user, _connector = _provision_org(db)
    settings = get_settings()

    result = get_large_files(
        _ctx(db, organization_id=org.id, user_id=user.id),
        {"min_size_bytes": settings.ai_max_large_file_threshold_bytes * 10},
    )

    assert result["threshold"]["value"] == settings.ai_max_large_file_threshold_bytes


@requires_infra
def test_get_old_files_and_inactive_files_never_cross_organizations(db: Session) -> None:
    org_a, user_a, _ = _provision_org(db)
    org_b, _user_b, connector_b = _provision_org(db)
    old_date = datetime.now(UTC) - timedelta(days=800)
    _provision_file(
        db, connector_id=connector_b.id, name="ancient.docx", provider_file_id="f-1",
        modified_at=old_date, viewed_at=old_date,
    )

    old_result = get_old_files(_ctx(db, organization_id=org_a.id, user_id=user_a.id), {})
    inactive_result = get_inactive_files(_ctx(db, organization_id=org_a.id, user_id=user_a.id), {})

    assert old_result["total"] == 0
    assert inactive_result["total"] == 0


@requires_infra
def test_get_cleanup_candidates_returns_only_heuristic_matches(db: Session) -> None:
    org, user, connector = _provision_org(db)
    _provision_file(db, connector_id=connector.id, name="draft.tmp", provider_file_id="f-1")
    _provision_file(db, connector_id=connector.id, name="final_report.pdf", provider_file_id="f-2")

    result = get_cleanup_candidates(_ctx(db, organization_id=org.id, user_id=user.id), {})

    names = [f["name"] for f in result["files"]]
    assert "draft.tmp" in names
    assert "final_report.pdf" not in names
    assert "note" in result


@requires_infra
def test_get_file_requires_org_ownership(db: Session) -> None:
    org_a, user_a, _ = _provision_org(db)
    org_b, _user_b, connector_b = _provision_org(db)
    file_b = _provision_file(
        db, connector_id=connector_b.id, name="secret.pdf", provider_file_id="f-1"
    )

    result = get_file(
        _ctx(db, organization_id=org_a.id, user_id=user_a.id), {"file_id": str(file_b.id)}
    )

    assert result["found"] is False


@requires_infra
def test_get_file_returns_exact_metadata_for_an_owned_file(db: Session) -> None:
    org, user, connector = _provision_org(db)
    file = _provision_file(
        db, connector_id=connector.id, name="Q3 Report.pdf", provider_file_id="f-1", size_bytes=4_096
    )

    result = get_file(
        _ctx(db, organization_id=org.id, user_id=user.id), {"file_id": str(file.id)}
    )

    assert result["found"] is True
    assert result["name"] == "Q3 Report.pdf"
    assert result["size_bytes"] == 4_096


@requires_infra
def test_every_tool_ignores_an_injected_organization_id_in_args(db: Session) -> None:
    """The security boundary is `ToolContext`, not the args dict — a
    handler must produce the SAME result regardless of what an LLM stuffs
    into `args["organization_id"]`."""
    org, user, _connector = _provision_org(db)
    ctx = _ctx(db, organization_id=org.id, user_id=user.id)
    foreign_org_id = str(uuid.uuid4())

    honest = get_storage_overview(ctx, {})
    tampered = get_storage_overview(ctx, {"organization_id": foreign_org_id})

    assert honest == tampered
