import type { RetrievalMethod } from "@vault/types";

export function retrievalMethodLabel(method: RetrievalMethod): string {
  switch (method) {
    case "metadata":
      return "Name match";
    case "semantic":
      return "Semantic match";
    case "both":
      return "Name + semantic match";
    default:
      return method;
  }
}

export function retrievalMethodColor(method: RetrievalMethod): string {
  switch (method) {
    case "metadata":
      return "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300";
    case "semantic":
      return "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300";
    case "both":
      return "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300";
    default:
      return "bg-neutral-100 text-neutral-700 dark:bg-neutral-900 dark:text-neutral-300";
  }
}
