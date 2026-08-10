/** Mirrors apps/backend's execution/approval endpoints
 * (app/presentation/api/v1/schemas.py's Execution and Approval response classes). */
export type ExecutionActionType =
  | "move_file"
  | "move_folder"
  | "rename"
  | "archive"
  | "remove_duplicate"
  | "update_metadata";

export type ExecutionStepStatus = "pending" | "completed" | "failed" | "skipped" | "rolled_back";

export interface ExecutionStep {
  id: string;
  step_order: number;
  action_type: ExecutionActionType;
  target_file_id: string;
  pre_state: Record<string, unknown>;
  planned_change: Record<string, unknown>;
  status: ExecutionStepStatus;
}

export type ExecutionPlanStatus =
  | "pending_approval"
  | "approved"
  | "rejected"
  | "changes_requested"
  | "expired"
  | "executing"
  | "completed"
  | "failed"
  | "partially_completed"
  | "rolled_back";

export type ExecutionRiskLevel = "low" | "medium" | "high";

export interface ExecutionPlan {
  id: string;
  organization_id: string;
  recommendation_id: string;
  status: ExecutionPlanStatus;
  target_provider: string;
  estimated_impact: string;
  estimated_storage_savings_bytes: number | null;
  risk_level: ExecutionRiskLevel;
  rollback_available: boolean;
  required_permissions: string[];
  created_at: string;
  updated_at: string;
}

export interface ExecutionPlanDetail extends ExecutionPlan {
  steps: ExecutionStep[];
}

export interface CreateExecutionPlanRequest {
  recommendation_id: string;
}

export type ApprovalStatus = "pending" | "approved" | "rejected" | "changes_requested" | "expired";

export interface ApprovalRequest {
  id: string;
  execution_plan_id: string;
  organization_id: string;
  status: ApprovalStatus;
  expires_at: string;
  created_at: string;
  updated_at: string;
}

export type ApprovalDecisionType = "approve" | "reject" | "request_changes";

export interface ApprovalDecisionRequest {
  decision: ApprovalDecisionType;
  comments?: string;
}

export interface BulkApprovalDecisionRequest {
  approval_request_ids: string[];
  decision: ApprovalDecisionType;
  comments?: string;
}

export type ExecutionJobStatus =
  | "pending"
  | "running"
  | "paused"
  | "completed"
  | "failed"
  | "partially_completed"
  | "cancelled";

export interface ExecutionJob {
  id: string;
  execution_plan_id: string;
  organization_id: string;
  status: ExecutionJobStatus;
  is_rollback: boolean;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export type ExecutionResultStatus = "success" | "failed";
export type VerificationStatus = "verified" | "failed" | "skipped";

export interface ExecutionResult {
  id: string;
  execution_step_id: string;
  status: ExecutionResultStatus;
  verification_status: VerificationStatus;
  error: string | null;
  executed_at: string;
  verified_at: string | null;
}

export interface ExecutionJobDetail extends ExecutionJob {
  results: ExecutionResult[];
}
