import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from vault_shared.db.models import ExecutionStep, RollbackRecord


class RollbackRecordRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, *, execution_step_id: uuid.UUID, pre_state: dict) -> RollbackRecord:
        record = RollbackRecord(execution_step_id=execution_step_id, pre_state=pre_state)
        self._session.add(record)
        self._session.flush()
        return record

    def get_by_step(self, execution_step_id: uuid.UUID) -> RollbackRecord | None:
        return (
            self._session.query(RollbackRecord)
            .filter_by(execution_step_id=execution_step_id)
            .first()
        )

    def list_rollbackable_for_plan(self, execution_plan_id: uuid.UUID) -> list[RollbackRecord]:
        """Every not-yet-rolled-back record for a plan's steps — what
        `POST /v1/execution-plans/{id}/rollback` actually iterates over."""
        return (
            self._session.query(RollbackRecord)
            .join(ExecutionStep, RollbackRecord.execution_step_id == ExecutionStep.id)
            .filter(
                ExecutionStep.execution_plan_id == execution_plan_id,
                RollbackRecord.rolled_back.is_(False),
            )
            .all()
        )

    def mark_rolled_back(self, record: RollbackRecord, *, user_id: uuid.UUID) -> None:
        record.rolled_back = True
        record.rolled_back_at = datetime.now(UTC)
        record.rolled_back_by_user_id = user_id
        self._session.flush()
