import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from vault_shared.db.models import Folder, StorageConnector, StorageSource


class FolderRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_source_and_provider_id(
        self, *, storage_source_id: uuid.UUID, provider_file_id: str
    ) -> Folder | None:
        return (
            self._session.query(Folder)
            .filter_by(storage_source_id=storage_source_id, provider_file_id=provider_file_id)
            .first()
        )

    def upsert(
        self,
        *,
        storage_source_id: uuid.UUID,
        provider_file_id: str,
        provider_parent_id: str | None,
        parent_folder_id: uuid.UUID | None,
        name: str,
        path: str,
        owner_email: str | None,
        is_shared: bool,
        provider_created_at: datetime | None,
        provider_modified_at: datetime | None,
        scanned_at: datetime,
    ) -> Folder:
        folder = self.get_by_source_and_provider_id(
            storage_source_id=storage_source_id, provider_file_id=provider_file_id
        )
        if folder is None:
            folder = Folder(storage_source_id=storage_source_id, provider_file_id=provider_file_id)
            self._session.add(folder)

        folder.provider_parent_id = provider_parent_id
        folder.parent_folder_id = parent_folder_id
        folder.name = name
        folder.path = path
        folder.owner_email = owner_email
        folder.is_shared = is_shared
        folder.provider_created_at = provider_created_at
        folder.provider_modified_at = provider_modified_at
        folder.scanned_at = scanned_at
        self._session.flush()
        return folder

    def count_for_source(self, storage_source_id: uuid.UUID) -> int:
        return self._session.query(Folder).filter_by(storage_source_id=storage_source_id).count()

    def count_for_organization(self, organization_id: uuid.UUID) -> int:
        return (
            self._session.query(Folder)
            .join(StorageSource, Folder.storage_source_id == StorageSource.id)
            .join(StorageConnector, StorageSource.connector_id == StorageConnector.id)
            .filter(StorageConnector.organization_id == organization_id)
            .count()
        )

    def delete_by_source_and_provider_id(
        self, *, storage_source_id: uuid.UUID, provider_file_id: str
    ) -> bool:
        """Used by incremental sync when Drive reports an item removed or
        trashed; the FK's ON DELETE CASCADE handles any descendant folders/
        files still pointing at this one. Returns whether a row existed."""
        folder = self.get_by_source_and_provider_id(
            storage_source_id=storage_source_id, provider_file_id=provider_file_id
        )
        if folder is None:
            return False
        self._session.delete(folder)
        self._session.flush()
        return True

    def list_for_source(self, storage_source_id: uuid.UUID) -> list[Folder]:
        """Used only by the scanner's post-ingest hierarchy-resolution pass
        (`ScannerService._resolve_hierarchy`) — folders are a small subset
        of items even at reference scale (Handbook §20), so holding all of
        one source's folders in memory for that bounded pass is acceptable;
        `File` rows are never listed this way."""
        return self._session.query(Folder).filter_by(storage_source_id=storage_source_id).all()
