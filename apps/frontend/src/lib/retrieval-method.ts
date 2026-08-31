import type { ConversationRetrievalMethod } from "@vault/types";

export function retrievalMethodLabel(method: ConversationRetrievalMethod): string {
  switch (method) {
    case "metadata":
      return "Name match";
    case "semantic":
      return "Semantic match";
    case "both":
      return "Name + semantic match";
    case "tool":
      return "Storage Assistant";
    default:
      return method;
  }
}

export function retrievalMethodBadgeVariant(
  method: ConversationRetrievalMethod,
): "warning" | "ai" | "success" | "default" {
  switch (method) {
    case "metadata":
      return "warning";
    case "semantic":
      return "ai";
    case "both":
      return "success";
    case "tool":
      return "ai";
    default:
      return "default";
  }
}
