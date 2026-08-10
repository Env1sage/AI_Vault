import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vault_shared.db.session import Base

if TYPE_CHECKING:
    from vault_shared.db.models.storage_connector import StorageConnector


class ConnectorCredentials(Base):
    """OAuth tokens for one connector — one-to-one, deleted (not just
    blanked) on disconnect. Only ever holds *encrypted* token values
    (`app.infrastructure.security.encryption`) — Handbook §13's "encrypt
    sensitive tokens before persistence." Never serialized in an API
    response (Phase 3 spec: "never expose refresh tokens")."""

    __tablename__ = "connector_credentials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    connector_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("storage_connectors.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    access_token_encrypted: Mapped[str] = mapped_column(String(2048), nullable=False)
    refresh_token_encrypted: Mapped[str] = mapped_column(String(2048), nullable=False)
    granted_scopes: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    connector: Mapped["StorageConnector"] = relationship(back_populates="credentials")
