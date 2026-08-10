import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class RecommendationEvent(Base):
    """Append-only operational trail for one `RecommendationJob` — mirrors
    `EmbeddingEvent`/`EnrichmentEvent`/`ScanEvent` exactly, including the
    defensive `message` truncation to 1024 chars at write time (see
    `RecommendationEventRepository.record`) that fixed a real crash-
    cascade bug in Phases 4-5 (an unbounded exception string overflowing
    this same column shape elsewhere)."""

    __tablename__ = "recommendation_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    recommendation_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recommendation_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
