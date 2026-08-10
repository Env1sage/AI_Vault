import socket
import uuid
from urllib.parse import urlparse

import pytest
from app.application.auth_service import AuthService
from app.application.workflow_policy_service import WorkflowPolicyService
from app.application.workflow_service import WorkflowService
from app.infrastructure.auth.google_identity import GoogleUserInfo
from sqlalchemy.orm import Session
from vault_shared import NotFoundError, ValidationError, get_settings
from vault_shared.db.models import WorkflowPolicyStatus, WorkflowVersionStatus
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


_SIMPLE_NODES = [
    {"key": "n1", "node_type": "trigger", "name": "Start", "config": {}, "next_nodes": {"default": "n2"}},
    {"key": "n2", "node_type": "end", "name": "Done", "config": {}, "next_nodes": {}},
]


@requires_infra
def test_create_creates_a_workflow_with_a_draft_version(db: Session) -> None:
    user = _provision_user(db)
    service = WorkflowService(db)

    workflow = service.create(
        organization_id=user.organization_id, user_id=user.id, name="Archive stuff", description=None
    )

    detail = service.get_detail(workflow.id, organization_id=user.organization_id)
    assert detail.published_version is None
    assert detail.draft_version is not None
    assert detail.draft_version.status == WorkflowVersionStatus.DRAFT


@requires_infra
def test_replace_nodes_rejects_a_graph_with_no_trigger(db: Session) -> None:
    user = _provision_user(db)
    service = WorkflowService(db)
    workflow = service.create(
        organization_id=user.organization_id, user_id=user.id, name="Test", description=None
    )
    version, _nodes = service.get_or_create_draft(
        workflow.id, organization_id=user.organization_id, user_id=user.id
    )

    with pytest.raises(ValidationError):
        service.replace_nodes(
            version.id,
            workflow_id=workflow.id,
            organization_id=user.organization_id,
            nodes=[{"key": "n1", "node_type": "end", "name": "Done"}],
        )


@requires_infra
def test_replace_nodes_rejects_an_unknown_next_node_reference(db: Session) -> None:
    user = _provision_user(db)
    service = WorkflowService(db)
    workflow = service.create(
        organization_id=user.organization_id, user_id=user.id, name="Test", description=None
    )
    version, _nodes = service.get_or_create_draft(
        workflow.id, organization_id=user.organization_id, user_id=user.id
    )

    with pytest.raises(ValidationError):
        service.replace_nodes(
            version.id,
            workflow_id=workflow.id,
            organization_id=user.organization_id,
            nodes=[
                {
                    "key": "n1",
                    "node_type": "trigger",
                    "name": "Start",
                    "next_nodes": {"default": "ghost"},
                },
                {"key": "n2", "node_type": "end", "name": "Done"},
            ],
        )


@requires_infra
def test_replace_nodes_translates_client_keys_to_real_ids(db: Session) -> None:
    user = _provision_user(db)
    service = WorkflowService(db)
    workflow = service.create(
        organization_id=user.organization_id, user_id=user.id, name="Test", description=None
    )
    version, _nodes = service.get_or_create_draft(
        workflow.id, organization_id=user.organization_id, user_id=user.id
    )

    nodes = service.replace_nodes(
        version.id, workflow_id=workflow.id, organization_id=user.organization_id, nodes=_SIMPLE_NODES
    )

    trigger = next(n for n in nodes if n.node_type == "trigger")
    end = next(n for n in nodes if n.node_type == "end")
    assert trigger.next_nodes["default"] == str(end.id)


@requires_infra
def test_publish_requires_at_least_one_node(db: Session) -> None:
    user = _provision_user(db)
    service = WorkflowService(db)
    workflow = service.create(
        organization_id=user.organization_id, user_id=user.id, name="Empty", description=None
    )

    with pytest.raises(ValidationError):
        service.publish(workflow.id, organization_id=user.organization_id, user_id=user.id)


@requires_infra
def test_publish_then_rollback_restores_an_older_version(db: Session) -> None:
    user = _provision_user(db)
    service = WorkflowService(db)
    workflow = service.create(
        organization_id=user.organization_id, user_id=user.id, name="Test", description=None
    )
    version1, _ = service.get_or_create_draft(
        workflow.id, organization_id=user.organization_id, user_id=user.id
    )
    service.replace_nodes(
        version1.id, workflow_id=workflow.id, organization_id=user.organization_id, nodes=_SIMPLE_NODES
    )
    service.publish(workflow.id, organization_id=user.organization_id, user_id=user.id)

    # Publishing a second version supersedes the first.
    version2, _ = service.get_or_create_draft(
        workflow.id, organization_id=user.organization_id, user_id=user.id
    )
    service.replace_nodes(
        version2.id, workflow_id=workflow.id, organization_id=user.organization_id, nodes=_SIMPLE_NODES
    )
    service.publish(workflow.id, organization_id=user.organization_id, user_id=user.id)

    detail = service.get_detail(workflow.id, organization_id=user.organization_id)
    assert detail.published_version.id == version2.id

    rolled_back = service.rollback_to_version(
        workflow.id, version1.id, organization_id=user.organization_id, user_id=user.id
    )
    assert rolled_back.id == version1.id

    detail_after = service.get_detail(workflow.id, organization_id=user.organization_id)
    assert detail_after.published_version.id == version1.id


@requires_infra
def test_get_or_create_draft_clones_nodes_from_the_published_version(db: Session) -> None:
    user = _provision_user(db)
    service = WorkflowService(db)
    workflow = service.create(
        organization_id=user.organization_id, user_id=user.id, name="Test", description=None
    )
    version1, _ = service.get_or_create_draft(
        workflow.id, organization_id=user.organization_id, user_id=user.id
    )
    service.replace_nodes(
        version1.id, workflow_id=workflow.id, organization_id=user.organization_id, nodes=_SIMPLE_NODES
    )
    service.publish(workflow.id, organization_id=user.organization_id, user_id=user.id)

    version2, nodes2 = service.get_or_create_draft(
        workflow.id, organization_id=user.organization_id, user_id=user.id
    )

    assert version2.id != version1.id
    assert version2.status == WorkflowVersionStatus.DRAFT
    assert len(nodes2) == 2


@requires_infra
def test_clone_copies_the_published_graph_into_a_new_workflow(db: Session) -> None:
    user = _provision_user(db)
    service = WorkflowService(db)
    workflow = service.create(
        organization_id=user.organization_id, user_id=user.id, name="Original", description=None
    )
    version, _ = service.get_or_create_draft(
        workflow.id, organization_id=user.organization_id, user_id=user.id
    )
    service.replace_nodes(
        version.id, workflow_id=workflow.id, organization_id=user.organization_id, nodes=_SIMPLE_NODES
    )
    service.publish(workflow.id, organization_id=user.organization_id, user_id=user.id)

    cloned = service.clone(workflow.id, organization_id=user.organization_id, user_id=user.id)

    assert cloned.id != workflow.id
    cloned_detail = service.get_detail(cloned.id, organization_id=user.organization_id)
    assert cloned_detail.draft_version is not None


@requires_infra
def test_set_status_rejects_cross_organization_access(db: Session) -> None:
    user = _provision_user(db)
    other_user = _provision_user(db)
    service = WorkflowService(db)
    workflow = service.create(
        organization_id=user.organization_id, user_id=user.id, name="Test", description=None
    )

    with pytest.raises(NotFoundError):
        service.set_status(
            workflow.id,
            organization_id=other_user.organization_id,
            user_id=other_user.id,
            status="paused",
        )


@requires_infra
def test_policy_versions_increment_and_publishing_archives_the_prior_version(db: Session) -> None:
    user = _provision_user(db)
    service = WorkflowPolicyService(db)

    v1 = service.create_draft(
        organization_id=user.organization_id,
        user_id=user.id,
        policy_key="archive-small",
        name="Archive small batches",
        description=None,
        effect="require_approval",
        conditions={},
    )
    assert v1.version == 1
    service.publish(v1.id, organization_id=user.organization_id, user_id=user.id)

    v2 = service.create_draft(
        organization_id=user.organization_id,
        user_id=user.id,
        policy_key="archive-small",
        name="Archive small batches (v2)",
        description=None,
        effect="auto_execute",
        conditions={"max_affected_files": 5},
    )
    assert v2.version == 2
    service.publish(v2.id, organization_id=user.organization_id, user_id=user.id)

    versions = service.list_versions(organization_id=user.organization_id, policy_key="archive-small")
    assert len(versions) == 2
    v1_reloaded = next(v for v in versions if v.id == v1.id)
    assert v1_reloaded.status == WorkflowPolicyStatus.ARCHIVED

    org_list = service.list_for_organization(user.organization_id)
    assert len(org_list) == 1
    assert org_list[0].id == v2.id


@requires_infra
def test_publish_a_second_policy_key_does_not_conflict_with_the_first(db: Session) -> None:
    user = _provision_user(db)
    service = WorkflowPolicyService(db)

    policy_a = service.create_draft(
        organization_id=user.organization_id, user_id=user.id, policy_key="policy-a",
        name="Policy A", description=None, effect="skip", conditions={},
    )
    policy_b = service.create_draft(
        organization_id=user.organization_id, user_id=user.id, policy_key="policy-b",
        name="Policy B", description=None, effect="auto_execute", conditions={},
    )
    service.publish(policy_a.id, organization_id=user.organization_id, user_id=user.id)
    service.publish(policy_b.id, organization_id=user.organization_id, user_id=user.id)

    org_list = service.list_for_organization(user.organization_id)
    assert {p.policy_key for p in org_list} == {"policy-a", "policy-b"}
    assert all(p.status == WorkflowPolicyStatus.PUBLISHED for p in org_list)
