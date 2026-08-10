from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.auth_service import AuthService
from app.application.connector_service import ConnectorService
from app.application.organization_service import OrganizationService
from app.application.scan_service import ScanService
from vault_shared.connectors.google_workspace import (
    GoogleWorkspaceOAuthClient,
    get_google_workspace_oauth_client,
)
from vault_shared.db.session import get_db


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_organization_service(db: Session = Depends(get_db)) -> OrganizationService:
    return OrganizationService(db)


def get_connector_service(
    db: Session = Depends(get_db),
    oauth_client: GoogleWorkspaceOAuthClient = Depends(get_google_workspace_oauth_client),
) -> ConnectorService:
    return ConnectorService(db, oauth_client=oauth_client)


def get_scan_service(db: Session = Depends(get_db)) -> ScanService:
    return ScanService(db)
