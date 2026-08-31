import type {
  NotificationStatus,
  WorkflowExecutionStatus,
  WorkflowNodeExecutionStatus,
  WorkflowPolicyStatus,
  WorkflowStatus,
} from "@vault/types";

export function workflowStatusColor(status: WorkflowStatus): string {
  switch (status) {
    case "active":
      return "text-green-600";
    case "paused":
      return "text-amber-600";
    case "disabled":
      return "text-neutral-500";
    default:
      return "text-neutral-500";
  }
}

export function executionStatusColor(status: WorkflowExecutionStatus): string {
  switch (status) {
    case "completed":
      return "text-green-600";
    case "failed":
      return "text-red-600";
    case "running":
      return "text-blue-600";
    case "paused":
      return "text-amber-600";
    case "cancelled":
      return "text-neutral-500";
    default:
      return "text-neutral-500";
  }
}

export function isActiveExecutionStatus(status: WorkflowExecutionStatus): boolean {
  return status === "pending" || status === "running" || status === "paused";
}

export function nodeExecutionStatusColor(status: WorkflowNodeExecutionStatus): string {
  switch (status) {
    case "completed":
      return "text-green-600";
    case "failed":
      return "text-red-600";
    case "skipped":
      return "text-neutral-500";
    case "waiting_approval":
    case "waiting_delay":
      return "text-amber-600";
    case "running":
      return "text-blue-600";
    default:
      return "text-neutral-500";
  }
}

export function policyStatusColor(status: WorkflowPolicyStatus): string {
  switch (status) {
    case "published":
      return "text-green-600";
    case "archived":
      return "text-neutral-500";
    case "draft":
      return "text-amber-600";
    default:
      return "text-neutral-500";
  }
}

export function notificationStatusColor(status: NotificationStatus): string {
  switch (status) {
    case "sent":
      return "text-green-600";
    case "failed":
      return "text-red-600";
    case "pending":
      return "text-amber-600";
    default:
      return "text-neutral-500";
  }
}

type BadgeVariant = "default" | "primary" | "ai" | "success" | "warning" | "destructive" | "outline";

export function workflowStatusBadgeVariant(status: WorkflowStatus): BadgeVariant {
  switch (status) {
    case "active":
      return "success";
    case "paused":
      return "warning";
    default:
      return "default";
  }
}

export function executionStatusBadgeVariant(status: WorkflowExecutionStatus): BadgeVariant {
  switch (status) {
    case "completed":
      return "success";
    case "failed":
      return "destructive";
    case "running":
      return "primary";
    case "paused":
      return "warning";
    default:
      return "default";
  }
}

export function nodeExecutionStatusBadgeVariant(status: WorkflowNodeExecutionStatus): BadgeVariant {
  switch (status) {
    case "completed":
      return "success";
    case "failed":
      return "destructive";
    case "waiting_approval":
    case "waiting_delay":
      return "warning";
    case "running":
      return "primary";
    default:
      return "default";
  }
}

export function policyStatusBadgeVariant(status: WorkflowPolicyStatus): BadgeVariant {
  switch (status) {
    case "published":
      return "success";
    case "draft":
      return "warning";
    default:
      return "default";
  }
}

export function notificationStatusBadgeVariant(status: NotificationStatus): BadgeVariant {
  switch (status) {
    case "sent":
      return "success";
    case "failed":
      return "destructive";
    case "pending":
      return "warning";
    default:
      return "default";
  }
}

export function nodeTypeLabel(nodeType: string): string {
  switch (nodeType) {
    case "trigger":
      return "Trigger";
    case "condition":
      return "Condition";
    case "decision":
      return "Decision";
    case "ai_evaluation":
      return "AI Evaluation";
    case "approval":
      return "Approval";
    case "execute_action":
      return "Execute Action";
    case "delay":
      return "Delay";
    case "notification":
      return "Notification";
    case "end":
      return "End";
    default:
      return nodeType;
  }
}
