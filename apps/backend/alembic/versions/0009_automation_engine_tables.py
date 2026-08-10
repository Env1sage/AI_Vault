"""automation engine tables — workflows, workflow_versions, workflow_nodes,
workflow_triggers, workflow_executions, workflow_node_executions,
scheduler_jobs, workflow_policies, notifications, automation_templates;
extends approval_requests/approval_decisions for workflow-node and
policy-driven approvals (ADR-021)

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workflows",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
    )
    op.create_index("ix_workflows_organization_id", "workflows", ["organization_id"])
    op.create_index("ix_workflows_status", "workflows", ["status"])

    op.create_table(
        "workflow_versions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
    )
    op.create_index("ix_workflow_versions_workflow_id", "workflow_versions", ["workflow_id"])
    op.create_index("ix_workflow_versions_status", "workflow_versions", ["status"])

    op.create_table(
        "workflow_nodes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("workflow_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_type", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("next_nodes", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("position_x", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("position_y", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["workflow_version_id"], ["workflow_versions.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_workflow_nodes_workflow_version_id", "workflow_nodes", ["workflow_version_id"]
    )

    op.create_table(
        "workflow_triggers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trigger_type", sa.String(length=20), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_workflow_triggers_workflow_id", "workflow_triggers", ["workflow_id"])
    op.create_index("ix_workflow_triggers_trigger_type", "workflow_triggers", ["trigger_type"])

    op.create_table(
        "workflow_executions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("trigger_type", sa.String(length=20), nullable=False),
        sa.Column("trigger_context", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("current_node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("context", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("triggered_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["workflow_version_id"], ["workflow_versions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["current_node_id"], ["workflow_nodes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["triggered_by_user_id"], ["users.id"]),
    )
    op.create_index("ix_workflow_executions_workflow_id", "workflow_executions", ["workflow_id"])
    op.create_index(
        "ix_workflow_executions_workflow_version_id", "workflow_executions", ["workflow_version_id"]
    )
    op.create_index(
        "ix_workflow_executions_organization_id", "workflow_executions", ["organization_id"]
    )
    op.create_index("ix_workflow_executions_status", "workflow_executions", ["status"])

    op.create_table(
        "workflow_node_executions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("workflow_execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("output_context", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("error", sa.String(length=2048), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["workflow_execution_id"], ["workflow_executions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["workflow_node_id"], ["workflow_nodes.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_workflow_node_executions_workflow_execution_id",
        "workflow_node_executions",
        ["workflow_execution_id"],
    )
    op.create_index(
        "ix_workflow_node_executions_workflow_node_id",
        "workflow_node_executions",
        ["workflow_node_id"],
    )
    op.create_index("ix_workflow_node_executions_status", "workflow_node_executions", ["status"])
    op.create_index(
        "ix_workflow_node_executions_created_at", "workflow_node_executions", ["created_at"]
    )

    op.create_table(
        "scheduler_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("workflow_trigger_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_workflow_execution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["workflow_trigger_id"], ["workflow_triggers.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["last_workflow_execution_id"], ["workflow_executions.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("workflow_trigger_id", name="uq_scheduler_job_workflow_trigger"),
    )
    op.create_index(
        "ix_scheduler_jobs_workflow_trigger_id", "scheduler_jobs", ["workflow_trigger_id"]
    )
    op.create_index("ix_scheduler_jobs_next_run_at", "scheduler_jobs", ["next_run_at"])

    op.create_table(
        "workflow_policies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_key", sa.String(length=100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("effect", sa.String(length=20), nullable=False),
        sa.Column("conditions", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
    )
    op.create_index(
        "ix_workflow_policies_organization_id", "workflow_policies", ["organization_id"]
    )
    op.create_index("ix_workflow_policies_policy_key", "workflow_policies", ["policy_key"])
    op.create_index("ix_workflow_policies_status", "workflow_policies", ["status"])

    op.create_table(
        "notifications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_execution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("error", sa.String(length=1024), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["workflow_execution_id"], ["workflow_executions.id"], ondelete="SET NULL"
        ),
    )
    op.create_index("ix_notifications_organization_id", "notifications", ["organization_id"])
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index(
        "ix_notifications_workflow_execution_id", "notifications", ["workflow_execution_id"]
    )
    op.create_index("ix_notifications_status", "notifications", ["status"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])

    op.create_table(
        "automation_templates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("node_definitions", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_automation_templates_organization_id", "automation_templates", ["organization_id"]
    )

    # Seed the phase spec's named example templates as global
    # (organization_id IS NULL) rows — same "seed via migration" pattern
    # 0002 already used for the three fixed `roles`. Node graphs use real,
    # implemented node types only; `EXECUTE_ACTION` nodes leave
    # `policy_key` blank since a policy is always organization-specific —
    # applying a template produces a draft the founder finishes
    # configuring (policy, cron schedule) before publishing.
    automation_templates_table = sa.table(
        "automation_templates",
        sa.column("organization_id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("category", sa.String),
        sa.column("node_definitions", postgresql.JSONB),
    )
    op.bulk_insert(
        automation_templates_table,
        [
            {
                "organization_id": None,
                "name": "Archive Inactive Files",
                "description": "Runs on a schedule; archives (Drive Trash) files matching the "
                "archive_candidates recommendation, gated by a policy you configure.",
                "category": "storage_optimization",
                "node_definitions": [
                    {
                        "key": "trigger",
                        "node_type": "trigger",
                        "name": "Start",
                        "config": {},
                        "next_nodes": {"default": "execute"},
                    },
                    {
                        "key": "execute",
                        "node_type": "execute_action",
                        "name": "Archive inactive files",
                        "config": {"rule_name": "archive_candidates", "policy_key": ""},
                        "next_nodes": {"default": "notify"},
                    },
                    {
                        "key": "notify",
                        "node_type": "notification",
                        "name": "Notify owner",
                        "config": {
                            "channel": "in_app",
                            "recipients": ["owner"],
                            "subject": "Archive workflow completed",
                            "body_template": "The archive-inactive-files workflow finished "
                            "running.",
                        },
                        "next_nodes": {"default": "end"},
                    },
                    {
                        "key": "end",
                        "node_type": "end",
                        "name": "Done",
                        "config": {},
                        "next_nodes": {},
                    },
                ],
            },
            {
                "organization_id": None,
                "name": "Weekly Storage Health Report",
                "description": "Runs on a schedule; notifies owners/admins that a fresh "
                "storage health snapshot is ready to review on the dashboard.",
                "category": "reporting",
                "node_definitions": [
                    {
                        "key": "trigger",
                        "node_type": "trigger",
                        "name": "Start",
                        "config": {},
                        "next_nodes": {"default": "notify"},
                    },
                    {
                        "key": "notify",
                        "node_type": "notification",
                        "name": "Notify owners and admins",
                        "config": {
                            "channel": "in_app",
                            "recipients": ["owner", "admin"],
                            "subject": "Weekly storage health report",
                            "body_template": "Your weekly storage summary is ready — check "
                            "the dashboard.",
                        },
                        "next_nodes": {"default": "end"},
                    },
                    {
                        "key": "end",
                        "node_type": "end",
                        "name": "Done",
                        "config": {},
                        "next_nodes": {},
                    },
                ],
            },
            {
                "organization_id": None,
                "name": "Duplicate Review Workflow",
                "description": "Runs on demand; builds an execution plan for the current "
                "duplicate_files recommendation, gated by a policy you configure.",
                "category": "storage_optimization",
                "node_definitions": [
                    {
                        "key": "trigger",
                        "node_type": "trigger",
                        "name": "Start",
                        "config": {},
                        "next_nodes": {"default": "execute"},
                    },
                    {
                        "key": "execute",
                        "node_type": "execute_action",
                        "name": "Review duplicates",
                        "config": {"rule_name": "duplicate_files", "policy_key": ""},
                        "next_nodes": {"default": "notify"},
                    },
                    {
                        "key": "notify",
                        "node_type": "notification",
                        "name": "Notify owner",
                        "config": {
                            "channel": "in_app",
                            "recipients": ["owner"],
                            "subject": "Duplicate review workflow completed",
                            "body_template": "The duplicate-review workflow finished running.",
                        },
                        "next_nodes": {"default": "end"},
                    },
                    {
                        "key": "end",
                        "node_type": "end",
                        "name": "Done",
                        "config": {},
                        "next_nodes": {},
                    },
                ],
            },
            {
                "organization_id": None,
                "name": "Stale Project Cleanup",
                "description": "Runs on a schedule; archives large, long-unused files matching "
                "the large_unused_files recommendation, gated by a policy you configure.",
                "category": "storage_optimization",
                "node_definitions": [
                    {
                        "key": "trigger",
                        "node_type": "trigger",
                        "name": "Start",
                        "config": {},
                        "next_nodes": {"default": "execute"},
                    },
                    {
                        "key": "execute",
                        "node_type": "execute_action",
                        "name": "Archive stale large files",
                        "config": {"rule_name": "large_unused_files", "policy_key": ""},
                        "next_nodes": {"default": "notify"},
                    },
                    {
                        "key": "notify",
                        "node_type": "notification",
                        "name": "Notify owner",
                        "config": {
                            "channel": "in_app",
                            "recipients": ["owner"],
                            "subject": "Stale project cleanup completed",
                            "body_template": "The stale-project-cleanup workflow finished running.",
                        },
                        "next_nodes": {"default": "end"},
                    },
                    {
                        "key": "end",
                        "node_type": "end",
                        "name": "Done",
                        "config": {},
                        "next_nodes": {},
                    },
                ],
            },
            {
                "organization_id": None,
                "name": "Public Sharing Audit",
                "description": "Runs on a schedule; summarizes the current publicly_shared_files "
                "recommendation and notifies owners/admins — reporting only, no execution "
                "(this rule isn't on the executable allowlist — see ADR-020).",
                "category": "security",
                "node_definitions": [
                    {
                        "key": "trigger",
                        "node_type": "trigger",
                        "name": "Start",
                        "config": {},
                        "next_nodes": {"default": "summarize"},
                    },
                    {
                        "key": "summarize",
                        "node_type": "ai_evaluation",
                        "name": "Summarize sharing exposure",
                        "config": {
                            "prompt_template": "Summarize the current publicly_shared_files "
                            "recommendation for this organization.",
                            "context_key": "summary",
                        },
                        "next_nodes": {"default": "notify"},
                    },
                    {
                        "key": "notify",
                        "node_type": "notification",
                        "name": "Notify owners and admins",
                        "config": {
                            "channel": "in_app",
                            "recipients": ["owner", "admin"],
                            "subject": "Public sharing audit",
                            "body_template": "{{summary}}",
                        },
                        "next_nodes": {"default": "end"},
                    },
                    {
                        "key": "end",
                        "node_type": "end",
                        "name": "Done",
                        "config": {},
                        "next_nodes": {},
                    },
                ],
            },
            {
                "organization_id": None,
                "name": "Monthly Knowledge Quality Report",
                "description": "Runs on a schedule; notifies owners/admins that a fresh "
                "knowledge-completeness summary is ready to review on the dashboard.",
                "category": "knowledge",
                "node_definitions": [
                    {
                        "key": "trigger",
                        "node_type": "trigger",
                        "name": "Start",
                        "config": {},
                        "next_nodes": {"default": "notify"},
                    },
                    {
                        "key": "notify",
                        "node_type": "notification",
                        "name": "Notify owners and admins",
                        "config": {
                            "channel": "in_app",
                            "recipients": ["owner", "admin"],
                            "subject": "Monthly knowledge quality report",
                            "body_template": "Your monthly knowledge-quality summary is "
                            "ready — check the dashboard.",
                        },
                        "next_nodes": {"default": "end"},
                    },
                    {
                        "key": "end",
                        "node_type": "end",
                        "name": "Done",
                        "config": {},
                        "next_nodes": {},
                    },
                ],
            },
        ],
    )

    # --- Extend Phase 8's approval_requests/approval_decisions (ADR-021) ---
    op.add_column(
        "approval_requests",
        sa.Column("workflow_node_execution_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.alter_column("approval_requests", "execution_plan_id", nullable=True)
    op.create_foreign_key(
        "fk_approval_requests_workflow_node_execution_id",
        "approval_requests",
        "workflow_node_executions",
        ["workflow_node_execution_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_approval_request_workflow_node_execution",
        "approval_requests",
        ["workflow_node_execution_id"],
    )
    op.create_index(
        "ix_approval_requests_workflow_node_execution_id",
        "approval_requests",
        ["workflow_node_execution_id"],
    )
    op.create_check_constraint(
        "ck_approval_requests_at_least_one_target",
        "approval_requests",
        "execution_plan_id IS NOT NULL OR workflow_node_execution_id IS NOT NULL",
    )

    op.add_column(
        "approval_decisions",
        sa.Column("decided_by_policy_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.alter_column("approval_decisions", "decider_user_id", nullable=True)
    op.create_foreign_key(
        "fk_approval_decisions_decided_by_policy_id",
        "approval_decisions",
        "workflow_policies",
        ["decided_by_policy_id"],
        ["id"],
    )
    op.create_check_constraint(
        "ck_approval_decisions_exactly_one_decider",
        "approval_decisions",
        "(decider_user_id IS NOT NULL) != (decided_by_policy_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_approval_decisions_exactly_one_decider", "approval_decisions", type_="check"
    )
    op.drop_constraint(
        "fk_approval_decisions_decided_by_policy_id", "approval_decisions", type_="foreignkey"
    )
    op.alter_column("approval_decisions", "decider_user_id", nullable=False)
    op.drop_column("approval_decisions", "decided_by_policy_id")

    op.drop_constraint(
        "ck_approval_requests_at_least_one_target", "approval_requests", type_="check"
    )
    op.drop_index("ix_approval_requests_workflow_node_execution_id", table_name="approval_requests")
    op.drop_constraint(
        "uq_approval_request_workflow_node_execution", "approval_requests", type_="unique"
    )
    op.drop_constraint(
        "fk_approval_requests_workflow_node_execution_id", "approval_requests", type_="foreignkey"
    )
    op.alter_column("approval_requests", "execution_plan_id", nullable=False)
    op.drop_column("approval_requests", "workflow_node_execution_id")

    op.execute("DELETE FROM automation_templates WHERE organization_id IS NULL")
    op.drop_index("ix_automation_templates_organization_id", table_name="automation_templates")
    op.drop_table("automation_templates")

    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_status", table_name="notifications")
    op.drop_index("ix_notifications_workflow_execution_id", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_index("ix_notifications_organization_id", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("ix_workflow_policies_status", table_name="workflow_policies")
    op.drop_index("ix_workflow_policies_policy_key", table_name="workflow_policies")
    op.drop_index("ix_workflow_policies_organization_id", table_name="workflow_policies")
    op.drop_table("workflow_policies")

    op.drop_index("ix_scheduler_jobs_next_run_at", table_name="scheduler_jobs")
    op.drop_index("ix_scheduler_jobs_workflow_trigger_id", table_name="scheduler_jobs")
    op.drop_table("scheduler_jobs")

    op.drop_index("ix_workflow_node_executions_created_at", table_name="workflow_node_executions")
    op.drop_index("ix_workflow_node_executions_status", table_name="workflow_node_executions")
    op.drop_index(
        "ix_workflow_node_executions_workflow_node_id", table_name="workflow_node_executions"
    )
    op.drop_index(
        "ix_workflow_node_executions_workflow_execution_id", table_name="workflow_node_executions"
    )
    op.drop_table("workflow_node_executions")

    op.drop_index("ix_workflow_executions_status", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_organization_id", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_workflow_version_id", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_workflow_id", table_name="workflow_executions")
    op.drop_table("workflow_executions")

    op.drop_index("ix_workflow_triggers_trigger_type", table_name="workflow_triggers")
    op.drop_index("ix_workflow_triggers_workflow_id", table_name="workflow_triggers")
    op.drop_table("workflow_triggers")

    op.drop_index("ix_workflow_nodes_workflow_version_id", table_name="workflow_nodes")
    op.drop_table("workflow_nodes")

    op.drop_index("ix_workflow_versions_status", table_name="workflow_versions")
    op.drop_index("ix_workflow_versions_workflow_id", table_name="workflow_versions")
    op.drop_table("workflow_versions")

    op.drop_index("ix_workflows_status", table_name="workflows")
    op.drop_index("ix_workflows_organization_id", table_name="workflows")
    op.drop_table("workflows")
