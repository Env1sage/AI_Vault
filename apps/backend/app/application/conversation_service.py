import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.application.context_builder_service import CitationCandidate, ContextBuilderService
from app.application.search_service import SearchService
from vault_shared import NotFoundError
from vault_shared.ai_gateway import AIGateway, Message
from vault_shared.db.models import (
    Citation,
    Conversation,
    ConversationMessage,
    MessageRole,
)
from vault_shared.db.repositories import (
    CitationRepository,
    ConversationMessageRepository,
    ConversationRepository,
)

_TITLE_MAX_LENGTH = 80
_MAX_TOKENS = 1024
# A chat answer's citation panel needs a short, high-confidence source list,
# not the up-to-20-result set the standalone /search page shows — this caps
# how many files ground a single conversational turn.
_MAX_GROUNDING_RESULTS = 6


@dataclass(frozen=True)
class AssistantTurn:
    conversation: Conversation
    user_message: ConversationMessage
    assistant_message: ConversationMessage
    citations: list[Citation]


@dataclass(frozen=True)
class ConversationDetail:
    conversation: Conversation
    messages: list[ConversationMessage]
    citations_by_message_id: dict[uuid.UUID, list[Citation]]


class ConversationService:
    """Phase 6's Conversation Framework — orchestrates retrieval →
    context assembly → `AIGateway.complete()` → citation persistence for
    a single turn. Deliberately single-turn *reasoning* per the phase
    spec ("single-turn query/response as the baseline capability"): each
    call retrieves and ranks context fresh from the current question, but
    the full message history is still passed to the completion provider so
    a follow-up question reads as part of the same conversation
    (spec: "context-aware follow-up questions"), never another
    organization's or user's history (Conversations are user-scoped, not
    just org-scoped — see `ConversationRepository.get_owned`)."""

    def __init__(self, db: Session, *, ai_gateway: AIGateway) -> None:
        self._db = db
        self._ai_gateway = ai_gateway
        self._conversations = ConversationRepository(db)
        self._messages = ConversationMessageRepository(db)
        self._citations = CitationRepository(db)
        self._search = SearchService(db, ai_gateway=ai_gateway)
        self._context_builder = ContextBuilderService(db)

    def list_for_user(
        self, *, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[Conversation]:
        return self._conversations.list_for_user(organization_id=organization_id, user_id=user_id)

    def get_owned(
        self, conversation_id: uuid.UUID, *, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> Conversation:
        conversation = self._conversations.get_owned(
            conversation_id, organization_id=organization_id, user_id=user_id
        )
        if conversation is None:
            raise NotFoundError("Conversation not found.")
        return conversation

    def get_detail(
        self, conversation_id: uuid.UUID, *, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> ConversationDetail:
        conversation = self.get_owned(
            conversation_id, organization_id=organization_id, user_id=user_id
        )
        messages = self._messages.list_for_conversation(conversation.id)
        citations = self._citations.list_for_messages([message.id for message in messages])
        citations_by_message_id: dict[uuid.UUID, list[Citation]] = {
            message.id: [] for message in messages
        }
        for citation in citations:
            citations_by_message_id[citation.message_id].append(citation)
        return ConversationDetail(
            conversation=conversation,
            messages=messages,
            citations_by_message_id=citations_by_message_id,
        )

    def ask(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID | None,
        question: str,
    ) -> AssistantTurn:
        if conversation_id is None:
            conversation = self._conversations.create(
                organization_id=organization_id,
                user_id=user_id,
                title=question[:_TITLE_MAX_LENGTH],
            )
        else:
            conversation = self.get_owned(
                conversation_id, organization_id=organization_id, user_id=user_id
            )

        history = self._messages.list_for_conversation(conversation.id)
        user_message = self._messages.create(
            conversation_id=conversation.id, role=MessageRole.USER, content=question
        )

        results = self._search.search(
            question,
            organization_id=organization_id,
            user_id=user_id,
            limit=_MAX_GROUNDING_RESULTS,
        )
        context_bundle = self._context_builder.build(results)

        completion_messages = [
            Message(role=message.role, content=message.content) for message in history
        ] + [Message(role=MessageRole.USER, content=question)]
        completion = self._ai_gateway.complete(
            messages=completion_messages,
            context=context_bundle.context_text or None,
            max_tokens=_MAX_TOKENS,
        )

        retrieval_method = _combined_retrieval_method(context_bundle.citations)
        assistant_message = self._messages.create(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=completion.text,
            retrieval_method=retrieval_method,
            provider=completion.provider,
            token_usage=completion.tokens_used,
        )

        citations = [
            self._citations.create(
                message_id=assistant_message.id,
                file_id=candidate.file.id,
                snippet=candidate.snippet,
                confidence=candidate.confidence,
                retrieval_method=candidate.retrieval_method,
            )
            for candidate in context_bundle.citations
        ]

        self._conversations.touch(conversation)
        self._db.commit()

        return AssistantTurn(
            conversation=conversation,
            user_message=user_message,
            assistant_message=assistant_message,
            citations=citations,
        )


def _combined_retrieval_method(citations: list[CitationCandidate]) -> str | None:
    methods = {citation.retrieval_method for citation in citations}
    if not methods:
        return None
    if len(methods) == 1:
        return methods.pop()
    return "both"
