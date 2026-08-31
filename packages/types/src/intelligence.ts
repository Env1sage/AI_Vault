/** Mirrors apps/backend's intelligence endpoints
 * (app/presentation/api/v1/schemas.py's IntelligenceJobResponse/IntelligenceProgressResponse). */
export interface IntelligenceProgress {
  files_pending: number;
  files_processed: number;
  files_failed: number;
  current_file_name: string | null;
  updated_at: string;
}

export type IntelligenceTrigger = "enrichment_completed" | "manual";

export type IntelligenceJobStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

export interface IntelligenceJob {
  id: string;
  connector_id: string;
  triggered_by: IntelligenceTrigger;
  status: IntelligenceJobStatus;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  progress: IntelligenceProgress | null;
}
