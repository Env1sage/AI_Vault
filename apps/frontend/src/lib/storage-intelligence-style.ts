import type { StorageAnalysisJobStatus } from "@vault/types";

type BadgeVariant = "default" | "primary" | "ai" | "success" | "warning" | "destructive" | "outline";

export function analysisStatusBadgeVariant(status: StorageAnalysisJobStatus): BadgeVariant {
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

export function analysisStatusLabel(status: StorageAnalysisJobStatus): string {
  switch (status) {
    case "completed":
      return "Complete";
    case "failed":
      return "Failed";
    case "running":
      return "Analyzing…";
    default:
      return "Pending";
  }
}

/** Never a bare percentage without context — pairs the number with a
 * qualitative label so a 0.4 confidence doesn't read as falsely precise
 * (Phase 1 spec §12.2: "do not manufacture false precision")." */
export function confidenceLabel(confidence: number): string {
  if (confidence >= 0.8) return "High confidence";
  if (confidence >= 0.5) return "Medium confidence";
  return "Low confidence";
}
