import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from vault_shared.db.models import ConnectorCredentials


class ConnectorCredentialsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_connector_id(self, connector_id: uuid.UUID) -> ConnectorCredentials | None:
        return (
            self._session.query(ConnectorCredentials).filter_by(connector_id=connector_id).first()
        )

    def upsert(
        self,
        *,
        connector_id: uuid.UUID,
        access_token_encrypted: str,
        refresh_token_encrypted: str,
        granted_scopes: str,
        expires_at: datetime,
    ) -> ConnectorCredentials:
        credentials = self.get_by_connector_id(connector_id)
        if credentials is None:
            credentials = ConnectorCredentials(connector_id=connector_id)
            self._session.add(credentials)

        credentials.access_token_encrypted = access_token_encrypted
        credentials.refresh_token_encrypted = refresh_token_encrypted
        credentials.granted_scopes = granted_scopes
        credentials.expires_at = expires_at
        self._session.flush()
        return credentials

    def update_access_token(
        self,
        credentials: ConnectorCredentials,
        *,
        access_token_encrypted: str,
        expires_at: datetime,
    ) -> None:
        credentials.access_token_encrypted = access_token_encrypted
        credentials.expires_at = expires_at
        self._session.flush()

    def delete(self, credentials: ConnectorCredentials) -> None:
        self._session.delete(credentials)
        self._session.flush()
