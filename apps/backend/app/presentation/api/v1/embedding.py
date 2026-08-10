import uuid

from fastapi import APIRouter, Depends

from app.application.embedding_job_service import EmbeddingJobService
from app.presentation.api.v1.schemas import EmbeddingJobResponse
from app.presentation.dependencies.auth import get_current_user, require_role
from app.presentation.dependencies.rate_limit import rate_limiter
from app.presentation.dependencies.services import get_embedding_job_service
from vault_shared.db.models import RoleName, User

embedding_router = APIRouter(tags=["embedding"])

_require_owner_or_admin = require_role(RoleName.OWNER, RoleName.ADMIN)
_start_embedding_rate_limit = rate_limiter("embedding-start", limit=10, window_seconds=60)


@embedding_router.post(
    "/connectors/{connector_id}/embedding",
    response_model=EmbeddingJobResponse,
    status_code=201,
    dependencies=[Depends(_start_embedding_rate_limit)],
)
def start_embedding(
    connector_id: uuid.UUID,
    user: User = Depends(_require_owner_or_admin),
    service: EmbeddingJobService = Depends(get_embedding_job_service),
) -> EmbeddingJobResponse:
    job = service.start(connector_id, organization_id=user.organization_id, user_id=user.id)
    return EmbeddingJobResponse.from_model(job)


@embedding_router.get(
    "/connectors/{connector_id}/embedding", response_model=list[EmbeddingJobResponse]
)
def list_embedding_jobs(
    connector_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: EmbeddingJobService = Depends(get_embedding_job_service),
) -> list[EmbeddingJobResponse]:
    jobs = service.list_for_connector(connector_id, organization_id=user.organization_id)
    return [EmbeddingJobResponse.from_model(job) for job in jobs]


@embedding_router.get("/embedding/{embedding_job_id}", response_model=EmbeddingJobResponse)
def get_embedding_job(
    embedding_job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: EmbeddingJobService = Depends(get_embedding_job_service),
) -> EmbeddingJobResponse:
    job = service.get_owned(embedding_job_id, organization_id=user.organization_id)
    progress = service.get_progress(job.id)
    return EmbeddingJobResponse.from_model(job, progress=progress)


@embedding_router.post("/embedding/{embedding_job_id}/cancel", response_model=EmbeddingJobResponse)
def cancel_embedding_job(
    embedding_job_id: uuid.UUID,
    user: User = Depends(_require_owner_or_admin),
    service: EmbeddingJobService = Depends(get_embedding_job_service),
) -> EmbeddingJobResponse:
    job = service.get_owned(embedding_job_id, organization_id=user.organization_id)
    cancelled = service.cancel(job, organization_id=user.organization_id, user_id=user.id)
    return EmbeddingJobResponse.from_model(cancelled)
