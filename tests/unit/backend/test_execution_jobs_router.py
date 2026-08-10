import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from app.main import app
from app.presentation.dependencies.auth import get_current_user
from app.presentation.dependencies.services import get_execution_job_service
from fastapi.testclient import TestClient
from vault_shared import ConflictError, NotFoundError

client = TestClient(app)


class _FakeExecutionJob:
    def __init__(self, *, status: str = "running", is_rollback: bool = False) -> None:
        self.id = uuid.uuid4()
        self.execution_plan_id = uuid.uuid4()
        self.organization_id = uuid.uuid4()
        self.status = status
        self.is_rollback = is_rollback
        self.error = None
        self.started_at = datetime.now(UTC)
        self.completed_at = None
        self.created_at = datetime.now(UTC)


class _FakeExecutionResult:
    def __init__(self) -> None:
        self.id = uuid.uuid4()
        self.execution_step_id = uuid.uuid4()
        self.status = "success"
        self.verification_status = "verified"
        self.error = None
        self.executed_at = datetime.now(UTC)
        self.verified_at = datetime.now(UTC)


class _FakeExecutionJobDetail:
    def __init__(self, *, job: _FakeExecutionJob | None = None) -> None:
        self.job = job or _FakeExecutionJob()
        self.results = [_FakeExecutionResult()]


@pytest.fixture
def fake_job_service() -> MagicMock:
    service = MagicMock()
    app.dependency_overrides[get_execution_job_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_execution_job_service, None)


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


def test_list_execution_jobs_requires_authentication(fake_job_service) -> None:
    response = client.get("/v1/execution-jobs")
    assert response.status_code == 401


def test_list_execution_jobs_returns_items(as_member, fake_job_service) -> None:
    fake_job_service.list_for_organization.return_value = [_FakeExecutionJob()]

    response = client.get("/v1/execution-jobs?status=running")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_execution_job_returns_detail_with_results(as_member, fake_job_service) -> None:
    fake_job_service.get_detail.return_value = _FakeExecutionJobDetail()

    response = client.get(f"/v1/execution-jobs/{uuid.uuid4()}")

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 1
    assert body["results"][0]["status"] == "success"


def test_get_execution_job_returns_not_found(as_member, fake_job_service) -> None:
    fake_job_service.get_detail.side_effect = NotFoundError("Execution job not found.")

    response = client.get(f"/v1/execution-jobs/{uuid.uuid4()}")

    assert response.status_code == 404


def test_owner_can_cancel_a_job(as_owner, fake_job_service) -> None:
    fake_job_service.get_owned.return_value = _FakeExecutionJob(status="running")
    fake_job_service.cancel.return_value = _FakeExecutionJob(status="running")

    response = client.post(f"/v1/execution-jobs/{uuid.uuid4()}/cancel")

    assert response.status_code == 200
    fake_job_service.cancel.assert_called_once()


def test_member_cannot_cancel_a_job(as_member, fake_job_service) -> None:
    response = client.post(f"/v1/execution-jobs/{uuid.uuid4()}/cancel")

    assert response.status_code == 403
    fake_job_service.cancel.assert_not_called()


def test_cancel_propagates_conflict_for_a_finished_job(as_owner, fake_job_service) -> None:
    fake_job_service.get_owned.return_value = _FakeExecutionJob(status="completed")
    fake_job_service.cancel.side_effect = ConflictError("Cannot cancel a job that is already completed.")

    response = client.post(f"/v1/execution-jobs/{uuid.uuid4()}/cancel")

    assert response.status_code == 409


def test_owner_can_pause_a_running_job(as_owner, fake_job_service) -> None:
    fake_job_service.get_owned.return_value = _FakeExecutionJob(status="running")
    fake_job_service.pause.return_value = _FakeExecutionJob(status="running")

    response = client.post(f"/v1/execution-jobs/{uuid.uuid4()}/pause")

    assert response.status_code == 200
    fake_job_service.pause.assert_called_once()


def test_pause_propagates_conflict_for_a_non_running_job(as_owner, fake_job_service) -> None:
    fake_job_service.get_owned.return_value = _FakeExecutionJob(status="pending")
    fake_job_service.pause.side_effect = ConflictError("Only a running job can be paused.")

    response = client.post(f"/v1/execution-jobs/{uuid.uuid4()}/pause")

    assert response.status_code == 409


def test_owner_can_resume_a_paused_job(as_owner, fake_job_service) -> None:
    fake_job_service.get_owned.return_value = _FakeExecutionJob(status="paused")
    fake_job_service.resume.return_value = _FakeExecutionJob(status="pending")

    response = client.post(f"/v1/execution-jobs/{uuid.uuid4()}/resume")

    assert response.status_code == 200
    fake_job_service.resume.assert_called_once()


def test_member_cannot_resume_a_job(as_member, fake_job_service) -> None:
    response = client.post(f"/v1/execution-jobs/{uuid.uuid4()}/resume")

    assert response.status_code == 403
    fake_job_service.resume.assert_not_called()
