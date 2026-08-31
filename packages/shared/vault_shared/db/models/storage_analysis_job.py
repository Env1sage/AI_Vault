import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class StorageAnalysisJobStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StorageAnalysisTrigger(enum.StrEnum):
    """`SCAN_COMPLETED`: auto-enqueued alongside enrichment when a `ScanJob`
    finishes — deliberately a sibling of the enrichment chain, not a
    successor of it. Storage Intelligence reads `File.checksum` and other
    raw scan fields directly (see `DuplicateDetector`), never
    `FileMetadata.duplicate_group_key` (an enrichment-owned, 20-member-
    capped field — Phase 5's relationship-discovery concern, not this
    layer's), so it has no real dependency on enrichment/embedding/
    recommendation and shouldn't wait behind them. `MANUAL`: an explicit
    "re-analyze storage" request from the dashboard."""

    SCAN_COMPLETED = "scan_completed"
    MANUAL = "manual"


class StorageAnalysisJob(Base):
    """One run of the Storage Intelligence Layer over an *organization's*
    full current file inventory — organization-scoped like
    `RecommendationJob` (storage totals/duplicates reason about an org's
    files as a whole, potentially across multiple connectors), not
    connector-scoped like `ScanJob`/`EnrichmentJob`/`EmbeddingJob`.

    No cooperative-cancellation column and no per-item progress table,
    same rationale as `RecommendationJob`: a single aggregate pass over
    already-stored data, no per-file external I/O, nothing meaningful to
    report mid-run."""

    __tablename__ = "storage_analysis_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    triggered_by: Mapped[str] = mapped_column(String(20), nullable=False)
    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=StorageAnalysisJobStatus.PENDING
    )
    error: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
