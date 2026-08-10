from fastapi import APIRouter, Depends

from app.application.organization_service import OrganizationService
from app.presentation.api.v1.schemas import OrganizationResponse, OrganizationUpdateRequest
from app.presentation.dependencies.auth import get_current_user, require_role
from app.presentation.dependencies.services import get_organization_service
from vault_shared.db.models import RoleName, User

organizations_router = APIRouter(prefix="/organizations", tags=["organizations"])

_require_owner_or_admin = require_role(RoleName.OWNER, RoleName.ADMIN)


@organizations_router.get("/current", response_model=OrganizationResponse)
def get_current_organization(user: User = Depends(get_current_user)) -> OrganizationResponse:
    return OrganizationResponse.from_model(user.organization)


@organizations_router.patch("/current", response_model=OrganizationResponse)
def update_current_organization(
    body: OrganizationUpdateRequest,
    user: User = Depends(_require_owner_or_admin),
    service: OrganizationService = Depends(get_organization_service),
) -> OrganizationResponse:
    organization = service.rename(user.organization, name=body.name)
    return OrganizationResponse.from_model(organization)
