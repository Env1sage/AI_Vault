import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class SchedulerJob(Base):
    """One-to-one scheduler bookkeeping row for a `SCHEDULED`
    `WorkflowTrigger` (Phase 9's own named DB entity, kept separate from
    `WorkflowTrigger` so "what triggers this" and "when did/will this fire"
    don't share a row). `next_run_at` is precomputed from the trigger's cron
    expression via `croniter`; the scheduler's periodic sweep claims a due
    row with a single atomic `UPDATE ... WHERE next_run_at <= now() ...
    RETURNING`, which is what prevents the phase spec's named "trigger
    duplication" failure mode under more than one scheduler process."""

    __tablename__ = "scheduler_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    workflow_trigger_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_triggers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_workflow_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workflow_executions.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
