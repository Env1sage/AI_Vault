import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from vault_shared.db.models import Role, User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self._session.get(User, user_id)

    def list_for_organization_by_roles(
        self, *, organization_id: uuid.UUID, role_names: list[str]
    ) -> list[User]:
        """Resolves a workflow `NOTIFICATION`/`APPROVAL` node's
        `recipients: ["owner", "admin"]`-style config into real users —
        every user in the organization holding one of the named roles."""
        return (
            self._session.query(User)
            .join(Role, User.role_id == Role.id)
            .filter(User.organization_id == organization_id, Role.name.in_(role_names))
            .all()
        )

    def get_by_google_sub(self, google_sub: str) -> User | None:
        return self._session.query(User).filter_by(google_sub=google_sub).first()

    def get_by_email(self, email: str) -> User | None:
        return self._session.query(User).filter_by(email=email).first()

    def create(
        self,
        *,
        organization_id: uuid.UUID,
        role_id: uuid.UUID,
        google_sub: str,
        email: str,
        name: str,
        avatar_url: str | None,
    ) -> User:
        user = User(
            organization_id=organization_id,
            role_id=role_id,
            google_sub=google_sub,
            email=email,
            name=name,
            avatar_url=avatar_url,
        )
        self._session.add(user)
        self._session.flush()
        return user

    def mark_login(self, user: User) -> None:
        user.last_login_at = datetime.now(UTC)
        self._session.flush()
