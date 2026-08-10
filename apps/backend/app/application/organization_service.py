from sqlalchemy.orm import Session

from vault_shared.db.models import Organization
from vault_shared.db.repositories import OrganizationRepository


class OrganizationService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._organizations = OrganizationRepository(db)

    def rename(self, organization: Organization, *, name: str) -> Organization:
        updated = self._organizations.update_name(organization, name=name)
        self._db.commit()
        return updated
