import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vault_shared.db.session import Base

if TYPE_CHECKING:
    from vault_shared.db.models.enrichment_progress import EnrichmentProgress


class EnrichmentJobStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EnrichmentTrigger(enum.StrEnum):
    """`SCAN_COMPLETED`: auto-enqueued when a `ScanJob` finishes (Handbook §7's
    "Scanner detects → Metadata extracted" pipeline step) — the normal,
    steady-state path. `MANUAL`: an explicit re-enrichment request (phase
    spec's "reprocessing updated files" from the frontend)."""

    SCAN_COMPLETED = "scan_completed"
    MANUAL = "manual"


class EnrichmentJob(Base):
    """One execution of the Metadata Engine over a connector's pending files
    (Handbook §8.3/§8.4) — mirrors `ScanJob`'s shape deliberately (same
    cooperative-cancellation, same status lifecycle) since it's the same
    kind of long-running, resumable worker job. "Pending files" is computed
    at run time (any `File` with no `FileMetadata` row, or a `scanned_at`
    newer than its `FileMetadata.enriched_at`) rather than snapshotted at
    job creation, which is what makes reprocessing and resumption both just
    "run the query again" instead of needing their own bookkeeping."""

    __tablename__ = "enrichment_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    connector_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("storage_connectors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scan_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("scan_jobs.id", ondelete="SET NULL"), nullable=True
    )
    triggered_by: Mapped[str] = mapped_column(String(20), nullable=False)
    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=EnrichmentJobStatus.PENDING
    )
    cancel_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    progress: Mapped["EnrichmentProgress | None"] = relationship(
        back_populates="enrichment_job", uselist=False, cascade="all, delete-orphan"
    )
