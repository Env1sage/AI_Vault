"""storage intelligence tables — storage_analysis_jobs, storage_analysis_events,
duplicate_groups, duplicate_group_members, storage_analysis_snapshots

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-20
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "storage_analysis_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("triggered_by", sa.String(length=20), nullable=False),
        sa.Column("triggered_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("error", sa.String(length=2048), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["triggered_by_user_id"], ["users.id"]),
    )
    op.create_index(
        "ix_storage_analysis_jobs_organization_id", "storage_analysis_jobs", ["organization_id"]
    )

    op.create_table(
        "storage_analysis_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("storage_analysis_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("message", sa.String(length=1024), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["storage_analysis_job_id"], ["storage_analysis_jobs.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_storage_analysis_events_storage_analysis_job_id",
        "storage_analysis_events",
        ["storage_analysis_job_id"],
    )
    op.create_index(
        "ix_storage_analysis_events_created_at", "storage_analysis_events", ["created_at"]
    )

    op.create_table(
        "duplicate_groups",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_analysis_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("checksum", sa.String(length=255), nullable=False),
        sa.Column("file_count", sa.Integer(), nullable=False),
        sa.Column("total_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("recoverable_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("recommended_keep_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recommended_keep_reason", sa.String(length=500), nullable=True),
        sa.Column("recommended_keep_confidence", sa.Float(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["storage_analysis_job_id"], ["storage_analysis_jobs.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["recommended_keep_file_id"], ["files.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("organization_id", "checksum", name="uq_duplicate_group_org_checksum"),
    )
    op.create_index(
        "ix_duplicate_groups_organization_id", "duplicate_groups", ["organization_id"]
    )
    op.create_index("ix_duplicate_groups_checksum", "duplicate_groups", ["checksum"])

    op.create_table(
        "duplicate_group_members",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("duplicate_group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_recommended_keep", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["duplicate_group_id"], ["duplicate_groups.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "duplicate_group_id", "file_id", name="uq_duplicate_group_member"
        ),
    )
    op.create_index(
        "ix_duplicate_group_members_duplicate_group_id",
        "duplicate_group_members",
        ["duplicate_group_id"],
    )
    op.create_index(
        "ix_duplicate_group_members_file_id", "duplicate_group_members", ["file_id"]
    )

    op.create_table(
        "storage_analysis_snapshots",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_analysis_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("total_size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_folders", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "breakdown_by_type_bytes", postgresql.JSONB(), nullable=False, server_default="{}"
        ),
        sa.Column(
            "breakdown_by_size_bucket_bytes",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "breakdown_by_source_bytes", postgresql.JSONB(), nullable=False, server_default="{}"
        ),
        sa.Column("duplicate_group_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_file_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "duplicate_recoverable_bytes", sa.BigInteger(), nullable=False, server_default="0"
        ),
        sa.Column("large_file_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("large_file_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("old_file_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("old_file_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("inactive_file_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("inactive_file_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "temporary_candidate_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "temporary_candidate_bytes", sa.BigInteger(), nullable=False, server_default="0"
        ),
        sa.Column(
            "total_potential_savings_bytes", sa.BigInteger(), nullable=False, server_default="0"
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["storage_analysis_job_id"], ["storage_analysis_jobs.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_storage_analysis_snapshots_organization_id",
        "storage_analysis_snapshots",
        ["organization_id"],
    )
    op.create_index(
        "ix_storage_analysis_snapshots_created_at", "storage_analysis_snapshots", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_storage_analysis_snapshots_created_at", table_name="storage_analysis_snapshots"
    )
    op.drop_index(
        "ix_storage_analysis_snapshots_organization_id", table_name="storage_analysis_snapshots"
    )
    op.drop_table("storage_analysis_snapshots")

    op.drop_index(
        "ix_duplicate_group_members_file_id", table_name="duplicate_group_members"
    )
    op.drop_index(
        "ix_duplicate_group_members_duplicate_group_id", table_name="duplicate_group_members"
    )
    op.drop_table("duplicate_group_members")

    op.drop_index("ix_duplicate_groups_checksum", table_name="duplicate_groups")
    op.drop_index("ix_duplicate_groups_organization_id", table_name="duplicate_groups")
    op.drop_table("duplicate_groups")

    op.drop_index(
        "ix_storage_analysis_events_created_at", table_name="storage_analysis_events"
    )
    op.drop_index(
        "ix_storage_analysis_events_storage_analysis_job_id",
        table_name="storage_analysis_events",
    )
    op.drop_table("storage_analysis_events")

    op.drop_index("ix_storage_analysis_jobs_organization_id", table_name="storage_analysis_jobs")
    op.drop_table("storage_analysis_jobs")
