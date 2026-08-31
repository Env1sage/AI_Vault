"""execution_plans: relax the origin check constraint to allow an ad-hoc
plan (neither recommendation nor duplicate group) — used by Storage
Intelligence's large/old/inactive/temporary-candidate listings, where a
plan targets a set of files the user picked directly rather than a
precomputed group

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-25
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_execution_plans_exactly_one_origin", "execution_plans", type_="check"
    )
    op.create_check_constraint(
        "ck_execution_plans_at_most_one_origin",
        "execution_plans",
        "NOT (recommendation_id IS NOT NULL AND duplicate_group_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_execution_plans_at_most_one_origin", "execution_plans", type_="check"
    )
    op.create_check_constraint(
        "ck_execution_plans_exactly_one_origin",
        "execution_plans",
        "(recommendation_id IS NOT NULL) != (duplicate_group_id IS NOT NULL)",
    )
