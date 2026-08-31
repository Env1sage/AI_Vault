const TOOL_LABELS: Record<string, string> = {
  get_storage_overview: "Storage overview",
  get_storage_statistics: "Storage breakdown",
  get_duplicate_summary: "Duplicate summary",
  get_duplicate_group: "Duplicate group",
  get_large_files: "Largest files",
  get_old_files: "Oldest files",
  get_inactive_files: "Inactive files",
  get_cleanup_candidates: "Cleanup candidates",
  search_files: "File search",
  get_file: "File lookup",
};

export function assistantToolLabel(toolName: string): string {
  return TOOL_LABELS[toolName] ?? toolName;
}
