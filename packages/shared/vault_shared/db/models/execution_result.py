import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class ExecutionResultStatus(enum.StrEnum):
    SUCCESS = "success"
    FAILED = "failed"


class VerificationStatus(enum.StrEnum):
    VERIFIED = "verified"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExecutionResult(Base):
    """The outcome of actually running one `ExecutionStep` (Handbook §8.7:
    "capture before/after state") plus the Verification Engine's follow-up
    check (Phase 8 spec) — one row per step per *job*, not per step alone:
    a forward-execution job and a later rollback job each produce their
    own `ExecutionResult` for the same step (rolling back is itself a
    verified operation), so `execution_step_id` is indexed but not
    unique — `(execution_job_id, execution_step_id)` is the real natural
    key, enforced by construction (`ExecutionService` never creates more
    than one result per step within a single job) rather than a DB
    constraint, since a forward job's step is never re-executed within
    that same job (a failed step stays failed; a retry means a fresh
    plan) but *is* legitimately revisited by a distinct rollback job."""

    __tablename__ = "execution_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    execution_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("execution_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    execution_step_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("execution_steps.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    error: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
