import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class Folder(Base):
    """Provider-neutral folder record — `parent_folder_id` is our own
    self-referential hierarchy (rebuilt from the provider's raw parent id at
    scan time), so the storage hierarchy is represented independently of
    Google Drive's specific object model (Handbook §8.2's "provider-neutral
    identifiers and relationships")."""

    __tablename__ = "folders"
    __table_args__ = (
        UniqueConstraint(
            "storage_source_id", "provider_file_id", name="uq_folder_source_provider_id"
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

    owner_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    is_shared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    provider_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    provider_modified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
