from fastapi import APIRouter, Depends

from app.application.search_service import SearchService
from app.presentation.api.v1.schemas import SearchRequest, SearchResponse, SearchResultResponse
from app.presentation.dependencies.auth import get_current_user
from app.presentation.dependencies.rate_limit import rate_limiter
from app.presentation.dependencies.services import get_search_service
from vault_shared.db.models import User

search_router = APIRouter(tags=["search"])

# Phase 10 (ADR-022) — every AI-Gateway-backed endpoint gets a rate limit;
# search embeds the query on every call, the same cost profile as an
# embedding job, just synchronous and per-request instead of batched.
_search_rate_limit = rate_limiter("search", limit=60, window_seconds=60)


@search_router.post(
    "/search", response_model=SearchResponse, dependencies=[Depends(_search_rate_limit)]
)
def search(
    request: SearchRequest,
    user: User = Depends(get_current_user),
    service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    results = service.search(
        request.query, organization_id=user.organization_id, user_id=user.id
    )
    return SearchResponse(
        query=request.query,
        results=[SearchResultResponse.from_result(r) for r in results],
    )
