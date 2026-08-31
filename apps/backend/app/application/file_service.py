import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from vault_shared import NotFoundError
from vault_shared.db.models import (
    File,
    FileClassification,
    FileExtraction,
    FileIntelligence,
    FileMetadata,
    FileRelationship,
    KnowledgeAttribute,
)
from vault_shared.db.repositories import (
    FileClassificationRepository,
    FileExtractionRepository,
    FileIntelligenceRepository,
    FileMetadataRepository,
    FileRelationshipRepository,
    FileRepository,
    KnowledgeAttributeRepository,
    StorageConnectorRepository,
)


@dataclass(frozen=True)
class RelatedFile:
    file: File
    relationship: FileRelationship


@dataclass(frozen=True)
class FileDetail:
    file: File
    metadata: FileMetadata | None
    classification: FileClassification | None
    extraction: FileExtraction | None
    intelligence: FileIntelligence | None
    knowledge_attributes: list[KnowledgeAttribute]
    related_files: list[RelatedFile]


class FileService:
    """Read-only — the Knowledge Engine's persistence layer (`FileMetadata`,
    `FileClassification`, etc.) is written exclusively by
    `apps/worker`'s `EnrichmentService`; the backend only ever assembles and
    serves what's already there for the frontend's file detail view
    (Phase 5 spec's Frontend Deliverables)."""

    def __init__(self, db: Session) -> None:
        self._connectors = StorageConnectorRepository(db)
        self._files = FileRepository(db)
        self._file_metadata = FileMetadataRepository(db)
        self._classifications = FileClassificationRepository(db)
        self._extractions = FileExtractionRepository(db)
        self._intelligence = FileIntelligenceRepository(db)
        self._knowledge_attributes = KnowledgeAttributeRepository(db)
        self._relationships = FileRelationshipRepository(db)

    def list_for_connector(
        self, connector_id: uuid.UUID, *, organization_id: uuid.UUID, limit: int, offset: int
    ) -> tuple[list[File], int]:
        connector = self._connectors.get_by_id(connector_id)
        if connector is None or connector.organization_id != organization_id:
            raise NotFoundError("Connector not found.")
        files = self._files.list_for_connector(connector_id, limit=limit, offset=offset)
        total = self._files.count_for_connector(connector_id)
        return files, total

    def get_detail(self, file_id: uuid.UUID, *, organization_id: uuid.UUID) -> FileDetail:
        file = self._files.get_owned_by_organization(file_id, organization_id=organization_id)
        if file is None:
            raise NotFoundError("File not found.")

        relationship_rows = self._relationships.list_for_file(file.id)

        def other_side(row: FileRelationship) -> uuid.UUID:
            return row.related_file_id if row.file_id == file.id else row.file_id

        related_ids = {other_side(row) for row in relationship_rows}
        related_files_by_id = {f.id: f for f in self._files.list_by_ids(list(related_ids))}

        related_files = [
            RelatedFile(file=related_files_by_id[other_side(row)], relationship=row)
            for row in relationship_rows
            if other_side(row) in related_files_by_id
        ]

        return FileDetail(
            file=file,
            metadata=self._file_metadata.get_by_file_id(file.id),
            classification=self._classifications.get_by_file_id(file.id),
            extraction=self._extractions.get_by_file_id(file.id),
            intelligence=self._intelligence.get_by_file_id(file.id),
            knowledge_attributes=self._knowledge_attributes.list_for_file(file.id),
            related_files=related_files,
        )
