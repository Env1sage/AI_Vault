import type {
  ApprovalStatus,
  ExecutionJobStatus,
  ExecutionPlanStatus,
  ExecutionRiskLevel,
} from "@vault/types";

export function planStatusColor(status: ExecutionPlanStatus): string {
  switch (status) {
    case "completed":
    case "approved":
      return "text-green-600";
    case "failed":
    case "rejected":
      return "text-red-600";
    case "partially_completed":
    case "changes_requested":
      return "text-amber-600";
    case "executing":
      return "text-blue-600";
    case "expired":
    case "rolled_back":
      return "text-neutral-500";
    default:
      return "text-neutral-500";
  }
}

export function jobStatusColor(status: ExecutionJobStatus): string {
  switch (status) {
    case "completed":
      return "text-green-600";
    case "failed":
      return "text-red-600";
    case "partially_completed":
      return "text-amber-600";
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

export function isActiveJobStatus(status: ExecutionJobStatus): boolean {
  return status === "pending" || status === "running" || status === "paused";
}

export function approvalStatusColor(status: ApprovalStatus): string {
  switch (status) {
    case "approved":
      return "text-green-600";
    case "rejected":
      return "text-red-600";
    case "changes_requested":
      return "text-amber-600";
    case "expired":
      return "text-neutral-500";
    case "pending":
      return "text-blue-600";
    default:
      return "text-neutral-500";
  }
}

export function riskLevelColor(risk: ExecutionRiskLevel): string {
  switch (risk) {
    case "high":
      return "text-red-600";
    case "medium":
      return "text-amber-600";
    case "low":
      return "text-neutral-500";
    default:
      return "text-neutral-500";
  }
}

type BadgeVariant = "default" | "primary" | "ai" | "success" | "warning" | "destructive" | "outline";

export function planStatusBadgeVariant(status: ExecutionPlanStatus): BadgeVariant {
  switch (status) {
    case "completed":
    case "approved":
      return "success";
    case "failed":
    case "rejected":
      return "destructive";
    case "partially_completed":
    case "changes_requested":
      return "warning";
    case "executing":
      return "primary";
    default:
      return "default";
  }
}

export function jobStatusBadgeVariant(status: ExecutionJobStatus): BadgeVariant {
  switch (status) {
    case "completed":
      return "success";
    case "failed":
      return "destructive";
    case "partially_completed":
    case "paused":
      return "warning";
    case "running":
      return "primary";
    default:
      return "default";
  }
}

export function approvalStatusBadgeVariant(status: ApprovalStatus): BadgeVariant {
  switch (status) {
    case "approved":
      return "success";
    case "rejected":
      return "destructive";
    case "changes_requested":
      return "warning";
    case "pending":
      return "primary";
    default:
      return "default";
  }
}

export function riskLevelBadgeVariant(risk: ExecutionRiskLevel): BadgeVariant {
  switch (risk) {
    case "high":
      return "destructive";
    case "medium":
      return "warning";
    default:
      return "default";
  }
}

export function actionTypeLabel(actionType: string): string {
  switch (actionType) {
    case "move_file":
      return "Move file";
    case "move_folder":
      return "Move folder";
    case "rename":
      return "Rename";
    case "archive":
      return "Archive (Drive trash)";
    case "remove_duplicate":
      return "Remove duplicate (Drive trash)";
    case "update_metadata":
      return "Update metadata";
    case "create_archive":
      return "Create archive";
    default:
      return actionType;
  }
}
