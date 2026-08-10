from collections.abc import Callable

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.infrastructure.auth.jwt import decode_access_token
from vault_shared import ForbiddenError, UnauthorizedError
from vault_shared.db.models import RoleName, User
from vault_shared.db.session import get_db


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """The identity boundary every other authenticated endpoint depends on
    (Handbook §8.11) — extracts and validates the bearer JWT, then loads the
    user (with organization/role context via relationships) from the DB."""
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise UnauthorizedError("Missing or malformed Authorization header.")

    token = auth_header.split(" ", 1)[1].strip()
    claims = decode_access_token(token)

    user = db.get(User, claims.user_id)
    if user is None:
        raise UnauthorizedError("User no longer exists.")
    return user


def require_role(*roles: RoleName) -> Callable[..., User]:
    """Authorization guard (Handbook §13.1) — distinct from authentication.
    A caller can be fully authenticated (get_current_user succeeds) and still
    get a 403 here if their role isn't in `roles`."""
    allowed = {role.value for role in roles}

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role.name not in allowed:
            raise ForbiddenError("You do not have permission to perform this action.")
        return user

    return dependency
