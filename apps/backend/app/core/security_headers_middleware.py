from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from vault_shared import get_settings

# This API never renders HTML or serves third-party scripts for its own
# JSON endpoints — `default-src 'none'` is safe everywhere except the
# Swagger UI at `/v1/docs`, which FastAPI serves from a CDN
# (`https://cdn.jsdelivr.net`) and needs script/style/image sources beyond
# 'none'. Two policies, chosen per-path, rather than one loose policy for
# every response (Handbook §13 — narrowest control that satisfies the need).
_DOCS_PATHS = frozenset({"/v1/docs", "/v1/redoc"})
_API_CSP = "default-src 'none'; frame-ancestors 'none'"
_DOCS_CSP = (
    "default-src 'none'; "
    "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "img-src 'self' https://fastapi.tiangolo.com data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds the response headers a security review checklist (Phase 10,
    ADR-022) expects on every response — none of these are a substitute
    for the actual controls (auth, CORS, input validation) elsewhere in
    the stack, they're defense-in-depth against a browser being tricked
    into doing something the API's own logic didn't intend."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        response.headers["Content-Security-Policy"] = (
            _DOCS_CSP if request.url.path in _DOCS_PATHS else _API_CSP
        )
        # Only meaningful over HTTPS (Handbook §13's `cookie_secure` flag is
        # the same signal: false for plain-http local dev, true anywhere
        # actually deployed) — sending it over plain HTTP is a harmless
        # no-op, not a lie, since the browser only honors it on HTTPS
        # origins in the first place.
        if get_settings().cookie_secure:
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains"
            )

        return response
