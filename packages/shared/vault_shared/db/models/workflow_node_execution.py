import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vault_shared.db.session import Base


class WorkflowNodeExecutionStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_APPROVAL = "waiting_approval"
    WAITING_DELAY = "waiting_delay"


class WorkflowNodeExecution(Base):
    """Per-node execution history for one `WorkflowExecution` — not named
    as its own top-level entity in the phase spec's DB Deliverables list,
    but required to satisfy "Persist execution state," "Resume interrupted
    workflows," and the frontend's Execution Logs view; the same
    spec-implied-not-spec-literal addition Phase 8 made for
    `ExecutionResult`/`RollbackRecord`. `output_context` is what this node
    contributed back to the running `WorkflowExecution.context` dict."""

    __tablename__ = "workflow_node_executions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    workflow_execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workflow_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=WorkflowNodeExecutionStatus.PENDING, index=True
    )
    output_context: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
