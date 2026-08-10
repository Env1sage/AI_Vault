import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class ExtractionStatus(enum.StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"
    SKIPPED_TOO_LARGE = "skipped_too_large"
    # The provider denied *content* access to this specific file (e.g. the
    # owner disabled download/copy/print for viewers) even though its
    # metadata was readable — permanent for this file, not a connector-wide
    # problem, and therefore never retried.
    FORBIDDEN = "forbidden"


class FileExtraction(Base):
    """Content Extraction Framework output (Phase 5 spec) — normalized,
    sanitized text pulled from supported file formats, kept separate from
    `FileMetadata` since it can be large and is consumed differently (it's
    the "Search Preparation" surface a future Embedding Engine reads, not a
    metadata field the file-detail UI renders directly). One-to-one with
    `File`. A missing/failed/unsupported extraction never blocks the rest of
    the enrichment pipeline for that file (Phase 5 spec's "failures should
    affect only the relevant processor")."""

    __tablename__ = "file_extractions"

    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), primary_key=True
    )

    status: Mapped[str] = mapped_column(String(20), nullable=False)
    extractor_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    char_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
