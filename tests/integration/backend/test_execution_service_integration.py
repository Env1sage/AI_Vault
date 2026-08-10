import socket
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

import pytest
from app.application.approval_service import ApprovalService
from app.application.auth_service import AuthService
from app.application.execution_job_service import ExecutionJobService
from app.application.execution_plan_service import ExecutionPlanService
from app.infrastructure.auth.google_identity import GoogleUserInfo
from sqlalchemy.orm import Session
from vault_shared import ConflictError, NotFoundError, ValidationError, get_settings
from vault_shared.db.models import (
    ApprovalStatus,
    ConnectorProvider,
    DriveType,
    ExecutionActionType,
    ExecutionJobStatus,
    ExecutionPlanStatus,
    RecommendationStatus,
)
from vault_shared.db.repositories import (
    ApprovalRequestRepository,
    ConnectorCredentialsRepository,
    ExecutionJobRepository,
    ExecutionPlanRepository,
    ExecutionStepRepository,
    FileRepository,
    RecommendationJobRepository,
    RecommendationRepository,
    RollbackRecordRepository,
    StorageConnectorRepository,
    StorageSourceRepository,
)
from vault_shared.db.session import get_session_factory
from vault_shared.execution import DRIVE_WRITE_SCOPE
from vault_shared.security.encryption import encrypt_token


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


def _provision_connector(db: Session, *, organization_id: uuid.UUID, user_id: uuid.UUID, granted_scopes: str):
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
        granted_scopes=granted_scopes,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db.commit()
    return connector


def _provision_file(db: Session, *, connector_id: uuid.UUID, name: str, provider_file_id: str, size_bytes: int = 100):
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
        size_bytes=size_bytes,
        owner_email="founder@acme.com",
        is_shared=False,
        permissions_summary=None,
        version_id=None,
        checksum=None,
        provider_created_at=now,
        provider_modified_at=now,
        provider_viewed_at=None,
        scanned_at=now,
    )
    db.commit()
    return file


def _provision_recommendation(
    db: Session,
    *,
    organization_id: uuid.UUID,
    rule_name: str,
    affected_file_ids: list[uuid.UUID],
    status: str = RecommendationStatus.ACTIVE,
):
    job = RecommendationJobRepository(db).create(
        organization_id=organization_id, triggered_by="manual", triggered_by_user_id=None
    )
    recommendation = RecommendationRepository(db).upsert(
        organization_id=organization_id,
        recommendation_job_id=job.id,
        rule_name=rule_name,
        category="storage_optimization",
        title=f"{rule_name} fired",
        description="A test recommendation.",
        confidence=0.8,
        estimated_impact="some impact",
        impact_value=10.0,
        risk_level="low",
        suggested_action="Do something.",
        related_departments=[],
        affected_file_ids=[str(fid) for fid in affected_file_ids],
        priority_score=50.0,
    )
    if status != RecommendationStatus.ACTIVE:
        recommendation.status = status
        db.flush()
    db.commit()
    return recommendation


# ----------------------------------------------------------------------
# ExecutionPlanService
# ----------------------------------------------------------------------


@requires_infra
def test_create_plan_builds_a_step_per_affected_file_with_low_risk(db: Session) -> None:
    user = _provision_user(db)
    connector = _provision_connector(
        db, organization_id=user.organization_id, user_id=user.id, granted_scopes=DRIVE_WRITE_SCOPE
    )
    file_a = _provision_file(db, connector_id=connector.id, name="A.txt", provider_file_id="f-a")
    file_b = _provision_file(db, connector_id=connector.id, name="B.txt", provider_file_id="f-b")
    recommendation = _provision_recommendation(
        db, organization_id=user.organization_id, rule_name="duplicate_files",
        affected_file_ids=[file_a.id, file_b.id],
    )
    service = ExecutionPlanService(db)

    plan = service.create_plan(recommendation.id, organization_id=user.organization_id, user_id=user.id)

    assert plan.status == ExecutionPlanStatus.PENDING_APPROVAL
    assert plan.risk_level == "low"
    assert plan.rollback_available is True

    detail = service.get_detail(plan.id, organization_id=user.organization_id)
    assert len(detail.steps) == 2
    assert {s.action_type for s in detail.steps} == {ExecutionActionType.REMOVE_DUPLICATE}

    approval = ApprovalRequestRepository(db).get_by_plan(plan.id)
    assert approval is not None
    assert approval.status == ApprovalStatus.PENDING


@requires_infra
def test_create_plan_rejects_a_non_executable_rule(db: Session) -> None:
    user = _provision_user(db)
    connector = _provision_connector(
        db, organization_id=user.organization_id, user_id=user.id, granted_scopes=DRIVE_WRITE_SCOPE
    )
    file_a = _provision_file(db, connector_id=connector.id, name="A.txt", provider_file_id="f-a")
    recommendation = _provision_recommendation(
        db, organization_id=user.organization_id, rule_name="orphaned_ownership",
        affected_file_ids=[file_a.id],
    )
    service = ExecutionPlanService(db)

    with pytest.raises(ValidationError):
        service.create_plan(recommendation.id, organization_id=user.organization_id, user_id=user.id)


@requires_infra
def test_create_plan_rejects_a_resolved_recommendation(db: Session) -> None:
    user = _provision_user(db)
    connector = _provision_connector(
        db, organization_id=user.organization_id, user_id=user.id, granted_scopes=DRIVE_WRITE_SCOPE
    )
    file_a = _provision_file(db, connector_id=connector.id, name="A.txt", provider_file_id="f-a")
    recommendation = _provision_recommendation(
        db, organization_id=user.organization_id, rule_name="duplicate_files",
        affected_file_ids=[file_a.id], status=RecommendationStatus.RESOLVED,
    )
    service = ExecutionPlanService(db)

    with pytest.raises(ConflictError):
        service.create_plan(recommendation.id, organization_id=user.organization_id, user_id=user.id)


@requires_infra
def test_create_plan_rejects_a_second_plan_while_one_is_active(db: Session) -> None:
    user = _provision_user(db)
    connector = _provision_connector(
        db, organization_id=user.organization_id, user_id=user.id, granted_scopes=DRIVE_WRITE_SCOPE
    )
    file_a = _provision_file(db, connector_id=connector.id, name="A.txt", provider_file_id="f-a")
    recommendation = _provision_recommendation(
        db, organization_id=user.organization_id, rule_name="duplicate_files",
        affected_file_ids=[file_a.id],
    )
    service = ExecutionPlanService(db)
    service.create_plan(recommendation.id, organization_id=user.organization_id, user_id=user.id)

    with pytest.raises(ConflictError):
        service.create_plan(recommendation.id, organization_id=user.organization_id, user_id=user.id)


@requires_infra
def test_create_plan_computes_high_risk_for_many_files(db: Session) -> None:
    user = _provision_user(db)
    connector = _provision_connector(
        db, organization_id=user.organization_id, user_id=user.id, granted_scopes=DRIVE_WRITE_SCOPE
    )
    files = [
        _provision_file(db, connector_id=connector.id, name=f"F{i}.txt", provider_file_id=f"f-{i}")
        for i in range(101)
    ]
    recommendation = _provision_recommendation(
        db, organization_id=user.organization_id, rule_name="archive_candidates",
        affected_file_ids=[f.id for f in files],
    )
    service = ExecutionPlanService(db)

    plan = service.create_plan(recommendation.id, organization_id=user.organization_id, user_id=user.id)

    assert plan.risk_level == "high"


# ----------------------------------------------------------------------
# ApprovalService
# ----------------------------------------------------------------------


def _provision_plan_with_approval(db: Session, *, user, granted_scopes: str, rule_name: str = "duplicate_files"):
    connector = _provision_connector(
        db, organization_id=user.organization_id, user_id=user.id, granted_scopes=granted_scopes
    )
    file_a = _provision_file(
        db, connector_id=connector.id, name="A.txt", provider_file_id=f"f-{uuid.uuid4().hex[:8]}"
    )
    recommendation = _provision_recommendation(
        db, organization_id=user.organization_id, rule_name=rule_name, affected_file_ids=[file_a.id]
    )
    plan = ExecutionPlanService(db).create_plan(
        recommendation.id, organization_id=user.organization_id, user_id=user.id
    )
    approval = ApprovalRequestRepository(db).get_by_plan(plan.id)
    return plan, approval


@requires_infra
def test_decide_approve_is_blocked_when_the_connector_lacks_write_scope(db: Session) -> None:
    user = _provision_user(db)
    _plan, approval = _provision_plan_with_approval(
        db, user=user, granted_scopes="https://www.googleapis.com/auth/drive.readonly"
    )
    service = ApprovalService(db)

    with pytest.raises(ValidationError):
        service.decide(
            approval.id, organization_id=user.organization_id, user_id=user.id,
            decision="approve", comments=None, ip_address=None,
        )


@requires_infra
def test_decide_approve_creates_an_execution_job_when_permissions_are_satisfied(db: Session) -> None:
    user = _provision_user(db)
    plan, approval = _provision_plan_with_approval(db, user=user, granted_scopes=DRIVE_WRITE_SCOPE)
    service = ApprovalService(db)

    decided = service.decide(
        approval.id, organization_id=user.organization_id, user_id=user.id,
        decision="approve", comments="go ahead", ip_address="127.0.0.1",
    )

    assert decided.status == ApprovalStatus.APPROVED
    updated_plan = ExecutionPlanRepository(db).get_by_id(plan.id)
    assert updated_plan.status == ExecutionPlanStatus.APPROVED

    jobs = ExecutionJobRepository(db).list_for_plan(plan.id)
    assert len(jobs) == 1
    assert jobs[0].status == ExecutionJobStatus.PENDING
    assert jobs[0].triggered_by_user_id == user.id


@requires_infra
def test_decide_reject_is_terminal_and_creates_no_job(db: Session) -> None:
    user = _provision_user(db)
    plan, approval = _provision_plan_with_approval(db, user=user, granted_scopes=DRIVE_WRITE_SCOPE)
    service = ApprovalService(db)

    decided = service.decide(
        approval.id, organization_id=user.organization_id, user_id=user.id,
        decision="reject", comments=None, ip_address=None,
    )

    assert decided.status == ApprovalStatus.REJECTED
    updated_plan = ExecutionPlanRepository(db).get_by_id(plan.id)
    assert updated_plan.status == ExecutionPlanStatus.REJECTED
    assert ExecutionJobRepository(db).list_for_plan(plan.id) == []

    with pytest.raises(ConflictError):
        service.decide(
            approval.id, organization_id=user.organization_id, user_id=user.id,
            decision="approve", comments=None, ip_address=None,
        )


@requires_infra
def test_bulk_decide_isolates_a_bad_id_from_the_rest(db: Session) -> None:
    user = _provision_user(db)
    _plan1, approval1 = _provision_plan_with_approval(db, user=user, granted_scopes=DRIVE_WRITE_SCOPE)
    service = ApprovalService(db)

    results = service.bulk_decide(
        [approval1.id, uuid.uuid4()],
        organization_id=user.organization_id, user_id=user.id,
        decision="reject", comments=None, ip_address=None,
    )

    assert len(results) == 1
    assert results[0].id == approval1.id
    assert results[0].status == ApprovalStatus.REJECTED


# ----------------------------------------------------------------------
# ExecutionJobService
# ----------------------------------------------------------------------


@requires_infra
def test_cancel_rejects_an_already_completed_job(db: Session) -> None:
    user = _provision_user(db)
    plan, approval = _provision_plan_with_approval(db, user=user, granted_scopes=DRIVE_WRITE_SCOPE)
    ApprovalService(db).decide(
        approval.id, organization_id=user.organization_id, user_id=user.id,
        decision="approve", comments=None, ip_address=None,
    )
    jobs = ExecutionJobRepository(db)
    job = jobs.list_for_plan(plan.id)[0]
    jobs.mark_completed(job)
    db.commit()

    service = ExecutionJobService(db)
    with pytest.raises(ConflictError):
        service.cancel(job, organization_id=user.organization_id, user_id=user.id)


@requires_infra
def test_pause_only_allowed_while_running(db: Session) -> None:
    user = _provision_user(db)
    plan, approval = _provision_plan_with_approval(db, user=user, granted_scopes=DRIVE_WRITE_SCOPE)
    ApprovalService(db).decide(
        approval.id, organization_id=user.organization_id, user_id=user.id,
        decision="approve", comments=None, ip_address=None,
    )
    jobs = ExecutionJobRepository(db)
    job = jobs.list_for_plan(plan.id)[0]

    service = ExecutionJobService(db)
    with pytest.raises(ConflictError):
        service.pause(job, organization_id=user.organization_id, user_id=user.id)

    jobs.mark_running(job)
    db.commit()
    paused = service.pause(job, organization_id=user.organization_id, user_id=user.id)
    assert jobs.is_pause_requested(paused.id) is True


@requires_infra
def test_resume_only_allowed_while_paused(db: Session) -> None:
    user = _provision_user(db)
    plan, approval = _provision_plan_with_approval(db, user=user, granted_scopes=DRIVE_WRITE_SCOPE)
    ApprovalService(db).decide(
        approval.id, organization_id=user.organization_id, user_id=user.id,
        decision="approve", comments=None, ip_address=None,
    )
    jobs = ExecutionJobRepository(db)
    job = jobs.list_for_plan(plan.id)[0]
    jobs.mark_running(job)
    jobs.mark_paused(job)
    db.commit()

    service = ExecutionJobService(db)
    resumed = service.resume(job, organization_id=user.organization_id, user_id=user.id)
    assert resumed.status == ExecutionJobStatus.PENDING


@requires_infra
def test_trigger_rollback_requires_a_rollbackable_record(db: Session) -> None:
    user = _provision_user(db)
    plan, _approval = _provision_plan_with_approval(db, user=user, granted_scopes=DRIVE_WRITE_SCOPE)
    service = ExecutionJobService(db)

    with pytest.raises(ConflictError):
        service.trigger_rollback(plan.id, organization_id=user.organization_id, user_id=user.id)


@requires_infra
def test_trigger_rollback_creates_a_rollback_job_when_a_record_exists(db: Session) -> None:
    user = _provision_user(db)
    plan, _approval = _provision_plan_with_approval(db, user=user, granted_scopes=DRIVE_WRITE_SCOPE)
    step = ExecutionStepRepository(db).list_for_plan(plan.id)[0]
    RollbackRecordRepository(db).create(execution_step_id=step.id, pre_state={"trashed": False})
    db.commit()

    service = ExecutionJobService(db)
    job = service.trigger_rollback(plan.id, organization_id=user.organization_id, user_id=user.id)

    assert job.is_rollback is True
    assert job.status == ExecutionJobStatus.PENDING

    with pytest.raises(ConflictError):
        service.trigger_rollback(plan.id, organization_id=user.organization_id, user_id=user.id)


@requires_infra
def test_trigger_rollback_rejects_an_unknown_plan(db: Session) -> None:
    user = _provision_user(db)
    service = ExecutionJobService(db)

    with pytest.raises(NotFoundError):
        service.trigger_rollback(uuid.uuid4(), organization_id=user.organization_id, user_id=user.id)
