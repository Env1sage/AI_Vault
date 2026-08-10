import uuid
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from vault_shared.db.models import FileRelationship, StorageConnector


class FileRelationshipRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_file(self, file_id: uuid.UUID) -> list[FileRelationship]:
        """Relationships are stored directionally (one row per discovered
        pair) but conceptually symmetric, so this returns both directions —
        rows where the file is the subject and rows where it's the object."""
        return (
            self._session.query(FileRelationship)
            .filter(
                or_(
                    FileRelationship.file_id == file_id,
                    FileRelationship.related_file_id == file_id,
                )
            )
            .all()
        )

    def list_for_organization(self, organization_id: uuid.UUID) -> list[FileRelationship]:
        """Every relationship edge across an organization's connectors —
        used by the Recommendation Engine's connectivity-based insight and
        the duplicate-files rule's grouping. Relationships are bounded per
        connector by design (ADR-017's group-size cap), so this stays
        small even at reference scale."""
        return (
            self._session.query(FileRelationship)
            .join(StorageConnector, FileRelationship.connector_id == StorageConnector.id)
            .filter(StorageConnector.organization_id == organization_id)
            .all()
        )

    def upsert(
        self,
        *,
        connector_id: uuid.UUID,
        file_id: uuid.UUID,
        related_file_id: uuid.UUID,
        relationship_type: str,
        confidence: float,
        metadata: dict,
        discovered_at: datetime,
    ) -> FileRelationship:
        relationship = (
            self._session.query(FileRelationship)
            .filter_by(
                file_id=file_id,
                related_file_id=related_file_id,
                relationship_type=relationship_type,
            )
            .first()
        )
        if relationship is None:
            relationship = FileRelationship(
                connector_id=connector_id,
                file_id=file_id,
                related_file_id=related_file_id,
                relationship_type=relationship_type,
            )
            self._session.add(relationship)

        relationship.confidence = confidence
        relationship.metadata_ = metadata
        relationship.discovered_at = discovered_at
        self._session.flush()
        return relationship
