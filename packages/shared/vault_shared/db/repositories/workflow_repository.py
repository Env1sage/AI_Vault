import uuid

from sqlalchemy.orm import Session

from vault_shared.db.models import Workflow


class WorkflowRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        organization_id: uuid.UUID,
        created_by_user_id: uuid.UUID,
        name: str,
        description: str | None,
    ) -> Workflow:
        workflow = Workflow(
            organization_id=organization_id,
            created_by_user_id=created_by_user_id,
            name=name,
            description=description,
        )
        self._session.add(workflow)
        self._session.flush()
        return workflow

    def get_by_id(self, workflow_id: uuid.UUID) -> Workflow | None:
        return self._session.get(Workflow, workflow_id)

    def get_owned(self, workflow_id: uuid.UUID, *, organization_id: uuid.UUID) -> Workflow | None:
        return (
            self._session.query(Workflow)
            .filter_by(id=workflow_id, organization_id=organization_id)
            .first()
        )

    def list_for_organization(
        self, organization_id: uuid.UUID, *, status: str | None = None
    ) -> list[Workflow]:
        query = self._session.query(Workflow).filter_by(organization_id=organization_id)
        if status is not None:
            query = query.filter(Workflow.status == status)
        return query.order_by(Workflow.created_at.desc()).all()

    def update_status(self, workflow: Workflow, *, status: str) -> None:
        workflow.status = status
        self._session.flush()
