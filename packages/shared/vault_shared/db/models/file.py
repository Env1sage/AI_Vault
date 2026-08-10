import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class File(Base):
    """Provider-neutral file metadata record — no file *contents* are ever
    stored here (Phase 4 spec: "do not download full file contents").
    `permissions_summary` is a simplified text summary, not the provider's
    raw ACL — enough to know a file is shared and with whom broadly, not a
    full permissions mirror."""

    __tablename__ = "files"
    __table_args__ = (
        UniqueConstraint(
            "storage_source_id", "provider_file_id", name="uq_file_source_provider_id"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    storage_source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("storage_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_folder_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("folders.id", ondelete="CASCADE"), nullable=True, index=True
    )

    provider_file_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_parent_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str] = mapped_column(String(1024), nullable=False)
    path: Mapped[str] = mapped_column(String(4096), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    owner_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    is_shared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    permissions_summary: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    version_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(255), nullable=True)

    provider_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    provider_modified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    provider_viewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
