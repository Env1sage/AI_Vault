import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class ExecutionJobStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"
    CANCELLED = "cancelled"


class ExecutionJob(Base):
    """One worker run executing an *approved* `ExecutionPlan`'s steps
    (Handbook §8.7, Phase 8's Execution Queue) — created only by an
    `approve` `ApprovalDecision`, never directly. Both `cancel_requested`
    and `pause_requested` are cooperative flags checked between steps
    (same column-only-query pattern as every prior job's cancellation,
    ADR-016) — `PAUSED` is not terminal (a paused job can be resumed and
    continues from its first non-terminal step), unlike `CANCELLED`.

    `is_rollback` reuses this exact job/status/audit machinery for the
    Rollback Framework (Phase 8 spec) instead of inventing a parallel
    mechanism — rollback is itself a mutating Drive call (un-trash,
    move-back, rename-back), so it has to run in the worker like forward
    execution does; `ExecutionService.run()` branches on this flag to
    iterate `RollbackRecord`s in reverse instead of `ExecutionStep`s
    forward."""

    __tablename__ = "execution_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    execution_plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("execution_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Always set in practice (an approval's `approve` decision or a
    # rollback request always has an acting user) — nullable for schema
    # consistency with every other job model's `triggered_by_user_id`,
    # which allows for a future purely-system-triggered execution path.
    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ExecutionJobStatus.PENDING, index=True
    )
    is_rollback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pause_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
