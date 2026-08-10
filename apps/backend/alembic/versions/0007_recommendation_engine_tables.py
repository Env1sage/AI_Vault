"""recommendation engine tables — recommendation_jobs, recommendation_events,
recommendations, insight_records, dashboard_snapshots

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-03
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recommendation_jobs",
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
        sa.Column("recommendations_active", sa.Integer(), nullable=True),
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
        "ix_recommendation_jobs_organization_id", "recommendation_jobs", ["organization_id"]
    )

    op.create_table(
        "recommendation_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("recommendation_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("message", sa.String(length=1024), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["recommendation_job_id"], ["recommendation_jobs.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_recommendation_events_recommendation_job_id",
        "recommendation_events",
        ["recommendation_job_id"],
    )
    op.create_index(
        "ix_recommendation_events_created_at", "recommendation_events", ["created_at"]
    )

    op.create_table(
        "recommendations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recommendation_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("estimated_impact", sa.String(length=500), nullable=False),
        sa.Column("impact_value", sa.Float(), nullable=True),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("suggested_action", sa.Text(), nullable=False),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("related_departments", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("affected_file_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("priority_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["recommendation_job_id"], ["recommendation_jobs.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("organization_id", "rule_name", name="uq_recommendation_org_rule"),
    )
    op.create_index("ix_recommendations_organization_id", "recommendations", ["organization_id"])
    op.create_index(
        "ix_recommendations_recommendation_job_id", "recommendations", ["recommendation_job_id"]
    )
    op.create_index("ix_recommendations_category", "recommendations", ["category"])
    op.create_index("ix_recommendations_status", "recommendations", ["status"])

    op.create_table(
        "insight_records",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recommendation_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("insight_type", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("related_file_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["recommendation_job_id"], ["recommendation_jobs.id"], ondelete="SET NULL"
        ),
    )
    op.create_index("ix_insight_records_organization_id", "insight_records", ["organization_id"])
    op.create_index("ix_insight_records_created_at", "insight_records", ["created_at"])

    op.create_table(
        "dashboard_snapshots",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recommendation_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("connected_providers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_folders", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_storage_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("classified_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unclassified_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pending_enrichment_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("embedded_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("relationship_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_recommendations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "knowledge_completeness_score", sa.Float(), nullable=False, server_default="0"
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["recommendation_job_id"], ["recommendation_jobs.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_dashboard_snapshots_organization_id", "dashboard_snapshots", ["organization_id"]
    )
    op.create_index("ix_dashboard_snapshots_created_at", "dashboard_snapshots", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_dashboard_snapshots_created_at", table_name="dashboard_snapshots")
    op.drop_index("ix_dashboard_snapshots_organization_id", table_name="dashboard_snapshots")
    op.drop_table("dashboard_snapshots")

    op.drop_index("ix_insight_records_created_at", table_name="insight_records")
    op.drop_index("ix_insight_records_organization_id", table_name="insight_records")
    op.drop_table("insight_records")

    op.drop_index("ix_recommendations_status", table_name="recommendations")
    op.drop_index("ix_recommendations_category", table_name="recommendations")
    op.drop_index("ix_recommendations_recommendation_job_id", table_name="recommendations")
    op.drop_index("ix_recommendations_organization_id", table_name="recommendations")
    op.drop_table("recommendations")

    op.drop_index("ix_recommendation_events_created_at", table_name="recommendation_events")
    op.drop_index(
        "ix_recommendation_events_recommendation_job_id", table_name="recommendation_events"
    )
    op.drop_table("recommendation_events")

    op.drop_index("ix_recommendation_jobs_organization_id", table_name="recommendation_jobs")
    op.drop_table("recommendation_jobs")
