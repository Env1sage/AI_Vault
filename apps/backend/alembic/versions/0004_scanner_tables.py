"""scanner tables — storage_sources, folders, files, scan_jobs, scan_events, scan_progress

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-28
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "storage_sources",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("connector_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_drive_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("drive_type", sa.String(length=20), nullable=False),
        sa.Column("change_token", sa.String(length=2048), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["connector_id"], ["storage_connectors.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "connector_id", "provider_drive_id", name="uq_storage_source_connector_drive"
        ),
    )
    op.create_index("ix_storage_sources_connector_id", "storage_sources", ["connector_id"])

    op.create_table(
        "folders",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("storage_source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_folder_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider_file_id", sa.String(length=255), nullable=False),
        sa.Column("provider_parent_id", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=1024), nullable=False),
        sa.Column("path", sa.String(length=4096), nullable=False),
        sa.Column("owner_email", sa.String(length=320), nullable=True),
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("provider_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["storage_source_id"], ["storage_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_folder_id"], ["folders.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "storage_source_id", "provider_file_id", name="uq_folder_source_provider_id"
        ),
    )
    op.create_index("ix_folders_storage_source_id", "folders", ["storage_source_id"])
    op.create_index("ix_folders_parent_folder_id", "folders", ["parent_folder_id"])

    op.create_table(
        "files",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("storage_source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_folder_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider_file_id", sa.String(length=255), nullable=False),
        sa.Column("provider_parent_id", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=1024), nullable=False),
        sa.Column("path", sa.String(length=4096), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("owner_email", sa.String(length=320), nullable=True),
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("permissions_summary", sa.String(length=2048), nullable=True),
        sa.Column("version_id", sa.String(length=255), nullable=True),
        sa.Column("checksum", sa.String(length=255), nullable=True),
        sa.Column("provider_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["storage_source_id"], ["storage_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_folder_id"], ["folders.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "storage_source_id", "provider_file_id", name="uq_file_source_provider_id"
        ),
    )
    op.create_index("ix_files_storage_source_id", "files", ["storage_source_id"])
    op.create_index("ix_files_parent_folder_id", "files", ["parent_folder_id"])

    op.create_table(
        "scan_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("connector_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("triggered_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scan_type", sa.String(length=20), nullable=False, server_default="full"),
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
        sa.ForeignKeyConstraint(["triggered_by_user_id"], ["users.id"]),
    )
    op.create_index("ix_scan_jobs_connector_id", "scan_jobs", ["connector_id"])

    op.create_table(
        "scan_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("scan_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("message", sa.String(length=1024), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["scan_job_id"], ["scan_jobs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_scan_events_scan_job_id", "scan_events", ["scan_job_id"])
    op.create_index("ix_scan_events_created_at", "scan_events", ["created_at"])

    op.create_table(
        "scan_progress",
        sa.Column("scan_job_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sources_discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sources_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("folders_discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_source_name", sa.String(length=255), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["scan_job_id"], ["scan_jobs.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("scan_progress")

    op.drop_index("ix_scan_events_created_at", table_name="scan_events")
    op.drop_index("ix_scan_events_scan_job_id", table_name="scan_events")
    op.drop_table("scan_events")

    op.drop_index("ix_scan_jobs_connector_id", table_name="scan_jobs")
    op.drop_table("scan_jobs")

    op.drop_index("ix_files_parent_folder_id", table_name="files")
    op.drop_index("ix_files_storage_source_id", table_name="files")
    op.drop_table("files")

    op.drop_index("ix_folders_parent_folder_id", table_name="folders")
    op.drop_index("ix_folders_storage_source_id", table_name="folders")
    op.drop_table("folders")

    op.drop_index("ix_storage_sources_connector_id", table_name="storage_sources")
    op.drop_table("storage_sources")
