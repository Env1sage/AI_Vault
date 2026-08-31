/** Mirrors apps/backend's storage endpoints
 * (app/presentation/api/v1/schemas.py's Storage* response classes). */

export interface StorageFile {
  id: string;
  name: string;
  path: string;
  mime_type: string | null;
  size_bytes: number | null;
  provider_modified_at: string | null;
  provider_viewed_at: string | null;
  storage_source_id: string;
}

export interface StorageFileListResponse {
  items: StorageFile[];
  total: number;
}

export interface DuplicateGroup {
  id: string;
  checksum: string;
  file_count: number;
  total_size_bytes: number;
  recoverable_size_bytes: number;
  recommended_keep_file_id: string | null;
  recommended_keep_reason: string | null;
  recommended_keep_confidence: number | null;
  created_at: string;
  updated_at: string;
}

export interface DuplicateGroupListResponse {
  items: DuplicateGroup[];
  total: number;
}

export interface DuplicateGroupMember {
  file: StorageFile;
  is_recommended_keep: boolean;
}

export interface DuplicateGroupDetail extends DuplicateGroup {
  members: DuplicateGroupMember[];
}

export type StorageAnalysisJobTrigger = "scan_completed" | "manual";
export type StorageAnalysisJobStatus = "pending" | "running" | "completed" | "failed";

export interface StorageAnalysisJob {
  id: string;
  organization_id: string;
  triggered_by: StorageAnalysisJobTrigger;
  status: StorageAnalysisJobStatus;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface StorageOverview {
  total_size_bytes: number | null;
  total_files: number | null;
  total_folders: number | null;
  duplicate_group_count: number | null;
  duplicate_file_count: number | null;
  duplicate_recoverable_bytes: number | null;
  large_file_count: number | null;
  large_file_bytes: number | null;
  old_file_count: number | null;
  old_file_bytes: number | null;
  inactive_file_count: number | null;
  inactive_file_bytes: number | null;
  temporary_candidate_count: number | null;
  temporary_candidate_bytes: number | null;
  total_potential_savings_bytes: number | null;
  last_analyzed_at: string | null;
  last_analysis_status: StorageAnalysisJobStatus | null;
}

export interface StorageSourceBreakdown {
  name: string;
  bytes: number;
}

export interface StorageStatistics {
  breakdown_by_type_bytes: Record<string, number>;
  breakdown_by_size_bucket_bytes: Record<string, number>;
  breakdown_by_source_bytes: Record<string, StorageSourceBreakdown>;
  computed_at: string | null;
}
