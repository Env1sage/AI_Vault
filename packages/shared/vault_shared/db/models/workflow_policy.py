import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class WorkflowPolicyEffect(enum.StrEnum):
    AUTO_EXECUTE = "auto_execute"
    REQUIRE_APPROVAL = "require_approval"
    SKIP = "skip"


class WorkflowPolicyStatus(enum.StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class WorkflowPolicy(Base):
    """A versioned, organization-owned automation rule an `EXECUTE_ACTION`
    node references to decide its own fate (Phase 9 spec: "Policies
    determine execution behavior... must be versioned and auditable"; ADR-
    021's central decision — automation never bypasses the Approval System,
    it becomes a second kind of *approver*). `policy_key` groups the history
    of edits to "the same" policy over time (each edit is a new row, never
    an in-place update — full history retained); at most one row per
    `(organization_id, policy_key)` is ever `PUBLISHED` (service-layer
    invariant). `effect`:
    - `AUTO_EXECUTE` — an `EXECUTE_ACTION` node using this policy creates its
      `ExecutionPlan` and immediately auto-decides its `ApprovalRequest` as
      approved, attributed to this policy (`ApprovalDecision.
      decided_by_policy_id`), not a human.
    - `REQUIRE_APPROVAL` — the plan is created but the workflow pauses at a
      real, human-decided `ApprovalRequest`, exactly like Phase 8.
    - `SKIP` — the node does nothing at all this run (no plan is even
      created) — the mechanism behind "skip actions on executive folders,"
      "never modify legal documents."
    `conditions` is a small structured JSONB filter (min unused-days,
    max size, excluded folder/department names) evaluated against the
    candidate recommendation's affected files — not `eval()`-based, see
    `worker.workflow.policy_evaluator`."""

    __tablename__ = "workflow_policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    policy_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=WorkflowPolicyStatus.DRAFT, index=True
    )
    effect: Mapped[str] = mapped_column(String(20), nullable=False)
    conditions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
