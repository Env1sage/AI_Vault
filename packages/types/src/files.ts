/** Mirrors apps/backend's file endpoints
 * (app/presentation/api/v1/schemas.py's File*Response classes). */
export interface FileSummary {
  id: string;
  name: string;
  path: string;
  mime_type: string | null;
  size_bytes: number | null;
  is_shared: boolean;
  owner_email: string | null;
  provider_modified_at: string | null;
}

export interface FileListResponse {
  items: FileSummary[];
  total: number;
}

export interface FileMetadata {
  normalized_extension: string | null;
  mime_type_validated: boolean;
  mime_mismatch_reason: string | null;
  naming_pattern: string | null;
  version_label: string | null;
  owner_summary: string | null;
  sharing_summary: string | null;
  duplicate_group_key: string | null;
  language: string | null;
  enriched_at: string;
}

export interface FileClassification {
  document_type: string;
  confidence: number;
  method: string;
  classified_at: string;
}

export type FileExtractionStatus = "success" | "failed" | "unsupported" | "skipped_too_large";

export interface FileExtractionInfo {
  status: FileExtractionStatus;
  extractor_name: string | null;
  char_count: number | null;
  error: string | null;
  extracted_at: string;
}

export interface KnowledgeAttribute {
  attribute_type: string;
  value: string;
  confidence: number;
  source: string;
}

export type RelationshipType = "sequential_version" | "duplicate_candidate" | "shared_ownership";

export interface RelatedFile {
  file_id: string;
  name: string;
  path: string;
  relationship_type: RelationshipType;
  confidence: number;
  metadata: Record<string, unknown>;
}

export interface FileDetail {
  id: string;
  name: string;
  path: string;
  mime_type: string | null;
  size_bytes: number | null;
  is_shared: boolean;
  owner_email: string | null;
  provider_modified_at: string | null;
  metadata: FileMetadata | null;
  classification: FileClassification | null;
  extraction: FileExtractionInfo | null;
  knowledge_attributes: KnowledgeAttribute[];
  related_files: RelatedFile[];
}
