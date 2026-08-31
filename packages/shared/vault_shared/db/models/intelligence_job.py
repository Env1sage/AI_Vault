import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vault_shared.db.session import Base

if TYPE_CHECKING:
    from vault_shared.db.models.intelligence_progress import IntelligenceProgress


class IntelligenceJobStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IntelligenceTrigger(enum.StrEnum):
    """`ENRICHMENT_COMPLETED`: auto-enqueued when an `EnrichmentJob`
    finishes — triggered in *parallel* with `EmbeddingJob`, not
    sequentially before it (see `IntelligenceJob`'s own docstring for
    why). `MANUAL`: an explicit re-analysis request."""

    ENRICHMENT_COMPLETED = "enrichment_completed"
    MANUAL = "manual"


class IntelligenceJob(Base):
    """One execution of Phase 2's AI File Intelligence pipeline over a
    connector's pending files — mirrors `EmbeddingJob`'s shape (same
    cooperative-cancellation, same status lifecycle, "pending" computed at
    run time). Unlike `EmbeddingJob`, this job calls a real hosted LLM
    (`OpenAICompatibleCompletionProvider`) and so has a genuine external-
    connectivity failure mode — its worker-side `IntelligenceService`
    mirrors `EnrichmentService`'s `DependencyUnavailableError` retry
    branch, not `EmbeddingService`'s (which has none, by design, since its
    provider is fully local).

    Triggered in parallel with `EmbeddingJob` off the same
    `EnrichmentJob.status == COMPLETED` event, not sequentially before it —
    a slow/unreachable/unconfigured LLM must never delay Embedding's
    search-readiness path. Known, non-blocking limitation: `RecommendationJob`
    triggers off Embedding completion, so it can run before this job's
    `FileIntelligence` rows exist for the same batch. Nothing in this phase
    feeds Recommendations from Intelligence data, so this is inert today —
    a future phase that does must gate on `IntelligenceJobRepository.
    has_active_job()`, not change this trigger."""

    __tablename__ = "intelligence_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    connector_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("storage_connectors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    enrichment_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("enrichment_jobs.id", ondelete="SET NULL"), nullable=True
    )
    triggered_by: Mapped[str] = mapped_column(String(20), nullable=False)
    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=IntelligenceJobStatus.PENDING
    )
    cancel_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    progress: Mapped["IntelligenceProgress | None"] = relationship(
        back_populates="intelligence_job", uselist=False, cascade="all, delete-orphan"
    )
