import uuid

from fastapi import APIRouter, Depends

from app.application.conversation_service import ConversationService
from app.presentation.api.v1.schemas import (
    AskRequest,
    AskResponse,
    ConversationDetailResponse,
    ConversationResponse,
)
from app.presentation.dependencies.auth import get_current_user
from app.presentation.dependencies.rate_limit import rate_limiter
from app.presentation.dependencies.services import get_conversation_service
from vault_shared.db.models import User

conversations_router = APIRouter(tags=["conversations"])

# Phase 10 (ADR-022) — every `ask()` call assembles RAG context and invokes
# the AI Gateway's completion provider; rate-limited the same as search.
_ask_rate_limit = rate_limiter("conversation-ask", limit=30, window_seconds=60)


@conversations_router.get("/conversations", response_model=list[ConversationResponse])
def list_conversations(
    user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> list[ConversationResponse]:
    conversations = service.list_for_user(organization_id=user.organization_id, user_id=user.id)
    return [ConversationResponse.from_model(c) for c in conversations]


@conversations_router.get(
    "/conversations/{conversation_id}", response_model=ConversationDetailResponse
)
def get_conversation(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationDetailResponse:
    detail = service.get_detail(
        conversation_id, organization_id=user.organization_id, user_id=user.id
    )
    return ConversationDetailResponse.from_detail(detail)


@conversations_router.post(
    "/conversations",
    response_model=AskResponse,
    status_code=201,
    dependencies=[Depends(_ask_rate_limit)],
)
def start_conversation(
    request: AskRequest,
    user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> AskResponse:
    turn = service.ask(
        organization_id=user.organization_id,
        user_id=user.id,
        conversation_id=None,
        question=request.question,
    )
    return AskResponse.from_turn(turn)


@conversations_router.post(
    "/conversations/{conversation_id}/messages",
    response_model=AskResponse,
    status_code=201,
    dependencies=[Depends(_ask_rate_limit)],
)
def send_message(
    conversation_id: uuid.UUID,
    request: AskRequest,
    user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> AskResponse:
    turn = service.ask(
        organization_id=user.organization_id,
        user_id=user.id,
        conversation_id=conversation_id,
        question=request.question,
    )
    return AskResponse.from_turn(turn)
