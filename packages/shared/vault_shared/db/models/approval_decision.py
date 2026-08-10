import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class ApprovalDecisionType(enum.StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"


class ApprovalDecision(Base):
    """The immutable record of who — or, since Phase 9, *what policy* —
    decided what on an `ApprovalRequest`, and why (Phase 8 spec: "Each
    approval records: Approver, Timestamp, Decision, Comments, Client IP,
    Organization context"). Append-only — never updated after creation,
    same guarantee every other `*Event`/`*Audit` table in this codebase
    makes.

    Phase 9 (ADR-021): exactly one of `decider_user_id`/
    `decided_by_policy_id` is set (DB CHECK constraint). A human decision
    is unchanged from Phase 8; a policy's `AUTO_EXECUTE` effect produces a
    decision attributed to the `WorkflowPolicy` that made it instead of a
    person — this is the mechanism that lets automation "never bypass the
    Approval System": every execution, automated or not, still has exactly
    one `ApprovalDecision` row, just with a different kind of decider.
    `ip_address` is always null for a policy-attributed decision (no
    request, no client)."""

    __tablename__ = "approval_decisions"
    __table_args__ = (
        CheckConstraint(
            "(decider_user_id IS NOT NULL) != (decided_by_policy_id IS NOT NULL)",
            name="ck_approval_decisions_exactly_one_decider",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    approval_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("approval_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    decider_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    decided_by_policy_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workflow_policies.id"), nullable=True
    )
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
