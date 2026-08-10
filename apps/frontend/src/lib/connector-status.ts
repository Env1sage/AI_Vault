import type { Connector } from "@vault/types";

export function connectorStatusColor(status: Connector["status"]): string {
  switch (status) {
    case "connected":
      return "text-green-600";
    case "error":
      return "text-red-600";
    default:
      return "text-neutral-500";
  }
}
