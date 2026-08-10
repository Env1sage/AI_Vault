import uuid

from fastapi import APIRouter, Depends, Query

from app.application.workflow_service import WorkflowService
from app.application.workflow_trigger_service import WorkflowTriggerService
from app.presentation.api.v1.schemas import (
    CreateWorkflowRequest,
    CreateWorkflowTriggerRequest,
    ReplaceWorkflowNodesRequest,
    SetWorkflowStatusRequest,
    SetWorkflowTriggerEnabledRequest,
    WorkflowDetailResponse,
    WorkflowDraftResponse,
    WorkflowNodeResponse,
    WorkflowResponse,
    WorkflowTriggerResponse,
    WorkflowVersionResponse,
)
from app.presentation.dependencies.auth import get_current_user, require_role
from app.presentation.dependencies.services import (
    get_workflow_service,
    get_workflow_trigger_service,
)
from vault_shared.db.models import RoleName, User

workflows_router = APIRouter(tags=["workflows"])

_require_owner_or_admin = require_role(RoleName.OWNER, RoleName.ADMIN)


@workflows_router.post("/workflows", response_model=WorkflowResponse, status_code=201)
def create_workflow(
    request: CreateWorkflowRequest,
    user: User = Depends(_require_owner_or_admin),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowResponse:
    workflow = service.create(
        organization_id=user.organization_id,
        user_id=user.id,
        name=request.name,
        description=request.description,
    )
    return WorkflowResponse.from_model(workflow)


@workflows_router.get("/workflows", response_model=list[WorkflowResponse])
def list_workflows(
    status: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    service: WorkflowService = Depends(get_workflow_service),
) -> list[WorkflowResponse]:
    workflows = service.list_for_organization(user.organization_id, status=status)
    return [WorkflowResponse.from_model(w) for w in workflows]


@workflows_router.get("/workflows/{workflow_id}", response_model=WorkflowDetailResponse)
def get_workflow(
    workflow_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowDetailResponse:
    detail = service.get_detail(workflow_id, organization_id=user.organization_id)
    return WorkflowDetailResponse.from_detail(detail)


@workflows_router.get(
    "/workflows/{workflow_id}/versions", response_model=list[WorkflowVersionResponse]
)
def list_workflow_versions(
    workflow_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: WorkflowService = Depends(get_workflow_service),
) -> list[WorkflowVersionResponse]:
    versions = service.list_versions(workflow_id, organization_id=user.organization_id)
    return [WorkflowVersionResponse.from_model(v) for v in versions]


@workflows_router.post("/workflows/{workflow_id}/draft", response_model=WorkflowDraftResponse)
def get_or_create_draft(
    workflow_id: uuid.UUID,
    user: User = Depends(_require_owner_or_admin),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowDraftResponse:
    version, nodes = service.get_or_create_draft(
        workflow_id, organization_id=user.organization_id, user_id=user.id
    )
    return WorkflowDraftResponse(
        version=WorkflowVersionResponse.from_model(version),
        nodes=[WorkflowNodeResponse.from_model(n) for n in nodes],
    )


@workflows_router.put(
    "/workflows/{workflow_id}/versions/{workflow_version_id}/nodes",
    response_model=list[WorkflowNodeResponse],
)
def replace_workflow_nodes(
    workflow_id: uuid.UUID,
    workflow_version_id: uuid.UUID,
    request: ReplaceWorkflowNodesRequest,
    user: User = Depends(_require_owner_or_admin),
    service: WorkflowService = Depends(get_workflow_service),
) -> list[WorkflowNodeResponse]:
    nodes = service.replace_nodes(
        workflow_version_id,
        workflow_id=workflow_id,
        organization_id=user.organization_id,
        nodes=[node.model_dump() for node in request.nodes],
    )
    return [WorkflowNodeResponse.from_model(n) for n in nodes]


@workflows_router.post(
    "/workflows/{workflow_id}/publish", response_model=WorkflowVersionResponse, status_code=201
)
def publish_workflow(
    workflow_id: uuid.UUID,
    user: User = Depends(_require_owner_or_admin),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowVersionResponse:
    version = service.publish(workflow_id, organization_id=user.organization_id, user_id=user.id)
    return WorkflowVersionResponse.from_model(version)


@workflows_router.post(
    "/workflows/{workflow_id}/versions/{workflow_version_id}/rollback",
    response_model=WorkflowVersionResponse,
)
def rollback_workflow(
    workflow_id: uuid.UUID,
    workflow_version_id: uuid.UUID,
    user: User = Depends(_require_owner_or_admin),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowVersionResponse:
    version = service.rollback_to_version(
        workflow_id, workflow_version_id, organization_id=user.organization_id, user_id=user.id
    )
    return WorkflowVersionResponse.from_model(version)


@workflows_router.post("/workflows/{workflow_id}/status", response_model=WorkflowResponse)
def set_workflow_status(
    workflow_id: uuid.UUID,
    request: SetWorkflowStatusRequest,
    user: User = Depends(_require_owner_or_admin),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowResponse:
    workflow = service.set_status(
        workflow_id, organization_id=user.organization_id, user_id=user.id, status=request.status
    )
    return WorkflowResponse.from_model(workflow)


@workflows_router.post(
    "/workflows/{workflow_id}/clone", response_model=WorkflowResponse, status_code=201
)
def clone_workflow(
    workflow_id: uuid.UUID,
    user: User = Depends(_require_owner_or_admin),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowResponse:
    cloned = service.clone(workflow_id, organization_id=user.organization_id, user_id=user.id)
    return WorkflowResponse.from_model(cloned)


@workflows_router.post(
    "/workflows/{workflow_id}/triggers", response_model=WorkflowTriggerResponse, status_code=201
)
def create_workflow_trigger(
    workflow_id: uuid.UUID,
    request: CreateWorkflowTriggerRequest,
    user: User = Depends(_require_owner_or_admin),
    service: WorkflowTriggerService = Depends(get_workflow_trigger_service),
) -> WorkflowTriggerResponse:
    trigger = service.create(
        workflow_id,
        organization_id=user.organization_id,
        user_id=user.id,
        trigger_type=request.trigger_type,
        config=request.config,
    )
    return WorkflowTriggerResponse.from_model(trigger)


@workflows_router.get(
    "/workflows/{workflow_id}/triggers", response_model=list[WorkflowTriggerResponse]
)
def list_workflow_triggers(
    workflow_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: WorkflowTriggerService = Depends(get_workflow_trigger_service),
) -> list[WorkflowTriggerResponse]:
    triggers = service.list_for_workflow(workflow_id, organization_id=user.organization_id)
    return [WorkflowTriggerResponse.from_model(t) for t in triggers]


@workflows_router.post(
    "/workflows/{workflow_id}/triggers/{workflow_trigger_id}/enabled",
    response_model=WorkflowTriggerResponse,
)
def set_workflow_trigger_enabled(
    workflow_id: uuid.UUID,
    workflow_trigger_id: uuid.UUID,
    request: SetWorkflowTriggerEnabledRequest,
    user: User = Depends(_require_owner_or_admin),
    service: WorkflowTriggerService = Depends(get_workflow_trigger_service),
) -> WorkflowTriggerResponse:
    trigger = service.set_enabled(
        workflow_trigger_id,
        workflow_id=workflow_id,
        organization_id=user.organization_id,
        user_id=user.id,
        enabled=request.enabled,
    )
    return WorkflowTriggerResponse.from_model(trigger)
