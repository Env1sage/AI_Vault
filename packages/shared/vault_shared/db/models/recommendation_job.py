import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class RecommendationJobStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RecommendationTrigger(enum.StrEnum):
    """`EMBEDDING_COMPLETED`: auto-enqueued when an `EmbeddingJob` finishes
    (Phase 7's Architecture Impact: AI Intelligence Engine → Recommendation
    Engine) — the normal, steady-state path. `MANUAL`: an explicit
    "refresh recommendations" request from the dashboard."""

    EMBEDDING_COMPLETED = "embedding_completed"
    MANUAL = "manual"


class RecommendationJob(Base):
    """One run of the Recommendation Engine over an *organization's* full
    current data (Handbook's Recommendation Engine) — organization-scoped,
    not connector-scoped like every prior job (`ScanJob`/`EnrichmentJob`/
    `EmbeddingJob`), since recommendations and the dashboard reason about
    an org's storage as a whole, potentially across multiple connectors.

    Deliberately has no cooperative-cancellation column and no per-item
    `Progress` table, unlike the per-file jobs it follows — this is a
    single aggregate computation over already-stored data (no per-file
    external I/O), typically finishing in seconds, so there's no
    meaningful "N/M processed" to report mid-run and nothing worth
    cancelling partway through. `recommendations_active` is set once, at
    completion, as a simple result summary."""

    __tablename__ = "recommendation_jobs"

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
        String(20), nullable=False, default=RecommendationJobStatus.PENDING
    )
    error: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    recommendations_active: Mapped[int | None] = mapped_column(Integer, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
