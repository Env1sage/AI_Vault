import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class EnrichmentEvent(Base):
    """Append-only operational trail for one enrichment job — mirrors
    `ScanEvent` exactly. Distinct from `audit_logs` (user-triggered lifecycle
    actions only); this is the debugging/observability trail the phase
    spec's Logging & Observability section asks for (processor execution,
    extraction success/failure, classification results, retry attempts)."""

    __tablename__ = "enrichment_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    enrichment_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("enrichment_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
