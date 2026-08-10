from fastapi import APIRouter, Response

from vault_shared.metrics import METRICS_CONTENT_TYPE, generate_latest_metrics

metrics_router = APIRouter(tags=["metrics"])


@metrics_router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    """Prometheus scrape target (Phase 10, ADR-022). Deliberately not under
    `/v1` — this is an operational endpoint, not a product API, and should
    be reachable only from the monitoring network in production (a
    firewall/ingress rule, not application-layer auth — a scraper has no
    user session to authenticate with)."""
    return Response(content=generate_latest_metrics(), media_type=METRICS_CONTENT_TYPE)
