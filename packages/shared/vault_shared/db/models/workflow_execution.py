import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class WorkflowExecutionStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowExecution(Base):
    """One run of a `Workflow`'s currently-published version (Phase 9's
    Workflow Execution Engine) — a single path through the node graph, not
    a set of independent steps like `ExecutionJob`'s plan-steps, so there is
    no `PARTIALLY_COMPLETED` status here: one node failing fails the run.
    `current_node_id` is where execution is (or is paused) — `PAUSED` means
    waiting on an `ApprovalRequest` (an `APPROVAL` node, or an
    `EXECUTE_ACTION` node whose policy required approval) or a `DELAY`
    node's scheduled continuation; both resume by re-enqueuing
    `worker.workflow.run` for this same execution id, which picks up
    exactly where it left off. `cancel_requested`/`pause_requested` mirror
    `ExecutionJob`'s cooperative flags."""

    __tablename__ = "workflow_executions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workflow_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=WorkflowExecutionStatus.PENDING, index=True
    )
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False)
    trigger_context: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    current_node_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workflow_nodes.id", ondelete="SET NULL"), nullable=True
    )
    context: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    cancel_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pause_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
