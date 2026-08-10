"""enable pgcrypto extension

Revision ID: 0001
Revises:
Create Date: 2026-07-28
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Every future phase needs gen_random_uuid() for primary keys (Handbook
    # §9's entities are UUID-keyed from Phase 2 onward) — enabled once here
    # rather than per-migration.
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')


def downgrade() -> None:
    op.execute('DROP EXTENSION IF EXISTS "pgcrypto"')
