import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from vault_shared.db.models import ExecutionResult


class ExecutionResultRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        execution_job_id: uuid.UUID,
        execution_step_id: uuid.UUID,
        status: str,
        verification_status: str,
        error: str | None,
        executed_at: datetime,
        verified_at: datetime | None,
    ) -> ExecutionResult:
        result = ExecutionResult(
            execution_job_id=execution_job_id,
            execution_step_id=execution_step_id,
            status=status,
            verification_status=verification_status,
            error=error[:2048] if error else None,
            executed_at=executed_at,
            verified_at=verified_at,
        )
        self._session.add(result)
        self._session.flush()
        return result

    def list_for_job(self, execution_job_id: uuid.UUID) -> list[ExecutionResult]:
        return (
            self._session.query(ExecutionResult)
            .filter_by(execution_job_id=execution_job_id)
            .order_by(ExecutionResult.executed_at)
            .all()
        )

    def get_by_job_and_step(
        self, *, execution_job_id: uuid.UUID, execution_step_id: uuid.UUID
    ) -> ExecutionResult | None:
        """Scoped by job, not step alone — a forward-execution job and a
        later rollback job each have their own result for the same step
        (see `ExecutionResult`'s docstring)."""
        return (
            self._session.query(ExecutionResult)
            .filter_by(execution_job_id=execution_job_id, execution_step_id=execution_step_id)
            .first()
        )
