import uuid

from sqlalchemy.orm import Session

from vault_shared.db.models import ExecutionStep, ExecutionStepStatus


class ExecutionStepRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        execution_plan_id: uuid.UUID,
        step_order: int,
        action_type: str,
        target_file_id: uuid.UUID,
        pre_state: dict,
        planned_change: dict,
    ) -> ExecutionStep:
        step = ExecutionStep(
            execution_plan_id=execution_plan_id,
            step_order=step_order,
            action_type=action_type,
            target_file_id=target_file_id,
            pre_state=pre_state,
            planned_change=planned_change,
        )
        self._session.add(step)
        self._session.flush()
        return step

    def get_by_id(self, execution_step_id: uuid.UUID) -> ExecutionStep | None:
        return self._session.get(ExecutionStep, execution_step_id)

    def list_for_plan(self, execution_plan_id: uuid.UUID) -> list[ExecutionStep]:
        return (
            self._session.query(ExecutionStep)
            .filter_by(execution_plan_id=execution_plan_id)
            .order_by(ExecutionStep.step_order)
            .all()
        )

    def mark_status(self, step: ExecutionStep, *, status: str) -> None:
        step.status = status
        self._session.flush()

    def mark_completed(self, step: ExecutionStep) -> None:
        self.mark_status(step, status=ExecutionStepStatus.COMPLETED)

    def mark_failed(self, step: ExecutionStep) -> None:
        self.mark_status(step, status=ExecutionStepStatus.FAILED)

    def mark_skipped(self, step: ExecutionStep) -> None:
        self.mark_status(step, status=ExecutionStepStatus.SKIPPED)

    def mark_rolled_back(self, step: ExecutionStep) -> None:
        self.mark_status(step, status=ExecutionStepStatus.ROLLED_BACK)
