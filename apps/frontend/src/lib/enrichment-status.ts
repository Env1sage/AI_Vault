import type { EnrichmentJobStatus } from "@vault/types";

export function enrichmentStatusColor(status: EnrichmentJobStatus): string {
  switch (status) {
    case "completed":
      return "text-green-600";
    case "failed":
      return "text-red-600";
    case "cancelled":
      return "text-neutral-500";
    case "running":
      return "text-blue-600";
    default:
      return "text-neutral-500";
  }
}

export function isActiveEnrichmentStatus(status: EnrichmentJobStatus): boolean {
  return status === "pending" || status === "running";
}

export function enrichmentStatusBadgeVariant(
  status: EnrichmentJobStatus,
): "success" | "destructive" | "primary" | "default" {
  switch (status) {
    case "completed":
      return "success";
    case "failed":
      return "destructive";
    case "running":
      return "primary";
    default:
      return "default";
  }
}
