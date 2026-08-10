import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from app.main import app
from app.presentation.dependencies.auth import get_current_user
from app.presentation.dependencies.services import get_embedding_job_service
from fastapi.testclient import TestClient
from vault_shared import ConflictError, NotFoundError

client = TestClient(app)


class _FakeEmbeddingJob:
    def __init__(self, *, connector_id: uuid.UUID | None = None) -> None:
        self.id = uuid.uuid4()
        self.connector_id = connector_id or uuid.uuid4()
        self.triggered_by = "manual"
        self.status = "pending"
        self.error = None
        self.started_at = None
        self.completed_at = None
        self.created_at = datetime.now(UTC)


class _FakeEmbeddingProgress:
    def __init__(self) -> None:
        self.files_pending = 20
        self.files_processed = 5
        self.files_failed = 0
        self.current_file_name = "Report.pdf"
        self.updated_at = datetime.now(UTC)


@pytest.fixture
def fake_embedding_service() -> MagicMock:
    service = MagicMock()
    app.dependency_overrides[get_embedding_job_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_embedding_job_service, None)


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


def test_start_embedding_requires_authentication(fake_embedding_service) -> None:
    response = client.post(f"/v1/connectors/{uuid.uuid4()}/embedding")
    assert response.status_code == 401


def test_owner_can_start_embedding(as_owner, fake_embedding_service) -> None:
    connector_id = uuid.uuid4()
    fake_embedding_service.start.return_value = _FakeEmbeddingJob(connector_id=connector_id)

    response = client.post(f"/v1/connectors/{connector_id}/embedding")

    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    fake_embedding_service.start.assert_called_once()
    assert fake_embedding_service.start.call_args.args[0] == connector_id


def test_member_cannot_start_embedding(as_member, fake_embedding_service) -> None:
    response = client.post(f"/v1/connectors/{uuid.uuid4()}/embedding")

    assert response.status_code == 403
    fake_embedding_service.start.assert_not_called()


def test_start_embedding_propagates_conflict_when_already_running(
    as_owner, fake_embedding_service
) -> None:
    fake_embedding_service.start.side_effect = ConflictError(
        "An embedding job is already pending or running for this connector."
    )

    response = client.post(f"/v1/connectors/{uuid.uuid4()}/embedding")

    assert response.status_code == 409


def test_list_embedding_jobs_returns_jobs_for_the_connector(as_member, fake_embedding_service) -> None:
    connector_id = uuid.uuid4()
    fake_embedding_service.list_for_connector.return_value = [
        _FakeEmbeddingJob(connector_id=connector_id)
    ]

    response = client.get(f"/v1/connectors/{connector_id}/embedding")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_list_embedding_jobs_returns_not_found_for_another_organizations_connector(
    as_member, fake_embedding_service
) -> None:
    fake_embedding_service.list_for_connector.side_effect = NotFoundError("Connector not found.")

    response = client.get(f"/v1/connectors/{uuid.uuid4()}/embedding")

    assert response.status_code == 404


def test_get_embedding_job_includes_progress(as_member, fake_embedding_service) -> None:
    job = _FakeEmbeddingJob()
    job.status = "running"
    fake_embedding_service.get_owned.return_value = job
    fake_embedding_service.get_progress.return_value = _FakeEmbeddingProgress()

    response = client.get(f"/v1/embedding/{job.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "running"
    assert body["progress"]["files_processed"] == 5
    assert body["progress"]["current_file_name"] == "Report.pdf"


def test_get_embedding_job_returns_not_found_for_another_organizations_job(
    as_member, fake_embedding_service
) -> None:
    fake_embedding_service.get_owned.side_effect = NotFoundError("Embedding job not found.")

    response = client.get(f"/v1/embedding/{uuid.uuid4()}")

    assert response.status_code == 404


def test_owner_can_cancel_an_embedding_job(as_owner, fake_embedding_service) -> None:
    job = _FakeEmbeddingJob()
    fake_embedding_service.get_owned.return_value = job
    cancelled = _FakeEmbeddingJob(connector_id=job.connector_id)
    cancelled.id = job.id
    cancelled.status = "cancelled"
    fake_embedding_service.cancel.return_value = cancelled

    response = client.post(f"/v1/embedding/{job.id}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_member_cannot_cancel_an_embedding_job(as_member, fake_embedding_service) -> None:
    response = client.post(f"/v1/embedding/{uuid.uuid4()}/cancel")

    assert response.status_code == 403
    fake_embedding_service.cancel.assert_not_called()


def test_cancel_propagates_conflict_when_job_is_not_running(as_owner, fake_embedding_service) -> None:
    job = _FakeEmbeddingJob()
    job.status = "completed"
    fake_embedding_service.get_owned.return_value = job
    fake_embedding_service.cancel.side_effect = ConflictError("Embedding job is not running.")

    response = client.post(f"/v1/embedding/{job.id}/cancel")

    assert response.status_code == 409
