import uuid

from fastapi import APIRouter, Depends, Query

from app.application.workflow_execution_service import WorkflowExecutionService
from app.presentation.api.v1.schemas import (
    WorkflowExecutionDetailResponse,
    WorkflowExecutionResponse,
)
from app.presentation.dependencies.auth import get_current_user, require_role
from app.presentation.dependencies.rate_limit import rate_limiter
from app.presentation.dependencies.services import get_workflow_execution_service
from vault_shared.db.models import RoleName, User

workflow_executions_router = APIRouter(tags=["workflow-executions"])

_require_owner_or_admin = require_role(RoleName.OWNER, RoleName.ADMIN)

# Phase 9 spec's explicit Security Requirement: "Rate limiting for
# scheduled jobs" — a manual trigger is the one execution-starting action
# a user can fire repeatedly themselves (scheduled/event triggers are
# already bounded by the scheduler's own ~60s sweep and per-workflow
# "one active run at a time" check).
_trigger_rate_limit = rate_limiter("workflow-trigger-manual", limit=30, window_seconds=60)


@workflow_executions_router.post(
    "/workflows/{workflow_id}/executions",
    response_model=WorkflowExecutionResponse,
    status_code=201,
    dependencies=[Depends(_trigger_rate_limit)],
)
def trigger_workflow_manually(
    workflow_id: uuid.UUID,
    user: User = Depends(_require_owner_or_admin),
    service: WorkflowExecutionService = Depends(get_workflow_execution_service),
) -> WorkflowExecutionResponse:
    execution = service.trigger_manual(
        workflow_id, organization_id=user.organization_id, user_id=user.id
    )
    return WorkflowExecutionResponse.from_model(execution)


@workflow_executions_router.get(
    "/workflows/{workflow_id}/executions", response_model=list[WorkflowExecutionResponse]
)
def list_executions_for_workflow(
    workflow_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: WorkflowExecutionService = Depends(get_workflow_execution_service),
) -> list[WorkflowExecutionResponse]:
    executions = service.list_for_workflow(workflow_id, organization_id=user.organization_id)
    return [WorkflowExecutionResponse.from_model(e) for e in executions]


@workflow_executions_router.get(
    "/workflow-executions", response_model=list[WorkflowExecutionResponse]
)
def list_workflow_executions(
    status: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    service: WorkflowExecutionService = Depends(get_workflow_execution_service),
) -> list[WorkflowExecutionResponse]:
    executions = service.list_for_organization(user.organization_id, status=status)
    return [WorkflowExecutionResponse.from_model(e) for e in executions]


@workflow_executions_router.get(
    "/workflow-executions/{workflow_execution_id}", response_model=WorkflowExecutionDetailResponse
)
def get_workflow_execution(
    workflow_execution_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: WorkflowExecutionService = Depends(get_workflow_execution_service),
) -> WorkflowExecutionDetailResponse:
    detail = service.get_detail(workflow_execution_id, organization_id=user.organization_id)
    return WorkflowExecutionDetailResponse.from_detail(detail)


@workflow_executions_router.post(
    "/workflow-executions/{workflow_execution_id}/cancel", response_model=WorkflowExecutionResponse
)
def cancel_workflow_execution(
    workflow_execution_id: uuid.UUID,
    user: User = Depends(_require_owner_or_admin),
    service: WorkflowExecutionService = Depends(get_workflow_execution_service),
) -> WorkflowExecutionResponse:
    execution = service.get_owned(workflow_execution_id, organization_id=user.organization_id)
    cancelled = service.cancel(execution, organization_id=user.organization_id, user_id=user.id)
    return WorkflowExecutionResponse.from_model(cancelled)


@workflow_executions_router.post(
    "/workflow-executions/{workflow_execution_id}/pause", response_model=WorkflowExecutionResponse
)
def pause_workflow_execution(
    workflow_execution_id: uuid.UUID,
    user: User = Depends(_require_owner_or_admin),
    service: WorkflowExecutionService = Depends(get_workflow_execution_service),
) -> WorkflowExecutionResponse:
    execution = service.get_owned(workflow_execution_id, organization_id=user.organization_id)
    paused = service.pause(execution, organization_id=user.organization_id, user_id=user.id)
    return WorkflowExecutionResponse.from_model(paused)


@workflow_executions_router.post(
    "/workflow-executions/{workflow_execution_id}/resume", response_model=WorkflowExecutionResponse
)
def resume_workflow_execution(
    workflow_execution_id: uuid.UUID,
    user: User = Depends(_require_owner_or_admin),
    service: WorkflowExecutionService = Depends(get_workflow_execution_service),
) -> WorkflowExecutionResponse:
    execution = service.get_owned(workflow_execution_id, organization_id=user.organization_id)
    resumed = service.resume(execution, organization_id=user.organization_id, user_id=user.id)
    return WorkflowExecutionResponse.from_model(resumed)
