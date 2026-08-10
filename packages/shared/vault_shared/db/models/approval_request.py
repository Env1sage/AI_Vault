import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class ApprovalStatus(enum.StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"
    EXPIRED = "expired"


class ApprovalRequest(Base):
    """One human-approval gate for one `ExecutionPlan` — Handbook §13's
    "Approval workflow for destructive actions... explicit human approval
    captured before execution." One-to-one with its plan this phase (a
    `changes_requested`/`rejected` decision is terminal; a founder wanting
    to try again generates a fresh plan, not a re-opened approval) —
    "Multi-step approvals" is explicitly future-ready per the phase spec,
    not built now. `expires_at` is checked lazily (`ApprovalRequestRepository.
    expire_if_overdue`) whenever a request is read, the same self-healing
    "pending" pattern every prior phase's resumable queries used, rather
    than a separate scheduled job this codebase has no scheduler for yet.

    Phase 9 (ADR-021): also the gate a workflow's `APPROVAL` node — or an
    `EXECUTE_ACTION` node whose policy says `REQUIRE_APPROVAL` — pauses on.
    At least one of `execution_plan_id`/`workflow_node_execution_id` is set
    (DB CHECK constraint) — *not* exactly one: a plan-only approval (the
    manual "create execution plan" flow) works exactly as in Phase 8; a
    workflow-node-only approval has no plan of its own (a plain `APPROVAL`
    gate before, say, a notification); and a workflow-triggered
    `EXECUTE_ACTION` node needing human sign-off sets **both** — a real
    `ExecutionPlan` was built, and deciding it must also resume the paused
    `WorkflowExecution`, so `ApprovalService.decide()` performs each side
    effect independently based on which column is populated, never as an
    either/or branch. Both columns stay nullable-but-unique so each still
    enforces "at most one open approval request" for its own kind of
    target."""

    __tablename__ = "approval_requests"
    __table_args__ = (
        CheckConstraint(
            "execution_plan_id IS NOT NULL OR workflow_node_execution_id IS NOT NULL",
            name="ck_approval_requests_at_least_one_target",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    execution_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("execution_plans.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,
        index=True,
    )
    workflow_node_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workflow_node_executions.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ApprovalStatus.PENDING, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
