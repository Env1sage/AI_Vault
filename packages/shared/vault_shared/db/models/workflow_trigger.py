import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class WorkflowTriggerType(enum.StrEnum):
    SCHEDULED = "scheduled"
    EVENT = "event"
    MANUAL = "manual"


class WorkflowEventType(enum.StrEnum):
    """The Phase 9 spec's named event triggers. `SCAN_COMPLETED`,
    `ENRICHMENT_COMPLETED`, `RECOMMENDATION_GENERATED`, and
    `CONNECTOR_RECONNECTED` are wired to real completion hooks this phase;
    `FILE_ADDED`/`FILE_UPDATED`/`STORAGE_THRESHOLD_EXCEEDED` are modeled
    and configurable but have no real firing hook yet — see the Phase 9
    completion report's Known Limitations (the scanner doesn't currently
    distinguish an added vs. updated file as separate signals, and no
    existing job computes an aggregate storage-threshold check)."""

    SCAN_COMPLETED = "scan_completed"
    ENRICHMENT_COMPLETED = "enrichment_completed"
    RECOMMENDATION_GENERATED = "recommendation_generated"
    CONNECTOR_RECONNECTED = "connector_reconnected"
    FILE_ADDED = "file_added"
    FILE_UPDATED = "file_updated"
    STORAGE_THRESHOLD_EXCEEDED = "storage_threshold_exceeded"


class WorkflowTrigger(Base):
    """What starts a `Workflow` — always targets whichever `WorkflowVersion`
    is currently `PUBLISHED` at fire time, never a pinned version (Phase 9
    spec: Scheduled/Event/Manual triggers). `config` holds a cron expression
    for `SCHEDULED` (`{"cron": "0 2 * * *"}`) or an event name for `EVENT`
    (`{"event_type": "scan_completed"}`); empty for `MANUAL`. A `SCHEDULED`
    trigger's actual next/last-run bookkeeping lives on its own
    `SchedulerJob` row, not here — keeps "what triggers this" and "when did/
    will this fire" separate, per the phase spec's own DB entity list."""

    __tablename__ = "workflow_triggers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
