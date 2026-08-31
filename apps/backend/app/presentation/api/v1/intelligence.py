import uuid

from fastapi import APIRouter, Depends

from app.application.intelligence_job_service import IntelligenceJobService
from app.presentation.api.v1.schemas import IntelligenceJobResponse
from app.presentation.dependencies.auth import get_current_user, require_role
from app.presentation.dependencies.rate_limit import rate_limiter
from app.presentation.dependencies.services import get_intelligence_job_service
from vault_shared.db.models import RoleName, User

intelligence_router = APIRouter(tags=["intelligence"])

_require_owner_or_admin = require_role(RoleName.OWNER, RoleName.ADMIN)
_start_intelligence_rate_limit = rate_limiter("intelligence-start", limit=10, window_seconds=60)


@intelligence_router.post(
    "/connectors/{connector_id}/intelligence",
    response_model=IntelligenceJobResponse,
    status_code=201,
    dependencies=[Depends(_start_intelligence_rate_limit)],
)
def start_intelligence(
    connector_id: uuid.UUID,
    user: User = Depends(_require_owner_or_admin),
    service: IntelligenceJobService = Depends(get_intelligence_job_service),
) -> IntelligenceJobResponse:
    job = service.start(connector_id, organization_id=user.organization_id, user_id=user.id)
    return IntelligenceJobResponse.from_model(job)


@intelligence_router.get(
    "/connectors/{connector_id}/intelligence", response_model=list[IntelligenceJobResponse]
)
def list_intelligence_jobs(
    connector_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: IntelligenceJobService = Depends(get_intelligence_job_service),
) -> list[IntelligenceJobResponse]:
    jobs = service.list_for_connector(connector_id, organization_id=user.organization_id)
    return [IntelligenceJobResponse.from_model(job) for job in jobs]


@intelligence_router.get(
    "/intelligence/{intelligence_job_id}", response_model=IntelligenceJobResponse
)
def get_intelligence_job(
    intelligence_job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: IntelligenceJobService = Depends(get_intelligence_job_service),
) -> IntelligenceJobResponse:
    job = service.get_owned(intelligence_job_id, organization_id=user.organization_id)
    progress = service.get_progress(job.id)
    return IntelligenceJobResponse.from_model(job, progress=progress)


@intelligence_router.post(
    "/intelligence/{intelligence_job_id}/cancel", response_model=IntelligenceJobResponse
)
def cancel_intelligence_job(
    intelligence_job_id: uuid.UUID,
    user: User = Depends(_require_owner_or_admin),
    service: IntelligenceJobService = Depends(get_intelligence_job_service),
) -> IntelligenceJobResponse:
    job = service.get_owned(intelligence_job_id, organization_id=user.organization_id)
    cancelled = service.cancel(job, organization_id=user.organization_id, user_id=user.id)
    return IntelligenceJobResponse.from_model(cancelled)
