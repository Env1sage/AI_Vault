"""knowledge engine tables — file_metadata, file_classifications, file_extractions,
knowledge_attributes, file_relationships, enrichment_jobs, enrichment_progress,
enrichment_events

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-29
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "file_metadata",
        sa.Column("file_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("normalized_extension", sa.String(length=50), nullable=True),
        sa.Column("mime_type_validated", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("mime_mismatch_reason", sa.String(length=255), nullable=True),
        sa.Column("naming_pattern", sa.String(length=100), nullable=True),
        sa.Column("version_label", sa.String(length=50), nullable=True),
        sa.Column("owner_summary", sa.String(length=255), nullable=True),
        sa.Column("sharing_summary", sa.String(length=100), nullable=True),
        sa.Column("duplicate_group_key", sa.String(length=64), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=True),
        sa.Column("enriched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_file_metadata_duplicate_group_key", "file_metadata", ["duplicate_group_key"]
    )

    op.create_table(
        "file_classifications",
        sa.Column("file_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_type", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("method", sa.String(length=100), nullable=False),
        sa.Column("classified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "file_extractions",
        sa.Column("file_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("extractor_name", sa.String(length=50), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("char_count", sa.Integer(), nullable=True),
        sa.Column("error", sa.String(length=1024), nullable=True),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "knowledge_attributes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attribute_type", sa.String(length=50), nullable=False),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "file_id", "attribute_type", "value", name="uq_knowledge_attribute_file_type_value"
        ),
    )
    op.create_index("ix_knowledge_attributes_file_id", "knowledge_attributes", ["file_id"])

    op.create_table(
        "file_relationships",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("connector_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("related_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_type", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["connector_id"], ["storage_connectors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["related_file_id"], ["files.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "file_id", "related_file_id", "relationship_type", name="uq_file_relationship"
        ),
    )
    op.create_index("ix_file_relationships_connector_id", "file_relationships", ["connector_id"])
    op.create_index("ix_file_relationships_file_id", "file_relationships", ["file_id"])
    op.create_index(
        "ix_file_relationships_related_file_id", "file_relationships", ["related_file_id"]
    )

    op.create_table(
        "enrichment_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("connector_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scan_job_id", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.ForeignKeyConstraint(["scan_job_id"], ["scan_jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["triggered_by_user_id"], ["users.id"]),
    )
    op.create_index("ix_enrichment_jobs_connector_id", "enrichment_jobs", ["connector_id"])

    op.create_table(
        "enrichment_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("enrichment_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("message", sa.String(length=1024), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["enrichment_job_id"], ["enrichment_jobs.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_enrichment_events_enrichment_job_id", "enrichment_events", ["enrichment_job_id"]
    )
    op.create_index("ix_enrichment_events_created_at", "enrichment_events", ["created_at"])

    op.create_table(
        "enrichment_progress",
        sa.Column("enrichment_job_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("files_pending", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_file_name", sa.String(length=1024), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["enrichment_job_id"], ["enrichment_jobs.id"], ondelete="CASCADE"
        ),
    )


def downgrade() -> None:
    op.drop_table("enrichment_progress")

    op.drop_index("ix_enrichment_events_created_at", table_name="enrichment_events")
    op.drop_index(
        "ix_enrichment_events_enrichment_job_id", table_name="enrichment_events"
    )
    op.drop_table("enrichment_events")

    op.drop_index("ix_enrichment_jobs_connector_id", table_name="enrichment_jobs")
    op.drop_table("enrichment_jobs")

    op.drop_index("ix_file_relationships_related_file_id", table_name="file_relationships")
    op.drop_index("ix_file_relationships_file_id", table_name="file_relationships")
    op.drop_index("ix_file_relationships_connector_id", table_name="file_relationships")
    op.drop_table("file_relationships")

    op.drop_index("ix_knowledge_attributes_file_id", table_name="knowledge_attributes")
    op.drop_table("knowledge_attributes")

    op.drop_table("file_extractions")

    op.drop_table("file_classifications")

    op.drop_index("ix_file_metadata_duplicate_group_key", table_name="file_metadata")
    op.drop_table("file_metadata")
