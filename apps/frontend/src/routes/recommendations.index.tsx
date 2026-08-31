import { useQuery } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { RecommendationCategory, RecommendationListResponse } from "@vault/types";
import { Lightbulb, Search } from "lucide-react";
import { useState } from "react";

import { AppShell } from "@/components/app-shell/app-shell";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { apiClient } from "@/lib/api-client";
import { categoryBadgeVariant, categoryLabel, riskBadgeVariant } from "@/lib/recommendation-style";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/recommendations/")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: RecommendationsPage,
});

const CATEGORIES: RecommendationCategory[] = [
  "storage_optimization",
  "knowledge_optimization",
  "security",
  "collaboration",
  "productivity",
];

function RecommendationsPage() {
  const [category, setCategory] = useState<string>("all");
  const [status, setStatus] = useState<string>("active");
  const [search, setSearch] = useState("");

  const params = new URLSearchParams();
  if (category !== "all") params.set("category", category);
  if (status !== "all") params.set("status", status);
  if (search.trim()) params.set("search", search.trim());

  const recommendationsQuery = useQuery({
    queryKey: ["recommendations", category, status, search],
    queryFn: () =>
      apiClient.get<RecommendationListResponse>(`/v1/recommendations?${params.toString()}`),
  });

  const recommendations = recommendationsQuery.data?.items ?? [];

  return (
    <AppShell title="Recommendations">
      <div className="mx-auto flex max-w-4xl flex-col gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Recommendation Center</h1>
          <p className="text-sm text-muted-foreground">
            Explainable, deterministic suggestions across storage, security, and productivity.
          </p>
        </div>

        <Card className="flex flex-wrap items-center gap-2 p-2">
          <div className="relative min-w-[12rem] flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search recommendations…"
              className="pl-9"
            />
          </div>
          <Select value={category} onValueChange={setCategory}>
            <SelectTrigger className="w-44">
              <SelectValue placeholder="Category" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All categories</SelectItem>
              {CATEGORIES.map((value) => (
                <SelectItem key={value} value={value}>
                  {categoryLabel(value)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger className="w-36">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="resolved">Resolved</SelectItem>
              <SelectItem value="all">All statuses</SelectItem>
            </SelectContent>
          </Select>
        </Card>

        {recommendationsQuery.isLoading && (
          <div className="flex flex-col gap-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-24 rounded-xl" />
            ))}
          </div>
        )}
        {recommendationsQuery.isError && (
          <EmptyState title="Couldn't load recommendations" description="Please try again." />
        )}
        {recommendations.length === 0 && !recommendationsQuery.isLoading && (
          <EmptyState
            icon={Lightbulb}
            title="No recommendations match these filters"
            description="Try a different category or status, or check back after the next scan."
          />
        )}

        <ul className="flex flex-col gap-3">
          {recommendations.map((recommendation) => (
            <li key={recommendation.id}>
              <Link
                to="/recommendations/$recommendationId"
                params={{ recommendationId: recommendation.id }}
                className="flex flex-col gap-2 rounded-xl border border-border bg-card p-4 shadow-clay-sm transition-all hover:-translate-y-0.5 hover:shadow-clay"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="min-w-0 truncate font-medium">{recommendation.title}</p>
                  <Badge variant={categoryBadgeVariant(recommendation.category)}>
                    {categoryLabel(recommendation.category)}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground">{recommendation.estimated_impact}</p>
                <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  <Badge variant={riskBadgeVariant(recommendation.risk_level)}>
                    {recommendation.risk_level} risk
                  </Badge>
                  <span>{Math.round(recommendation.confidence * 100)}% confidence</span>
                  <span>priority {recommendation.priority_score.toFixed(0)}</span>
                  {recommendation.status === "resolved" && <Badge variant="success">Resolved</Badge>}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </AppShell>
  );
}
