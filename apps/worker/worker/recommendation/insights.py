import statistics
from collections import defaultdict
from typing import Protocol

from worker.recommendation.context import InsightResult, RuleContext

_MIN_RELATIONSHIP_EDGES_FOR_HUB = 2
_MAX_HUB_DOCUMENTS = 5
_MIN_GROUP_SIZE_FOR_ANOMALY_CHECK = 5
_ANOMALY_SIZE_MULTIPLE = 5
_MAX_ANOMALIES_REPORTED = 10


class InsightGenerator(Protocol):
    insight_type: str

    def evaluate(self, context: RuleContext) -> InsightResult | None: ...


class HighConnectivityDocumentsInsight:
    """Files with the most discovered relationship edges (version chains,
    duplicate candidates, shared-ownership groups) — a proxy for "these
    documents seem foundational or frequently referenced" (Phase 7 spec's
    "high-value documents" / "frequently reused assets"), read entirely
    off Phase 5's already-discovered `FileRelationship` graph rather than
    any new signal."""

    insight_type = "high_connectivity_documents"

    def evaluate(self, context: RuleContext) -> InsightResult | None:
        edge_counts: dict = defaultdict(int)
        for relationship in context.relationships:
            edge_counts[relationship.file_id] += 1
            edge_counts[relationship.related_file_id] += 1

        hubs = sorted(
            (
                (file_id, count)
                for file_id, count in edge_counts.items()
                if count >= _MIN_RELATIONSHIP_EDGES_FOR_HUB
            ),
            key=lambda pair: pair[1],
            reverse=True,
        )[:_MAX_HUB_DOCUMENTS]
        if not hubs:
            return None

        files_by_id = {row.file.id: row.file for row in context.rows}
        names = [files_by_id[file_id].name for file_id, _ in hubs if file_id in files_by_id]
        if not names:
            return None

        return InsightResult(
            title=f"{len(names)} documents are central to your knowledge graph",
            description=(
                "These files participate in the most discovered relationships (versions, "
                "duplicates, or shared ownership) with other files: " + ", ".join(names)
            ),
            confidence=0.5,
            related_file_ids=[str(file_id) for file_id, _ in hubs if file_id in files_by_id],
        )


class FileSizeAnomalyInsight:
    """A file whose size is a statistical outlier relative to its own
    document-type peers — a lightweight, deterministic anomaly signal
    (Phase 7 spec's "knowledge anomalies"), not a content-based check."""

    insight_type = "file_size_anomaly"

    def evaluate(self, context: RuleContext) -> InsightResult | None:
        by_type: dict = defaultdict(list)
        for row in context.rows:
            if row.classification and row.file.size_bytes:
                by_type[row.classification.document_type].append(row)

        anomalies = []
        for rows in by_type.values():
            if len(rows) < _MIN_GROUP_SIZE_FOR_ANOMALY_CHECK:
                continue
            sizes = [row.file.size_bytes for row in rows]
            median_size = statistics.median(sizes)
            if median_size <= 0:
                continue
            for row in rows:
                if row.file.size_bytes > median_size * _ANOMALY_SIZE_MULTIPLE:
                    anomalies.append(row)

        if not anomalies:
            return None

        anomalies = anomalies[:_MAX_ANOMALIES_REPORTED]
        return InsightResult(
            title=f"{len(anomalies)} files are unusually large for their type",
            description=(
                f"{len(anomalies)} files are more than {_ANOMALY_SIZE_MULTIPLE}x the typical "
                "size for other documents of the same classification — worth a look."
            ),
            confidence=0.4,
            related_file_ids=[str(row.file.id) for row in anomalies],
        )


INSIGHTS: list[InsightGenerator] = [
    HighConnectivityDocumentsInsight(),
    FileSizeAnomalyInsight(),
]
