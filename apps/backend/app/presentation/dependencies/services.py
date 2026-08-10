from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.auth_service import AuthService
from app.application.organization_service import OrganizationService
from vault_shared.db.session import get_db


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_organization_service(db: Session = Depends(get_db)) -> OrganizationService:
    return OrganizationService(db)
