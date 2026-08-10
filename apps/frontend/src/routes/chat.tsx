import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import type { AskResponse, Conversation } from "@vault/types";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api-client";
import { formatRelativeTime } from "@/lib/format-relative-time";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/chat")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: ChatPage,
});

function ChatPage() {
  const navigate = useNavigate();
  const [question, setQuestion] = useState("");

  const conversationsQuery = useQuery({
    queryKey: ["conversations"],
    queryFn: () => apiClient.get<Conversation[]>("/v1/conversations"),
  });

  const askMutation = useMutation({
    mutationFn: (askQuestion: string) =>
      apiClient.post<AskResponse>("/v1/conversations", { question: askQuestion }),
    onSuccess: (response) =>
      void navigate({
        to: "/chat/$conversationId",
        params: { conversationId: response.conversation.id },
      }),
  });

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (question.trim().length === 0) return;
    askMutation.mutate(question.trim());
  }

  const conversations = conversationsQuery.data ?? [];

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-8">
      <Link to="/dashboard" className="text-sm underline">
        ← Back to dashboard
      </Link>
      <h1 className="text-xl font-semibold">Chat</h1>

      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask a question about your files…"
          rows={3}
          className="rounded-md border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-800 dark:bg-neutral-950"
        />
        <Button
          type="submit"
          className="w-fit"
          disabled={askMutation.isPending || question.trim().length === 0}
        >
          {askMutation.isPending ? "Asking…" : "Start conversation"}
        </Button>
        {askMutation.isError && (
          <p className="text-sm text-red-600">Couldn't send that question. Please try again.</p>
        )}
      </form>

      <section>
        <h2 className="mb-3 font-medium">Conversations</h2>
        {conversationsQuery.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
        {conversationsQuery.isError && (
          <p className="text-sm text-red-600">Couldn't load conversation history.</p>
        )}
        {conversations.length === 0 && !conversationsQuery.isLoading && (
          <p className="text-sm text-neutral-500">No conversations yet — ask a question above.</p>
        )}
        <ul className="flex flex-col gap-2">
          {conversations.map((conversation) => (
            <li key={conversation.id}>
              <Link
                to="/chat/$conversationId"
                params={{ conversationId: conversation.id }}
                className="flex items-center justify-between rounded-lg border border-neutral-200 p-3 text-sm hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900"
              >
                <span className="truncate">{conversation.title ?? "Untitled conversation"}</span>
                <span className="shrink-0 text-neutral-400">
                  {formatRelativeTime(conversation.updated_at)}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
