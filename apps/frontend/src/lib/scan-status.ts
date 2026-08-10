import type { ScanStatus } from "@vault/types";

export function scanStatusColor(status: ScanStatus): string {
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

export function isActiveScanStatus(status: ScanStatus): boolean {
  return status === "pending" || status === "running";
}
