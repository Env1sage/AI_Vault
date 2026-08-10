import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class ScanEvent(Base):
    """Append-only operational log for one scan job (Phase 4 spec's
    "Logging & Observability": started/completed/cancelled/resumed, errors,
    retry attempts) — distinct from `AuditLog` (Handbook §8.12), which stays
    reserved for security-relevant events (a scan starting/completing is
    also audit-logged once, at the connector level; this table is the
    higher-volume operational trail, not the compliance one)."""

    __tablename__ = "scan_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    scan_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scan_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
