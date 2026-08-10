import { useMutation } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { SearchResponse } from "@vault/types";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api-client";
import { retrievalMethodColor, retrievalMethodLabel } from "@/lib/retrieval-method";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/search")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: SearchPage,
});

function SearchPage() {
  const [query, setQuery] = useState("");

  const searchMutation = useMutation({
    mutationFn: (searchQuery: string) =>
      apiClient.post<SearchResponse>("/v1/search", { query: searchQuery }),
  });

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (query.trim().length === 0) return;
    searchMutation.mutate(query.trim());
  }

  const results = searchMutation.data?.results ?? [];

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-8">
      <Link to="/dashboard" className="text-sm underline">
        ← Back to dashboard
      </Link>
      <h1 className="text-xl font-semibold">Search</h1>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search files by name, owner, topic…"
          className="flex-1 rounded-md border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-800 dark:bg-neutral-950"
        />
        <Button type="submit" disabled={searchMutation.isPending || query.trim().length === 0}>
          {searchMutation.isPending ? "Searching…" : "Search"}
        </Button>
      </form>

      {searchMutation.isError && (
        <p className="text-sm text-red-600">Couldn't run that search. Please try again.</p>
      )}

      {searchMutation.isSuccess && results.length === 0 && (
        <p className="text-sm text-neutral-500">
          No matching files found for "{searchMutation.data.query}".
        </p>
      )}

      {results.length > 0 && (
        <ul className="flex flex-col gap-2">
          {results.map((result) => (
            <li key={result.file_id}>
              <Link
                to="/files/$fileId"
                params={{ fileId: result.file_id }}
                className="flex items-center justify-between gap-4 rounded-lg border border-neutral-200 p-3 text-sm hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium">{result.name}</p>
                  <p className="truncate text-neutral-500">{result.path}</p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <span
                    className={`rounded-full px-2 py-1 text-xs font-medium ${retrievalMethodColor(result.retrieval_method)}`}
                  >
                    {retrievalMethodLabel(result.retrieval_method)}
                  </span>
                  <span className="text-neutral-400">{Math.round(result.score * 100)}%</span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
