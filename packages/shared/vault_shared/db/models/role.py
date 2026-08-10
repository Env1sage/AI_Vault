import enum
import uuid

from sqlalchemy import String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class RoleName(enum.StrEnum):
    """Fixed role set for Phase 2 — no dynamic role management yet (Handbook
    §13: "roles and permissions are explicit, not inferred")."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")
