"""files.trashed — set by ExecutionService after a successful trash action
(ARCHIVE/REMOVE_DUPLICATE) and excluded from storage-total aggregation, so
archiving a file actually reduces reported storage instead of the stale
row lingering in every total indefinitely

Revision ID: 0018
Revises: 0017
Create Date: 2026-09-03
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "files",
        sa.Column("trashed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_files_trashed", "files", ["trashed"])


def downgrade() -> None:
    op.drop_index("ix_files_trashed", table_name="files")
    op.drop_column("files", "trashed")
