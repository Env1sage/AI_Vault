import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { AskResponse, Citation, ConversationDetail, ConversationMessage, ExecutionPlan } from "@vault/types";
import { Archive, ChevronLeft, Send, Sparkles } from "lucide-react";
import { useState } from "react";

import { AppShell } from "@/components/app-shell/app-shell";
import { MarkdownMessage } from "@/components/markdown-message";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/ui/toaster";
import { ApiError, apiClient } from "@/lib/api-client";
import { assistantToolLabel } from "@/lib/assistant-tool";
import { fileTypeIconElement } from "@/lib/file-icon";
import { formatBytes } from "@/lib/format-bytes";
import { cn } from "@/lib/utils";
import { retrievalMethodBadgeVariant, retrievalMethodLabel } from "@/lib/retrieval-method";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/chat/$conversationId")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: ChatDetailPage,
});

function ThinkingBubble() {
  return (
    <div className="flex items-start gap-2.5">
      <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-ai-muted text-ai">
        <Sparkles className="size-3.5" />
      </span>
      <div className="flex items-center gap-1 rounded-2xl rounded-tl-sm border border-border bg-card px-4 py-3 shadow-clay-sm">
        <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.3s]" />
        <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.15s]" />
        <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground" />
      </div>
    </div>
  );
}

/** Turns a tool answer's cited files into an actionable list — not just a
 * "here's where this came from" link, but somewhere to actually pick files
 * and archive them, the same safe (approval-gated, reversible) path every
 * other cleanup action in the app already uses. */
function CitationFileList({ citations }: { citations: Citation[] }) {
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const canManage = user?.role === "owner" || user?.role === "admin";
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const archiveMutation = useMutation({
    mutationFn: () =>
      apiClient.post<ExecutionPlan>("/v1/execution-plans", {
        file_ids: Array.from(selected),
        action_type: "archive",
      }),
    onSuccess: (plan) => {
      void queryClient.invalidateQueries({ queryKey: ["execution-plans"] });
      setSelected(new Set());
      toast.success("Archive plan created", {
        description:
          "Nothing is touched yet — review and approve it to move these files to Google Drive's Trash (reversible).",
        action: {
          label: "Review & approve",
          onClick: () => {
            window.location.href = `/execution-plans/${plan.id}`;
          },
        },
      });
    },
  });

  function toggle(fileId: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(fileId)) next.delete(fileId);
      else next.add(fileId);
      return next;
    });
  }

  return (
    <div className="w-full max-w-[85%] rounded-xl border border-border bg-card p-3 shadow-clay-sm">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-xs font-medium text-muted-foreground">
          Sources ({citations.length})
        </p>
        {canManage && selected.size > 0 && (
          <Button
            size="sm"
            variant="outline"
            disabled={archiveMutation.isPending}
            onClick={() => archiveMutation.mutate()}
          >
            <Archive className="size-3.5" />
            {archiveMutation.isPending
              ? "Creating plan…"
              : `Archive ${selected.size} selected`}
          </Button>
        )}
      </div>
      <ul className="flex flex-col gap-1">
        {citations.map((citation) => (
          <li
            key={citation.id}
            className="flex items-center gap-2 rounded-lg p-2 text-xs transition-colors hover:bg-secondary"
          >
            {canManage && (
              <input
                type="checkbox"
                checked={selected.has(citation.file_id)}
                onChange={() => toggle(citation.file_id)}
                className="size-3.5 shrink-0 accent-primary"
                aria-label={`Select ${citation.file_name ?? "this file"}`}
              />
            )}
            <span className="flex size-6 shrink-0 items-center justify-center rounded-md bg-secondary text-muted-foreground">
              {fileTypeIconElement(citation.file_mime_type, { className: "size-3.5" })}
            </span>
            <Link
              to="/files/$fileId"
              params={{ fileId: citation.file_id }}
              className="flex min-w-0 flex-1 items-center justify-between gap-2"
            >
              <span className="min-w-0 flex-1">
                <span className="block truncate font-medium text-foreground/90">
                  {citation.file_name ?? "View file"}
                </span>
                {citation.snippet && (
                  <span className="block truncate text-muted-foreground">
                    {citation.snippet.slice(0, 80).replaceAll("\n", " ")}
                  </span>
                )}
              </span>
              <span className="flex shrink-0 items-center gap-1.5">
                {citation.file_size_bytes !== null && (
                  <span className="text-muted-foreground">
                    {formatBytes(citation.file_size_bytes)}
                  </span>
                )}
                <Badge variant={retrievalMethodBadgeVariant(citation.retrieval_method)}>
                  {retrievalMethodLabel(citation.retrieval_method)}
                </Badge>
                <span className="text-muted-foreground">
                  {Math.round(citation.confidence * 100)}%
                </span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
      {archiveMutation.isError && (
        <p className="mt-2 text-xs text-destructive">
          {archiveMutation.error instanceof ApiError
            ? archiveMutation.error.message
            : "Couldn't create an archive plan."}
        </p>
      )}
      {canManage && selected.size === 0 && (
        <p className="mt-2 text-xs text-muted-foreground">
          Select files above to archive them (reversible, requires approval).
        </p>
      )}
    </div>
  );
}

function MessageBubble({ message }: { message: ConversationMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex flex-col gap-2", isUser ? "items-end" : "items-start")}>
      <div className={cn("flex max-w-[85%] items-start gap-2.5", isUser && "flex-row-reverse")}>
        {!isUser && (
          <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-ai-muted text-ai">
            <Sparkles className="size-3.5" />
          </span>
        )}
        <div
          className={cn(
            "rounded-2xl px-4 py-2.5 text-sm shadow-clay-sm",
            isUser
              ? "whitespace-pre-wrap rounded-tr-sm bg-primary text-primary-foreground"
              : "rounded-tl-sm border border-border bg-card",
          )}
        >
          {isUser ? message.content : <MarkdownMessage content={message.content} />}
          {!isUser && (message.provider || message.tool_name) && (
            <p className="mt-1.5 flex items-center gap-1.5 text-xs opacity-60">
              {message.provider && <span>via {message.provider}</span>}
              {message.tool_name && (
                <Badge variant="ai">{assistantToolLabel(message.tool_name)}</Badge>
              )}
            </p>
          )}
        </div>
      </div>

      {message.citations.length > 0 && <CitationFileList citations={message.citations} />}
    </div>
  );
}

function ChatDetailPage() {
  const { conversationId } = Route.useParams();
  const queryClient = useQueryClient();
  const [question, setQuestion] = useState("");
  // Echoed immediately on submit so the thread feels live while the real
  // answer is still generating server-side, rather than sitting blank for
  // the several seconds a real completion call takes.
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);

  const conversationQuery = useQuery({
    queryKey: ["conversations", conversationId],
    queryFn: () => apiClient.get<ConversationDetail>(`/v1/conversations/${conversationId}`),
  });

  const askMutation = useMutation({
    mutationFn: (askQuestion: string) =>
      apiClient.post<AskResponse>(`/v1/conversations/${conversationId}/messages`, {
        question: askQuestion,
      }),
    onSuccess: () => {
      setPendingQuestion(null);
      void queryClient.invalidateQueries({ queryKey: ["conversations", conversationId] });
    },
    onError: () => {
      setQuestion(pendingQuestion ?? "");
      setPendingQuestion(null);
    },
  });

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (trimmed.length === 0) return;
    setPendingQuestion(trimmed);
    setQuestion("");
    askMutation.mutate(trimmed);
  }

  const conversation = conversationQuery.data;

  return (
    <AppShell title="Conversation">
      <div className="mx-auto flex max-w-2xl flex-col gap-4">
        <Link
          to="/chat"
          className="flex w-fit items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ChevronLeft className="size-4" /> Back to conversations
        </Link>

        {conversationQuery.isLoading && (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-16 w-2/3 rounded-2xl" />
            <Skeleton className="ml-auto h-10 w-1/2 rounded-2xl" />
          </div>
        )}
        {conversationQuery.isError && (
          <p className="text-sm text-destructive">Couldn&rsquo;t load this conversation.</p>
        )}

        {conversation && (
          <>
            <h1 className="text-lg font-semibold">
              {conversation.title ?? "Untitled conversation"}
            </h1>

            <div className="flex flex-col gap-5">
              {conversation.messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}
              {pendingQuestion && (
                <>
                  <div className="flex flex-col items-end gap-2">
                    <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-primary px-4 py-2.5 text-sm text-primary-foreground shadow-clay-sm">
                      {pendingQuestion}
                    </div>
                  </div>
                  <ThinkingBubble />
                </>
              )}
            </div>

            <form onSubmit={handleSubmit} className="sticky bottom-4 flex gap-2 pt-2">
              <textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="Ask a follow-up question…"
                rows={1}
                className="flex-1 resize-none rounded-full border border-input bg-card px-4 py-2.5 text-sm shadow-clay placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              <Button
                type="submit"
                variant="ai"
                size="icon"
                className="rounded-full"
                disabled={askMutation.isPending || question.trim().length === 0}
                aria-label="Send"
              >
                <Send className="size-4" />
              </Button>
            </form>
            {askMutation.isError && (
              <p className="text-sm text-destructive">
                Couldn&rsquo;t send that message. Please try again.
              </p>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
