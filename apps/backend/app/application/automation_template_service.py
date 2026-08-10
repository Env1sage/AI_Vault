import uuid

from sqlalchemy.orm import Session

from app.application.workflow_service import WorkflowService
from vault_shared import NotFoundError
from vault_shared.db.models import AutomationTemplate, Workflow
from vault_shared.db.repositories import AutomationTemplateRepository


class AutomationTemplateService:
    """Read/apply surface for the Templates Gallery (Phase 9 spec:
    "Ship initial templates... Templates should be customizable"). Applying
    a template creates a brand-new `Workflow` with a draft version seeded
    from the template's node graph — never a live reference back to the
    template — so editing the resulting workflow can never affect the
    template itself or any other organization's copy of it."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._templates = AutomationTemplateRepository(db)
        self._workflows = WorkflowService(db)

    def list_available(self, *, organization_id: uuid.UUID) -> list[AutomationTemplate]:
        return self._templates.list_available(organization_id=organization_id)

    def apply(
        self,
        automation_template_id: uuid.UUID,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        workflow_name: str | None = None,
    ) -> Workflow:
        template = self._templates.get_by_id(automation_template_id)
        if template is None:
            raise NotFoundError("Automation template not found.")

        workflow = self._workflows.create(
            organization_id=organization_id,
            user_id=user_id,
            name=workflow_name or template.name,
            description=template.description,
        )
        version, _existing_nodes = self._workflows.get_or_create_draft(
            workflow.id, organization_id=organization_id, user_id=user_id
        )
        self._workflows.replace_nodes(
            version.id,
            workflow_id=workflow.id,
            organization_id=organization_id,
            nodes=list(template.node_definitions),
        )
        return workflow
