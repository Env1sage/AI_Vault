/** Mirrors apps/backend's automation-engine endpoints
 * (app/presentation/api/v1/schemas.py's Workflow/Automation response classes). */
export type WorkflowStatus = "active" | "paused" | "disabled";

export interface Workflow {
  id: string;
  organization_id: string;
  created_by_user_id: string;
  name: string;
  description: string | null;
  status: WorkflowStatus;
  created_at: string;
  updated_at: string;
}

export type WorkflowVersionStatus = "draft" | "published" | "superseded";

export interface WorkflowVersion {
  id: string;
  workflow_id: string;
  version_number: number;
  status: WorkflowVersionStatus;
  published_at: string | null;
  created_at: string;
}

export interface WorkflowDetail extends Workflow {
  published_version: WorkflowVersion | null;
  draft_version: WorkflowVersion | null;
}

export type WorkflowNodeType =
  | "trigger"
  | "condition"
  | "decision"
  | "ai_evaluation"
  | "approval"
  | "execute_action"
  | "delay"
  | "notification"
  | "end";

export interface WorkflowNode {
  id: string;
  node_type: WorkflowNodeType;
  name: string;
  config: Record<string, unknown>;
  next_nodes: Record<string, string>;
  position_x: number;
  position_y: number;
}

export interface WorkflowDraft {
  version: WorkflowVersion;
  nodes: WorkflowNode[];
}

export interface CreateWorkflowRequest {
  name: string;
  description?: string;
}

export interface SetWorkflowStatusRequest {
  status: WorkflowStatus;
}

export interface WorkflowNodeInput {
  key: string;
  node_type: WorkflowNodeType;
  name: string;
  config: Record<string, unknown>;
  next_nodes: Record<string, string>;
  position_x?: number;
  position_y?: number;
}

export interface ReplaceWorkflowNodesRequest {
  nodes: WorkflowNodeInput[];
}

export type WorkflowTriggerType = "scheduled" | "event" | "manual";

export type WorkflowEventType =
  | "scan_completed"
  | "enrichment_completed"
  | "recommendation_generated"
  | "connector_reconnected"
  | "file_added"
  | "file_updated"
  | "storage_threshold_exceeded";

export interface WorkflowTrigger {
  id: string;
  workflow_id: string;
  trigger_type: WorkflowTriggerType;
  config: Record<string, unknown>;
  enabled: boolean;
  created_at: string;
}

export interface CreateWorkflowTriggerRequest {
  trigger_type: WorkflowTriggerType;
  config: Record<string, unknown>;
}

export interface SetWorkflowTriggerEnabledRequest {
  enabled: boolean;
}

export type WorkflowExecutionStatus =
  | "pending"
  | "running"
  | "paused"
  | "completed"
  | "failed"
  | "cancelled";

export interface WorkflowExecution {
  id: string;
  workflow_id: string;
  workflow_version_id: string;
  organization_id: string;
  status: WorkflowExecutionStatus;
  trigger_type: WorkflowTriggerType;
  current_node_id: string | null;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export type WorkflowNodeExecutionStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "skipped"
  | "waiting_approval"
  | "waiting_delay";

export interface WorkflowNodeExecution {
  id: string;
  workflow_node_id: string;
  status: WorkflowNodeExecutionStatus;
  output_context: Record<string, unknown>;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface WorkflowExecutionDetail extends WorkflowExecution {
  node_executions: WorkflowNodeExecution[];
}

export type WorkflowPolicyEffect = "auto_execute" | "require_approval" | "skip";
export type WorkflowPolicyStatus = "draft" | "published" | "archived";

export interface WorkflowPolicy {
  id: string;
  organization_id: string;
  policy_key: string;
  version: number;
  name: string;
  description: string | null;
  status: WorkflowPolicyStatus;
  effect: WorkflowPolicyEffect;
  conditions: Record<string, unknown>;
  published_at: string | null;
  created_at: string;
}

export interface CreateWorkflowPolicyRequest {
  policy_key: string;
  name: string;
  description?: string;
  effect: WorkflowPolicyEffect;
  conditions: Record<string, unknown>;
}

export type NotificationChannel = "in_app" | "email";
export type NotificationStatus = "pending" | "sent" | "failed";

export interface Notification {
  id: string;
  workflow_execution_id: string | null;
  channel: NotificationChannel;
  subject: string;
  body: string;
  status: NotificationStatus;
  sent_at: string | null;
  created_at: string;
}

export interface AutomationTemplate {
  id: string;
  name: string;
  description: string | null;
  category: string;
  node_definitions: WorkflowNodeInput[];
}

export interface ApplyAutomationTemplateRequest {
  workflow_name?: string;
}
