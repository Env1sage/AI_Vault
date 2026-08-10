import type { RecommendationCategory, RecommendationRiskLevel } from "@vault/types";

export function categoryLabel(category: RecommendationCategory): string {
  switch (category) {
    case "storage_optimization":
      return "Storage";
    case "knowledge_optimization":
      return "Knowledge";
    case "security":
      return "Security";
    case "collaboration":
      return "Collaboration";
    case "productivity":
      return "Productivity";
    default:
      return category;
  }
}

export function categoryColor(category: RecommendationCategory): string {
  switch (category) {
    case "storage_optimization":
      return "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300";
    case "knowledge_optimization":
      return "bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300";
    case "security":
      return "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300";
    case "collaboration":
      return "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300";
    case "productivity":
      return "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300";
    default:
      return "bg-neutral-100 text-neutral-700 dark:bg-neutral-900 dark:text-neutral-300";
  }
}

export function riskColor(risk: RecommendationRiskLevel): string {
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
