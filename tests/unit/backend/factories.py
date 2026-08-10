import uuid
from datetime import UTC, datetime

from vault_shared.db.models import Organization, Role, User


def make_organization(*, name: str = "Acme", slug: str = "acme") -> Organization:
    organization = Organization(name=name, slug=slug)
    organization.id = uuid.uuid4()
    organization.created_at = datetime.now(UTC)
    organization.updated_at = datetime.now(UTC)
    return organization


def make_role(name: str = "owner") -> Role:
    role = Role(name=name, description="")
    role.id = uuid.uuid4()
    return role


def make_user(
    *,
    organization: Organization | None = None,
    role: Role | None = None,
    email: str = "founder@example.com",
    name: str = "Ada Founder",
) -> User:
    organization = organization or make_organization()
    role = role or make_role()

    user = User(
        organization_id=organization.id,
        role_id=role.id,
        google_sub="1234567890",
        email=email,
        name=name,
        avatar_url=None,
    )
    user.id = uuid.uuid4()
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    user.last_login_at = None
    # Set relationship attributes directly — safe on a transient (session-less)
    # object since this is a plain assignment, not a lazy-load fetch.
    user.organization = organization
    user.role = role
    return user
