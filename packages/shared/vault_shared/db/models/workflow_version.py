import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class WorkflowVersionStatus(enum.StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    SUPERSEDED = "superseded"


class WorkflowVersion(Base):
    """One editable snapshot of a `Workflow`'s node graph (Phase 9 spec's
    "Draft version, Published version, Version history, Rollback support" —
    "no workflow should change silently"). At most one version per workflow
    is ever `PUBLISHED` at a time (service-layer invariant, not a DB
    constraint — same pattern as `Recommendation`'s natural-key upsert);
    publishing an older `SUPERSEDED` version again is how "rollback"
    works — the previously-published version becomes `SUPERSEDED` in the
    same transaction. `WorkflowExecution.workflow_version_id` freezes which
    version a given run actually executed, so a later edit can never change
    the meaning of history."""

    __tablename__ = "workflow_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=WorkflowVersionStatus.DRAFT, index=True
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
