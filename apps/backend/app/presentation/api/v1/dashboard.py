from fastapi import APIRouter, Depends, Response

from app.application.dashboard_service import DashboardService
from app.infrastructure.cache.response_cache import get_cached_json, set_cached_json
from app.presentation.api.v1.schemas import DashboardResponse
from app.presentation.dependencies.auth import get_current_user
from app.presentation.dependencies.services import get_dashboard_service
from vault_shared import get_settings
from vault_shared.db.models import User

dashboard_router = APIRouter(tags=["dashboard"])


@dashboard_router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service),
) -> Response:
    # Phase 10 (ADR-022) — cached per-organization, not globally: every
    # org's dashboard is a different query result, and caching them
    # together would leak one org's data into another's response.
    cache_key = f"dashboard:{user.organization_id}"
    cached = get_cached_json(cache_key)
    if cached is not None:
        return Response(content=cached, media_type="application/json")

    overview = service.get_overview(user.organization_id)
    body = DashboardResponse.from_overview(overview).model_dump_json()
    set_cached_json(cache_key, body, ttl_seconds=get_settings().dashboard_cache_ttl_seconds)
    return Response(content=body, media_type="application/json")
