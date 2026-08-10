import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vault_shared.db.session import Base

if TYPE_CHECKING:
    from vault_shared.db.models.embedding_progress import EmbeddingProgress


class EmbeddingJobStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EmbeddingTrigger(enum.StrEnum):
    """`ENRICHMENT_COMPLETED`: auto-enqueued when an `EnrichmentJob` finishes
    (Phase 6's Architecture Impact: Knowledge Engine → Embedding Engine) —
    the normal, steady-state path. `MANUAL`: an explicit re-embedding
    request."""

    ENRICHMENT_COMPLETED = "enrichment_completed"
    MANUAL = "manual"


class EmbeddingJob(Base):
    """One execution of the Embedding Engine over a connector's pending
    files (Handbook §8.5) — mirrors `EnrichmentJob`/`ScanJob`'s shape
    deliberately: same cooperative-cancellation, same status lifecycle,
    same "pending" computed at run time rather than snapshotted (any `File`
    with extracted text but no `Embedding` row, or whose extraction is
    newer than its embedding) — see ADR-018."""

    __tablename__ = "embedding_jobs"

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
        String(20), nullable=False, default=EmbeddingJobStatus.PENDING
    )
    cancel_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    progress: Mapped["EmbeddingProgress | None"] = relationship(
        back_populates="embedding_job", uselist=False, cascade="all, delete-orphan"
    )
