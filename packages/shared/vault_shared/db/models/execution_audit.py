import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class ExecutionAudit(Base):
    """The Execution Engine's comprehensive, append-only operational trail
    (Handbook §8.12 Audit Engine's before/after-state guarantee; Phase 8
    spec's "Log: Plan creation, Approval events, Validation results,
    Execution start, Step completion, Verification, Rollback, Failures,
    User interactions"). Deliberately its own table, not a reuse of the
    generic `AuditLog` — this one carries plan/job context columns
    `AuditLog` doesn't have and is queryable as one continuous timeline
    per plan. A handful of the same events are *also* written to the
    generic `AuditLog` (approval decisions, specifically) for the
    cross-module "everything sensitive in one place" view every other
    phase's `AuditLog` entries already provide — the two are
    complementary, not duplicates: this table is the execution-specific
    detail trail, `AuditLog` is the coarse cross-cutting index."""

    __tablename__ = "execution_audits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    execution_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("execution_plans.id", ondelete="SET NULL"), nullable=True, index=True
    )
    execution_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("execution_jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
