import { useMutation } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { SearchResponse } from "@vault/types";
import { Search as SearchIcon, SearchX } from "lucide-react";
import { useEffect, useState } from "react";
import { z } from "zod";

import { AppShell } from "@/components/app-shell/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { apiClient } from "@/lib/api-client";
import { fileTypeIcon } from "@/lib/file-icon";
import { retrievalMethodBadgeVariant, retrievalMethodLabel } from "@/lib/retrieval-method";
import { useAuthStore } from "@/stores/auth-store";

const searchParamsSchema = z.object({
  q: z.string().optional(),
});

export const Route = createFileRoute("/search")({
  validateSearch: searchParamsSchema,
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: SearchPage,
});

function SearchPage() {
  const { q } = Route.useSearch();
  const [query, setQuery] = useState(q ?? "");

  const searchMutation = useMutation({
    mutationFn: (searchQuery: string) =>
      apiClient.post<SearchResponse>("/v1/search", { query: searchQuery }),
  });

  useEffect(() => {
    if (q && q.trim().length > 0) {
      searchMutation.mutate(q);
    }
    // Only re-run when the incoming ?q= changes (e.g. from the command palette).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (query.trim().length === 0) return;
    searchMutation.mutate(query.trim());
  }

  const results = searchMutation.data?.results ?? [];

  return (
    <AppShell title="Search">
      <div className="mx-auto flex max-w-3xl flex-col gap-6">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Search</h1>
          <p className="text-sm text-muted-foreground">
            Search by file name, owner, topic, or ask a natural-language question.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="flex gap-2">
          <div className="relative flex-1">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Show invoices from last year…"
              className="pl-9"
              autoFocus
            />
          </div>
          <Button type="submit" disabled={searchMutation.isPending || query.trim().length === 0}>
            {searchMutation.isPending ? "Searching…" : "Search"}
          </Button>
        </form>

        {searchMutation.isPending && (
          <div className="flex flex-col gap-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-16 rounded-xl" />
            ))}
          </div>
        )}

        {searchMutation.isError && (
          <EmptyState title="Couldn't run that search" description="Please try again." />
        )}

        {searchMutation.isSuccess && results.length === 0 && (
          <EmptyState
            icon={SearchX}
            title="No matches found"
            description={`Nothing matched "${searchMutation.data.query}". Try a different phrase, or check that this connector has been scanned.`}
          />
        )}

        {results.length > 0 && (
          <ul className="flex flex-col gap-2">
            {results.map((result) => {
              const Icon = fileTypeIcon(null);
              return (
                <li key={result.file_id}>
                  <Link
                    to="/files/$fileId"
                    params={{ fileId: result.file_id }}
                    className="flex items-center gap-3 rounded-xl border border-border bg-card p-3 shadow-clay-sm transition-shadow hover:shadow-clay"
                  >
                    <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-secondary text-muted-foreground">
                      <Icon className="size-4" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{result.name}</p>
                      <p className="truncate text-xs text-muted-foreground">{result.path}</p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <Badge variant={retrievalMethodBadgeVariant(result.retrieval_method)}>
                        {retrievalMethodLabel(result.retrieval_method)}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {Math.round(result.score * 100)}%
                      </span>
                    </div>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </AppShell>
  );
}
