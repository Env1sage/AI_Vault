"""archive_jobs — Archive MVP's record of one compressed package created
from a CREATE_ARCHIVE execution plan (manifest, object storage key, sizes)

Revision ID: 0017
Revises: 0016
Create Date: 2026-09-03
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "archive_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("object_storage_key", sa.String(length=1024), nullable=True),
        sa.Column("original_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("compressed_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("file_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("manifest", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["execution_plan_id"], ["execution_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.UniqueConstraint("execution_plan_id", name="uq_archive_jobs_execution_plan_id"),
    )
    op.create_index("ix_archive_jobs_organization_id", "archive_jobs", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_archive_jobs_organization_id", table_name="archive_jobs")
    op.drop_table("archive_jobs")
