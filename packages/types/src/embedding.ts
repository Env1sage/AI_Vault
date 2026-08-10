/** Mirrors apps/backend's embedding endpoints
 * (app/presentation/api/v1/schemas.py's EmbeddingJobResponse/EmbeddingProgressResponse). */
export interface EmbeddingProgress {
  files_pending: number;
  files_processed: number;
  files_failed: number;
  current_file_name: string | null;
  updated_at: string;
}

export type EmbeddingTrigger = "enrichment_completed" | "manual";

export type EmbeddingJobStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

export interface EmbeddingJob {
  id: string;
  connector_id: string;
  triggered_by: EmbeddingTrigger;
  status: EmbeddingJobStatus;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  progress: EmbeddingProgress | null;
}
