import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vault_shared.db.session import Base

if TYPE_CHECKING:
    from vault_shared.db.models.enrichment_job import EnrichmentJob


class EnrichmentProgress(Base):
    """Live counters for one enrichment job — a separate one-to-one table
    from `EnrichmentJob` for the same reason `ScanProgress` is separate from
    `ScanJob`: these update far more often (every file) than the job row,
    and the frontend polls this specifically for the progress indicator."""

    __tablename__ = "enrichment_progress"

    enrichment_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("enrichment_jobs.id", ondelete="CASCADE"), primary_key=True
    )
    files_pending: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_file_name: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    enrichment_job: Mapped["EnrichmentJob"] = relationship(back_populates="progress")
