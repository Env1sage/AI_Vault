import type { EmbeddingJobStatus } from "@vault/types";

export function embeddingStatusColor(status: EmbeddingJobStatus): string {
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

export function isActiveEmbeddingStatus(status: EmbeddingJobStatus): boolean {
  return status === "pending" || status === "running";
}

export function embeddingStatusBadgeVariant(
  status: EmbeddingJobStatus,
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
