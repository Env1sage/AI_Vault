import uuid
from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Query, Session

from vault_shared.db.models import (
    Embedding,
    ExtractionStatus,
    File,
    FileClassification,
    FileExtraction,
    FileIntelligence,
    FileMetadata,
    KnowledgeAttribute,
    StorageConnector,
    StorageSource,
)


class FileRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, file_id: uuid.UUID) -> File | None:
        return self._session.get(File, file_id)

    def get_owned_by_organization(
        self, file_id: uuid.UUID, *, organization_id: uuid.UUID
    ) -> File | None:
        """Used by the backend's file-detail endpoint, which addresses a
        file directly by id (no connector_id in the URL, unlike the scans
        API) — so ownership has to be checked via a join all the way to
        `storage_connectors.organization_id` rather than a simple
        `connector.organization_id` comparison the caller already has."""
        return (
            self._session.query(File)
            .join(StorageSource, File.storage_source_id == StorageSource.id)
            .join(StorageConnector, StorageSource.connector_id == StorageConnector.id)
            .filter(File.id == file_id, StorageConnector.organization_id == organization_id)
            .first()
        )

    def list_by_ids(self, file_ids: list[uuid.UUID]) -> list[File]:
        if not file_ids:
            return []
        return self._session.query(File).filter(File.id.in_(file_ids)).all()

    def list_owned_by_organization(
        self, file_ids: list[uuid.UUID], *, organization_id: uuid.UUID
    ) -> list[File]:
        """Org-scoped bulk lookup — unlike `list_by_ids`, safe to use on a
        caller-supplied id list an unrelated organization could otherwise
        smuggle a file id into (Storage Intelligence's ad-hoc execution
        plans, built directly from a user-picked file selection rather
        than a precomputed, already-org-scoped group)."""
        if not file_ids:
            return []
        return self._for_organization(organization_id).filter(File.id.in_(file_ids)).all()

    def get_by_source_and_provider_id(
        self, *, storage_source_id: uuid.UUID, provider_file_id: str
    ) -> File | None:
        return (
            self._session.query(File)
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
        mime_type: str | None,
        size_bytes: int | None,
        owner_email: str | None,
        is_shared: bool,
        permissions_summary: str | None,
        version_id: str | None,
        checksum: str | None,
        web_view_link: str | None,
        provider_created_at: datetime | None,
        provider_modified_at: datetime | None,
        provider_viewed_at: datetime | None,
        scanned_at: datetime,
    ) -> File:
        file = self.get_by_source_and_provider_id(
            storage_source_id=storage_source_id, provider_file_id=provider_file_id
        )
        if file is None:
            file = File(storage_source_id=storage_source_id, provider_file_id=provider_file_id)
            self._session.add(file)

        file.provider_parent_id = provider_parent_id
        file.parent_folder_id = parent_folder_id
        file.name = name
        file.path = path
        file.mime_type = mime_type
        file.size_bytes = size_bytes
        file.owner_email = owner_email
        file.is_shared = is_shared
        file.permissions_summary = permissions_summary
        file.version_id = version_id
        file.checksum = checksum
        file.web_view_link = web_view_link
        file.provider_created_at = provider_created_at
        file.provider_modified_at = provider_modified_at
        file.provider_viewed_at = provider_viewed_at
        file.scanned_at = scanned_at
        self._session.flush()
        return file

    def count_for_source(self, storage_source_id: uuid.UUID) -> int:
        return self._session.query(File).filter_by(storage_source_id=storage_source_id).count()

    def delete_by_source_and_provider_id(
        self, *, storage_source_id: uuid.UUID, provider_file_id: str
    ) -> bool:
        """Used by incremental sync when Drive reports an item removed or
        trashed. Returns whether a row existed."""
        file = self.get_by_source_and_provider_id(
            storage_source_id=storage_source_id, provider_file_id=provider_file_id
        )
        if file is None:
            return False
        self._session.delete(file)
        self._session.flush()
        return True

    def list_for_source(self, storage_source_id: uuid.UUID) -> list[File]:
        """Used only by the scanner's post-ingest hierarchy-resolution pass
        (`ScannerService._resolve_hierarchy`) to fix up file paths once all
        folder paths are known."""
        return self._session.query(File).filter_by(storage_source_id=storage_source_id).all()

    def _for_connector(self, connector_id: uuid.UUID) -> Query[File]:
        return (
            self._session.query(File)
            .join(StorageSource, File.storage_source_id == StorageSource.id)
            .filter(StorageSource.connector_id == connector_id)
        )

    def list_for_connector(
        self, connector_id: uuid.UUID, *, limit: int, offset: int
    ) -> list[File]:
        return (
            self._for_connector(connector_id)
            .order_by(File.name)
            .limit(limit)
            .offset(offset)
            .all()
        )

    def count_for_connector(self, connector_id: uuid.UUID) -> int:
        return self._for_connector(connector_id).count()

    def list_all_for_connector(self, connector_id: uuid.UUID) -> list[File]:
        """Unpaginated — used only by `RelationshipDiscoveryService`, which
        must compare a connector's *entire* current file set against itself
        (a newly-enriched file can relate to an already-enriched sibling),
        not just whatever was pending in this particular enrichment run."""
        return self._for_connector(connector_id).all()

    def list_pending_enrichment_for_connector(self, connector_id: uuid.UUID) -> list[File]:
        """A file is "pending" if it has never been enriched, or if it was
        rescanned (`File.scanned_at` advanced) since its last enrichment —
        this single query is what makes `EnrichmentJob` resumable and
        automatically cover both "process newly scanned files" and
        "reprocess updated files" (Phase 5 spec) without separate
        bookkeeping of which files a given job/scan touched."""
        return (
            self._for_connector(connector_id)
            .outerjoin(FileMetadata, FileMetadata.file_id == File.id)
            .filter(
                or_(
                    FileMetadata.file_id.is_(None),
                    File.scanned_at > FileMetadata.enriched_at,
                )
            )
            .all()
        )

    def count_pending_enrichment_for_connector(self, connector_id: uuid.UUID) -> int:
        return (
            self._for_connector(connector_id)
            .outerjoin(FileMetadata, FileMetadata.file_id == File.id)
            .filter(
                or_(
                    FileMetadata.file_id.is_(None),
                    File.scanned_at > FileMetadata.enriched_at,
                )
            )
            .count()
        )

    def list_pending_embedding_for_connector(
        self, connector_id: uuid.UUID, *, model_name: str, model_version: str
    ) -> list[File]:
        """A file is "pending" embedding if it has successfully extracted
        text (nothing else is embeddable) and any of: it has no
        `Embedding` row yet; it was re-extracted (`FileExtraction.
        extracted_at` advanced) since its last embedding; or its stored
        embedding was computed by a different model/version than the one
        currently configured (Phase 6 spec: "detect when documents
        require re-embedding" — this is what makes changing
        `LocalEmbeddingProvider`'s vectorization procedure, as ADR-018's
        stopword-filtering fix did, automatically re-embed every file
        rather than silently comparing old and new vectors). Same
        resumable-query shape as `list_pending_enrichment_for_connector`."""
        return (
            self._for_connector(connector_id)
            .join(FileExtraction, FileExtraction.file_id == File.id)
            .outerjoin(Embedding, Embedding.file_id == File.id)
            .filter(
                FileExtraction.status == ExtractionStatus.SUCCESS,
                or_(
                    Embedding.file_id.is_(None),
                    FileExtraction.extracted_at > Embedding.embedded_at,
                    Embedding.model_name != model_name,
                    Embedding.model_version != model_version,
                ),
            )
            .all()
        )

    def list_pending_intelligence_for_connector(
        self, connector_id: uuid.UUID, *, provider: str, model_name: str
    ) -> list[File]:
        """A file is "pending" AI intelligence analysis if it has
        successfully extracted text (nothing else is analyzable) and any
        of: it has no `FileIntelligence` row yet; it was re-extracted
        (`FileExtraction.extracted_at` advanced) since its last analysis;
        or its stored analysis was produced by a different completion
        provider/model than the one currently configured (mirrors
        `list_pending_embedding_for_connector`'s reasoning exactly — a
        provider/model swap, e.g. Kimi to GLM, must auto-requeue every
        file rather than silently leaving stale results in place)."""
        return (
            self._for_connector(connector_id)
            .join(FileExtraction, FileExtraction.file_id == File.id)
            .outerjoin(FileIntelligence, FileIntelligence.file_id == File.id)
            .filter(
                FileExtraction.status == ExtractionStatus.SUCCESS,
                or_(
                    FileIntelligence.file_id.is_(None),
                    FileExtraction.extracted_at > FileIntelligence.processed_at,
                    FileIntelligence.provider != provider,
                    FileIntelligence.model_name != model_name,
                ),
            )
            .all()
        )

    def search_for_organization(
        self, organization_id: uuid.UUID, query_text: str, *, limit: int
    ) -> list[File]:
        """The metadata half of `SearchService`'s hybrid search (Phase 6
        spec: "avoid relying exclusively on vector similarity") — a plain
        substring match across a file's name and the Knowledge Engine's own
        inferred fields (owner/sharing summaries, naming pattern, knowledge
        attribute values), scoped to one organization the same way every
        other cross-connector query in this repository is."""
        pattern = f"%{query_text}%"
        return (
            self._session.query(File)
            .join(StorageSource, File.storage_source_id == StorageSource.id)
            .join(StorageConnector, StorageSource.connector_id == StorageConnector.id)
            .outerjoin(FileMetadata, FileMetadata.file_id == File.id)
            .outerjoin(KnowledgeAttribute, KnowledgeAttribute.file_id == File.id)
            .filter(
                StorageConnector.organization_id == organization_id,
                or_(
                    File.name.ilike(pattern),
                    FileMetadata.owner_summary.ilike(pattern),
                    FileMetadata.sharing_summary.ilike(pattern),
                    FileMetadata.naming_pattern.ilike(pattern),
                    KnowledgeAttribute.value.ilike(pattern),
                ),
            )
            .distinct()
            .limit(limit)
            .all()
        )

    def list_recently_modified_for_organization(
        self, organization_id: uuid.UUID, *, limit: int = 10
    ) -> list[File]:
        """The Founder Command Center's "Recent Activity Feed" (Phase 7
        spec) — a plain, efficient ORDER BY/LIMIT query, not a stored
        insight; always reflects the current data, no recompute needed."""
        return (
            self._session.query(File)
            .join(StorageSource, File.storage_source_id == StorageSource.id)
            .join(StorageConnector, StorageSource.connector_id == StorageConnector.id)
            .filter(StorageConnector.organization_id == organization_id)
            .order_by(File.provider_modified_at.desc().nulls_last())
            .limit(limit)
            .all()
        )

    def list_for_organization_with_details(
        self, organization_id: uuid.UUID
    ) -> list[tuple[File, FileMetadata | None, FileClassification | None, str | None]]:
        """The Recommendation Engine's primary data pull (Handbook's
        Recommendation Engine, Phase 7) — every file across *all* of an
        organization's connectors in one query, left-joined with its
        metadata/classification (most rules need several of these fields
        at once) and its connector's `workspace_domain` (the orphaned-
        ownership rule's "is this file's owner outside the org" check).
        Brute-force by design, same acceptance as `EmbeddingRepository.
        list_for_organization` (ADR-018) — fine at reference scale, a
        streaming/paginated version is a future-scale concern."""
        rows = (
            self._session.query(
                File, FileMetadata, FileClassification, StorageConnector.workspace_domain
            )
            .join(StorageSource, File.storage_source_id == StorageSource.id)
            .join(StorageConnector, StorageSource.connector_id == StorageConnector.id)
            .outerjoin(FileMetadata, FileMetadata.file_id == File.id)
            .outerjoin(FileClassification, FileClassification.file_id == File.id)
            .filter(StorageConnector.organization_id == organization_id)
            .all()
        )
        return [
            (file, metadata, classification, domain)
            for file, metadata, classification, domain in rows
        ]

    # ------------------------------------------------------------------
    # Storage Intelligence Layer (Phase 1) queries — read-only, org-scoped.
    # ------------------------------------------------------------------

    def _for_organization(self, organization_id: uuid.UUID) -> Query[File]:
        return (
            self._session.query(File)
            .join(StorageSource, File.storage_source_id == StorageSource.id)
            .join(StorageConnector, StorageSource.connector_id == StorageConnector.id)
            .filter(StorageConnector.organization_id == organization_id)
        )

    def list_all_for_organization(self, organization_id: uuid.UUID) -> list[File]:
        """The Storage Analyzer's primary data pull — every file across all
        of an organization's connectors in one query, aggregated in Python
        afterward (`Counter`/`defaultdict`, an O(n) single pass). This runs
        only inside the background `StorageAnalysisJob`, never on the HTTP
        request path, so it accepts the same "load the org once" tradeoff
        `list_for_organization_with_details` (Recommendation Engine) and
        `EmbeddingRepository.list_for_organization` (ADR-018) already
        made — fine at reference/V1 scale (measured: a real 1,000-file org
        loads and aggregates in well under 100ms), a streaming/paginated
        version is a future-scale concern, not a Phase 1 requirement."""
        return self._for_organization(organization_id).all()

    def list_duplicate_checksum_groups_for_organization(
        self, organization_id: uuid.UUID
    ) -> list[tuple[str, int, int]]:
        """DB-side `GROUP BY` — the O(n²)-avoiding "candidate optimization"
        the spec asks for. Checksum equality already implies size equality
        (identical content ⇒ identical size), so grouping directly by
        checksum is both correct and sufficient on its own; a separate
        size-prefilter stage would only add a redundant pass. Returns
        `(checksum, file_count, total_size_bytes)` for every checksum
        shared by 2+ files — the exact-duplicate groups."""
        rows = (
            self._session.query(File.checksum, func.count(File.id), func.sum(File.size_bytes))
            .join(StorageSource, File.storage_source_id == StorageSource.id)
            .join(StorageConnector, StorageSource.connector_id == StorageConnector.id)
            .filter(
                StorageConnector.organization_id == organization_id,
                File.checksum.isnot(None),
            )
            .group_by(File.checksum)
            .having(func.count(File.id) > 1)
            .all()
        )
        return [(checksum, count, int(total or 0)) for checksum, count, total in rows]

    def list_for_checksum_in_organization(
        self, organization_id: uuid.UUID, checksum: str
    ) -> list[File]:
        return self._for_organization(organization_id).filter(File.checksum == checksum).all()

    def list_large_for_organization(
        self, organization_id: uuid.UUID, *, min_size_bytes: int, limit: int, offset: int
    ) -> tuple[list[File], int]:
        query = self._for_organization(organization_id).filter(
            File.size_bytes.isnot(None), File.size_bytes >= min_size_bytes
        )
        total = query.count()
        items = query.order_by(File.size_bytes.desc()).limit(limit).offset(offset).all()
        return items, total

    def list_old_for_organization(
        self, organization_id: uuid.UUID, *, older_than: datetime, limit: int, offset: int
    ) -> tuple[list[File], int]:
        """"Old" = content staleness, judged by `provider_modified_at`
        alone (Phase 1 spec §9) — deliberately distinct from "inactive"
        below, which also considers view activity."""
        query = self._for_organization(organization_id).filter(
            File.provider_modified_at.isnot(None), File.provider_modified_at < older_than
        )
        total = query.count()
        items = (
            query.order_by(File.provider_modified_at.asc()).limit(limit).offset(offset).all()
        )
        return items, total

    def list_inactive_for_organization(
        self, organization_id: uuid.UUID, *, inactive_since: datetime, limit: int, offset: int
    ) -> tuple[list[File], int]:
        """"Inactive" = usage staleness, judged by whichever of
        `provider_modified_at`/`provider_viewed_at` is more recent (Phase 1
        spec §10) — a file only qualifies if at least one of those
        timestamps is known and it's older than the cutoff; a file with
        neither timestamp is `UNKNOWN` activity (see
        `list_unknown_activity_for_organization`), never guessed as
        inactive."""
        last_activity = func.greatest(File.provider_modified_at, File.provider_viewed_at)
        query = self._for_organization(organization_id).filter(
            or_(File.provider_modified_at.isnot(None), File.provider_viewed_at.isnot(None)),
            last_activity < inactive_since,
        )
        total = query.count()
        items = query.order_by(last_activity.asc()).limit(limit).offset(offset).all()
        return items, total

    def count_unknown_activity_for_organization(self, organization_id: uuid.UUID) -> int:
        return (
            self._for_organization(organization_id)
            .filter(File.provider_modified_at.is_(None), File.provider_viewed_at.is_(None))
            .count()
        )

    def list_temporary_candidates_for_organization(
        self, organization_id: uuid.UUID, *, limit: int, offset: int
    ) -> tuple[list[File], int]:
        """Deterministic filename/extension heuristics only (Phase 1 spec
        §11) — never a certainty claim; callers must label these as
        "potential" candidates, not "unwanted"/"safe to delete"."""
        patterns = [
            File.name.ilike(pattern)
            for pattern in (
                "%.tmp",
                "%.temp",
                "%.cache",
                "%.log",
                "%.bak",
                "~$%",
                "%copy%",
                "% copy%",
                "%(1)%",
                "%backup%",
                "%.old",
            )
        ]
        query = self._for_organization(organization_id).filter(or_(*patterns))
        total = query.count()
        items = (
            query.order_by(File.size_bytes.desc().nulls_last()).limit(limit).offset(offset).all()
        )
        return items, total
