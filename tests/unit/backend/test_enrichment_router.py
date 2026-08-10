import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from app.main import app
from app.presentation.dependencies.auth import get_current_user
from app.presentation.dependencies.services import get_enrichment_job_service
from fastapi.testclient import TestClient
from vault_shared import ConflictError, NotFoundError

client = TestClient(app)


class _FakeEnrichmentJob:
    def __init__(self, *, connector_id: uuid.UUID | None = None) -> None:
        self.id = uuid.uuid4()
        self.connector_id = connector_id or uuid.uuid4()
        self.triggered_by = "manual"
        self.status = "pending"
        self.error = None
        self.started_at = None
        self.completed_at = None
        self.created_at = datetime.now(UTC)


class _FakeEnrichmentProgress:
    def __init__(self) -> None:
        self.files_pending = 10
        self.files_processed = 4
        self.files_failed = 1
        self.current_file_name = "Report.pdf"
        self.updated_at = datetime.now(UTC)


@pytest.fixture
def fake_enrichment_service() -> MagicMock:
    service = MagicMock()
    app.dependency_overrides[get_enrichment_job_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_enrichment_job_service, None)


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


def test_start_enrichment_requires_authentication(fake_enrichment_service) -> None:
    response = client.post(f"/v1/connectors/{uuid.uuid4()}/enrichment")
    assert response.status_code == 401


def test_owner_can_start_enrichment(as_owner, fake_enrichment_service) -> None:
    connector_id = uuid.uuid4()
    fake_enrichment_service.start.return_value = _FakeEnrichmentJob(connector_id=connector_id)

    response = client.post(f"/v1/connectors/{connector_id}/enrichment")

    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    fake_enrichment_service.start.assert_called_once()
    assert fake_enrichment_service.start.call_args.args[0] == connector_id


def test_member_cannot_start_enrichment(as_member, fake_enrichment_service) -> None:
    response = client.post(f"/v1/connectors/{uuid.uuid4()}/enrichment")

    assert response.status_code == 403
    fake_enrichment_service.start.assert_not_called()


def test_start_enrichment_propagates_conflict_when_already_running(
    as_owner, fake_enrichment_service
) -> None:
    fake_enrichment_service.start.side_effect = ConflictError(
        "An enrichment job is already pending or running for this connector."
    )

    response = client.post(f"/v1/connectors/{uuid.uuid4()}/enrichment")

    assert response.status_code == 409


def test_list_enrichment_jobs_returns_jobs_for_the_connector(as_member, fake_enrichment_service) -> None:
    connector_id = uuid.uuid4()
    fake_enrichment_service.list_for_connector.return_value = [
        _FakeEnrichmentJob(connector_id=connector_id)
    ]

    response = client.get(f"/v1/connectors/{connector_id}/enrichment")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_list_enrichment_jobs_returns_not_found_for_another_organizations_connector(
    as_member, fake_enrichment_service
) -> None:
    fake_enrichment_service.list_for_connector.side_effect = NotFoundError("Connector not found.")

    response = client.get(f"/v1/connectors/{uuid.uuid4()}/enrichment")

    assert response.status_code == 404


def test_get_enrichment_job_includes_progress(as_member, fake_enrichment_service) -> None:
    job = _FakeEnrichmentJob()
    job.status = "running"
    fake_enrichment_service.get_owned.return_value = job
    fake_enrichment_service.get_progress.return_value = _FakeEnrichmentProgress()

    response = client.get(f"/v1/enrichment/{job.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "running"
    assert body["progress"]["files_processed"] == 4
    assert body["progress"]["current_file_name"] == "Report.pdf"


def test_get_enrichment_job_returns_not_found_for_another_organizations_job(
    as_member, fake_enrichment_service
) -> None:
    fake_enrichment_service.get_owned.side_effect = NotFoundError("Enrichment job not found.")

    response = client.get(f"/v1/enrichment/{uuid.uuid4()}")

    assert response.status_code == 404


def test_owner_can_cancel_an_enrichment_job(as_owner, fake_enrichment_service) -> None:
    job = _FakeEnrichmentJob()
    fake_enrichment_service.get_owned.return_value = job
    cancelled = _FakeEnrichmentJob(connector_id=job.connector_id)
    cancelled.id = job.id
    cancelled.status = "cancelled"
    fake_enrichment_service.cancel.return_value = cancelled

    response = client.post(f"/v1/enrichment/{job.id}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_member_cannot_cancel_an_enrichment_job(as_member, fake_enrichment_service) -> None:
    response = client.post(f"/v1/enrichment/{uuid.uuid4()}/cancel")

    assert response.status_code == 403
    fake_enrichment_service.cancel.assert_not_called()


def test_cancel_propagates_conflict_when_job_is_not_running(as_owner, fake_enrichment_service) -> None:
    job = _FakeEnrichmentJob()
    job.status = "completed"
    fake_enrichment_service.get_owned.return_value = job
    fake_enrichment_service.cancel.side_effect = ConflictError("Enrichment job is not running.")

    response = client.post(f"/v1/enrichment/{job.id}/cancel")

    assert response.status_code == 409
