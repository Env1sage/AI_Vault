import type { ConversationMessage } from "@vault/types";

export type AIResponseVariant = "prose-only" | "file-detail" | "file-list";

/** `get_file` is the only tool whose one citation deserves an expanded
 * single-file layout instead of a list row. */
const FILE_DETAIL_TOOLS = new Set(["get_file"]);

/** Dispatch is driven by whether citations exist, not by `tool_name` alone:
 * a bundled-tool answer (e.g. "how much can I recover if I clean up") can
 * carry citations from a *second* tool call while `tool_name` only ever
 * records the first (see conversation_service.py's tool_calls[0].name) — so
 * treating tool_name as authoritative would wrongly hide a real file list. */
export function pickRenderVariant(message: ConversationMessage): AIResponseVariant {
  if (message.citations.length === 0) return "prose-only";
  if (message.tool_name && FILE_DETAIL_TOOLS.has(message.tool_name)) return "file-detail";
  return "file-list";
}
