import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class AutomationTemplate(Base):
    """A reusable workflow blueprint (Phase 9's Automation Templates —
    "Archive inactive files," "Weekly storage health report," etc.).
    `organization_id IS NULL` means a global, system-seeded template
    available to every organization; a non-null value would be an
    organization's own saved template (not produced by anything this phase,
    but the column supports it without a future migration).
    `node_definitions` is a serializable node-graph blueprint — applying a
    template means parsing this JSONB into real `WorkflowNode` rows for a
    new draft `WorkflowVersion`, never referencing it live."""

    __tablename__ = "automation_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    node_definitions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
