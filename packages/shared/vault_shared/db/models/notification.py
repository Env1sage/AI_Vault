import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class NotificationChannel(enum.StrEnum):
    """Only IN_APP and EMAIL are implemented this phase (the founder's
    binding choice — email is a stub, no real send). SLACK/TEAMS/DISCORD/
    WEBHOOK values can be added later with no migration, since the column
    is a plain string, not a DB-level enum type — same convention as every
    other "string enum" field in this codebase."""

    IN_APP = "in_app"
    EMAIL = "email"


class NotificationStatus(enum.StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class Notification(Base):
    """One notification to one recipient (Phase 9's Notification Framework)
    — a fan-out to N recipients is N rows, not one row with a recipient
    list, matching the "one row per actual audience member" convention
    already used for `ApprovalDecision`/audit rows. `workflow_execution_id`
    is nullable because not every notification originates from a workflow
    (a future direct/manual notification could exist), though every one
    that does this phase, does."""

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workflow_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workflow_executions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=NotificationStatus.PENDING, index=True
    )
    error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
