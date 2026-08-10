import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from vault_shared.metrics import record_http_request


class MetricsMiddleware(BaseHTTPMiddleware):
    """Records one HTTP request duration/count observation per response
    (Phase 10, ADR-022). Uses the matched route's *template* path
    (`request.scope["route"].path`, e.g. `/v1/files/{file_id}`), not the
    resolved URL — labeling a Prometheus metric with a real UUID would be
    an unbounded-cardinality mistake."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        started_at = time.perf_counter()
        response = await call_next(request)
        duration_seconds = time.perf_counter() - started_at

        route = request.scope.get("route")
        path = route.path if route is not None else request.url.path

        record_http_request(
            method=request.method,
            path=path,
            status_code=response.status_code,
            duration_seconds=duration_seconds,
        )
        return response
