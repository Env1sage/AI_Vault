import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class RollbackRecord(Base):
    """The authoritative pre-mutation state for one successfully-executed
    `ExecutionStep`, captured immediately before the actual Drive write
    (Phase 8's Rollback Framework) — distinct from `ExecutionStep.
    pre_state`, which is a plan-time snapshot for founder review and may
    be stale by the time a plan is actually approved and executed. Created
    for every successful step regardless of whether rollback is ever
    invoked, so "can this be undone" is always answerable from stored
    data, not a live Drive re-derivation."""

    __tablename__ = "rollback_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    execution_step_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("execution_steps.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    pre_state: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    rolled_back: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rolled_back_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rolled_back_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
