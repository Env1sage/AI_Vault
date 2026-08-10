/** Mirrors apps/backend's enrichment endpoints
 * (app/presentation/api/v1/schemas.py's EnrichmentJobResponse/EnrichmentProgressResponse). */
export interface EnrichmentProgress {
  files_pending: number;
  files_processed: number;
  files_failed: number;
  current_file_name: string | null;
  updated_at: string;
}

export type EnrichmentTrigger = "scan_completed" | "manual";

export type EnrichmentJobStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

export interface EnrichmentJob {
  id: string;
  connector_id: string;
  triggered_by: EnrichmentTrigger;
  status: EnrichmentJobStatus;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  progress: EnrichmentProgress | null;
}
