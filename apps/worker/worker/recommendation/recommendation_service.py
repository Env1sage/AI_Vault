import uuid

from sqlalchemy.orm import Session

from vault_shared import get_logger
from vault_shared.db.models import RecommendationJob
from vault_shared.db.repositories import (
    DashboardSnapshotRepository,
    EmbeddingRepository,
    FileRelationshipRepository,
    FileRepository,
    FolderRepository,
    InsightRecordRepository,
    KnowledgeAttributeRepository,
    RecommendationEventRepository,
    RecommendationJobRepository,
    RecommendationRepository,
    StorageConnectorRepository,
)
from worker.recommendation.context import FileRow, RuleContext
from worker.recommendation.insights import INSIGHTS
from worker.recommendation.priority import score_priority
from worker.recommendation.rules import RULES

logger = get_logger("worker.recommendation.recommendation_service")

# Below this many files, per-rule signals (ratios, "who owns the most
# shared files") are too noisy to be meaningful — a brand-new organization
# with a handful of files gets a dashboard snapshot but no recommendations
# yet, rather than confidently-worded noise.
_MIN_FILES_FOR_RULES = 5


class RecommendationService:
    """The Recommendation Engine (Handbook's Founder Command Center &
    Recommendation Engine, Phase 7) — organization-scoped, unlike every
    prior job (`ScanJob`/`EnrichmentJob`/`EmbeddingJob`) which is per-
    connector, since recommendations and the dashboard reason about an
    org's storage as a whole. Runs entirely over already-stored data (no
    external API calls, no per-file I/O) — a single deterministic pass:
    pull the org's data once, evaluate every rule and insight generator
    against it, persist the results, and record one `DashboardSnapshot`.

    100% deterministic in this phase, no `AIGateway` calls — Phase 6's
    completion provider is still a stub (per the founder's explicit
    choice), so there is no real reasoning capability to invoke yet.
    `RecommendationRule`/`InsightGenerator` are still generic Protocols a
    future AI-reasoning-based rule could implement without a redesign —
    see ADR-019."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._connectors = StorageConnectorRepository(db)
        self._files = FileRepository(db)
        self._folders = FolderRepository(db)
        self._relationships = FileRelationshipRepository(db)
        self._embeddings = EmbeddingRepository(db)
        self._knowledge_attributes = KnowledgeAttributeRepository(db)
        self._jobs = RecommendationJobRepository(db)
        self._events = RecommendationEventRepository(db)
        self._recommendations = RecommendationRepository(db)
        self._insights = InsightRecordRepository(db)
        self._snapshots = DashboardSnapshotRepository(db)

    def run(self, recommendation_job_id: uuid.UUID) -> None:
        job = self._jobs.get_by_id(recommendation_job_id)
        if job is None:
            logger.warning(
                "recommendation_job_not_found",
                extra={"recommendation_job_id": str(recommendation_job_id)},
            )
            return

        self._jobs.mark_running(job)
        self._events.record(recommendation_job_id=job.id, event_type="recommendation_started")
        self._db.commit()

        try:
            active_count = self._generate(job)
        except Exception as exc:  # noqa: BLE001 - job execution boundary must never crash the worker
            logger.exception(
                "recommendation_job_failed", extra={"recommendation_job_id": str(job.id)}
            )
            self._db.rollback()
            self._jobs.mark_failed(job, error=str(exc))
            self._events.record(
                recommendation_job_id=job.id, event_type="recommendation_failed", message=str(exc)
            )
            self._db.commit()
            return

        self._jobs.mark_completed(job, recommendations_active=active_count)
        self._events.record(
            recommendation_job_id=job.id,
            event_type="recommendation_completed",
            metadata={"recommendations_active": active_count},
        )
        self._db.commit()

    def _generate(self, job: RecommendationJob) -> int:
        organization_id = job.organization_id
        connectors = self._connectors.list_for_organization(organization_id)
        detail_rows = self._files.list_for_organization_with_details(organization_id)
        relationships = self._relationships.list_for_organization(organization_id)
        embeddings = self._embeddings.list_for_organization(organization_id)
        folder_count = self._folders.count_for_organization(organization_id)

        rows = [
            FileRow(
                file=file,
                metadata=metadata,
                classification=classification,
                workspace_domain=domain,
            )
            for file, metadata, classification, domain in detail_rows
        ]
        context = RuleContext(
            organization_id=organization_id,
            rows=rows,
            relationships=relationships,
            connector_count=len(connectors),
            embedded_file_ids={embedding.file_id for _, embedding in embeddings},
        )

        fired: dict[str, tuple] = {}
        if len(rows) >= _MIN_FILES_FOR_RULES:
            for rule in RULES:
                try:
                    result = rule.evaluate(context)
                except Exception:  # noqa: BLE001 - one rule's bug must not stop the others
                    logger.exception("recommendation_rule_failed", extra={"rule": rule.name})
                    self._events.record(
                        recommendation_job_id=job.id,
                        event_type="rule_failed",
                        metadata={"rule_name": rule.name},
                    )
                    continue
                if result is not None:
                    fired[rule.name] = (rule, result)

        max_impact = max(
            (result.impact_value for _, result in fired.values() if result.impact_value),
            default=0.0,
        )
        for rule, result in fired.values():
            impact_ratio = (
                (result.impact_value / max_impact)
                if max_impact and result.impact_value
                else 0.0
            )
            priority = score_priority(
                category=rule.category,
                confidence=result.confidence,
                risk_level=result.risk_level,
                impact_ratio=impact_ratio,
            )
            departments = self._knowledge_attributes.list_department_values_for_files(
                [uuid.UUID(fid) for fid in result.affected_file_ids]
            )
            self._recommendations.upsert(
                organization_id=organization_id,
                recommendation_job_id=job.id,
                rule_name=rule.name,
                category=rule.category,
                title=result.title,
                description=result.description,
                confidence=result.confidence,
                estimated_impact=result.estimated_impact,
                impact_value=result.impact_value,
                risk_level=result.risk_level,
                suggested_action=result.suggested_action,
                related_departments=departments,
                affected_file_ids=result.affected_file_ids,
                priority_score=priority,
            )
        self._recommendations.resolve_stale(
            organization_id=organization_id, seen_rule_names=set(fired)
        )

        if len(rows) >= _MIN_FILES_FOR_RULES:
            for insight in INSIGHTS:
                try:
                    insight_result = insight.evaluate(context)
                except Exception:  # noqa: BLE001 - one insight's bug must not stop the others
                    logger.exception(
                        "recommendation_insight_failed", extra={"insight": insight.insight_type}
                    )
                    continue
                if insight_result is not None:
                    self._insights.create(
                        organization_id=organization_id,
                        recommendation_job_id=job.id,
                        insight_type=insight.insight_type,
                        title=insight_result.title,
                        description=insight_result.description,
                        confidence=insight_result.confidence,
                        related_file_ids=insight_result.related_file_ids,
                    )

        active_count = self._recommendations.count_active_for_organization(organization_id)
        classified_count = sum(1 for row in rows if row.classification is not None)
        pending_enrichment_count = sum(1 for row in rows if row.metadata is None)
        self._snapshots.create(
            organization_id=organization_id,
            recommendation_job_id=job.id,
            connected_providers=len(connectors),
            total_files=len(rows),
            total_folders=folder_count,
            total_storage_bytes=sum(row.file.size_bytes or 0 for row in rows),
            classified_files=classified_count,
            unclassified_files=len(rows) - classified_count,
            pending_enrichment_files=pending_enrichment_count,
            embedded_files=len(context.embedded_file_ids),
            relationship_count=len(relationships),
            active_recommendations=active_count,
            knowledge_completeness_score=(classified_count / len(rows)) if rows else 0.0,
        )
        self._db.commit()
        return active_count
