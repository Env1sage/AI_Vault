import pytest
from factories import make_organization, make_role, make_user
from vault_shared.db.models import Organization, Role, User


@pytest.fixture
def organization() -> Organization:
    return make_organization()


@pytest.fixture
def owner_role() -> Role:
    return make_role("owner")


@pytest.fixture
def member_role() -> Role:
    return make_role("member")


@pytest.fixture
def owner_user(organization: Organization, owner_role: Role) -> User:
    return make_user(organization=organization, role=owner_role)


@pytest.fixture
def member_user(organization: Organization, member_role: Role) -> User:
    return make_user(organization=organization, role=member_role, email="member@example.com")
