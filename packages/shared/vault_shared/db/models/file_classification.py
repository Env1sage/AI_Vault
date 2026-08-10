import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class FileClassification(Base):
    """The Classification Pipeline's output (Phase 5 spec) — one document-type
    label per file, produced by deterministic rules (`method` records which
    rule matched, e.g. "mime_pdf" or "keyword_invoice", for explainability —
    Handbook's Design Principles: "produce explainable outputs"). One-to-one
    with `File`; re-enrichment overwrites this row rather than accumulating
    history, since only the current classification is actionable."""

    __tablename__ = "file_classifications"

    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), primary_key=True
    )

    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    method: Mapped[str] = mapped_column(String(100), nullable=False)
    classified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
