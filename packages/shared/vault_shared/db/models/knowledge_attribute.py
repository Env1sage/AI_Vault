import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class KnowledgeAttribute(Base):
    """A single inferred fact linking a file to organizational context —
    department, time period, and (future) project/campaign — per the
    Knowledge Builder's "relate items to departments/people" responsibility
    (Handbook §8.4). Deliberately an open-ended key/value/confidence shape
    (`attribute_type`/`value`) rather than dedicated columns per attribute
    kind, since the phase spec expects this to grow (project, campaign) as
    inference improves — Phase 5's Design Principles: "provider-neutral and
    extensible." `source` records which processor produced it, for the same
    explainability reason `FileClassification.method` does."""

    __tablename__ = "knowledge_attributes"
    __table_args__ = (
        UniqueConstraint(
            "file_id", "attribute_type", "value", name="uq_knowledge_attribute_file_type_value"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True
    )

    attribute_type: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
