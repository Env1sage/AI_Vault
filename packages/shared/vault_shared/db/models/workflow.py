import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class WorkflowStatus(enum.StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class Workflow(Base):
    """An organization-owned automation workflow (Phase 9 spec). The
    workflow itself only tracks identity, ownership, and the pause/resume/
    disable lifecycle (Handbook §17's "Administrators can pause, resume,
    clone, or disable workflows") — its actual node graph lives on
    `WorkflowVersion`/`WorkflowNode` so editing never mutates what already
    ran; see ADR-021."""

    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=WorkflowStatus.ACTIVE, index=True
    )
    # No `published_version_id` column here — deliberately avoids a circular
    # FK with `workflow_versions`. "The currently published version" is
    # derived by querying `WorkflowVersion` for `(workflow_id, status=
    # PUBLISHED)`, a service-layer-enforced single-active invariant (same
    # pattern as `ExecutionPlanRepository.has_active_plan_for_recommendation`).

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
