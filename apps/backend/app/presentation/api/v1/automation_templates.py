import uuid

from fastapi import APIRouter, Depends

from app.application.automation_template_service import AutomationTemplateService
from app.presentation.api.v1.schemas import (
    ApplyAutomationTemplateRequest,
    AutomationTemplateResponse,
    WorkflowResponse,
)
from app.presentation.dependencies.auth import get_current_user, require_role
from app.presentation.dependencies.services import get_automation_template_service
from vault_shared.db.models import RoleName, User

automation_templates_router = APIRouter(tags=["automation-templates"])

_require_owner_or_admin = require_role(RoleName.OWNER, RoleName.ADMIN)


@automation_templates_router.get(
    "/automation-templates", response_model=list[AutomationTemplateResponse]
)
def list_automation_templates(
    user: User = Depends(get_current_user),
    service: AutomationTemplateService = Depends(get_automation_template_service),
) -> list[AutomationTemplateResponse]:
    templates = service.list_available(organization_id=user.organization_id)
    return [AutomationTemplateResponse.from_model(t) for t in templates]


@automation_templates_router.post(
    "/automation-templates/{automation_template_id}/apply",
    response_model=WorkflowResponse,
    status_code=201,
)
def apply_automation_template(
    automation_template_id: uuid.UUID,
    request: ApplyAutomationTemplateRequest,
    user: User = Depends(_require_owner_or_admin),
    service: AutomationTemplateService = Depends(get_automation_template_service),
) -> WorkflowResponse:
    workflow = service.apply(
        automation_template_id,
        organization_id=user.organization_id,
        user_id=user.id,
        workflow_name=request.workflow_name,
    )
    return WorkflowResponse.from_model(workflow)
