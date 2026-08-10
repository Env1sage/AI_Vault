import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class Embedding(Base):
    """A vector representation of one file's content/metadata (Handbook
    §8.5 Embedding Engine) — one-to-one with `File`, keyed by a shared
    primary key like Phase 5's per-file tables. Stores the vector as a
    plain Postgres array and does similarity search in application code
    (brute-force cosine similarity) rather than a dedicated vector
    extension (pgvector) — Handbook §9/§22 explicitly defer a dedicated
    vector store to Petabyte Scale; this is the "not solved now" interim
    that keeps the stack dependency-free until that trigger is hit. See
    ADR-018.

    `model_name`/`model_version` let a future re-embedding (a different or
    upgraded model) be detected and never silently compared against
    stale vectors from a different model — `EmbeddingService` only ever
    treats a file as "up to date" when both the model identity and
    `content_hash` match what's currently stored."""

    __tablename__ = "embeddings"

    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), primary_key=True
    )

    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    vector: Mapped[list[float]] = mapped_column(ARRAY(Float), nullable=False)
    # sha256 of the text that was embedded — lets `EmbeddingService` skip
    # re-embedding a file whose extracted text hasn't actually changed,
    # even if `FileExtraction.extracted_at` was bumped by a no-op rescan.
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
