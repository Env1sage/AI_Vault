import uuid

from fastapi import APIRouter, Depends, Request

from app.application.connector_service import ConnectorService
from app.presentation.api.v1.request_utils import client_ip
from app.presentation.api.v1.schemas import (
    CompleteConnectRequest,
    ConnectorResponse,
    InitiateConnectResponse,
)
from app.presentation.dependencies.auth import get_current_user, require_role
from app.presentation.dependencies.rate_limit import rate_limiter
from app.presentation.dependencies.services import get_connector_service
from vault_shared.db.models import RoleName, User

connectors_router = APIRouter(prefix="/connectors", tags=["connectors"])

_require_owner_or_admin = require_role(RoleName.OWNER, RoleName.ADMIN)
# Phase 10 (ADR-022) — both ends of the OAuth handshake: initiating one
# repeatedly is a state-table-exhaustion risk, and the callback is the one
# unauthenticated-adjacent step (Google-issued code/state, but still a
# network-reachable POST) in the whole connector platform.
_connect_rate_limit = rate_limiter("connector-connect", limit=10, window_seconds=60)
_callback_rate_limit = rate_limiter("connector-callback", limit=10, window_seconds=60)


@connectors_router.get("", response_model=list[ConnectorResponse])
def list_connectors(
    user: User = Depends(get_current_user),
    service: ConnectorService = Depends(get_connector_service),
) -> list[ConnectorResponse]:
    connectors = service.list_for_organization(user.organization_id)
    return [ConnectorResponse.from_model(connector) for connector in connectors]


@connectors_router.post(
    "/google/connect",
    response_model=InitiateConnectResponse,
    dependencies=[Depends(_connect_rate_limit)],
)
def connect_google(
    user: User = Depends(_require_owner_or_admin),
    service: ConnectorService = Depends(get_connector_service),
) -> InitiateConnectResponse:
    authorize_url = service.initiate_connect(organization_id=user.organization_id, user_id=user.id)
    return InitiateConnectResponse(authorize_url=authorize_url)


@connectors_router.post(
    "/google/callback",
    response_model=ConnectorResponse,
    dependencies=[Depends(_callback_rate_limit)],
)
def google_callback(
    body: CompleteConnectRequest,
    request: Request,
    user: User = Depends(_require_owner_or_admin),
    service: ConnectorService = Depends(get_connector_service),
) -> ConnectorResponse:
    connector = service.complete_connect(
        code=body.code,
        state=body.state,
        organization_id=user.organization_id,
        user_id=user.id,
        ip_address=client_ip(request),
    )
    return ConnectorResponse.from_model(connector)


@connectors_router.get("/{connector_id}/status", response_model=ConnectorResponse)
def get_connector_status(
    connector_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ConnectorService = Depends(get_connector_service),
) -> ConnectorResponse:
    connector = service.get_owned(connector_id, organization_id=user.organization_id)
    return ConnectorResponse.from_model(connector)


@connectors_router.post("/{connector_id}/verify", response_model=ConnectorResponse)
def verify_connector(
    connector_id: uuid.UUID,
    request: Request,
    user: User = Depends(get_current_user),
    service: ConnectorService = Depends(get_connector_service),
) -> ConnectorResponse:
    connector = service.get_owned(connector_id, organization_id=user.organization_id)
    verified = service.verify(connector, ip_address=client_ip(request))
    return ConnectorResponse.from_model(verified)


@connectors_router.post("/{connector_id}/disconnect", response_model=ConnectorResponse)
def disconnect_connector(
    connector_id: uuid.UUID,
    request: Request,
    user: User = Depends(_require_owner_or_admin),
    service: ConnectorService = Depends(get_connector_service),
) -> ConnectorResponse:
    connector = service.get_owned(connector_id, organization_id=user.organization_id)
    disconnected = service.disconnect(connector, ip_address=client_ip(request))
    return ConnectorResponse.from_model(disconnected)
