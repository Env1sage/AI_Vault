import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class DuplicateGroupMember(Base):
    """One file's membership in a `DuplicateGroup` — a pure derived fact,
    fully replaced (delete-then-insert) every time its group is
    recomputed, unlike `Recommendation`'s soft-resolve history (there's no
    advisory/audit value in remembering a file's *past* group membership,
    only its current one)."""

    __tablename__ = "duplicate_group_members"
    __table_args__ = (
        UniqueConstraint("duplicate_group_id", "file_id", name="uq_duplicate_group_member"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    duplicate_group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("duplicate_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_recommended_keep: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
