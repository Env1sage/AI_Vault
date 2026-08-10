import uuid

from sqlalchemy.orm import Session

from vault_shared.db.models import ConversationMessage


class ConversationMessageRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        retrieval_method: str | None = None,
        provider: str | None = None,
        token_usage: int | None = None,
    ) -> ConversationMessage:
        message = ConversationMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            retrieval_method=retrieval_method,
            provider=provider,
            token_usage=token_usage,
        )
        self._session.add(message)
        self._session.flush()
        return message

    def list_for_conversation(self, conversation_id: uuid.UUID) -> list[ConversationMessage]:
        return (
            self._session.query(ConversationMessage)
            .filter_by(conversation_id=conversation_id)
            .order_by(ConversationMessage.created_at)
            .all()
        )
