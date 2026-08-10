import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vault_shared.db.session import Base

if TYPE_CHECKING:
    from vault_shared.db.models.scan_job import ScanJob


class ScanProgress(Base):
    """Live counters for one scan job — deliberately a separate one-to-one
    table from `ScanJob` (not extra columns on it) since these fields are
    updated far more frequently (every page/source processed) than the job
    record itself, and the frontend polls this for the progress indicator
    without needing to touch `scan_jobs`."""

    __tablename__ = "scan_progress"

    scan_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scan_jobs.id", ondelete="CASCADE"), primary_key=True
    )
    sources_discovered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sources_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    folders_discovered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_discovered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    scan_job: Mapped["ScanJob"] = relationship(back_populates="progress")
