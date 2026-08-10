"""ai intelligence tables — embeddings, embedding_jobs, embedding_progress,
embedding_events, conversations, conversation_messages, citations,
search_sessions

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-31
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "embeddings",
        sa.Column("file_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("vector", postgresql.ARRAY(sa.Float()), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("embedded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "embedding_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("connector_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enrichment_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("triggered_by", sa.String(length=20), nullable=False),
        sa.Column("triggered_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error", sa.String(length=2048), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["connector_id"], ["storage_connectors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["enrichment_job_id"], ["enrichment_jobs.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["triggered_by_user_id"], ["users.id"]),
    )
    op.create_index("ix_embedding_jobs_connector_id", "embedding_jobs", ["connector_id"])

    op.create_table(
        "embedding_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("embedding_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("message", sa.String(length=1024), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["embedding_job_id"], ["embedding_jobs.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_embedding_events_embedding_job_id", "embedding_events", ["embedding_job_id"]
    )
    op.create_index("ix_embedding_events_created_at", "embedding_events", ["created_at"])

    op.create_table(
        "embedding_progress",
        sa.Column("embedding_job_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("files_pending", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_file_name", sa.String(length=1024), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["embedding_job_id"], ["embedding_jobs.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "conversations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_conversations_organization_id", "conversations", ["organization_id"])
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    op.create_table(
        "conversation_messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("retrieval_method", sa.String(length=20), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("token_usage", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_conversation_messages_conversation_id", "conversation_messages", ["conversation_id"]
    )
    op.create_index(
        "ix_conversation_messages_created_at", "conversation_messages", ["created_at"]
    )

    op.create_table(
        "citations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snippet", sa.String(length=1024), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("retrieval_method", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["message_id"], ["conversation_messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_citations_message_id", "citations", ["message_id"])
    op.create_index("ix_citations_file_id", "citations", ["file_id"])

    op.create_table(
        "search_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("query_text", sa.String(length=1024), nullable=False),
        sa.Column("result_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_search_sessions_organization_id", "search_sessions", ["organization_id"])
    op.create_index("ix_search_sessions_user_id", "search_sessions", ["user_id"])
    op.create_index("ix_search_sessions_created_at", "search_sessions", ["created_at"])


def downgrade() -> None:
    op.drop_table("search_sessions")

    op.drop_index("ix_citations_file_id", table_name="citations")
    op.drop_index("ix_citations_message_id", table_name="citations")
    op.drop_table("citations")

    op.drop_index(
        "ix_conversation_messages_created_at", table_name="conversation_messages"
    )
    op.drop_index(
        "ix_conversation_messages_conversation_id", table_name="conversation_messages"
    )
    op.drop_table("conversation_messages")

    op.drop_index("ix_conversations_user_id", table_name="conversations")
    op.drop_index("ix_conversations_organization_id", table_name="conversations")
    op.drop_table("conversations")

    op.drop_table("embedding_progress")

    op.drop_index("ix_embedding_events_created_at", table_name="embedding_events")
    op.drop_index("ix_embedding_events_embedding_job_id", table_name="embedding_events")
    op.drop_table("embedding_events")

    op.drop_index("ix_embedding_jobs_connector_id", table_name="embedding_jobs")
    op.drop_table("embedding_jobs")

    op.drop_table("embeddings")
