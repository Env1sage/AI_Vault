"""file intelligence tables — file_intelligence, intelligence_jobs,
intelligence_events, intelligence_progress (Phase 2 — AI File Intelligence)

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-25
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "file_intelligence",
        sa.Column("file_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("document_type", sa.String(length=100), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("entities", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("structured_metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("topics", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("error", sa.String(length=2048), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "intelligence_jobs",
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
    op.create_index("ix_intelligence_jobs_connector_id", "intelligence_jobs", ["connector_id"])

    op.create_table(
        "intelligence_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("intelligence_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("message", sa.String(length=1024), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["intelligence_job_id"], ["intelligence_jobs.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_intelligence_events_intelligence_job_id",
        "intelligence_events",
        ["intelligence_job_id"],
    )
    op.create_index("ix_intelligence_events_created_at", "intelligence_events", ["created_at"])

    op.create_table(
        "intelligence_progress",
        sa.Column("intelligence_job_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("files_pending", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_file_name", sa.String(length=1024), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["intelligence_job_id"], ["intelligence_jobs.id"], ondelete="CASCADE"
        ),
    )


def downgrade() -> None:
    op.drop_table("intelligence_progress")

    op.drop_index("ix_intelligence_events_created_at", table_name="intelligence_events")
    op.drop_index(
        "ix_intelligence_events_intelligence_job_id", table_name="intelligence_events"
    )
    op.drop_table("intelligence_events")

    op.drop_index("ix_intelligence_jobs_connector_id", table_name="intelligence_jobs")
    op.drop_table("intelligence_jobs")

    op.drop_table("file_intelligence")
