import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from app.main import app
from app.presentation.dependencies.auth import get_current_user
from app.presentation.dependencies.services import get_automation_template_service
from fastapi.testclient import TestClient
from vault_shared import NotFoundError

client = TestClient(app)


class _FakeTemplate:
    def __init__(self) -> None:
        self.id = uuid.uuid4()
        self.name = "Archive Inactive Files"
        self.description = "Runs on a schedule; archives inactive files."
        self.category = "storage_optimization"
        self.node_definitions = [{"key": "trigger", "node_type": "trigger"}]


class _FakeWorkflow:
    def __init__(self) -> None:
        self.id = uuid.uuid4()
        self.organization_id = uuid.uuid4()
        self.created_by_user_id = uuid.uuid4()
        self.name = "Archive Inactive Files"
        self.description = "Runs on a schedule; archives inactive files."
        self.status = "active"
        self.created_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)


@pytest.fixture
def fake_service() -> MagicMock:
    service = MagicMock()
    app.dependency_overrides[get_automation_template_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_automation_template_service, None)


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


def test_list_templates_requires_authentication(fake_service) -> None:
    response = client.get("/v1/automation-templates")
    assert response.status_code == 401


def test_list_templates_returns_items(as_member, fake_service) -> None:
    fake_service.list_available.return_value = [_FakeTemplate()]

    response = client.get("/v1/automation-templates")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_owner_can_apply_a_template(as_owner, fake_service) -> None:
    fake_service.apply.return_value = _FakeWorkflow()

    response = client.post(f"/v1/automation-templates/{uuid.uuid4()}/apply", json={})

    assert response.status_code == 201
    assert response.json()["name"] == "Archive Inactive Files"


def test_member_cannot_apply_a_template(as_member, fake_service) -> None:
    response = client.post(f"/v1/automation-templates/{uuid.uuid4()}/apply", json={})

    assert response.status_code == 403
    fake_service.apply.assert_not_called()


def test_apply_template_returns_not_found_for_a_missing_template(as_owner, fake_service) -> None:
    fake_service.apply.side_effect = NotFoundError("Automation template not found.")

    response = client.post(f"/v1/automation-templates/{uuid.uuid4()}/apply", json={})

    assert response.status_code == 404
