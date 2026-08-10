import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from app.main import app
from app.presentation.dependencies.auth import get_current_user
from app.presentation.dependencies.services import get_scan_service
from fastapi.testclient import TestClient
from vault_shared import ConflictError, NotFoundError

client = TestClient(app)


class _FakeScanJob:
    def __init__(self, *, connector_id: uuid.UUID | None = None) -> None:
        self.id = uuid.uuid4()
        self.connector_id = connector_id or uuid.uuid4()
        self.scan_type = "full"
        self.status = "pending"
        self.error = None
        self.started_at = None
        self.completed_at = None
        self.created_at = datetime.now(UTC)


class _FakeScanProgress:
    def __init__(self) -> None:
        self.sources_discovered = 2
        self.sources_completed = 1
        self.folders_discovered = 10
        self.files_discovered = 42
        self.current_source_name = "Shared Drive"
        self.updated_at = datetime.now(UTC)


@pytest.fixture
def fake_scan_service() -> MagicMock:
    service = MagicMock()
    app.dependency_overrides[get_scan_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_scan_service, None)


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


def test_start_scan_requires_authentication(fake_scan_service) -> None:
    response = client.post(f"/v1/connectors/{uuid.uuid4()}/scans")
    assert response.status_code == 401


def test_owner_can_start_a_scan(as_owner, fake_scan_service) -> None:
    connector_id = uuid.uuid4()
    fake_scan_service.start_scan.return_value = _FakeScanJob(connector_id=connector_id)

    response = client.post(f"/v1/connectors/{connector_id}/scans")

    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    assert response.json()["scan_type"] == "full"
    fake_scan_service.start_scan.assert_called_once()
    assert fake_scan_service.start_scan.call_args.args[0] == connector_id


def test_member_cannot_start_a_scan(as_member, fake_scan_service) -> None:
    response = client.post(f"/v1/connectors/{uuid.uuid4()}/scans")

    assert response.status_code == 403
    fake_scan_service.start_scan.assert_not_called()


def test_start_scan_propagates_conflict_when_already_running(as_owner, fake_scan_service) -> None:
    fake_scan_service.start_scan.side_effect = ConflictError(
        "A scan is already pending or running for this connector."
    )

    response = client.post(f"/v1/connectors/{uuid.uuid4()}/scans")

    assert response.status_code == 409


def test_start_scan_accepts_an_explicit_scan_type(as_owner, fake_scan_service) -> None:
    connector_id = uuid.uuid4()
    fake_scan_service.start_scan.return_value = _FakeScanJob(connector_id=connector_id)

    response = client.post(
        f"/v1/connectors/{connector_id}/scans", json={"scan_type": "incremental"}
    )

    assert response.status_code == 201
    assert fake_scan_service.start_scan.call_args.kwargs["scan_type"] == "incremental"


def test_start_scan_rejects_an_invalid_scan_type(as_owner, fake_scan_service) -> None:
    response = client.post(
        f"/v1/connectors/{uuid.uuid4()}/scans", json={"scan_type": "bogus"}
    )
    assert response.status_code == 422


def test_list_scans_returns_jobs_for_the_connector(as_member, fake_scan_service) -> None:
    connector_id = uuid.uuid4()
    fake_scan_service.list_for_connector.return_value = [
        _FakeScanJob(connector_id=connector_id)
    ]

    response = client.get(f"/v1/connectors/{connector_id}/scans")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_list_scans_returns_not_found_for_another_organizations_connector(
    as_member, fake_scan_service
) -> None:
    fake_scan_service.list_for_connector.side_effect = NotFoundError("Connector not found.")

    response = client.get(f"/v1/connectors/{uuid.uuid4()}/scans")

    assert response.status_code == 404


def test_get_scan_includes_progress(as_member, fake_scan_service) -> None:
    job = _FakeScanJob()
    job.status = "running"
    fake_scan_service.get_owned.return_value = job
    fake_scan_service.get_progress.return_value = _FakeScanProgress()

    response = client.get(f"/v1/scans/{job.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "running"
    assert body["progress"]["files_discovered"] == 42
    assert body["progress"]["current_source_name"] == "Shared Drive"


def test_get_scan_returns_not_found_for_another_organizations_job(
    as_member, fake_scan_service
) -> None:
    fake_scan_service.get_owned.side_effect = NotFoundError("Scan job not found.")

    response = client.get(f"/v1/scans/{uuid.uuid4()}")

    assert response.status_code == 404


def test_owner_can_cancel_a_scan(as_owner, fake_scan_service) -> None:
    job = _FakeScanJob()
    fake_scan_service.get_owned.return_value = job
    cancelled = _FakeScanJob(connector_id=job.connector_id)
    cancelled.id = job.id
    cancelled.status = "cancelled"
    fake_scan_service.cancel.return_value = cancelled

    response = client.post(f"/v1/scans/{job.id}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_member_cannot_cancel_a_scan(as_member, fake_scan_service) -> None:
    response = client.post(f"/v1/scans/{uuid.uuid4()}/cancel")

    assert response.status_code == 403
    fake_scan_service.cancel.assert_not_called()


def test_cancel_propagates_conflict_when_scan_is_not_running(as_owner, fake_scan_service) -> None:
    job = _FakeScanJob()
    job.status = "completed"
    fake_scan_service.get_owned.return_value = job
    fake_scan_service.cancel.side_effect = ConflictError("Scan job is not running.")

    response = client.post(f"/v1/scans/{job.id}/cancel")

    assert response.status_code == 409
