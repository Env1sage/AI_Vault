from sqlalchemy.orm import Session

from vault_shared.db.models import Role, RoleName


class RoleRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_name(self, name: RoleName) -> Role:
        role = self._session.query(Role).filter_by(name=name.value).first()
        if role is None:
            # Should be impossible against a correctly-migrated database —
            # roles are seeded by migration 0002, not created at runtime.
            raise RuntimeError(f"Role '{name.value}' is not seeded — run migrations.")
        return role
