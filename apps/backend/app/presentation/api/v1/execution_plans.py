import uuid

from fastapi import APIRouter, Depends, Query

from app.application.approval_service import ApprovalService
from app.application.execution_job_service import ExecutionJobService
from app.application.execution_plan_service import ExecutionPlanService
from app.presentation.api.v1.schemas import (
    CreateExecutionPlanRequest,
    ExecutionJobResponse,
    ExecutionPlanDetailResponse,
    ExecutionPlanResponse,
    PermanentDeleteRequest,
)
from app.presentation.dependencies.auth import get_current_user, require_role
from app.presentation.dependencies.rate_limit import rate_limiter
from app.presentation.dependencies.services import (
    get_approval_service,
    get_execution_job_service,
    get_execution_plan_service,
)
from vault_shared import ValidationError, VaultError, get_logger
from vault_shared.db.models import RoleName, User

logger = get_logger("app.presentation.api.v1.execution_plans")

execution_plans_router = APIRouter(tags=["execution-plans"])

_require_owner_or_admin = require_role(RoleName.OWNER, RoleName.ADMIN)
_create_plan_rate_limit = rate_limiter("execution-plan-create", limit=30, window_seconds=60)


@execution_plans_router.post(
    "/execution-plans",
    response_model=ExecutionPlanResponse,
    status_code=201,
    dependencies=[Depends(_create_plan_rate_limit)],
)
def create_execution_plan(
    request: CreateExecutionPlanRequest,
    user: User = Depends(_require_owner_or_admin),
    service: ExecutionPlanService = Depends(get_execution_plan_service),
    approvals: ApprovalService = Depends(get_approval_service),
) -> ExecutionPlanResponse:
    has_recommendation = request.recommendation_id is not None
    has_duplicate_group = request.duplicate_group_id is not None
    has_ad_hoc = bool(request.file_ids)
    if sum([has_recommendation, has_duplicate_group, has_ad_hoc]) != 1:
        raise ValidationError(
            "Provide exactly one of recommendation_id, duplicate_group_id, "
            "or file_ids (with action_type)."
        )

    if has_recommendation:
        plan = service.create_plan(
            uuid.UUID(request.recommendation_id),
            organization_id=user.organization_id,
            user_id=user.id,
        )
    elif has_duplicate_group:
        plan = service.create_plan_from_duplicate_group(
            uuid.UUID(request.duplicate_group_id),
            organization_id=user.organization_id,
            user_id=user.id,
        )
    else:
        if not request.action_type or not request.file_ids:
            raise ValidationError("action_type is required when providing file_ids.")
        plan = service.create_ad_hoc_plan(
            [uuid.UUID(fid) for fid in request.file_ids],
            action_type=request.action_type,
            organization_id=user.organization_id,
            user_id=user.id,
            new_name=request.new_name,
            new_parent_id=request.new_parent_id,
        )

    # Instant execution mode: every plan is auto-approved by its own
    # creator right away — no human review wait. A failure here (e.g. the
    # connector still lacks write scope) is logged and swallowed rather
    # than failing plan creation itself: the plan already exists and stays
    # PENDING_APPROVAL, reviewable/retryable from the unchanged Approvals
    # page once the underlying problem is fixed.
    try:
        approvals.auto_decide_as_creator(
            plan.id, organization_id=user.organization_id, user_id=user.id
        )
    except VaultError as exc:
        logger.warning(
            "auto_approval_failed", extra={"execution_plan_id": str(plan.id), "error": str(exc)}
        )
    # `service` and `approvals` share one request-scoped Session (both
    # depend on get_db), so `decide()`'s internal commit expires `plan`'s
    # attributes in place — the next read below transparently reloads its
    # now-current status ("approved"/"executing"), no separate re-fetch
    # needed on the success path.
    return ExecutionPlanResponse.from_model(plan)


@execution_plans_router.post(
    "/execution-plans/permanent-delete",
    response_model=ExecutionPlanResponse,
    status_code=201,
    dependencies=[Depends(_create_plan_rate_limit)],
)
def create_permanent_delete_plan(
    request: PermanentDeleteRequest,
    user: User = Depends(_require_owner_or_admin),
    service: ExecutionPlanService = Depends(get_execution_plan_service),
) -> ExecutionPlanResponse:
    """Deliberately never calls `auto_decide_as_creator` — every other
    execution plan in this app auto-approves instantly, but a real,
    unrecoverable Drive deletion always has to wait for a genuine, separate
    approval from the Approvals page, no matter who created it."""
    if not request.file_ids:
        raise ValidationError("Select at least one file.")
    plan = service.create_permanent_delete_plan(
        [uuid.UUID(fid) for fid in request.file_ids],
        organization_id=user.organization_id,
        user_id=user.id,
    )
    return ExecutionPlanResponse.from_model(plan)


@execution_plans_router.get("/execution-plans", response_model=list[ExecutionPlanResponse])
def list_execution_plans(
    status: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    service: ExecutionPlanService = Depends(get_execution_plan_service),
) -> list[ExecutionPlanResponse]:
    plans = service.list_for_organization(user.organization_id, status=status)
    return [ExecutionPlanResponse.from_model(plan) for plan in plans]


@execution_plans_router.get(
    "/execution-plans/{execution_plan_id}", response_model=ExecutionPlanDetailResponse
)
def get_execution_plan(
    execution_plan_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ExecutionPlanService = Depends(get_execution_plan_service),
) -> ExecutionPlanDetailResponse:
    detail = service.get_detail(execution_plan_id, organization_id=user.organization_id)
    return ExecutionPlanDetailResponse.from_detail(detail)


@execution_plans_router.post(
    "/execution-plans/{execution_plan_id}/rollback",
    response_model=ExecutionJobResponse,
    status_code=201,
)
def rollback_execution_plan(
    execution_plan_id: uuid.UUID,
    user: User = Depends(_require_owner_or_admin),
    service: ExecutionJobService = Depends(get_execution_job_service),
) -> ExecutionJobResponse:
    job = service.trigger_rollback(
        execution_plan_id, organization_id=user.organization_id, user_id=user.id
    )
    return ExecutionJobResponse.from_model(job)
