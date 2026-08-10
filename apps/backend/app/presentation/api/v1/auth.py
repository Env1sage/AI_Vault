from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response, status

from app.application.auth_service import AuthenticatedSession, AuthService
from app.infrastructure.auth.google_identity import (
    GoogleIdentityVerifier,
    get_google_identity_verifier,
)
from app.presentation.api.v1.request_utils import client_ip
from app.presentation.api.v1.schemas import GoogleLoginRequest, SessionResponse, UserProfileResponse
from app.presentation.dependencies.rate_limit import rate_limiter
from app.presentation.dependencies.services import get_auth_service
from vault_shared import UnauthorizedError, get_settings

auth_router = APIRouter(prefix="/auth", tags=["auth"])

_login_rate_limit = rate_limiter("auth-login", limit=20, window_seconds=60)
_refresh_rate_limit = rate_limiter("auth-refresh", limit=60, window_seconds=60)


def _set_refresh_cookie(response: Response, session: AuthenticatedSession) -> None:
    settings = get_settings()
    max_age = max(int((session.refresh_token_expires_at - datetime.now(UTC)).total_seconds()), 0)
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=session.refresh_token,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/v1/auth",
    )


def _session_response(session: AuthenticatedSession) -> SessionResponse:
    settings = get_settings()
    return SessionResponse(
        access_token=session.access_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserProfileResponse.from_model(session.user),
    )


@auth_router.post(
    "/login", response_model=SessionResponse, dependencies=[Depends(_login_rate_limit)]
)
def login(
    body: GoogleLoginRequest,
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
    verifier: GoogleIdentityVerifier = Depends(get_google_identity_verifier),
) -> SessionResponse:
    google_user = verifier.verify(body.id_token)
    session = service.complete_google_login(google_user=google_user, ip_address=client_ip(request))

    _set_refresh_cookie(response, session)
    return _session_response(session)


@auth_router.post(
    "/refresh", response_model=SessionResponse, dependencies=[Depends(_refresh_rate_limit)]
)
def refresh(
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
) -> SessionResponse:
    settings = get_settings()
    raw_token = request.cookies.get(settings.refresh_cookie_name)
    if not raw_token:
        raise UnauthorizedError("No active session.")

    session = service.refresh_session(raw_refresh_token=raw_token, ip_address=client_ip(request))

    _set_refresh_cookie(response, session)
    return _session_response(session)


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request, response: Response, service: AuthService = Depends(get_auth_service)
) -> None:
    settings = get_settings()
    raw_token = request.cookies.get(settings.refresh_cookie_name)

    if raw_token:
        service.logout(raw_refresh_token=raw_token, ip_address=client_ip(request))

    response.delete_cookie(settings.refresh_cookie_name, path="/v1/auth")
