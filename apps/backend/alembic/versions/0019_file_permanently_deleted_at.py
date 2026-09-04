"""files.permanently_deleted_at — set by ExecutionService after a
successful PERMANENT_DELETE step (Drive's real files.delete, never called
for any other action type). Only reachable from an already-trashed file.

Revision ID: 0019
Revises: 0018
Create Date: 2026-09-04
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "files",
        sa.Column("permanently_deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("files", "permanently_deleted_at")
