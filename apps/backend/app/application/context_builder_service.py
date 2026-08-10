import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.application.search_service import SearchResult
from vault_shared.db.models import File
from vault_shared.db.repositories import (
    FileExtractionRepository,
    FileMetadataRepository,
    FileRelationshipRepository,
    FileRepository,
)

# A rough token-budget stand-in (~4 chars/token, no real tokenizer in this
# phase — see `ExtractiveCompletionProvider`'s identical approximation).
# Keeps the assembled context well inside any real LLM's context window
# once one is configured, without pretending to a precision this stubbed
# phase can't back up.
_DEFAULT_MAX_CONTEXT_CHARS = 8000
_SNIPPET_CHARS = 600
_MAX_RELATED_NAMES = 3


@dataclass(frozen=True)
class CitationCandidate:
    file: File
    snippet: str | None
    confidence: float
    retrieval_method: str


@dataclass(frozen=True)
class ContextBundle:
    context_text: str
    citations: list[CitationCandidate]


class ContextBuilderService:
    """Phase 6's Context Builder — merges structured metadata, extracted
    content, and relationship data into one ranked, deduplicated,
    token-budget-aware block of text. Deliberately generic over its input
    (`SearchResult`, already ranked by `SearchService`) and output (a plain
    string plus a parallel citation list) so a future automation feature
    can reuse it without depending on the conversational flow that
    exercises it in this phase (phase spec: "reusable context assembly for
    future automation features")."""

    def __init__(self, db: Session) -> None:
        self._files = FileRepository(db)
        self._extractions = FileExtractionRepository(db)
        self._file_metadata = FileMetadataRepository(db)
        self._relationships = FileRelationshipRepository(db)

    def build(
        self, results: list[SearchResult], *, max_chars: int = _DEFAULT_MAX_CONTEXT_CHARS
    ) -> ContextBundle:
        blocks: list[str] = []
        citations: list[CitationCandidate] = []
        used_chars = 0
        seen_file_ids: set[uuid.UUID] = set()

        for result in results:
            if result.file.id in seen_file_ids:
                continue
            seen_file_ids.add(result.file.id)

            block, snippet = self._render_block(result.file)
            if used_chars + len(block) > max_chars:
                if not blocks:
                    blocks.append(block[:max_chars])
                break

            blocks.append(block)
            used_chars += len(block)
            citations.append(
                CitationCandidate(
                    file=result.file,
                    snippet=snippet,
                    confidence=result.score,
                    retrieval_method=result.retrieval_method,
                )
            )

        return ContextBundle(context_text="\n\n".join(blocks), citations=citations)

    def _render_block(self, file: File) -> tuple[str, str | None]:
        lines = [f"### {file.name} ({file.path})"]

        metadata = self._file_metadata.get_by_file_id(file.id)
        if metadata is not None and (metadata.owner_summary or metadata.sharing_summary):
            lines.append(
                f"Owner: {metadata.owner_summary or 'unknown'}; "
                f"Sharing: {metadata.sharing_summary or 'unknown'}"
            )

        related_names = self._related_file_names(file.id)
        if related_names:
            lines.append(f"Related files: {', '.join(related_names)}")

        extraction = self._extractions.get_by_file_id(file.id)
        snippet = None
        if extraction is not None and extraction.extracted_text:
            snippet = extraction.extracted_text[:_SNIPPET_CHARS]
            lines.append(snippet)
        else:
            lines.append("[no extracted content]")

        return "\n".join(lines), snippet

    def _related_file_names(self, file_id: uuid.UUID) -> list[str]:
        relationships = self._relationships.list_for_file(file_id)[:_MAX_RELATED_NAMES]
        other_ids = [
            (
                relationship.related_file_id
                if relationship.file_id == file_id
                else relationship.file_id
            )
            for relationship in relationships
        ]
        files_by_id = {file.id: file for file in self._files.list_by_ids(other_ids)}
        return [files_by_id[other_id].name for other_id in other_ids if other_id in files_by_id]
