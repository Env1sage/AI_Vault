import uuid

from fastapi import APIRouter, Depends

from app.application.enrichment_job_service import EnrichmentJobService
from app.presentation.api.v1.schemas import EnrichmentJobResponse
from app.presentation.dependencies.auth import get_current_user, require_role
from app.presentation.dependencies.rate_limit import rate_limiter
from app.presentation.dependencies.services import get_enrichment_job_service
from vault_shared.db.models import RoleName, User

enrichment_router = APIRouter(tags=["enrichment"])

_require_owner_or_admin = require_role(RoleName.OWNER, RoleName.ADMIN)
_start_enrichment_rate_limit = rate_limiter("enrichment-start", limit=10, window_seconds=60)


@enrichment_router.post(
    "/connectors/{connector_id}/enrichment",
    response_model=EnrichmentJobResponse,
    status_code=201,
    dependencies=[Depends(_start_enrichment_rate_limit)],
)
def start_enrichment(
    connector_id: uuid.UUID,
    user: User = Depends(_require_owner_or_admin),
    service: EnrichmentJobService = Depends(get_enrichment_job_service),
) -> EnrichmentJobResponse:
    job = service.start(connector_id, organization_id=user.organization_id, user_id=user.id)
    return EnrichmentJobResponse.from_model(job)


@enrichment_router.get(
    "/connectors/{connector_id}/enrichment", response_model=list[EnrichmentJobResponse]
)
def list_enrichment_jobs(
    connector_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: EnrichmentJobService = Depends(get_enrichment_job_service),
) -> list[EnrichmentJobResponse]:
    jobs = service.list_for_connector(connector_id, organization_id=user.organization_id)
    return [EnrichmentJobResponse.from_model(job) for job in jobs]


@enrichment_router.get("/enrichment/{enrichment_job_id}", response_model=EnrichmentJobResponse)
def get_enrichment_job(
    enrichment_job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: EnrichmentJobService = Depends(get_enrichment_job_service),
) -> EnrichmentJobResponse:
    job = service.get_owned(enrichment_job_id, organization_id=user.organization_id)
    progress = service.get_progress(job.id)
    return EnrichmentJobResponse.from_model(job, progress=progress)


@enrichment_router.post(
    "/enrichment/{enrichment_job_id}/cancel", response_model=EnrichmentJobResponse
)
def cancel_enrichment_job(
    enrichment_job_id: uuid.UUID,
    user: User = Depends(_require_owner_or_admin),
    service: EnrichmentJobService = Depends(get_enrichment_job_service),
) -> EnrichmentJobResponse:
    job = service.get_owned(enrichment_job_id, organization_id=user.organization_id)
    cancelled = service.cancel(job, organization_id=user.organization_id, user_id=user.id)
    return EnrichmentJobResponse.from_model(cancelled)
