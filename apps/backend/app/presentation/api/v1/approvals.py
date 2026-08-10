import uuid

from fastapi import APIRouter, Depends, Query, Request

from app.application.approval_service import ApprovalService
from app.presentation.api.v1.request_utils import client_ip
from app.presentation.api.v1.schemas import (
    ApprovalDecisionRequest,
    ApprovalRequestResponse,
    BulkApprovalDecisionRequest,
)
from app.presentation.dependencies.auth import get_current_user, require_role
from app.presentation.dependencies.rate_limit import rate_limiter
from app.presentation.dependencies.services import get_approval_service
from vault_shared.db.models import RoleName, User

approvals_router = APIRouter(tags=["approvals"])

_require_owner_or_admin = require_role(RoleName.OWNER, RoleName.ADMIN)
# Phase 10 (ADR-022) — approval decisions are the last gate before a real
# Drive mutation; a per-IP limit here is defense-in-depth against a
# compromised or scripted owner/admin session, not the primary control
# (JWT auth + role check already gate this endpoint).
_decide_rate_limit = rate_limiter("approval-decide", limit=60, window_seconds=60)
_bulk_decide_rate_limit = rate_limiter("approval-bulk-decide", limit=20, window_seconds=60)


@approvals_router.get("/approvals", response_model=list[ApprovalRequestResponse])
def list_approvals(
    status: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    service: ApprovalService = Depends(get_approval_service),
) -> list[ApprovalRequestResponse]:
    requests = service.list_for_organization(user.organization_id, status=status)
    return [ApprovalRequestResponse.from_model(request) for request in requests]


@approvals_router.get("/approvals/{approval_request_id}", response_model=ApprovalRequestResponse)
def get_approval(
    approval_request_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ApprovalService = Depends(get_approval_service),
) -> ApprovalRequestResponse:
    request = service.get_owned(approval_request_id, organization_id=user.organization_id)
    return ApprovalRequestResponse.from_model(request)


@approvals_router.post(
    "/approvals/{approval_request_id}/decide",
    response_model=ApprovalRequestResponse,
    dependencies=[Depends(_decide_rate_limit)],
)
def decide_approval(
    approval_request_id: uuid.UUID,
    body: ApprovalDecisionRequest,
    http_request: Request,
    user: User = Depends(_require_owner_or_admin),
    service: ApprovalService = Depends(get_approval_service),
) -> ApprovalRequestResponse:
    request = service.decide(
        approval_request_id,
        organization_id=user.organization_id,
        user_id=user.id,
        decision=body.decision,
        comments=body.comments,
        ip_address=client_ip(http_request),
    )
    return ApprovalRequestResponse.from_model(request)


@approvals_router.post(
    "/approvals/bulk-decide",
    response_model=list[ApprovalRequestResponse],
    dependencies=[Depends(_bulk_decide_rate_limit)],
)
def bulk_decide_approvals(
    body: BulkApprovalDecisionRequest,
    http_request: Request,
    user: User = Depends(_require_owner_or_admin),
    service: ApprovalService = Depends(get_approval_service),
) -> list[ApprovalRequestResponse]:
    requests = service.bulk_decide(
        [uuid.UUID(rid) for rid in body.approval_request_ids],
        organization_id=user.organization_id,
        user_id=user.id,
        decision=body.decision,
        comments=body.comments,
        ip_address=client_ip(http_request),
    )
    return [ApprovalRequestResponse.from_model(request) for request in requests]
