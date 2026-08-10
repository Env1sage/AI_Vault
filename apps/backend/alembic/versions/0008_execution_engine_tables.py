"""execution engine tables — execution_plans, execution_steps,
approval_requests, approval_decisions, execution_jobs, execution_results,
rollback_records, execution_audits

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-04
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "execution_plans",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recommendation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status", sa.String(length=30), nullable=False, server_default="pending_approval"
        ),
        sa.Column("target_provider", sa.String(length=50), nullable=False),
        sa.Column("estimated_impact", sa.Text(), nullable=False),
        sa.Column("estimated_storage_savings_bytes", sa.BigInteger(), nullable=True),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("rollback_available", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("required_permissions", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recommendation_id"], ["recommendations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
    )
    op.create_index("ix_execution_plans_organization_id", "execution_plans", ["organization_id"])
    op.create_index(
        "ix_execution_plans_recommendation_id", "execution_plans", ["recommendation_id"]
    )
    op.create_index("ix_execution_plans_status", "execution_plans", ["status"])

    op.create_table(
        "execution_steps",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("execution_plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.String(length=30), nullable=False),
        sa.Column("target_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pre_state", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("planned_change", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["execution_plan_id"], ["execution_plans.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["target_file_id"], ["files.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_execution_steps_execution_plan_id", "execution_steps", ["execution_plan_id"]
    )
    op.create_index("ix_execution_steps_target_file_id", "execution_steps", ["target_file_id"])

    op.create_table(
        "approval_requests",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("execution_plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["execution_plan_id"], ["execution_plans.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"]),
        sa.UniqueConstraint("execution_plan_id", name="uq_approval_request_execution_plan"),
    )
    op.create_index(
        "ix_approval_requests_organization_id", "approval_requests", ["organization_id"]
    )
    op.create_index("ix_approval_requests_status", "approval_requests", ["status"])

    op.create_table(
        "approval_decisions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("approval_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decider_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["approval_request_id"], ["approval_requests.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["decider_user_id"], ["users.id"]),
    )
    op.create_index(
        "ix_approval_decisions_approval_request_id", "approval_decisions", ["approval_request_id"]
    )
    op.create_index("ix_approval_decisions_created_at", "approval_decisions", ["created_at"])

    op.create_table(
        "execution_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("execution_plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("triggered_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("is_rollback", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("pause_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error", sa.String(length=2048), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["execution_plan_id"], ["execution_plans.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["triggered_by_user_id"], ["users.id"]),
    )
    op.create_index("ix_execution_jobs_execution_plan_id", "execution_jobs", ["execution_plan_id"])
    op.create_index("ix_execution_jobs_organization_id", "execution_jobs", ["organization_id"])
    op.create_index("ix_execution_jobs_status", "execution_jobs", ["status"])

    op.create_table(
        "execution_results",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("execution_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_step_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("verification_status", sa.String(length=20), nullable=False),
        sa.Column("error", sa.String(length=2048), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["execution_job_id"], ["execution_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["execution_step_id"], ["execution_steps.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_execution_results_execution_job_id", "execution_results", ["execution_job_id"]
    )
    op.create_index(
        "ix_execution_results_execution_step_id", "execution_results", ["execution_step_id"]
    )

    op.create_table(
        "rollback_records",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("execution_step_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pre_state", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("rolled_back", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("rolled_back_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rolled_back_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["execution_step_id"], ["execution_steps.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["rolled_back_by_user_id"], ["users.id"]),
        sa.UniqueConstraint("execution_step_id", name="uq_rollback_record_execution_step"),
    )
    op.create_index(
        "ix_rollback_records_execution_step_id", "rollback_records", ["execution_step_id"]
    )

    op.create_table(
        "execution_audits",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_plan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("execution_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("message", sa.String(length=1024), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["execution_plan_id"], ["execution_plans.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["execution_job_id"], ["execution_jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
    )
    op.create_index("ix_execution_audits_organization_id", "execution_audits", ["organization_id"])
    op.create_index(
        "ix_execution_audits_execution_plan_id", "execution_audits", ["execution_plan_id"]
    )
    op.create_index(
        "ix_execution_audits_execution_job_id", "execution_audits", ["execution_job_id"]
    )
    op.create_index("ix_execution_audits_created_at", "execution_audits", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_execution_audits_created_at", table_name="execution_audits")
    op.drop_index("ix_execution_audits_execution_job_id", table_name="execution_audits")
    op.drop_index("ix_execution_audits_execution_plan_id", table_name="execution_audits")
    op.drop_index("ix_execution_audits_organization_id", table_name="execution_audits")
    op.drop_table("execution_audits")

    op.drop_index("ix_rollback_records_execution_step_id", table_name="rollback_records")
    op.drop_table("rollback_records")

    op.drop_index("ix_execution_results_execution_step_id", table_name="execution_results")
    op.drop_index("ix_execution_results_execution_job_id", table_name="execution_results")
    op.drop_table("execution_results")

    op.drop_index("ix_execution_jobs_status", table_name="execution_jobs")
    op.drop_index("ix_execution_jobs_organization_id", table_name="execution_jobs")
    op.drop_index("ix_execution_jobs_execution_plan_id", table_name="execution_jobs")
    op.drop_table("execution_jobs")

    op.drop_index("ix_approval_decisions_created_at", table_name="approval_decisions")
    op.drop_index(
        "ix_approval_decisions_approval_request_id", table_name="approval_decisions"
    )
    op.drop_table("approval_decisions")

    op.drop_index("ix_approval_requests_status", table_name="approval_requests")
    op.drop_index("ix_approval_requests_organization_id", table_name="approval_requests")
    op.drop_table("approval_requests")

    op.drop_index("ix_execution_steps_target_file_id", table_name="execution_steps")
    op.drop_index("ix_execution_steps_execution_plan_id", table_name="execution_steps")
    op.drop_table("execution_steps")

    op.drop_index("ix_execution_plans_status", table_name="execution_plans")
    op.drop_index("ix_execution_plans_recommendation_id", table_name="execution_plans")
    op.drop_index("ix_execution_plans_organization_id", table_name="execution_plans")
    op.drop_table("execution_plans")
