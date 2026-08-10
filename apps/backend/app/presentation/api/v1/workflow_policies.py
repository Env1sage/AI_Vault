import uuid

from fastapi import APIRouter, Depends

from app.application.workflow_policy_service import WorkflowPolicyService
from app.presentation.api.v1.schemas import CreateWorkflowPolicyRequest, WorkflowPolicyResponse
from app.presentation.dependencies.auth import get_current_user, require_role
from app.presentation.dependencies.services import get_workflow_policy_service
from vault_shared.db.models import RoleName, User

workflow_policies_router = APIRouter(tags=["workflow-policies"])

_require_owner_or_admin = require_role(RoleName.OWNER, RoleName.ADMIN)


@workflow_policies_router.post(
    "/workflow-policies", response_model=WorkflowPolicyResponse, status_code=201
)
def create_workflow_policy(
    request: CreateWorkflowPolicyRequest,
    user: User = Depends(_require_owner_or_admin),
    service: WorkflowPolicyService = Depends(get_workflow_policy_service),
) -> WorkflowPolicyResponse:
    policy = service.create_draft(
        organization_id=user.organization_id,
        user_id=user.id,
        policy_key=request.policy_key,
        name=request.name,
        description=request.description,
        effect=request.effect,
        conditions=request.conditions,
    )
    return WorkflowPolicyResponse.from_model(policy)


@workflow_policies_router.get("/workflow-policies", response_model=list[WorkflowPolicyResponse])
def list_workflow_policies(
    user: User = Depends(get_current_user),
    service: WorkflowPolicyService = Depends(get_workflow_policy_service),
) -> list[WorkflowPolicyResponse]:
    policies = service.list_for_organization(user.organization_id)
    return [WorkflowPolicyResponse.from_model(p) for p in policies]


@workflow_policies_router.get(
    "/workflow-policies/{workflow_policy_id}", response_model=WorkflowPolicyResponse
)
def get_workflow_policy(
    workflow_policy_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: WorkflowPolicyService = Depends(get_workflow_policy_service),
) -> WorkflowPolicyResponse:
    policy = service.get_owned(workflow_policy_id, organization_id=user.organization_id)
    return WorkflowPolicyResponse.from_model(policy)


@workflow_policies_router.get(
    "/workflow-policies/by-key/{policy_key}/versions", response_model=list[WorkflowPolicyResponse]
)
def list_workflow_policy_versions(
    policy_key: str,
    user: User = Depends(get_current_user),
    service: WorkflowPolicyService = Depends(get_workflow_policy_service),
) -> list[WorkflowPolicyResponse]:
    versions = service.list_versions(organization_id=user.organization_id, policy_key=policy_key)
    return [WorkflowPolicyResponse.from_model(p) for p in versions]


@workflow_policies_router.post(
    "/workflow-policies/{workflow_policy_id}/publish", response_model=WorkflowPolicyResponse
)
def publish_workflow_policy(
    workflow_policy_id: uuid.UUID,
    user: User = Depends(_require_owner_or_admin),
    service: WorkflowPolicyService = Depends(get_workflow_policy_service),
) -> WorkflowPolicyResponse:
    policy = service.publish(
        workflow_policy_id, organization_id=user.organization_id, user_id=user.id
    )
    return WorkflowPolicyResponse.from_model(policy)


@workflow_policies_router.post(
    "/workflow-policies/{workflow_policy_id}/archive", response_model=WorkflowPolicyResponse
)
def archive_workflow_policy(
    workflow_policy_id: uuid.UUID,
    user: User = Depends(_require_owner_or_admin),
    service: WorkflowPolicyService = Depends(get_workflow_policy_service),
) -> WorkflowPolicyResponse:
    policy = service.archive(
        workflow_policy_id, organization_id=user.organization_id, user_id=user.id
    )
    return WorkflowPolicyResponse.from_model(policy)
