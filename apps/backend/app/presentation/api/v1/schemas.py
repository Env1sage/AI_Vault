from datetime import datetime

from pydantic import BaseModel, Field

from app.application.conversation_service import AssistantTurn, ConversationDetail
from app.application.file_service import FileDetail
from app.application.search_service import SearchResult
from vault_shared.db.models import (
    Citation,
    Conversation,
    ConversationMessage,
    EmbeddingJob,
    EmbeddingProgress,
    EnrichmentJob,
    EnrichmentProgress,
    File,
    FileClassification,
    FileExtraction,
    FileMetadata,
    KnowledgeAttribute,
    Organization,
    ScanJob,
    ScanProgress,
    StorageConnector,
    User,
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


