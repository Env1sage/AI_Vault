import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from vault_shared.ai_gateway import AIGateway, rank_by_similarity
from vault_shared.db.models import File
from vault_shared.db.repositories import (
    EmbeddingRepository,
    FileRepository,
    SearchSessionRepository,
)

_METADATA_SCORE = 1.0
# Empirically validated against this project's own real scanned files
# (see ADR-018) — mean-centered cosine similarity for genuinely related
# documents lands well above this, unrelated documents well below it.
_SEMANTIC_SCORE_THRESHOLD = 0.05
_MAX_SEMANTIC_CANDIDATES = 15
_MAX_RESULTS = 20


@dataclass(frozen=True)
class SearchResult:
    file: File
    score: float
    retrieval_method: str  # "metadata" | "semantic" | "both"


class SearchService:
    """Phase 6's Semantic Search Engine — deliberately hybrid (Handbook
    §8.14 / phase spec: "combining metadata search, knowledge attributes,
    and semantic embeddings... avoid relying exclusively on vector
    similarity"). A plain substring match on a file's name/metadata often
    finds the exact file a keyword search would; embedding similarity
    finds conceptually related files a keyword search would miss. Neither
    alone is what the phase asks for."""

    def __init__(self, db: Session, *, ai_gateway: AIGateway) -> None:
        self._db = db
        self._ai_gateway = ai_gateway
        self._files = FileRepository(db)
        self._embeddings = EmbeddingRepository(db)
        self._search_sessions = SearchSessionRepository(db)

    def search(
        self,
        query_text: str,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: int = _MAX_RESULTS,
    ) -> list[SearchResult]:
        results_by_file_id: dict[uuid.UUID, SearchResult] = {}

        for file in self._files.search_for_organization(organization_id, query_text, limit=limit):
            results_by_file_id[file.id] = SearchResult(
                file=file, score=_METADATA_SCORE, retrieval_method="metadata"
            )

        for file, score in self._semantic_matches(query_text, organization_id=organization_id):
            existing = results_by_file_id.get(file.id)
            if existing is None:
                results_by_file_id[file.id] = SearchResult(
                    file=file, score=score, retrieval_method="semantic"
                )
            else:
                results_by_file_id[file.id] = SearchResult(
                    file=file, score=max(existing.score, score), retrieval_method="both"
                )

        results = sorted(results_by_file_id.values(), key=lambda r: r.score, reverse=True)[:limit]

        self._search_sessions.record(
            organization_id=organization_id,
            user_id=user_id,
            query_text=query_text,
            result_count=len(results),
        )
        self._db.commit()
        return results

    def _semantic_matches(
        self, query_text: str, *, organization_id: uuid.UUID
    ) -> list[tuple[File, float]]:
        rows = self._embeddings.list_for_organization(organization_id)
        if not rows:
            return []

        [query_embedding] = self._ai_gateway.embed([query_text])
        candidate_vectors = [embedding.vector for _, embedding in rows]
        scores = rank_by_similarity(query_embedding.vector, candidate_vectors)

        candidate_files = [file for file, _ in rows]
        ranked = sorted(
            zip(scores, candidate_files, strict=True), reverse=True, key=lambda pair: pair[0]
        )
        return [
            (file, score)
            for score, file in ranked[:_MAX_SEMANTIC_CANDIDATES]
            if score >= _SEMANTIC_SCORE_THRESHOLD
        ]
