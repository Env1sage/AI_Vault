import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from app.main import app
from app.presentation.dependencies.auth import get_current_user
from app.presentation.dependencies.services import (
    get_workflow_service,
    get_workflow_trigger_service,
)
from fastapi.testclient import TestClient
from vault_shared import ConflictError, NotFoundError, ValidationError

client = TestClient(app)


class _FakeWorkflow:
    def __init__(self, *, status: str = "active") -> None:
        self.id = uuid.uuid4()
        self.organization_id = uuid.uuid4()
        self.created_by_user_id = uuid.uuid4()
        self.name = "Archive Inactive Files"
        self.description = "Archives old files"
        self.status = status
        self.created_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)


class _FakeWorkflowVersion:
    def __init__(self, *, status: str = "draft") -> None:
        self.id = uuid.uuid4()
        self.workflow_id = uuid.uuid4()
        self.version_number = 1
        self.status = status
        self.published_at = None
        self.created_at = datetime.now(UTC)


class _FakeWorkflowNode:
    def __init__(self) -> None:
        self.id = uuid.uuid4()
        self.node_type = "trigger"
        self.name = "Start"
        self.config: dict = {}
        self.next_nodes: dict = {}
        self.position_x = 0
        self.position_y = 0


class _FakeWorkflowDetail:
    def __init__(self) -> None:
        self.workflow = _FakeWorkflow()
        self.published_version = None
        self.draft_version = _FakeWorkflowVersion()


class _FakeWorkflowTrigger:
    def __init__(self) -> None:
        self.id = uuid.uuid4()
        self.workflow_id = uuid.uuid4()
        self.trigger_type = "scheduled"
        self.config = {"cron": "0 2 * * *"}
        self.enabled = True
        self.created_at = datetime.now(UTC)


@pytest.fixture
def fake_workflow_service() -> MagicMock:
    service = MagicMock()
    app.dependency_overrides[get_workflow_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_workflow_service, None)


@pytest.fixture
def fake_trigger_service() -> MagicMock:
    service = MagicMock()
    app.dependency_overrides[get_workflow_trigger_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_workflow_trigger_service, None)


@pytest.fixture
def as_owner(owner_user):
    app.dependency_overrides[get_current_user] = lambda: owner_user
    yield owner_user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def as_member(member_user):
    app.dependency_overrides[get_current_user] = lambda: member_user
    yield member_user
    app.dependency_overrides.pop(get_current_user, None)


def test_create_workflow_requires_authentication(fake_workflow_service) -> None:
    response = client.post("/v1/workflows", json={"name": "Test"})
    assert response.status_code == 401


def test_owner_can_create_a_workflow(as_owner, fake_workflow_service) -> None:
    fake_workflow_service.create.return_value = _FakeWorkflow()

    response = client.post("/v1/workflows", json={"name": "Archive Inactive Files"})

    assert response.status_code == 201
    assert response.json()["status"] == "active"


def test_member_cannot_create_a_workflow(as_member, fake_workflow_service) -> None:
    response = client.post("/v1/workflows", json={"name": "Test"})

    assert response.status_code == 403
    fake_workflow_service.create.assert_not_called()


def test_list_workflows_returns_items(as_member, fake_workflow_service) -> None:
    fake_workflow_service.list_for_organization.return_value = [_FakeWorkflow()]

    response = client.get("/v1/workflows")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_workflow_returns_detail(as_member, fake_workflow_service) -> None:
    fake_workflow_service.get_detail.return_value = _FakeWorkflowDetail()

    response = client.get(f"/v1/workflows/{uuid.uuid4()}")

    assert response.status_code == 200
    body = response.json()
    assert body["draft_version"]["status"] == "draft"
    assert body["published_version"] is None


def test_get_workflow_returns_not_found(as_member, fake_workflow_service) -> None:
    fake_workflow_service.get_detail.side_effect = NotFoundError("Workflow not found.")

    response = client.get(f"/v1/workflows/{uuid.uuid4()}")

    assert response.status_code == 404


def test_get_or_create_draft_returns_version_and_nodes(as_owner, fake_workflow_service) -> None:
    fake_workflow_service.get_or_create_draft.return_value = (
        _FakeWorkflowVersion(),
        [_FakeWorkflowNode()],
    )

    response = client.post(f"/v1/workflows/{uuid.uuid4()}/draft")

    assert response.status_code == 200
    body = response.json()
    assert len(body["nodes"]) == 1


def test_replace_workflow_nodes_propagates_validation_error(as_owner, fake_workflow_service) -> None:
    fake_workflow_service.replace_nodes.side_effect = ValidationError(
        "A workflow must have exactly one trigger node."
    )

    response = client.put(
        f"/v1/workflows/{uuid.uuid4()}/versions/{uuid.uuid4()}/nodes",
        json={"nodes": [{"key": "n1", "node_type": "end", "name": "Done"}]},
    )

    assert response.status_code == 422


def test_publish_workflow_propagates_conflict_when_no_draft(as_owner, fake_workflow_service) -> None:
    fake_workflow_service.publish.side_effect = ConflictError(
        "This workflow has no draft version to publish."
    )

    response = client.post(f"/v1/workflows/{uuid.uuid4()}/publish")

    assert response.status_code == 409


def test_owner_can_publish_a_workflow(as_owner, fake_workflow_service) -> None:
    fake_workflow_service.publish.return_value = _FakeWorkflowVersion(status="published")

    response = client.post(f"/v1/workflows/{uuid.uuid4()}/publish")

    assert response.status_code == 201
    assert response.json()["status"] == "published"


def test_set_workflow_status_rejects_an_invalid_value(as_owner, fake_workflow_service) -> None:
    response = client.post(f"/v1/workflows/{uuid.uuid4()}/status", json={"status": "not_a_status"})

    assert response.status_code == 422
    fake_workflow_service.set_status.assert_not_called()


def test_owner_can_clone_a_workflow(as_owner, fake_workflow_service) -> None:
    fake_workflow_service.clone.return_value = _FakeWorkflow()

    response = client.post(f"/v1/workflows/{uuid.uuid4()}/clone")

    assert response.status_code == 201


def test_create_workflow_trigger_rejects_unknown_trigger_type(as_owner, fake_trigger_service) -> None:
    response = client.post(
        f"/v1/workflows/{uuid.uuid4()}/triggers", json={"trigger_type": "carrier_pigeon", "config": {}}
    )

    assert response.status_code == 422
    fake_trigger_service.create.assert_not_called()


def test_owner_can_create_a_scheduled_trigger(as_owner, fake_trigger_service) -> None:
    fake_trigger_service.create.return_value = _FakeWorkflowTrigger()

    response = client.post(
        f"/v1/workflows/{uuid.uuid4()}/triggers",
        json={"trigger_type": "scheduled", "config": {"cron": "0 2 * * *"}},
    )

    assert response.status_code == 201
    assert response.json()["trigger_type"] == "scheduled"


def test_member_cannot_toggle_a_trigger(as_member, fake_trigger_service) -> None:
    response = client.post(
        f"/v1/workflows/{uuid.uuid4()}/triggers/{uuid.uuid4()}/enabled", json={"enabled": False}
    )

    assert response.status_code == 403
    fake_trigger_service.set_enabled.assert_not_called()
