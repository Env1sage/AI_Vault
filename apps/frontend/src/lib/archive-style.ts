import type { ArchiveJobStatus } from "@vault/types";

type BadgeVariant = "default" | "primary" | "ai" | "success" | "warning" | "destructive" | "outline";

export function archiveStatusBadgeVariant(status: ArchiveJobStatus): BadgeVariant {
  switch (status) {
    case "completed":
      return "success";
    case "failed":
      return "destructive";
    case "creating":
      return "primary";
    case "deleted":
      return "outline";
    default:
      return "default";
  }
}

export function archiveStatusLabel(status: ArchiveJobStatus): string {
  switch (status) {
    case "completed":
      return "Ready";
    case "failed":
      return "Failed";
    case "creating":
      return "Creating…";
    case "deleted":
      return "Deleted";
    default:
      return "Pending";
  }
}
