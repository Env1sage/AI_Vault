import type { Connector } from "@vault/types";

export function connectorStatusColor(status: Connector["status"]): string {
  switch (status) {
    case "connected":
      return "text-green-600";
    case "error":
      return "text-red-600";
    case "reauth_required":
      return "text-amber-600";
    default:
      return "text-neutral-500";
  }
}

export function connectorStatusBadgeVariant(
  status: Connector["status"],
): "success" | "destructive" | "warning" | "default" {
  switch (status) {
    case "connected":
      return "success";
    case "error":
      return "destructive";
    case "reauth_required":
      return "warning";
    default:
      return "default";
  }
}
