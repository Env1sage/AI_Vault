import uuid

from sqlalchemy.orm import Session

from vault_shared.db.models import Organization


class OrganizationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, organization_id: uuid.UUID) -> Organization | None:
        return self._session.get(Organization, organization_id)

    def get_by_slug(self, slug: str) -> Organization | None:
        return self._session.query(Organization).filter_by(slug=slug).first()

    def create(self, *, name: str, slug: str) -> Organization:
        organization = Organization(name=name, slug=slug)
        self._session.add(organization)
        self._session.flush()
        return organization

    def update_name(self, organization: Organization, *, name: str) -> Organization:
        organization.name = name
        self._session.flush()
        return organization
