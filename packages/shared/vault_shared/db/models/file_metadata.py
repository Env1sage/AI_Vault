import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class FileMetadata(Base):
    """Enriched, deterministic facts about a `File` — the Metadata Engine's
    per-file output (Handbook §8.3). One-to-one with `File` via a shared
    primary key; row presence means "this file has been enriched at least
    once," which is what `EnrichmentService` uses to find pending work
    (a `File` whose `scanned_at` is newer than this row's `enriched_at`, or
    with no row at all, needs (re)processing) — never overwrites the raw
    scan data on `File` itself (Phase 5 spec's "never overwrite raw scan
    data")."""

    __tablename__ = "file_metadata"

    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), primary_key=True
    )

    normalized_extension: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mime_type_validated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    mime_mismatch_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    naming_pattern: Mapped[str | None] = mapped_column(String(100), nullable=True)
    version_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    owner_summary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sharing_summary: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Files sharing a non-null key are duplicate *candidates* — candidate
    # generation only (Phase 5 spec); nothing acts on this automatically.
    duplicate_group_key: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)

    enriched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
