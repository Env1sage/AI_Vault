import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from app.main import app
from app.presentation.dependencies.auth import get_current_user
from app.presentation.dependencies.services import (
    get_approval_service,
    get_execution_job_service,
    get_execution_plan_service,
)
from fastapi.testclient import TestClient
from vault_shared import ConflictError, NotFoundError, ValidationError

client = TestClient(app)


class _FakeExecutionStep:
    def __init__(self) -> None:
        self.id = uuid.uuid4()
        self.step_order = 0
        self.action_type = "remove_duplicate"
        self.target_file_id = uuid.uuid4()
        self.pre_state: dict = {}
        self.planned_change = {"action": "remove_duplicate"}
        self.status = "pending"


class _FakeExecutionPlan:
    def __init__(
        self,
        *,
        status: str = "pending_approval",
        risk_level: str = "medium",
        duplicate_group_id: uuid.UUID | None = None,
    ) -> None:
        self.id = uuid.uuid4()
        self.organization_id = uuid.uuid4()
        self.recommendation_id = None if duplicate_group_id else uuid.uuid4()
        self.duplicate_group_id = duplicate_group_id
        self.status = status
        self.target_provider = "google_workspace"
        self.estimated_impact = "17 files, ~16.5 MB"
        self.estimated_storage_savings_bytes = 17_287_885
        self.risk_level = risk_level
        self.rollback_available = True
        self.required_permissions = ["google_workspace:drive:write"]
        self.created_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)


class _FakeExecutionPlanDetail:
    def __init__(self, *, plan: _FakeExecutionPlan | None = None) -> None:
        self.plan = plan or _FakeExecutionPlan()
        self.steps = [_FakeExecutionStep()]


class _FakeExecutionJob:
    def __init__(self, *, status: str = "pending", is_rollback: bool = False) -> None:
        self.id = uuid.uuid4()
        self.execution_plan_id = uuid.uuid4()
        self.organization_id = uuid.uuid4()
        self.status = status
        self.is_rollback = is_rollback
        self.error = None
        self.started_at = None
        self.completed_at = None
        self.created_at = datetime.now(UTC)


@pytest.fixture
def fake_plan_service() -> MagicMock:
    service = MagicMock()
    app.dependency_overrides[get_execution_plan_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_execution_plan_service, None)


@pytest.fixture
def fake_job_service() -> MagicMock:
    service = MagicMock()
    app.dependency_overrides[get_execution_job_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_execution_job_service, None)


@pytest.fixture(autouse=True)
def fake_approval_service() -> MagicMock:
    """Instant-execution mode: `create_execution_plan` always depends on
    `ApprovalService` now (it auto-approves every plan right after
    creation), so every test hitting this endpoint needs it overridden —
    autouse, since even the error-path tests reach dependency resolution
    before their handler-body exception is raised."""
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


def test_create_execution_plan_requires_authentication(fake_plan_service) -> None:
    response = client.post(
        "/v1/execution-plans", json={"recommendation_id": str(uuid.uuid4())}
    )
    assert response.status_code == 401


def test_owner_can_create_an_execution_plan(as_owner, fake_plan_service) -> None:
    fake_plan_service.create_plan.return_value = _FakeExecutionPlan()

    response = client.post(
        "/v1/execution-plans", json={"recommendation_id": str(uuid.uuid4())}
    )

    assert response.status_code == 201
    assert response.json()["status"] == "pending_approval"


def test_create_execution_plan_auto_approves_immediately(
    as_owner, fake_plan_service, fake_approval_service
) -> None:
    """Instant-execution mode: no separate human-approval step — the
    creator's own plan is auto-approved right after it's built."""
    plan = _FakeExecutionPlan()
    fake_plan_service.create_plan.return_value = plan

    response = client.post(
        "/v1/execution-plans", json={"recommendation_id": str(uuid.uuid4())}
    )

    assert response.status_code == 201
    fake_approval_service.auto_decide_as_creator.assert_called_once_with(
        plan.id, organization_id=as_owner.organization_id, user_id=as_owner.id
    )


def test_create_execution_plan_still_succeeds_when_auto_approval_fails(
    as_owner, fake_plan_service, fake_approval_service
) -> None:
    """E.g. the connector still lacks write scope — plan creation itself
    must not fail just because instant execution couldn't proceed; the
    plan stays reviewable from the Approvals page instead."""
    fake_plan_service.create_plan.return_value = _FakeExecutionPlan()
    fake_approval_service.auto_decide_as_creator.side_effect = ValidationError(
        "Cannot approve — execution permissions are not satisfied."
    )

    response = client.post(
        "/v1/execution-plans", json={"recommendation_id": str(uuid.uuid4())}
    )

    assert response.status_code == 201


def test_member_cannot_create_an_execution_plan(as_member, fake_plan_service) -> None:
    response = client.post(
        "/v1/execution-plans", json={"recommendation_id": str(uuid.uuid4())}
    )

    assert response.status_code == 403
    fake_plan_service.create_plan.assert_not_called()


def test_owner_can_create_an_execution_plan_from_a_duplicate_group(
    as_owner, fake_plan_service
) -> None:
    group_id = uuid.uuid4()
    fake_plan_service.create_plan_from_duplicate_group.return_value = _FakeExecutionPlan(
        duplicate_group_id=group_id
    )

    response = client.post(
        "/v1/execution-plans", json={"duplicate_group_id": str(group_id)}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["duplicate_group_id"] == str(group_id)
    assert body["recommendation_id"] is None
    fake_plan_service.create_plan_from_duplicate_group.assert_called_once()
    fake_plan_service.create_plan.assert_not_called()


def test_create_execution_plan_rejects_neither_origin_provided(as_owner, fake_plan_service) -> None:
    response = client.post("/v1/execution-plans", json={})

    assert response.status_code == 422
    fake_plan_service.create_plan.assert_not_called()
    fake_plan_service.create_plan_from_duplicate_group.assert_not_called()


def test_create_execution_plan_rejects_both_origins_provided(as_owner, fake_plan_service) -> None:
    response = client.post(
        "/v1/execution-plans",
        json={"recommendation_id": str(uuid.uuid4()), "duplicate_group_id": str(uuid.uuid4())},
    )

    assert response.status_code == 422
    fake_plan_service.create_plan.assert_not_called()
    fake_plan_service.create_plan_from_duplicate_group.assert_not_called()


def test_create_execution_plan_propagates_validation_error_for_a_non_executable_rule(
    as_owner, fake_plan_service
) -> None:
    fake_plan_service.create_plan.side_effect = ValidationError(
        "Recommendations from rule 'orphaned_ownership' have no supported execution action yet."
    )

    response = client.post(
        "/v1/execution-plans", json={"recommendation_id": str(uuid.uuid4())}
    )

    assert response.status_code == 422


def test_create_execution_plan_propagates_conflict_for_a_duplicate_plan(
    as_owner, fake_plan_service
) -> None:
    fake_plan_service.create_plan.side_effect = ConflictError(
        "An execution plan is already pending or in progress for this recommendation."
    )

    response = client.post(
        "/v1/execution-plans", json={"recommendation_id": str(uuid.uuid4())}
    )

    assert response.status_code == 409


def test_list_execution_plans_returns_items(as_member, fake_plan_service) -> None:
    fake_plan_service.list_for_organization.return_value = [_FakeExecutionPlan()]

    response = client.get("/v1/execution-plans")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_execution_plan_returns_detail_with_steps(as_member, fake_plan_service) -> None:
    fake_plan_service.get_detail.return_value = _FakeExecutionPlanDetail()

    response = client.get(f"/v1/execution-plans/{uuid.uuid4()}")

    assert response.status_code == 200
    body = response.json()
    assert len(body["steps"]) == 1
    assert body["steps"][0]["action_type"] == "remove_duplicate"


def test_get_execution_plan_returns_not_found_for_a_missing_plan(
    as_member, fake_plan_service
) -> None:
    fake_plan_service.get_detail.side_effect = NotFoundError("Execution plan not found.")

    response = client.get(f"/v1/execution-plans/{uuid.uuid4()}")

    assert response.status_code == 404


def test_owner_can_trigger_a_rollback(as_owner, fake_job_service) -> None:
    fake_job_service.trigger_rollback.return_value = _FakeExecutionJob(is_rollback=True)

    response = client.post(f"/v1/execution-plans/{uuid.uuid4()}/rollback")

    assert response.status_code == 201
    assert response.json()["is_rollback"] is True


def test_member_cannot_trigger_a_rollback(as_member, fake_job_service) -> None:
    response = client.post(f"/v1/execution-plans/{uuid.uuid4()}/rollback")

    assert response.status_code == 403
    fake_job_service.trigger_rollback.assert_not_called()


def test_rollback_propagates_conflict_when_nothing_to_roll_back(
    as_owner, fake_job_service
) -> None:
    fake_job_service.trigger_rollback.side_effect = ConflictError(
        "Nothing to roll back for this plan."
    )

    response = client.post(f"/v1/execution-plans/{uuid.uuid4()}/rollback")

    assert response.status_code == 409
