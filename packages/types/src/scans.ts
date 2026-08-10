/** Mirrors apps/backend's scan endpoints
 * (app/presentation/api/v1/schemas.py's ScanJobResponse/ScanProgressResponse). */
export interface ScanProgress {
  sources_discovered: number;
  sources_completed: number;
  folders_discovered: number;
  files_discovered: number;
  current_source_name: string | null;
  updated_at: string;
}

export type ScanType = "full" | "incremental";

export type ScanStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

export interface ScanJob {
  id: string;
  connector_id: string;
  scan_type: ScanType;
  status: ScanStatus;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  progress: ScanProgress | null;
}

export interface StartScanRequest {
  scan_type?: ScanType;
}
