import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from app.main import app
from app.presentation.dependencies.auth import get_current_user
from app.presentation.dependencies.services import get_approval_service
from fastapi.testclient import TestClient
from vault_shared import ConflictError, ValidationError

client = TestClient(app)


class _FakeApprovalRequest:
    def __init__(self, *, status: str = "pending") -> None:
        self.id = uuid.uuid4()
        self.execution_plan_id = uuid.uuid4()
        self.organization_id = uuid.uuid4()
        self.status = status
        self.expires_at = datetime.now(UTC) + timedelta(hours=72)
        self.created_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)


@pytest.fixture
def fake_approval_service() -> MagicMock:
    service = MagicMock()
    app.dependency_overrides[get_approval_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_approval_service, None)


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


def test_list_approvals_requires_authentication(fake_approval_service) -> None:
    response = client.get("/v1/approvals")
    assert response.status_code == 401


def test_list_approvals_returns_items(as_member, fake_approval_service) -> None:
    fake_approval_service.list_for_organization.return_value = [_FakeApprovalRequest()]

    response = client.get("/v1/approvals?status=pending")

    assert response.status_code == 200
    assert len(response.json()) == 1
    fake_approval_service.list_for_organization.assert_called_once_with(
        as_member.organization_id, status="pending"
    )


def test_get_approval_returns_item(as_member, fake_approval_service) -> None:
    fake_approval_service.get_owned.return_value = _FakeApprovalRequest()

    response = client.get(f"/v1/approvals/{uuid.uuid4()}")

    assert response.status_code == 200
    assert response.json()["status"] == "pending"


def test_owner_can_approve(as_owner, fake_approval_service) -> None:
    fake_approval_service.decide.return_value = _FakeApprovalRequest(status="approved")

    response = client.post(
        f"/v1/approvals/{uuid.uuid4()}/decide",
        json={"decision": "approve", "comments": "looks fine"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_member_cannot_decide(as_member, fake_approval_service) -> None:
    response = client.post(
        f"/v1/approvals/{uuid.uuid4()}/decide", json={"decision": "approve"}
    )

    assert response.status_code == 403
    fake_approval_service.decide.assert_not_called()


def test_decide_rejects_an_invalid_decision_value(as_owner, fake_approval_service) -> None:
    response = client.post(
        f"/v1/approvals/{uuid.uuid4()}/decide", json={"decision": "maybe_later"}
    )

    assert response.status_code == 422
    fake_approval_service.decide.assert_not_called()


def test_decide_propagates_conflict_when_already_decided(as_owner, fake_approval_service) -> None:
    fake_approval_service.decide.side_effect = ConflictError(
        "This approval request is already approved."
    )

    response = client.post(
        f"/v1/approvals/{uuid.uuid4()}/decide", json={"decision": "approve"}
    )

    assert response.status_code == 409


def test_decide_approve_propagates_validation_error_when_permissions_are_insufficient(
    as_owner, fake_approval_service
) -> None:
    fake_approval_service.decide.side_effect = ValidationError(
        "Cannot approve — execution permissions are not satisfied: Connector was authorized "
        "without Drive write access."
    )

    response = client.post(
        f"/v1/approvals/{uuid.uuid4()}/decide", json={"decision": "approve"}
    )

    assert response.status_code == 422
    assert "write access" in response.json()["error"]["message"]


def test_decide_passes_client_ip_through(as_owner, fake_approval_service) -> None:
    fake_approval_service.decide.return_value = _FakeApprovalRequest(status="rejected")

    client.post(
        f"/v1/approvals/{uuid.uuid4()}/decide",
        json={"decision": "reject", "comments": "not needed"},
    )

    _, kwargs = fake_approval_service.decide.call_args
    assert kwargs["decision"] == "reject"
    assert kwargs["comments"] == "not needed"
    assert "ip_address" in kwargs


def test_owner_can_bulk_decide(as_owner, fake_approval_service) -> None:
    fake_approval_service.bulk_decide.return_value = [
        _FakeApprovalRequest(status="rejected"),
        _FakeApprovalRequest(status="rejected"),
    ]

    response = client.post(
        "/v1/approvals/bulk-decide",
        json={
            "approval_request_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
            "decision": "reject",
        },
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_bulk_decide_requires_at_least_one_id(as_owner, fake_approval_service) -> None:
    response = client.post(
        "/v1/approvals/bulk-decide", json={"approval_request_ids": [], "decision": "reject"}
    )

    assert response.status_code == 422
    fake_approval_service.bulk_decide.assert_not_called()


def test_member_cannot_bulk_decide(as_member, fake_approval_service) -> None:
    response = client.post(
        "/v1/approvals/bulk-decide",
        json={"approval_request_ids": [str(uuid.uuid4())], "decision": "approve"},
    )

    assert response.status_code == 403
    fake_approval_service.bulk_decide.assert_not_called()
