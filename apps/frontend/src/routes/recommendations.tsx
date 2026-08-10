import { useQuery } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { RecommendationCategory, RecommendationListResponse } from "@vault/types";
import { useState } from "react";

import { apiClient } from "@/lib/api-client";
import { categoryColor, categoryLabel, riskColor } from "@/lib/recommendation-style";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/recommendations")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: RecommendationsPage,
});

const _CATEGORIES: RecommendationCategory[] = [
  "storage_optimization",
  "knowledge_optimization",
  "security",
  "collaboration",
  "productivity",
];

function RecommendationsPage() {
  const [category, setCategory] = useState<string>("");
  const [status, setStatus] = useState<string>("active");
  const [search, setSearch] = useState("");

  const params = new URLSearchParams();
  if (category) params.set("category", category);
  if (status) params.set("status", status);
  if (search.trim()) params.set("search", search.trim());

  const recommendationsQuery = useQuery({
    queryKey: ["recommendations", category, status, search],
    queryFn: () =>
      apiClient.get<RecommendationListResponse>(`/v1/recommendations?${params.toString()}`),
  });

  const recommendations = recommendationsQuery.data?.items ?? [];

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-8">
      <Link to="/dashboard" className="text-sm underline">
        ← Back to dashboard
      </Link>
      <h1 className="text-xl font-semibold">Recommendations</h1>

      <div className="flex flex-wrap gap-2">
        <select
          value={category}
          onChange={(event) => setCategory(event.target.value)}
          className="rounded-md border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-800 dark:bg-neutral-950"
        >
          <option value="">All categories</option>
          {_CATEGORIES.map((value) => (
            <option key={value} value={value}>
              {categoryLabel(value)}
            </option>
          ))}
        </select>

        <select
          value={status}
          onChange={(event) => setStatus(event.target.value)}
          className="rounded-md border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-800 dark:bg-neutral-950"
        >
          <option value="active">Active</option>
          <option value="resolved">Resolved</option>
          <option value="">All statuses</option>
        </select>

        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search recommendations…"
          className="flex-1 rounded-md border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-800 dark:bg-neutral-950"
        />
      </div>

      {recommendationsQuery.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
      {recommendationsQuery.isError && (
        <p className="text-sm text-red-600">Couldn't load recommendations.</p>
      )}
      {recommendations.length === 0 && !recommendationsQuery.isLoading && (
        <p className="text-sm text-neutral-500">No recommendations match these filters.</p>
      )}

      <ul className="flex flex-col gap-2">
        {recommendations.map((recommendation) => (
          <li key={recommendation.id}>
            <Link
              to="/recommendations/$recommendationId"
              params={{ recommendationId: recommendation.id }}
              className="flex flex-col gap-2 rounded-lg border border-neutral-200 p-3 text-sm hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900"
            >
              <div className="flex items-center justify-between gap-3">
                <p className="min-w-0 truncate font-medium">{recommendation.title}</p>
                <span
                  className={`shrink-0 rounded-full px-2 py-1 text-xs font-medium ${categoryColor(recommendation.category)}`}
                >
                  {categoryLabel(recommendation.category)}
                </span>
              </div>
              <p className="text-neutral-500">{recommendation.estimated_impact}</p>
              <div className="flex items-center gap-3 text-xs text-neutral-400">
                <span className={riskColor(recommendation.risk_level)}>
                  {recommendation.risk_level} risk
                </span>
                <span>{Math.round(recommendation.confidence * 100)}% confidence</span>
                <span>priority {recommendation.priority_score.toFixed(0)}</span>
                {recommendation.status === "resolved" && (
                  <span className="text-green-600">resolved</span>
                )}
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
