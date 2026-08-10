import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from app.main import app
from app.presentation.dependencies.auth import get_current_user
from app.presentation.dependencies.services import get_workflow_execution_service
from fastapi.testclient import TestClient
from vault_shared import ConflictError, NotFoundError

client = TestClient(app)


class _FakeExecution:
    def __init__(self, *, status: str = "pending") -> None:
        self.id = uuid.uuid4()
        self.workflow_id = uuid.uuid4()
        self.workflow_version_id = uuid.uuid4()
        self.organization_id = uuid.uuid4()
        self.status = status
        self.trigger_type = "manual"
        self.current_node_id = None
        self.error = None
        self.started_at = None
        self.completed_at = None
        self.created_at = datetime.now(UTC)


class _FakeNodeExecution:
    def __init__(self) -> None:
        self.id = uuid.uuid4()
        self.workflow_node_id = uuid.uuid4()
        self.status = "completed"
        self.output_context: dict = {}
        self.error = None
        self.started_at = datetime.now(UTC)
        self.completed_at = datetime.now(UTC)


class _FakeExecutionDetail:
    def __init__(self) -> None:
        self.execution = _FakeExecution(status="completed")
        self.node_executions = [_FakeNodeExecution()]


@pytest.fixture
def fake_service() -> MagicMock:
    service = MagicMock()
    app.dependency_overrides[get_workflow_execution_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_workflow_execution_service, None)


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


def test_trigger_manually_requires_authentication(fake_service) -> None:
    response = client.post(f"/v1/workflows/{uuid.uuid4()}/executions")
    assert response.status_code == 401


def test_owner_can_trigger_manually(as_owner, fake_service) -> None:
    fake_service.trigger_manual.return_value = _FakeExecution()

    response = client.post(f"/v1/workflows/{uuid.uuid4()}/executions")

    assert response.status_code == 201
    assert response.json()["status"] == "pending"


def test_member_cannot_trigger_manually(as_member, fake_service) -> None:
    response = client.post(f"/v1/workflows/{uuid.uuid4()}/executions")

    assert response.status_code == 403
    fake_service.trigger_manual.assert_not_called()


def test_trigger_manually_propagates_conflict_when_no_published_version(as_owner, fake_service) -> None:
    fake_service.trigger_manual.side_effect = ConflictError(
        "This workflow has no published version to run."
    )

    response = client.post(f"/v1/workflows/{uuid.uuid4()}/executions")

    assert response.status_code == 409


def test_list_workflow_executions_returns_items(as_member, fake_service) -> None:
    fake_service.list_for_organization.return_value = [_FakeExecution()]

    response = client.get("/v1/workflow-executions")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_workflow_execution_returns_detail_with_node_executions(as_member, fake_service) -> None:
    fake_service.get_detail.return_value = _FakeExecutionDetail()

    response = client.get(f"/v1/workflow-executions/{uuid.uuid4()}")

    assert response.status_code == 200
    body = response.json()
    assert len(body["node_executions"]) == 1
    assert body["status"] == "completed"


def test_get_workflow_execution_returns_not_found(as_member, fake_service) -> None:
    fake_service.get_detail.side_effect = NotFoundError("Workflow execution not found.")

    response = client.get(f"/v1/workflow-executions/{uuid.uuid4()}")

    assert response.status_code == 404


def test_owner_can_cancel_an_execution(as_owner, fake_service) -> None:
    fake_service.get_owned.return_value = _FakeExecution(status="running")
    fake_service.cancel.return_value = _FakeExecution(status="running")

    response = client.post(f"/v1/workflow-executions/{uuid.uuid4()}/cancel")

    assert response.status_code == 200
    fake_service.cancel.assert_called_once()


def test_cancel_propagates_conflict_for_a_finished_execution(as_owner, fake_service) -> None:
    fake_service.get_owned.return_value = _FakeExecution(status="completed")
    fake_service.cancel.side_effect = ConflictError("Cannot cancel a run that is already completed.")

    response = client.post(f"/v1/workflow-executions/{uuid.uuid4()}/cancel")

    assert response.status_code == 409


def test_owner_can_pause_a_running_execution(as_owner, fake_service) -> None:
    fake_service.get_owned.return_value = _FakeExecution(status="running")
    fake_service.pause.return_value = _FakeExecution(status="running")

    response = client.post(f"/v1/workflow-executions/{uuid.uuid4()}/pause")

    assert response.status_code == 200
    fake_service.pause.assert_called_once()


def test_owner_can_resume_a_paused_execution(as_owner, fake_service) -> None:
    fake_service.get_owned.return_value = _FakeExecution(status="paused")
    fake_service.resume.return_value = _FakeExecution(status="pending")

    response = client.post(f"/v1/workflow-executions/{uuid.uuid4()}/resume")

    assert response.status_code == 200
    fake_service.resume.assert_called_once()


def test_member_cannot_resume_an_execution(as_member, fake_service) -> None:
    response = client.post(f"/v1/workflow-executions/{uuid.uuid4()}/resume")

    assert response.status_code == 403
    fake_service.resume.assert_not_called()
