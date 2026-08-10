import uuid

from sqlalchemy.orm import Session

from vault_shared.db.models import Workflow, WorkflowTrigger


class WorkflowTriggerRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self, *, workflow_id: uuid.UUID, trigger_type: str, config: dict, enabled: bool = True
    ) -> WorkflowTrigger:
        trigger = WorkflowTrigger(
            workflow_id=workflow_id, trigger_type=trigger_type, config=config, enabled=enabled
        )
        self._session.add(trigger)
        self._session.flush()
        return trigger

    def get_by_id(self, workflow_trigger_id: uuid.UUID) -> WorkflowTrigger | None:
        return self._session.get(WorkflowTrigger, workflow_trigger_id)

    def get_owned(
        self, workflow_trigger_id: uuid.UUID, *, workflow_id: uuid.UUID
    ) -> WorkflowTrigger | None:
        return (
            self._session.query(WorkflowTrigger)
            .filter_by(id=workflow_trigger_id, workflow_id=workflow_id)
            .first()
        )

    def list_for_workflow(self, workflow_id: uuid.UUID) -> list[WorkflowTrigger]:
        return self._session.query(WorkflowTrigger).filter_by(workflow_id=workflow_id).all()

    def list_enabled_by_event_type(
        self, *, organization_id: uuid.UUID, event_type: str
    ) -> list[WorkflowTrigger]:
        """Every enabled `EVENT` trigger configured for a given event name
        within one organization — used by `vault_shared.workflow_events.
        fire_workflow_event` (the scan/enrichment/recommendation/connector
        completion hooks) to find which workflows to start. Filtering by
        `config->>'event_type'` (a JSONB field lookup) rather than a
        dedicated column keeps `WorkflowTrigger` generic across trigger
        types; joining through `Workflow` for `organization_id` since a
        trigger has no organization column of its own."""
        return (
            self._session.query(WorkflowTrigger)
            .join(Workflow, WorkflowTrigger.workflow_id == Workflow.id)
            .filter(
                Workflow.organization_id == organization_id,
                WorkflowTrigger.trigger_type == "event",
                WorkflowTrigger.enabled.is_(True),
                WorkflowTrigger.config["event_type"].astext == event_type,
            )
            .all()
        )

    def set_enabled(self, trigger: WorkflowTrigger, *, enabled: bool) -> None:
        trigger.enabled = enabled
        self._session.flush()
