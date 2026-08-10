import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { AskResponse, ConversationDetail, ConversationMessage } from "@vault/types";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api-client";
import { retrievalMethodColor, retrievalMethodLabel } from "@/lib/retrieval-method";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/chat/$conversationId")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: ChatDetailPage,
});

function MessageBubble({ message }: { message: ConversationMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex flex-col gap-2 ${isUser ? "items-end" : "items-start"}`}>
      <div
        className={`max-w-[85%] rounded-lg border p-3 text-sm whitespace-pre-wrap ${
          isUser
            ? "border-blue-200 bg-blue-50 dark:border-blue-900 dark:bg-blue-950"
            : "border-neutral-200 bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-900"
        }`}
      >
        {message.content}
        {!isUser && message.provider && (
          <p className="mt-2 text-xs text-neutral-400">via {message.provider}</p>
        )}
      </div>

      {message.citations.length > 0 && (
        <div className="w-full max-w-[85%] rounded-lg border border-neutral-200 p-3 dark:border-neutral-800">
          <p className="mb-2 text-xs font-medium text-neutral-500">Sources</p>
          <ul className="flex flex-col gap-2">
            {message.citations.map((citation) => (
              <li key={citation.id}>
                <Link
                  to="/files/$fileId"
                  params={{ fileId: citation.file_id }}
                  className="flex items-center justify-between gap-2 rounded-md p-2 text-xs hover:bg-neutral-100 dark:hover:bg-neutral-800"
                >
                  <span className="truncate text-neutral-600 dark:text-neutral-300">
                    {citation.snippet
                      ? citation.snippet.slice(0, 80).replaceAll("\n", " ")
                      : "View file"}
                  </span>
                  <span className="flex shrink-0 items-center gap-2">
                    <span
                      className={`rounded-full px-2 py-0.5 font-medium ${retrievalMethodColor(citation.retrieval_method)}`}
                    >
                      {retrievalMethodLabel(citation.retrieval_method)}
                    </span>
                    <span className="text-neutral-400">
                      {Math.round(citation.confidence * 100)}%
                    </span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function ChatDetailPage() {
  const { conversationId } = Route.useParams();
  const queryClient = useQueryClient();
  const [question, setQuestion] = useState("");

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
      setQuestion("");
      void queryClient.invalidateQueries({ queryKey: ["conversations", conversationId] });
    },
  });

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (question.trim().length === 0) return;
    askMutation.mutate(question.trim());
  }

  const conversation = conversationQuery.data;

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-8">
      <Link to="/chat" className="text-sm underline">
        ← Back to conversations
      </Link>

      {conversationQuery.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
      {conversationQuery.isError && (
        <p className="text-sm text-red-600">Couldn't load this conversation.</p>
      )}

      {conversation && (
        <>
          <h1 className="text-xl font-semibold">{conversation.title ?? "Untitled conversation"}</h1>

          <div className="flex flex-col gap-4">
            {conversation.messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-2">
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask a follow-up question…"
              rows={3}
              className="rounded-md border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-800 dark:bg-neutral-950"
            />
            <Button
              type="submit"
              className="w-fit"
              disabled={askMutation.isPending || question.trim().length === 0}
            >
              {askMutation.isPending ? "Asking…" : "Send"}
            </Button>
            {askMutation.isError && (
              <p className="text-sm text-red-600">Couldn't send that message. Please try again.</p>
            )}
          </form>
        </>
      )}
    </main>
  );
}
