import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class WorkflowNodeType(enum.StrEnum):
    TRIGGER = "trigger"
    CONDITION = "condition"
    DECISION = "decision"
    AI_EVALUATION = "ai_evaluation"
    APPROVAL = "approval"
    EXECUTE_ACTION = "execute_action"
    DELAY = "delay"
    NOTIFICATION = "notification"
    END = "end"


class WorkflowNode(Base):
    """One node in a `WorkflowVersion`'s graph (Phase 9 spec's named node
    types). `config` is node-type-specific (e.g. a cron-free structured
    condition expression, an execute-action's policy reference, a
    notification's template) — deliberately not `eval()`-based, see
    `worker.workflow.execution_service` for the tiny, safe expression
    language this drives. `next_nodes` is a JSONB outcome→node-id map
    (e.g. `{"default": "<uuid>"}`, `{"true": "<uuid>", "false": "<uuid>"}`,
    `{"approved": "<uuid>", "rejected": "<uuid>"}`) — the graph's edges
    live on the node they leave, not a separate edges table (same "JSONB
    over join table" precedent as `FileRelationship.metadata_`/
    `Recommendation.affected_file_ids`). `position_x`/`position_y` exist
    only so a future visual/drag-and-drop builder has somewhere to persist
    layout — nothing in this phase's execution logic reads them."""

    __tablename__ = "workflow_nodes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    workflow_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_type: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    next_nodes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    position_x: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    position_y: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
