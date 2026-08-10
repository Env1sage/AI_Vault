from datetime import datetime

from pydantic import BaseModel, Field

from app.application.conversation_service import AssistantTurn, ConversationDetail
from app.application.dashboard_service import DashboardOverview
from app.application.execution_job_service import ExecutionJobDetail
from app.application.execution_plan_service import ExecutionPlanDetail
from app.application.file_service import FileDetail
from app.application.search_service import SearchResult
from app.application.workflow_execution_service import WorkflowExecutionDetail
from app.application.workflow_service import WorkflowDetail
from vault_shared.db.models import (
    ApprovalRequest,
    AutomationTemplate,
    Citation,
    Conversation,
    ConversationMessage,
    DashboardSnapshot,
    EmbeddingJob,
    EmbeddingProgress,
    EnrichmentJob,
    EnrichmentProgress,
    ExecutionJob,
    ExecutionPlan,
    ExecutionResult,
    ExecutionStep,
    File,
    FileClassification,
    FileExtraction,
    FileMetadata,
    InsightRecord,
    KnowledgeAttribute,
    Notification,
    Organization,
    Recommendation,
    RecommendationJob,
    ScanJob,
    ScanProgress,
    StorageConnector,
    User,
    Workflow,
    WorkflowExecution,
    WorkflowNode,
    WorkflowNodeExecution,
    WorkflowPolicy,
    WorkflowTrigger,
    WorkflowVersion,
)


class UserProfileResponse(BaseModel):
    id: str
    email: str
    name: str
    avatar_url: str | None
    role: str
    organization_id: str
    created_at: datetime
    last_login_at: datetime | None

    @classmethod
    def from_model(cls, user: User) -> "UserProfileResponse":
        return cls(
            id=str(user.id),
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            role=user.role.name,
            organization_id=str(user.organization_id),
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, organization: Organization) -> "OrganizationResponse":
        return cls(
            id=str(organization.id),
            name=organization.name,
            slug=organization.slug,
            created_at=organization.created_at,
            updated_at=organization.updated_at,
        )


class OrganizationUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=1)


class SessionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserProfileResponse


class ConnectorResponse(BaseModel):
    """Never includes token values — Phase 3 spec's "never expose refresh
    tokens" — those live only in ConnectorCredentials, which has no
    response schema of its own."""

    id: str
    provider: str
    status: str
    account_email: str | None
    workspace_domain: str | None
    last_verified_at: datetime | None
    last_failed_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, connector: StorageConnector) -> "ConnectorResponse":
        return cls(
            id=str(connector.id),
            provider=connector.provider,
            status=connector.status,
            account_email=connector.account_email,
            workspace_domain=connector.workspace_domain,
            last_verified_at=connector.last_verified_at,
            last_failed_at=connector.last_failed_at,
            last_error=connector.last_error,
            created_at=connector.created_at,
            updated_at=connector.updated_at,
        )


class InitiateConnectResponse(BaseModel):
    authorize_url: str


class CompleteConnectRequest(BaseModel):
    code: str = Field(min_length=1)
    state: str = Field(min_length=1)


class ScanProgressResponse(BaseModel):
    sources_discovered: int
    sources_completed: int
    folders_discovered: int
    files_discovered: int
    current_source_name: str | None
    updated_at: datetime

    @classmethod
    def from_model(cls, progress: ScanProgress) -> "ScanProgressResponse":
        return cls(
            sources_discovered=progress.sources_discovered,
            sources_completed=progress.sources_completed,
            folders_discovered=progress.folders_discovered,
            files_discovered=progress.files_discovered,
            current_source_name=progress.current_source_name,
            updated_at=progress.updated_at,
        )


class ScanJobResponse(BaseModel):
    id: str
    connector_id: str
    scan_type: str
    status: str
    error: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    progress: ScanProgressResponse | None = None

    @classmethod
    def from_model(cls, job: ScanJob, *, progress: ScanProgress | None = None) -> "ScanJobResponse":
        return cls(
            id=str(job.id),
            connector_id=str(job.connector_id),
            scan_type=job.scan_type,
            status=job.status,
            error=job.error,
            started_at=job.started_at,
            completed_at=job.completed_at,
            created_at=job.created_at,
            progress=ScanProgressResponse.from_model(progress) if progress else None,
        )


class StartScanRequest(BaseModel):
    scan_type: str = Field(default="full", pattern="^(full|incremental)$")


class FileSummaryResponse(BaseModel):
    id: str
    name: str
    path: str
    mime_type: str | None
    size_bytes: int | None
    is_shared: bool
    owner_email: str | None
    provider_modified_at: datetime | None

    @classmethod
    def from_model(cls, file: File) -> "FileSummaryResponse":
        return cls(
            id=str(file.id),
            name=file.name,
            path=file.path,
            mime_type=file.mime_type,
            size_bytes=file.size_bytes,
            is_shared=file.is_shared,
            owner_email=file.owner_email,
            provider_modified_at=file.provider_modified_at,
        )


class FileListResponse(BaseModel):
    items: list[FileSummaryResponse]
    total: int


class FileMetadataResponse(BaseModel):
    normalized_extension: str | None
    mime_type_validated: bool
    mime_mismatch_reason: str | None
    naming_pattern: str | None
    version_label: str | None
    owner_summary: str | None
    sharing_summary: str | None
    duplicate_group_key: str | None
    language: str | None
    enriched_at: datetime

    @classmethod
    def from_model(cls, metadata: FileMetadata) -> "FileMetadataResponse":
        return cls(
            normalized_extension=metadata.normalized_extension,
            mime_type_validated=metadata.mime_type_validated,
            mime_mismatch_reason=metadata.mime_mismatch_reason,
            naming_pattern=metadata.naming_pattern,
            version_label=metadata.version_label,
            owner_summary=metadata.owner_summary,
            sharing_summary=metadata.sharing_summary,
            duplicate_group_key=metadata.duplicate_group_key,
            language=metadata.language,
            enriched_at=metadata.enriched_at,
        )


class FileClassificationResponse(BaseModel):
    document_type: str
    confidence: float
    method: str
    classified_at: datetime

    @classmethod
    def from_model(cls, classification: FileClassification) -> "FileClassificationResponse":
        return cls(
            document_type=classification.document_type,
            confidence=classification.confidence,
            method=classification.method,
            classified_at=classification.classified_at,
        )


class FileExtractionResponse(BaseModel):
    """Never includes the extracted text itself — only its status/size —
    to keep the file-detail payload small; the text exists to feed a future
    Embedding Engine (Phase 5 spec's Search Preparation), not to be
    rendered directly in this phase's UI."""

    status: str
    extractor_name: str | None
    char_count: int | None
    error: str | None
    extracted_at: datetime

    @classmethod
    def from_model(cls, extraction: FileExtraction) -> "FileExtractionResponse":
        return cls(
            status=extraction.status,
            extractor_name=extraction.extractor_name,
            char_count=extraction.char_count,
            error=extraction.error,
            extracted_at=extraction.extracted_at,
        )


class KnowledgeAttributeResponse(BaseModel):
    attribute_type: str
    value: str
    confidence: float
    source: str

    @classmethod
    def from_model(cls, attribute: KnowledgeAttribute) -> "KnowledgeAttributeResponse":
        return cls(
            attribute_type=attribute.attribute_type,
            value=attribute.value,
            confidence=attribute.confidence,
            source=attribute.source,
        )


class RelatedFileResponse(BaseModel):
    file_id: str
    name: str
    path: str
    relationship_type: str
    confidence: float
    metadata: dict


class FileDetailResponse(BaseModel):
    id: str
    name: str
    path: str
    mime_type: str | None
    size_bytes: int | None
    is_shared: bool
    owner_email: str | None
    provider_modified_at: datetime | None
    metadata: FileMetadataResponse | None
    classification: FileClassificationResponse | None
    extraction: FileExtractionResponse | None
    knowledge_attributes: list[KnowledgeAttributeResponse]
    related_files: list[RelatedFileResponse]

    @classmethod
    def from_detail(cls, detail: FileDetail) -> "FileDetailResponse":
        file = detail.file
        return cls(
            id=str(file.id),
            name=file.name,
            path=file.path,
            mime_type=file.mime_type,
            size_bytes=file.size_bytes,
            is_shared=file.is_shared,
            owner_email=file.owner_email,
            provider_modified_at=file.provider_modified_at,
            metadata=FileMetadataResponse.from_model(detail.metadata) if detail.metadata else None,
            classification=(
                FileClassificationResponse.from_model(detail.classification)
                if detail.classification
                else None
            ),
            extraction=(
                FileExtractionResponse.from_model(detail.extraction) if detail.extraction else None
            ),
            knowledge_attributes=[
                KnowledgeAttributeResponse.from_model(attribute)
                for attribute in detail.knowledge_attributes
            ],
            related_files=[
                RelatedFileResponse(
                    file_id=str(related.file.id),
                    name=related.file.name,
                    path=related.file.path,
                    relationship_type=related.relationship.relationship_type,
                    confidence=related.relationship.confidence,
                    metadata=related.relationship.metadata_,
                )
                for related in detail.related_files
            ],
        )


class EnrichmentProgressResponse(BaseModel):
    files_pending: int
    files_processed: int
    files_failed: int
    current_file_name: str | None
    updated_at: datetime

    @classmethod
    def from_model(cls, progress: EnrichmentProgress) -> "EnrichmentProgressResponse":
        return cls(
            files_pending=progress.files_pending,
            files_processed=progress.files_processed,
            files_failed=progress.files_failed,
            current_file_name=progress.current_file_name,
            updated_at=progress.updated_at,
        )


class EnrichmentJobResponse(BaseModel):
    id: str
    connector_id: str
    triggered_by: str
    status: str
    error: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    progress: EnrichmentProgressResponse | None = None

    @classmethod
    def from_model(
        cls, job: EnrichmentJob, *, progress: EnrichmentProgress | None = None
    ) -> "EnrichmentJobResponse":
        return cls(
            id=str(job.id),
            connector_id=str(job.connector_id),
            triggered_by=job.triggered_by,
            status=job.status,
            error=job.error,
            started_at=job.started_at,
            completed_at=job.completed_at,
            created_at=job.created_at,
            progress=EnrichmentProgressResponse.from_model(progress) if progress else None,
        )


class EmbeddingProgressResponse(BaseModel):
    files_pending: int
    files_processed: int
    files_failed: int
    current_file_name: str | None
    updated_at: datetime

    @classmethod
    def from_model(cls, progress: EmbeddingProgress) -> "EmbeddingProgressResponse":
        return cls(
            files_pending=progress.files_pending,
            files_processed=progress.files_processed,
            files_failed=progress.files_failed,
            current_file_name=progress.current_file_name,
            updated_at=progress.updated_at,
        )


class EmbeddingJobResponse(BaseModel):
    id: str
    connector_id: str
    triggered_by: str
    status: str
    error: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    progress: EmbeddingProgressResponse | None = None

    @classmethod
    def from_model(
        cls, job: EmbeddingJob, *, progress: EmbeddingProgress | None = None
    ) -> "EmbeddingJobResponse":
        return cls(
            id=str(job.id),
            connector_id=str(job.connector_id),
            triggered_by=job.triggered_by,
            status=job.status,
            error=job.error,
            started_at=job.started_at,
            completed_at=job.completed_at,
            created_at=job.created_at,
            progress=EmbeddingProgressResponse.from_model(progress) if progress else None,
        )


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1024)


class SearchResultResponse(BaseModel):
    file_id: str
    name: str
    path: str
    mime_type: str | None
    score: float
    retrieval_method: str

    @classmethod
    def from_result(cls, result: SearchResult) -> "SearchResultResponse":
        return cls(
            file_id=str(result.file.id),
            name=result.file.name,
            path=result.file.path,
            mime_type=result.file.mime_type,
            score=result.score,
            retrieval_method=result.retrieval_method,
        )


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultResponse]


class CitationResponse(BaseModel):
    id: str
    file_id: str
    snippet: str | None
    confidence: float
    retrieval_method: str

    @classmethod
    def from_model(cls, citation: Citation) -> "CitationResponse":
        return cls(
            id=str(citation.id),
            file_id=str(citation.file_id),
            snippet=citation.snippet,
            confidence=citation.confidence,
            retrieval_method=citation.retrieval_method,
        )


class ConversationMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    retrieval_method: str | None
    provider: str | None
    token_usage: int | None
    created_at: datetime
    citations: list[CitationResponse] = []

    @classmethod
    def from_model(
        cls, message: ConversationMessage, *, citations: list[Citation] | None = None
    ) -> "ConversationMessageResponse":
        return cls(
            id=str(message.id),
            role=message.role,
            content=message.content,
            retrieval_method=message.retrieval_method,
            provider=message.provider,
            token_usage=message.token_usage,
            created_at=message.created_at,
            citations=[CitationResponse.from_model(c) for c in citations or []],
        )


class ConversationResponse(BaseModel):
    id: str
    title: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, conversation: Conversation) -> "ConversationResponse":
        return cls(
            id=str(conversation.id),
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )


class ConversationDetailResponse(ConversationResponse):
    messages: list[ConversationMessageResponse]

    @classmethod
    def from_detail(cls, detail: ConversationDetail) -> "ConversationDetailResponse":
        return cls(
            id=str(detail.conversation.id),
            title=detail.conversation.title,
            created_at=detail.conversation.created_at,
            updated_at=detail.conversation.updated_at,
            messages=[
                ConversationMessageResponse.from_model(
                    message, citations=detail.citations_by_message_id.get(message.id)
                )
                for message in detail.messages
            ],
        )


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4096)


class AskResponse(BaseModel):
    conversation: ConversationResponse
    user_message: ConversationMessageResponse
    assistant_message: ConversationMessageResponse

    @classmethod
    def from_turn(cls, turn: AssistantTurn) -> "AskResponse":
        return cls(
            conversation=ConversationResponse.from_model(turn.conversation),
            user_message=ConversationMessageResponse.from_model(turn.user_message),
            assistant_message=ConversationMessageResponse.from_model(
                turn.assistant_message, citations=turn.citations
            ),
        )


class DashboardSnapshotResponse(BaseModel):
    connected_providers: int
    total_files: int
    total_folders: int
    total_storage_bytes: int
    classified_files: int
    unclassified_files: int
    pending_enrichment_files: int
    embedded_files: int
    relationship_count: int
    active_recommendations: int
    knowledge_completeness_score: float
    created_at: datetime

    @classmethod
    def from_model(cls, snapshot: DashboardSnapshot) -> "DashboardSnapshotResponse":
        return cls(
            connected_providers=snapshot.connected_providers,
            total_files=snapshot.total_files,
            total_folders=snapshot.total_folders,
            total_storage_bytes=snapshot.total_storage_bytes,
            classified_files=snapshot.classified_files,
            unclassified_files=snapshot.unclassified_files,
            pending_enrichment_files=snapshot.pending_enrichment_files,
            embedded_files=snapshot.embedded_files,
            relationship_count=snapshot.relationship_count,
            active_recommendations=snapshot.active_recommendations,
            knowledge_completeness_score=snapshot.knowledge_completeness_score,
            created_at=snapshot.created_at,
        )


class InsightRecordResponse(BaseModel):
    id: str
    insight_type: str
    title: str
    description: str
    confidence: float
    related_file_ids: list[str]
    created_at: datetime

    @classmethod
    def from_model(cls, insight: InsightRecord) -> "InsightRecordResponse":
        return cls(
            id=str(insight.id),
            insight_type=insight.insight_type,
            title=insight.title,
            description=insight.description,
            confidence=insight.confidence,
            related_file_ids=insight.related_file_ids,
            created_at=insight.created_at,
        )


class DashboardResponse(BaseModel):
    connector_count: int
    latest_snapshot: DashboardSnapshotResponse | None
    snapshot_history: list[DashboardSnapshotResponse]
    recent_insights: list[InsightRecordResponse]
    recent_activity: list[FileSummaryResponse]
    latest_scan_status: str | None
    latest_enrichment_status: str | None
    latest_embedding_status: str | None
    latest_recommendation_status: str | None

    @classmethod
    def from_overview(cls, overview: DashboardOverview) -> "DashboardResponse":
        return cls(
            connector_count=len(overview.connectors),
            latest_snapshot=(
                DashboardSnapshotResponse.from_model(overview.latest_snapshot)
                if overview.latest_snapshot
                else None
            ),
            snapshot_history=[
                DashboardSnapshotResponse.from_model(snapshot)
                for snapshot in overview.snapshot_history
            ],
            recent_insights=[
                InsightRecordResponse.from_model(insight) for insight in overview.recent_insights
            ],
            recent_activity=[
                FileSummaryResponse.from_model(file) for file in overview.recent_activity
            ],
            latest_scan_status=overview.latest_scan_status,
            latest_enrichment_status=overview.latest_enrichment_status,
            latest_embedding_status=overview.latest_embedding_status,
            latest_recommendation_status=overview.latest_recommendation_status,
        )


class RecommendationResponse(BaseModel):
    id: str
    category: str
    rule_name: str
    title: str
    description: str
    confidence: float
    estimated_impact: str
    impact_value: float | None
    risk_level: str
    suggested_action: str
    requires_approval: bool
    related_departments: list[str]
    affected_file_ids: list[str]
    status: str
    priority_score: float
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None

    @classmethod
    def from_model(cls, recommendation: Recommendation) -> "RecommendationResponse":
        return cls(
            id=str(recommendation.id),
            category=recommendation.category,
            rule_name=recommendation.rule_name,
            title=recommendation.title,
            description=recommendation.description,
            confidence=recommendation.confidence,
            estimated_impact=recommendation.estimated_impact,
            impact_value=recommendation.impact_value,
            risk_level=recommendation.risk_level,
            suggested_action=recommendation.suggested_action,
            requires_approval=recommendation.requires_approval,
            related_departments=recommendation.related_departments,
            affected_file_ids=recommendation.affected_file_ids,
            status=recommendation.status,
            priority_score=recommendation.priority_score,
            created_at=recommendation.created_at,
            updated_at=recommendation.updated_at,
            resolved_at=recommendation.resolved_at,
        )


class RecommendationListResponse(BaseModel):
    items: list[RecommendationResponse]


class RecommendationJobResponse(BaseModel):
    id: str
    organization_id: str
    triggered_by: str
    status: str
    error: str | None
    recommendations_active: int | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    @classmethod
    def from_model(cls, job: RecommendationJob) -> "RecommendationJobResponse":
        return cls(
            id=str(job.id),
            organization_id=str(job.organization_id),
            triggered_by=job.triggered_by,
            status=job.status,
            error=job.error,
            recommendations_active=job.recommendations_active,
            started_at=job.started_at,
            completed_at=job.completed_at,
            created_at=job.created_at,
        )


class ExecutionStepResponse(BaseModel):
    id: str
    step_order: int
    action_type: str
    target_file_id: str
    pre_state: dict
    planned_change: dict
    status: str

    @classmethod
    def from_model(cls, step: ExecutionStep) -> "ExecutionStepResponse":
        return cls(
            id=str(step.id),
            step_order=step.step_order,
            action_type=step.action_type,
            target_file_id=str(step.target_file_id),
            pre_state=step.pre_state,
            planned_change=step.planned_change,
            status=step.status,
        )


class ExecutionPlanResponse(BaseModel):
    id: str
    organization_id: str
    recommendation_id: str
    status: str
    target_provider: str
    estimated_impact: str
    estimated_storage_savings_bytes: int | None
    risk_level: str
    rollback_available: bool
    required_permissions: list[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, plan: ExecutionPlan) -> "ExecutionPlanResponse":
        return cls(
            id=str(plan.id),
            organization_id=str(plan.organization_id),
            recommendation_id=str(plan.recommendation_id),
            status=plan.status,
            target_provider=plan.target_provider,
            estimated_impact=plan.estimated_impact,
            estimated_storage_savings_bytes=plan.estimated_storage_savings_bytes,
            risk_level=plan.risk_level,
            rollback_available=plan.rollback_available,
            required_permissions=plan.required_permissions,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
        )


class ExecutionPlanDetailResponse(ExecutionPlanResponse):
    steps: list[ExecutionStepResponse]

    @classmethod
    def from_detail(cls, detail: ExecutionPlanDetail) -> "ExecutionPlanDetailResponse":
        base = ExecutionPlanResponse.from_model(detail.plan)
        return cls(
            **base.model_dump(),
            steps=[ExecutionStepResponse.from_model(step) for step in detail.steps],
        )


class CreateExecutionPlanRequest(BaseModel):
    recommendation_id: str


class ApprovalRequestResponse(BaseModel):
    id: str
    execution_plan_id: str
    organization_id: str
    status: str
    expires_at: datetime
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, request: ApprovalRequest) -> "ApprovalRequestResponse":
        return cls(
            id=str(request.id),
            execution_plan_id=str(request.execution_plan_id),
            organization_id=str(request.organization_id),
            status=request.status,
            expires_at=request.expires_at,
            created_at=request.created_at,
            updated_at=request.updated_at,
        )


class ApprovalDecisionRequest(BaseModel):
    decision: str = Field(pattern="^(approve|reject|request_changes)$")
    comments: str | None = Field(default=None, max_length=4096)


class BulkApprovalDecisionRequest(BaseModel):
    approval_request_ids: list[str] = Field(min_length=1, max_length=100)
    decision: str = Field(pattern="^(approve|reject|request_changes)$")
    comments: str | None = Field(default=None, max_length=4096)


class ExecutionJobResponse(BaseModel):
    id: str
    execution_plan_id: str
    organization_id: str
    status: str
    is_rollback: bool
    error: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    @classmethod
    def from_model(cls, job: ExecutionJob) -> "ExecutionJobResponse":
        return cls(
            id=str(job.id),
            execution_plan_id=str(job.execution_plan_id),
            organization_id=str(job.organization_id),
            status=job.status,
            is_rollback=job.is_rollback,
            error=job.error,
            started_at=job.started_at,
            completed_at=job.completed_at,
            created_at=job.created_at,
        )


class ExecutionResultResponse(BaseModel):
    id: str
    execution_step_id: str
    status: str
    verification_status: str
    error: str | None
    executed_at: datetime
    verified_at: datetime | None

    @classmethod
    def from_model(cls, result: ExecutionResult) -> "ExecutionResultResponse":
        return cls(
            id=str(result.id),
            execution_step_id=str(result.execution_step_id),
            status=result.status,
            verification_status=result.verification_status,
            error=result.error,
            executed_at=result.executed_at,
            verified_at=result.verified_at,
        )


class ExecutionJobDetailResponse(ExecutionJobResponse):
    results: list[ExecutionResultResponse]

    @classmethod
    def from_detail(cls, detail: ExecutionJobDetail) -> "ExecutionJobDetailResponse":
        base = ExecutionJobResponse.from_model(detail.job)
        return cls(
            **base.model_dump(),
            results=[ExecutionResultResponse.from_model(result) for result in detail.results],
        )


# ---------------------------------------------------------------------------
# Phase 9 — Automation Engine (ADR-021)
# ---------------------------------------------------------------------------


class WorkflowResponse(BaseModel):
    id: str
    organization_id: str
    created_by_user_id: str
    name: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, workflow: Workflow) -> "WorkflowResponse":
        return cls(
            id=str(workflow.id),
            organization_id=str(workflow.organization_id),
            created_by_user_id=str(workflow.created_by_user_id),
            name=workflow.name,
            description=workflow.description,
            status=workflow.status,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
        )


class WorkflowVersionResponse(BaseModel):
    id: str
    workflow_id: str
    version_number: int
    status: str
    published_at: datetime | None
    created_at: datetime

    @classmethod
    def from_model(cls, version: WorkflowVersion) -> "WorkflowVersionResponse":
        return cls(
            id=str(version.id),
            workflow_id=str(version.workflow_id),
            version_number=version.version_number,
            status=version.status,
            published_at=version.published_at,
            created_at=version.created_at,
        )


class WorkflowNodeResponse(BaseModel):
    id: str
    node_type: str
    name: str
    config: dict
    next_nodes: dict
    position_x: int
    position_y: int

    @classmethod
    def from_model(cls, node: WorkflowNode) -> "WorkflowNodeResponse":
        return cls(
            id=str(node.id),
            node_type=node.node_type,
            name=node.name,
            config=node.config,
            next_nodes=node.next_nodes,
            position_x=node.position_x,
            position_y=node.position_y,
        )


class WorkflowDetailResponse(WorkflowResponse):
    published_version: WorkflowVersionResponse | None
    draft_version: WorkflowVersionResponse | None

    @classmethod
    def from_detail(cls, detail: WorkflowDetail) -> "WorkflowDetailResponse":
        base = WorkflowResponse.from_model(detail.workflow)
        return cls(
            **base.model_dump(),
            published_version=(
                WorkflowVersionResponse.from_model(detail.published_version)
                if detail.published_version
                else None
            ),
            draft_version=(
                WorkflowVersionResponse.from_model(detail.draft_version)
                if detail.draft_version
                else None
            ),
        )


class CreateWorkflowRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4096)


class SetWorkflowStatusRequest(BaseModel):
    status: str = Field(pattern="^(active|paused|disabled)$")


class WorkflowNodeInput(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    node_type: str
    name: str = Field(min_length=1, max_length=255)
    config: dict = Field(default_factory=dict)
    next_nodes: dict[str, str] = Field(default_factory=dict)
    position_x: int = 0
    position_y: int = 0


class ReplaceWorkflowNodesRequest(BaseModel):
    nodes: list[WorkflowNodeInput] = Field(min_length=1, max_length=200)


class WorkflowDraftResponse(BaseModel):
    version: WorkflowVersionResponse
    nodes: list[WorkflowNodeResponse]


class WorkflowTriggerResponse(BaseModel):
    id: str
    workflow_id: str
    trigger_type: str
    config: dict
    enabled: bool
    created_at: datetime

    @classmethod
    def from_model(cls, trigger: WorkflowTrigger) -> "WorkflowTriggerResponse":
        return cls(
            id=str(trigger.id),
            workflow_id=str(trigger.workflow_id),
            trigger_type=trigger.trigger_type,
            config=trigger.config,
            enabled=trigger.enabled,
            created_at=trigger.created_at,
        )


class CreateWorkflowTriggerRequest(BaseModel):
    trigger_type: str = Field(pattern="^(scheduled|event|manual)$")
    config: dict = Field(default_factory=dict)


class SetWorkflowTriggerEnabledRequest(BaseModel):
    enabled: bool


class WorkflowNodeExecutionResponse(BaseModel):
    id: str
    workflow_node_id: str
    status: str
    output_context: dict
    error: str | None
    started_at: datetime | None
    completed_at: datetime | None

    @classmethod
    def from_model(cls, node_execution: WorkflowNodeExecution) -> "WorkflowNodeExecutionResponse":
        return cls(
            id=str(node_execution.id),
            workflow_node_id=str(node_execution.workflow_node_id),
            status=node_execution.status,
            output_context=node_execution.output_context,
            error=node_execution.error,
            started_at=node_execution.started_at,
            completed_at=node_execution.completed_at,
        )


class WorkflowExecutionResponse(BaseModel):
    id: str
    workflow_id: str
    workflow_version_id: str
    organization_id: str
    status: str
    trigger_type: str
    current_node_id: str | None
    error: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    @classmethod
    def from_model(cls, execution: WorkflowExecution) -> "WorkflowExecutionResponse":
        return cls(
            id=str(execution.id),
            workflow_id=str(execution.workflow_id),
            workflow_version_id=str(execution.workflow_version_id),
            organization_id=str(execution.organization_id),
            status=execution.status,
            trigger_type=execution.trigger_type,
            current_node_id=str(execution.current_node_id) if execution.current_node_id else None,
            error=execution.error,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            created_at=execution.created_at,
        )


class WorkflowExecutionDetailResponse(WorkflowExecutionResponse):
    node_executions: list[WorkflowNodeExecutionResponse]

    @classmethod
    def from_detail(cls, detail: WorkflowExecutionDetail) -> "WorkflowExecutionDetailResponse":
        base = WorkflowExecutionResponse.from_model(detail.execution)
        return cls(
            **base.model_dump(),
            node_executions=[
                WorkflowNodeExecutionResponse.from_model(ne) for ne in detail.node_executions
            ],
        )


class WorkflowPolicyResponse(BaseModel):
    id: str
    organization_id: str
    policy_key: str
    version: int
    name: str
    description: str | None
    status: str
    effect: str
    conditions: dict
    published_at: datetime | None
    created_at: datetime

    @classmethod
    def from_model(cls, policy: WorkflowPolicy) -> "WorkflowPolicyResponse":
        return cls(
            id=str(policy.id),
            organization_id=str(policy.organization_id),
            policy_key=policy.policy_key,
            version=policy.version,
            name=policy.name,
            description=policy.description,
            status=policy.status,
            effect=policy.effect,
            conditions=policy.conditions,
            published_at=policy.published_at,
            created_at=policy.created_at,
        )


class CreateWorkflowPolicyRequest(BaseModel):
    policy_key: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4096)
    effect: str = Field(pattern="^(auto_execute|require_approval|skip)$")
    conditions: dict = Field(default_factory=dict)


class NotificationResponse(BaseModel):
    id: str
    workflow_execution_id: str | None
    channel: str
    subject: str
    body: str
    status: str
    sent_at: datetime | None
    created_at: datetime

    @classmethod
    def from_model(cls, notification: Notification) -> "NotificationResponse":
        return cls(
            id=str(notification.id),
            workflow_execution_id=(
                str(notification.workflow_execution_id)
                if notification.workflow_execution_id
                else None
            ),
            channel=notification.channel,
            subject=notification.subject,
            body=notification.body,
            status=notification.status,
            sent_at=notification.sent_at,
            created_at=notification.created_at,
        )


class AutomationTemplateResponse(BaseModel):
    id: str
    name: str
    description: str | None
    category: str
    node_definitions: list

    @classmethod
    def from_model(cls, template: AutomationTemplate) -> "AutomationTemplateResponse":
        return cls(
            id=str(template.id),
            name=template.name,
            description=template.description,
            category=template.category,
            node_definitions=template.node_definitions,
        )


class ApplyAutomationTemplateRequest(BaseModel):
    workflow_name: str | None = Field(default=None, max_length=255)
