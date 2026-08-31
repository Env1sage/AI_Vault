import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vault_shared.db.session import Base

if TYPE_CHECKING:
    from vault_shared.db.models.intelligence_job import IntelligenceJob


class IntelligenceProgress(Base):
    """Live counters for one intelligence job — separate from
    `IntelligenceJob` for the same reason `EmbeddingProgress`/
    `EnrichmentProgress` are separate from their jobs: updated far more
    often than the job row itself."""

    __tablename__ = "intelligence_progress"

    intelligence_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("intelligence_jobs.id", ondelete="CASCADE"), primary_key=True
    )
    files_pending: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_file_name: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    intelligence_job: Mapped["IntelligenceJob"] = relationship(back_populates="progress")
