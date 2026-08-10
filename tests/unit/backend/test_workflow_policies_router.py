import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from app.main import app
from app.presentation.dependencies.auth import get_current_user
from app.presentation.dependencies.services import get_workflow_policy_service
from fastapi.testclient import TestClient

client = TestClient(app)


class _FakePolicy:
    def __init__(self, *, status: str = "draft") -> None:
        self.id = uuid.uuid4()
        self.organization_id = uuid.uuid4()
        self.policy_key = "archive-small-batches"
        self.version = 1
        self.name = "Archive small batches"
        self.description = None
        self.status = status
        self.effect = "require_approval"
        self.conditions: dict = {"max_affected_files": 10}
        self.published_at = None
        self.created_at = datetime.now(UTC)


@pytest.fixture
def fake_service() -> MagicMock:
    service = MagicMock()
    app.dependency_overrides[get_workflow_policy_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_workflow_policy_service, None)


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


def test_create_policy_requires_authentication(fake_service) -> None:
    response = client.post(
        "/v1/workflow-policies",
        json={"policy_key": "x", "name": "X", "effect": "skip", "conditions": {}},
    )
    assert response.status_code == 401


def test_owner_can_create_a_draft_policy(as_owner, fake_service) -> None:
    fake_service.create_draft.return_value = _FakePolicy()

    response = client.post(
        "/v1/workflow-policies",
        json={
            "policy_key": "archive-small-batches",
            "name": "Archive small batches",
            "effect": "require_approval",
            "conditions": {"max_affected_files": 10},
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "draft"


def test_member_cannot_create_a_policy(as_member, fake_service) -> None:
    response = client.post(
        "/v1/workflow-policies",
        json={"policy_key": "x", "name": "X", "effect": "skip", "conditions": {}},
    )

    assert response.status_code == 403
    fake_service.create_draft.assert_not_called()


def test_create_policy_rejects_an_unknown_effect(as_owner, fake_service) -> None:
    response = client.post(
        "/v1/workflow-policies",
        json={"policy_key": "x", "name": "X", "effect": "auto_magic", "conditions": {}},
    )

    assert response.status_code == 422
    fake_service.create_draft.assert_not_called()


def test_list_policies_returns_items(as_member, fake_service) -> None:
    fake_service.list_for_organization.return_value = [_FakePolicy()]

    response = client.get("/v1/workflow-policies")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_list_policy_versions(as_member, fake_service) -> None:
    fake_service.list_versions.return_value = [_FakePolicy(), _FakePolicy(status="archived")]

    response = client.get("/v1/workflow-policies/by-key/archive-small-batches/versions")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_owner_can_publish_a_policy(as_owner, fake_service) -> None:
    fake_service.publish.return_value = _FakePolicy(status="published")

    response = client.post(f"/v1/workflow-policies/{uuid.uuid4()}/publish")

    assert response.status_code == 200
    assert response.json()["status"] == "published"


def test_member_cannot_publish_a_policy(as_member, fake_service) -> None:
    response = client.post(f"/v1/workflow-policies/{uuid.uuid4()}/publish")

    assert response.status_code == 403
    fake_service.publish.assert_not_called()


def test_owner_can_archive_a_policy(as_owner, fake_service) -> None:
    fake_service.archive.return_value = _FakePolicy(status="archived")

    response = client.post(f"/v1/workflow-policies/{uuid.uuid4()}/archive")

    assert response.status_code == 200
    assert response.json()["status"] == "archived"
