"""execution_plans: allow a plan to originate from a Storage Intelligence
DuplicateGroup as well as a Recommendation — recommendation_id becomes
nullable, duplicate_group_id is added

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-24
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("execution_plans", "recommendation_id", nullable=True)
    op.add_column(
        "execution_plans",
        sa.Column("duplicate_group_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_execution_plans_duplicate_group_id",
        "execution_plans",
        "duplicate_groups",
        ["duplicate_group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_execution_plans_duplicate_group_id", "execution_plans", ["duplicate_group_id"]
    )
    op.create_check_constraint(
        "ck_execution_plans_exactly_one_origin",
        "execution_plans",
        "(recommendation_id IS NOT NULL) != (duplicate_group_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_execution_plans_exactly_one_origin", "execution_plans", type_="check"
    )
    op.drop_index("ix_execution_plans_duplicate_group_id", table_name="execution_plans")
    op.drop_constraint(
        "fk_execution_plans_duplicate_group_id", "execution_plans", type_="foreignkey"
    )
    op.drop_column("execution_plans", "duplicate_group_id")
    op.alter_column("execution_plans", "recommendation_id", nullable=False)
