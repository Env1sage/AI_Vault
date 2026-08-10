import pytest
from app.main import app
from app.presentation.dependencies.auth import get_current_user
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture
def as_user(owner_user):
    app.dependency_overrides[get_current_user] = lambda: owner_user
    yield owner_user
    app.dependency_overrides.pop(get_current_user, None)


def test_me_returns_the_authenticated_users_profile(as_user) -> None:
    response = client.get("/v1/users/me")

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == as_user.email
    assert body["role"] == "owner"
    assert body["organization_id"] == str(as_user.organization_id)


def test_me_requires_authentication() -> None:
    response = client.get("/v1/users/me")

    assert response.status_code == 401
