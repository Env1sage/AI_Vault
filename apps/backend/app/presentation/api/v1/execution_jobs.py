import uuid

from fastapi import APIRouter, Depends, Query

from app.application.execution_job_service import ExecutionJobService
from app.presentation.api.v1.schemas import ExecutionJobDetailResponse, ExecutionJobResponse
from app.presentation.dependencies.auth import get_current_user, require_role
from app.presentation.dependencies.services import get_execution_job_service
from vault_shared.db.models import RoleName, User

execution_jobs_router = APIRouter(tags=["execution-jobs"])

_require_owner_or_admin = require_role(RoleName.OWNER, RoleName.ADMIN)


@execution_jobs_router.get("/execution-jobs", response_model=list[ExecutionJobResponse])
def list_execution_jobs(
    status: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    service: ExecutionJobService = Depends(get_execution_job_service),
) -> list[ExecutionJobResponse]:
    jobs = service.list_for_organization(user.organization_id, status=status)
    return [ExecutionJobResponse.from_model(job) for job in jobs]


@execution_jobs_router.get(
    "/execution-jobs/{execution_job_id}", response_model=ExecutionJobDetailResponse
)
def get_execution_job(
    execution_job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ExecutionJobService = Depends(get_execution_job_service),
) -> ExecutionJobDetailResponse:
    detail = service.get_detail(execution_job_id, organization_id=user.organization_id)
    return ExecutionJobDetailResponse.from_detail(detail)


@execution_jobs_router.post(
    "/execution-jobs/{execution_job_id}/cancel", response_model=ExecutionJobResponse
)
def cancel_execution_job(
    execution_job_id: uuid.UUID,
    user: User = Depends(_require_owner_or_admin),
    service: ExecutionJobService = Depends(get_execution_job_service),
) -> ExecutionJobResponse:
    job = service.get_owned(execution_job_id, organization_id=user.organization_id)
    cancelled = service.cancel(job, organization_id=user.organization_id, user_id=user.id)
    return ExecutionJobResponse.from_model(cancelled)


@execution_jobs_router.post(
    "/execution-jobs/{execution_job_id}/pause", response_model=ExecutionJobResponse
)
def pause_execution_job(
    execution_job_id: uuid.UUID,
    user: User = Depends(_require_owner_or_admin),
    service: ExecutionJobService = Depends(get_execution_job_service),
) -> ExecutionJobResponse:
    job = service.get_owned(execution_job_id, organization_id=user.organization_id)
    paused = service.pause(job, organization_id=user.organization_id, user_id=user.id)
    return ExecutionJobResponse.from_model(paused)


@execution_jobs_router.post(
    "/execution-jobs/{execution_job_id}/resume", response_model=ExecutionJobResponse
)
def resume_execution_job(
    execution_job_id: uuid.UUID,
    user: User = Depends(_require_owner_or_admin),
    service: ExecutionJobService = Depends(get_execution_job_service),
) -> ExecutionJobResponse:
    job = service.get_owned(execution_job_id, organization_id=user.organization_id)
    resumed = service.resume(job, organization_id=user.organization_id, user_id=user.id)
    return ExecutionJobResponse.from_model(resumed)
