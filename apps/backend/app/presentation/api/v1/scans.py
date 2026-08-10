import uuid

from fastapi import APIRouter, Depends

from app.application.scan_service import ScanService
from app.presentation.api.v1.schemas import ScanJobResponse, StartScanRequest
from app.presentation.dependencies.auth import get_current_user, require_role
from app.presentation.dependencies.rate_limit import rate_limiter
from app.presentation.dependencies.services import get_scan_service
from vault_shared.db.models import RoleName, ScanType, User

scans_router = APIRouter(tags=["scans"])

_require_owner_or_admin = require_role(RoleName.OWNER, RoleName.ADMIN)
# Phase 10 (ADR-022) — a scan enqueues a potentially large worker job; this
# bounds how many an org can kick off back-to-back, independent of the
# worker's own job-level retry/cancellation controls.
_start_scan_rate_limit = rate_limiter("scan-start", limit=10, window_seconds=60)


@scans_router.post(
    "/connectors/{connector_id}/scans",
    response_model=ScanJobResponse,
    status_code=201,
    dependencies=[Depends(_start_scan_rate_limit)],
)
def start_scan(
    connector_id: uuid.UUID,
    body: StartScanRequest | None = None,
    user: User = Depends(_require_owner_or_admin),
    service: ScanService = Depends(get_scan_service),
) -> ScanJobResponse:
    scan_type = ScanType(body.scan_type) if body else ScanType.FULL
    job = service.start_scan(
        connector_id,
        organization_id=user.organization_id,
        user_id=user.id,
        scan_type=scan_type,
    )
    return ScanJobResponse.from_model(job)


@scans_router.get("/connectors/{connector_id}/scans", response_model=list[ScanJobResponse])
def list_scans(
    connector_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ScanService = Depends(get_scan_service),
) -> list[ScanJobResponse]:
    jobs = service.list_for_connector(connector_id, organization_id=user.organization_id)
    return [ScanJobResponse.from_model(job) for job in jobs]


@scans_router.get("/scans/{scan_job_id}", response_model=ScanJobResponse)
def get_scan(
    scan_job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ScanService = Depends(get_scan_service),
) -> ScanJobResponse:
    job = service.get_owned(scan_job_id, organization_id=user.organization_id)
    progress = service.get_progress(job.id)
    return ScanJobResponse.from_model(job, progress=progress)


@scans_router.post("/scans/{scan_job_id}/cancel", response_model=ScanJobResponse)
def cancel_scan(
    scan_job_id: uuid.UUID,
    user: User = Depends(_require_owner_or_admin),
    service: ScanService = Depends(get_scan_service),
) -> ScanJobResponse:
    job = service.get_owned(scan_job_id, organization_id=user.organization_id)
    cancelled = service.cancel(job, organization_id=user.organization_id, user_id=user.id)
    return ScanJobResponse.from_model(cancelled)
