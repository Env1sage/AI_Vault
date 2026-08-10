import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from vault_shared.db.models import SchedulerJob


class SchedulerJobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_trigger(self, workflow_trigger_id: uuid.UUID) -> SchedulerJob | None:
        return (
            self._session.query(SchedulerJob)
            .filter_by(workflow_trigger_id=workflow_trigger_id)
            .first()
        )

    def upsert_for_trigger(
        self, workflow_trigger_id: uuid.UUID, *, next_run_at: datetime | None
    ) -> SchedulerJob:
        job = self.get_by_trigger(workflow_trigger_id)
        if job is None:
            job = SchedulerJob(workflow_trigger_id=workflow_trigger_id)
            self._session.add(job)
        job.next_run_at = next_run_at
        self._session.flush()
        return job

    def claim_due(self, *, now: datetime | None = None) -> list[SchedulerJob]:
        """Atomically claims every `SchedulerJob` whose `next_run_at` has
        passed by nulling it out in one `UPDATE ... RETURNING` — this is
        what prevents the phase spec's named "trigger duplication" failure
        mode if more than one scheduler-sweep process runs concurrently:
        Postgres's row-level locking means only one transaction can
        successfully claim a given row, and a second concurrent sweep's
        otherwise-identical `WHERE next_run_at <= now()` simply matches
        zero rows for anything already claimed. The caller (`SchedulerService`)
        is responsible for recomputing and setting a fresh `next_run_at`
        once it has actually fired the trigger — this claim step alone
        only *stops* re-firing, it does not reschedule."""
        now = now or datetime.now(UTC)
        stmt = (
            update(SchedulerJob)
            .where(SchedulerJob.next_run_at.is_not(None), SchedulerJob.next_run_at <= now)
            .values(next_run_at=None)
            .returning(SchedulerJob)
        )
        result = self._session.execute(stmt)
        self._session.flush()
        return list(result.scalars().all())

    def record_run(self, job: SchedulerJob, *, workflow_execution_id: uuid.UUID | None) -> None:
        job.last_run_at = datetime.now(UTC)
        job.last_workflow_execution_id = workflow_execution_id
        self._session.flush()

    def list_all(self) -> list[SchedulerJob]:
        return list(self._session.execute(select(SchedulerJob)).scalars().all())
