import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class IntelligenceStatus(enum.StrEnum):
    SUCCESS = "success"
    # The completion provider responded, but the response couldn't be
    # turned into usable structured output (non-JSON, wrong shape) — a
    # per-file outcome, never a whole-job failure (see IntelligenceService).
    FAILED = "failed"
    # No extracted text to analyze (missing/failed/unsupported
    # FileExtraction) — the LLM is never called with nothing to work with.
    UNSUPPORTED = "unsupported"


class FileIntelligence(Base):
    """Phase 2's AI File Intelligence output — one row per file, produced
    by a real completion-provider call (unlike `FileClassification`/
    `KnowledgeAttribute`, which stay 100% deterministic — Phase 5's
    "prioritize deterministic processing over AI usage" applies to those,
    not to this later, explicitly-AI stage). `document_type` here is
    deliberately a separate field from `FileClassification.document_type`:
    one is a rule match (`method` explains which rule), this one is an
    LLM's judgment call, and conflating them would hide that distinction
    from every consumer. `entities`/`structured_metadata`/`topics` are
    JSONB rather than rows in `KnowledgeAttribute` — that table's
    `UniqueConstraint(file_id, attribute_type, value)` doesn't tolerate
    near-duplicate LLM phrasing, and its bare `value: str` can't hold an
    entity's role/normalized form. One-to-one with `File`; re-analysis
    overwrites this row, same lifecycle as `FileClassification`."""

    __tablename__ = "file_intelligence"

    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), primary_key=True
    )

    status: Mapped[str] = mapped_column(String(20), nullable=False)
    document_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    entities: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    structured_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    topics: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    error: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
