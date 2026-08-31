import uuid

from sqlalchemy.orm import Session

from app.infrastructure.connectors.oauth_state import consume_state, issue_state
from app.infrastructure.queue.workflow_producer import enqueue_workflow_execution
from vault_shared import (
    ConflictError,
    DependencyUnavailableError,
    NotFoundError,
    ReauthRequiredError,
    UnauthorizedError,
    get_logger,
)
from vault_shared.connector_service import ConnectorTokenService
from vault_shared.connectors.google_workspace import GoogleWorkspaceOAuthClient
from vault_shared.db.models import ConnectorProvider, StorageConnector, WorkflowEventType
from vault_shared.db.models.storage_connector import ConnectorStatus
from vault_shared.db.repositories import (
    AuditLogRepository,
    ConnectorCredentialsRepository,
    StorageConnectorRepository,
)
from vault_shared.security.encryption import TokenEncryptionError, decrypt_token, encrypt_token
from vault_shared.workflow_events import fire_workflow_event

logger = get_logger("app.application.connector_service")


class ConnectorService:
    """Orchestrates the *interactive* connector lifecycle (Handbook §6.1.2
    application layer) — the connect/callback/verify/disconnect web flow.
    Composes `vault_shared.connector_service.ConnectorTokenService` for
    token refresh, since that piece is also needed by apps/worker (Phase 4's
    scanner) and can't depend on this class's Redis-backed OAuth state,
    which is backend-presentation-layer-only. See ADR-015."""

    def __init__(self, db: Session, *, oauth_client: GoogleWorkspaceOAuthClient) -> None:
        self._db = db
        self._oauth_client = oauth_client
        self._connectors = StorageConnectorRepository(db)
        self._credentials = ConnectorCredentialsRepository(db)
        self._audit_logs = AuditLogRepository(db)
        self._tokens = ConnectorTokenService(db, oauth_client=oauth_client)

    def list_for_organization(self, organization_id: uuid.UUID) -> list[StorageConnector]:
        return self._connectors.list_for_organization(organization_id)

    def get_owned(self, connector_id: uuid.UUID, *, organization_id: uuid.UUID) -> StorageConnector:
        connector = self._connectors.get_by_id(connector_id)
        if connector is None or connector.organization_id != organization_id:
            raise NotFoundError("Connector not found.")
        return connector

    def initiate_connect(self, *, organization_id: uuid.UUID, user_id: uuid.UUID) -> str:
        existing = self._connectors.get_by_organization_and_provider(
            organization_id=organization_id, provider=ConnectorProvider.GOOGLE_WORKSPACE
        )
        if existing is not None and existing.status == ConnectorStatus.CONNECTED:
            raise ConflictError("Google Workspace is already connected for this organization.")

        state = issue_state(
            provider=ConnectorProvider.GOOGLE_WORKSPACE,
            organization_id=organization_id,
            user_id=user_id,
        )
        self._audit_logs.record(
            event_type="connector_connect_initiated",
            organization_id=organization_id,
            user_id=user_id,
            metadata={"provider": ConnectorProvider.GOOGLE_WORKSPACE.value},
        )
        self._db.commit()
        return self._oauth_client.build_authorize_url(state=state)

    def complete_connect(
        self,
        *,
        code: str,
        state: str,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        ip_address: str | None,
    ) -> StorageConnector:
        claim = consume_state(provider=ConnectorProvider.GOOGLE_WORKSPACE, state=state)
        if claim.organization_id != organization_id:
            self._audit_logs.record(
                event_type="connector_connect_failed_state_mismatch",
                organization_id=organization_id,
                user_id=user_id,
                ip_address=ip_address,
            )
            self._db.commit()
            raise UnauthorizedError("This connection attempt doesn't belong to your organization.")

        token_set = self._oauth_client.exchange_code(code=code)
        if not token_set.refresh_token:
            self._audit_logs.record(
                event_type="connector_connect_failed_no_refresh_token",
                organization_id=organization_id,
                user_id=user_id,
                ip_address=ip_address,
            )
            self._db.commit()
            raise ConflictError(
                "Google did not grant offline access. Remove AI Project Vault from "
                "https://myaccount.google.com/permissions and try connecting again."
            )

        account_info = self._oauth_client.fetch_account_info(access_token=token_set.access_token)

        connector = self._connectors.upsert_connected(
            organization_id=organization_id,
            provider=ConnectorProvider.GOOGLE_WORKSPACE,
            connected_by_user_id=user_id,
            account_email=account_info.email,
            workspace_domain=account_info.workspace_domain,
        )
        self._credentials.upsert(
            connector_id=connector.id,
            access_token_encrypted=encrypt_token(token_set.access_token),
            refresh_token_encrypted=encrypt_token(token_set.refresh_token),
            granted_scopes=token_set.granted_scopes,
            expires_at=token_set.expires_at,
        )
        self._audit_logs.record(
            event_type="connector_connected",
            organization_id=organization_id,
            user_id=user_id,
            metadata={
                "provider": ConnectorProvider.GOOGLE_WORKSPACE.value,
                "account_email": account_info.email,
            },
            ip_address=ip_address,
        )
        self._db.commit()

        # Phase 9's `connector_reconnected` event trigger — fires on every
        # successful connect/reconnect (this method doesn't distinguish a
        # first connect from a reconnect; a workflow's own condition node
        # can if that matters to it). Best-effort: a workflow-trigger
        # failure must never fail the connector connection itself.
        fire_workflow_event(
            self._db,
            organization_id=organization_id,
            event_type=WorkflowEventType.CONNECTOR_RECONNECTED,
            payload={"connector_id": str(connector.id)},
            enqueue_workflow_execution=enqueue_workflow_execution,
        )
        return connector

    def get_valid_access_token(self, connector: StorageConnector) -> str:
        return self._tokens.get_valid_access_token(connector)

    def verify(self, connector: StorageConnector, *, ip_address: str | None) -> StorageConnector:
        try:
            access_token = self.get_valid_access_token(connector)
            account_info = self._oauth_client.fetch_account_info(access_token=access_token)
        except ReauthRequiredError as exc:
            self._connectors.mark_reauth_required(connector, error=str(exc))
            self._audit_logs.record(
                event_type="connector_reauth_required",
                organization_id=connector.organization_id,
                metadata={"provider": connector.provider, "reason": str(exc)},
                ip_address=ip_address,
            )
            self._db.commit()
            return connector
        except (
            NotFoundError,
            UnauthorizedError,
            DependencyUnavailableError,
            TokenEncryptionError,
        ) as exc:
            self._connectors.mark_error(connector, error=str(exc))
            self._audit_logs.record(
                event_type="connector_verification_failed",
                organization_id=connector.organization_id,
                metadata={"provider": connector.provider, "reason": str(exc)},
                ip_address=ip_address,
            )
            self._db.commit()
            return connector

        connector.account_email = account_info.email
        connector.workspace_domain = account_info.workspace_domain
        self._connectors.mark_verified(connector)
        self._audit_logs.record(
            event_type="connector_verified",
            organization_id=connector.organization_id,
            metadata={"provider": connector.provider},
            ip_address=ip_address,
        )
        self._db.commit()
        return connector

    def disconnect(
        self, connector: StorageConnector, *, ip_address: str | None
    ) -> StorageConnector:
        credentials = self._credentials.get_by_connector_id(connector.id)
        if credentials is not None:
            try:
                refresh_token = decrypt_token(credentials.refresh_token_encrypted)
                self._oauth_client.revoke(token=refresh_token)
            except TokenEncryptionError:
                logger.warning("connector_disconnect_could_not_decrypt_token_for_revoke")
            self._credentials.delete(credentials)

        self._connectors.mark_disconnected(connector)
        self._audit_logs.record(
            event_type="connector_disconnected",
            organization_id=connector.organization_id,
            metadata={"provider": connector.provider},
            ip_address=ip_address,
        )
        self._db.commit()
        return connector
