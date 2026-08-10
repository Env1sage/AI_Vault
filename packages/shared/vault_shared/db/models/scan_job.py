import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vault_shared.db.session import Base

if TYPE_CHECKING:
    from vault_shared.db.models.scan_progress import ScanProgress


class ScanType(enum.StrEnum):
    FULL = "full"
    INCREMENTAL = "incremental"


class ScanStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScanJob(Base):
    """One execution of the scanner against a connector's storage — scans
    every `StorageSource` the connector exposes. `cancel_requested` is
    cooperative: the worker checks it between sources/pages and stops
    cleanly rather than being killed (Phase 4 spec's "scan cancellation")."""

    __tablename__ = "scan_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    connector_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("storage_connectors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    scan_type: Mapped[str] = mapped_column(String(20), nullable=False, default=ScanType.FULL)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=ScanStatus.PENDING)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    progress: Mapped["ScanProgress | None"] = relationship(
        back_populates="scan_job", uselist=False, cascade="all, delete-orphan"
    )
