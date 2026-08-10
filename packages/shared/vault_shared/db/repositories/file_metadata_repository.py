import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from vault_shared.db.models import FileMetadata


class FileMetadataRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_file_id(self, file_id: uuid.UUID) -> FileMetadata | None:
        return self._session.get(FileMetadata, file_id)

    def upsert(
        self,
        *,
        file_id: uuid.UUID,
        normalized_extension: str | None,
        mime_type_validated: bool,
        mime_mismatch_reason: str | None,
        naming_pattern: str | None,
        version_label: str | None,
        owner_summary: str | None,
        sharing_summary: str | None,
        language: str | None,
        enriched_at: datetime,
    ) -> FileMetadata:
        """Deliberately has no `duplicate_group_key` parameter — that field
        is owned exclusively by `set_duplicate_group_key`, written by the
        later relationship-discovery pass, not the per-file processor pass
        this method serves. Leaving it out of the signature (rather than
        accepting and re-assigning it here) means a rerun of this method can
        never clobber a value the other pass already set."""
        metadata = self.get_by_file_id(file_id)
        if metadata is None:
            metadata = FileMetadata(file_id=file_id)
            self._session.add(metadata)

        metadata.normalized_extension = normalized_extension
        metadata.mime_type_validated = mime_type_validated
        metadata.mime_mismatch_reason = mime_mismatch_reason
        metadata.naming_pattern = naming_pattern
        metadata.version_label = version_label
        metadata.owner_summary = owner_summary
        metadata.sharing_summary = sharing_summary
        metadata.language = language
        metadata.enriched_at = enriched_at
        self._session.flush()
        return metadata

    def set_duplicate_group_key(self, file_id: uuid.UUID, key: str | None) -> None:
        """A targeted update, separate from `upsert` — called only by the
        relationship-discovery pass, which runs *after* every file's main
        `FileMetadata` row already exists from the per-file processing pass
        (Phase 5's two-pass shape, mirroring ADR-016's scanner)."""
        metadata = self.get_by_file_id(file_id)
        if metadata is not None:
            metadata.duplicate_group_key = key
            self._session.flush()
