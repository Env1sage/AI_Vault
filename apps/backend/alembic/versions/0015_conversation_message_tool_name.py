"""conversation_messages.tool_name — records which AI Storage Assistant
tool answered a turn, distinct from retrieval_method (String(20), too
narrow for tool names)

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-25
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversation_messages",
        sa.Column("tool_name", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversation_messages", "tool_name")
