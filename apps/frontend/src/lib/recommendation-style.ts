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

/** Badge variant per category — deliberately restrained (Redesign brief §4:
 * no rainbow dashboards). Security always reads as the destructive/danger
 * tone since it's the one category that's never "just informational". */
export function categoryBadgeVariant(
  category: RecommendationCategory,
): "primary" | "ai" | "destructive" | "warning" | "success" | "default" {
  switch (category) {
    case "storage_optimization":
      return "primary";
    case "knowledge_optimization":
      return "ai";
    case "security":
      return "destructive";
    case "collaboration":
      return "warning";
    case "productivity":
      return "success";
    default:
      return "default";
  }
}

/** @deprecated kept only for any lingering raw-class callers; prefer
 * `categoryBadgeVariant` + `<Badge>`. */
export function categoryColor(category: RecommendationCategory): string {
  switch (category) {
    case "storage_optimization":
      return "bg-primary/10 text-primary";
    case "knowledge_optimization":
      return "bg-ai-muted text-ai";
    case "security":
      return "bg-destructive-muted text-destructive";
    case "collaboration":
      return "bg-warning-muted text-warning";
    case "productivity":
      return "bg-success-muted text-success";
    default:
      return "bg-secondary text-secondary-foreground";
  }
}

export function riskBadgeVariant(
  risk: RecommendationRiskLevel,
): "destructive" | "warning" | "default" {
  switch (risk) {
    case "high":
      return "destructive";
    case "medium":
      return "warning";
    default:
      return "default";
  }
}

export function riskColor(risk: RecommendationRiskLevel): string {
  switch (risk) {
    case "high":
      return "text-destructive";
    case "medium":
      return "text-warning";
    default:
      return "text-muted-foreground";
  }
}
