import type { ConversationMessage } from "@vault/types";
import { Sparkles } from "lucide-react";

import { MarkdownMessage } from "@/components/markdown-message";
import { Badge } from "@/components/ui/badge";
import { assistantToolLabel } from "@/lib/assistant-tool";
import { pickRenderVariant } from "@/lib/ai-response-renderer";

import { AIFileDetailCard } from "./ai-file-detail-card";
import { AIFileResultList } from "./ai-file-result-list";

/** Renders a full assistant message: avatar + bordered bubble (prose via
 * MarkdownMessage, then the provider/tool-name meta line), followed by a
 * structured card as a *sibling* below the bubble when the message carries
 * citations — never nested inside it, so a file list/detail card never ends
 * up double-bordered inside the chat bubble. `content` must never be parsed
 * for structured data: its fixed-text shape only exists when no LLM
 * provider is configured (COMPLETION_PROVIDER=extractive); with a real
 * provider it's arbitrary prose. Citations are the only reliable source of
 * structured per-file data. */
export function AIResponseRenderer({ message }: { message: ConversationMessage }) {
  const variant = pickRenderVariant(message);
  return (
    <div className="flex flex-col items-start gap-2">
      <div className="flex max-w-[85%] items-start gap-2.5">
        <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-ai-muted text-ai">
          <Sparkles className="size-3.5" />
        </span>
        <div className="rounded-2xl rounded-tl-sm border border-border bg-card px-4 py-2.5 text-sm shadow-clay-sm">
          <MarkdownMessage content={message.content} />
          {(message.provider || message.tool_name) && (
            <p className="mt-1.5 flex items-center gap-1.5 text-xs opacity-60">
              {message.provider && <span>via {message.provider}</span>}
              {message.tool_name && (
                <Badge variant="ai">{assistantToolLabel(message.tool_name)}</Badge>
              )}
            </p>
          )}
        </div>
      </div>

      {variant === "file-detail" && message.citations[0] && (
        <AIFileDetailCard citation={message.citations[0]} />
      )}
      {variant === "file-list" && (
        <AIFileResultList citations={message.citations} toolName={message.tool_name} />
      )}
    </div>
  );
}
