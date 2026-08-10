import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from app.main import app
from app.presentation.dependencies.auth import get_current_user
from app.presentation.dependencies.services import get_notification_service
from fastapi.testclient import TestClient

client = TestClient(app)


class _FakeNotification:
    def __init__(self) -> None:
        self.id = uuid.uuid4()
        self.workflow_execution_id = uuid.uuid4()
        self.channel = "in_app"
        self.subject = "Weekly storage health report"
        self.body = "Your weekly summary is ready."
        self.status = "sent"
        self.sent_at = datetime.now(UTC)
        self.created_at = datetime.now(UTC)


@pytest.fixture
def fake_service() -> MagicMock:
    service = MagicMock()
    app.dependency_overrides[get_notification_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_notification_service, None)


@pytest.fixture
def as_member(member_user):
    app.dependency_overrides[get_current_user] = lambda: member_user
    yield member_user
    app.dependency_overrides.pop(get_current_user, None)


def test_list_notifications_requires_authentication(fake_service) -> None:
    response = client.get("/v1/notifications")
    assert response.status_code == 401


def test_list_notifications_returns_items_for_the_current_user(as_member, fake_service) -> None:
    fake_service.list_for_user.return_value = [_FakeNotification()]

    response = client.get("/v1/notifications")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["channel"] == "in_app"
    fake_service.list_for_user.assert_called_once_with(
        as_member.id, organization_id=as_member.organization_id
    )
