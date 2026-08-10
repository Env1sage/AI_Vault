import uuid

from sqlalchemy.orm import Session

from vault_shared.db.models import AutomationTemplate


class AutomationTemplateRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        organization_id: uuid.UUID | None,
        name: str,
        description: str | None,
        category: str,
        node_definitions: list,
    ) -> AutomationTemplate:
        template = AutomationTemplate(
            organization_id=organization_id,
            name=name,
            description=description,
            category=category,
            node_definitions=node_definitions,
        )
        self._session.add(template)
        self._session.flush()
        return template

    def get_by_id(self, automation_template_id: uuid.UUID) -> AutomationTemplate | None:
        return self._session.get(AutomationTemplate, automation_template_id)

    def list_available(self, *, organization_id: uuid.UUID) -> list[AutomationTemplate]:
        """Global (`organization_id IS NULL`) templates plus this
        organization's own — the Templates Gallery's full listing."""
        return (
            self._session.query(AutomationTemplate)
            .filter(
                (AutomationTemplate.organization_id.is_(None))
                | (AutomationTemplate.organization_id == organization_id)
            )
            .order_by(AutomationTemplate.category, AutomationTemplate.name)
            .all()
        )

    def exists_global(self, *, name: str) -> bool:
        return (
            self._session.query(AutomationTemplate)
            .filter_by(organization_id=None, name=name)
            .first()
            is not None
        )
