/** Mirrors apps/backend's archive endpoints
 * (app/presentation/api/v1/schemas.py's ArchiveJobResponse/ArchiveJobDetailResponse). */
export type ArchiveJobStatus = "pending" | "creating" | "completed" | "failed" | "deleted";

export interface ArchiveManifestEntry {
  file_id: string;
  name: string;
  path: string;
  size_bytes: number;
  mime_type: string | null;
  checksum_sha256: string;
}

export interface ArchiveJob {
  id: string;
  organization_id: string;
  execution_plan_id: string;
  name: string;
  status: ArchiveJobStatus;
  object_storage_key: string | null;
  original_size_bytes: number | null;
  compressed_size_bytes: number | null;
  file_count: number;
  created_by_user_id: string;
  created_at: string;
  completed_at: string | null;
}

export interface ArchiveJobDetail extends ArchiveJob {
  manifest: ArchiveManifestEntry[];
}
