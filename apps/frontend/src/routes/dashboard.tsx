import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type {
  Dashboard,
  ReadinessResponse,
  Recommendation,
  RecommendationJob,
  VersionResponse,
} from "@vault/types";
import {
  ArrowUpRight,
  BrainCircuit,
  Cloud,
  Database,
  FolderTree,
  HardDrive,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { AppShell } from "@/components/app-shell/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { apiClient } from "@/lib/api-client";
import { formatBytes } from "@/lib/format-bytes";
import { formatRelativeTime } from "@/lib/format-relative-time";
import { categoryBadgeVariant, categoryLabel, riskBadgeVariant } from "@/lib/recommendation-style";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/dashboard")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: DashboardPage,
});

function statusLabel(ok: boolean | undefined, isError: boolean): string {
  if (ok) return "Operational";
  if (isError) return "Unreachable";
  return "Checking…";
}

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <Card clay className="flex flex-col gap-3 p-5">
      <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <Icon className="size-[18px]" aria-hidden="true" />
      </div>
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="mt-0.5 text-2xl font-semibold tracking-tight">{value}</p>
        {sub ? <p className="mt-0.5 text-xs text-muted-foreground">{sub}</p> : null}
      </div>
    </Card>
  );
}

function StorageTrendChart({ points }: { points: number[] }) {
  if (points.length < 2) {
    return (
      <p className="flex h-40 items-center justify-center text-sm text-muted-foreground">
        Not enough scan history yet to show a trend.
      </p>
    );
  }
  const width = 560;
  const height = 160;
  const max = Math.max(...points);
  const min = Math.min(...points);
  const range = max - min || 1;
  const coords = points.map((value, index) => {
    const x = (index / (points.length - 1)) * width;
    const y = height - ((value - min) / range) * (height - 12) - 6;
    return [x, y] as const;
  });
  const linePath = coords.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x},${y}`).join(" ");
  const areaPath = `${linePath} L${width},${height} L0,${height} Z`;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-40 w-full" preserveAspectRatio="none">
      <defs>
        <linearGradient id="storage-trend-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--color-primary)" stopOpacity="0.22" />
          <stop offset="100%" stopColor="var(--color-primary)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaPath} fill="url(#storage-trend-fill)" />
      <path d={linePath} fill="none" stroke="var(--color-primary)" strokeWidth="2.5" strokeLinecap="round" />
      {coords.map(([x, y], index) => (
        <circle key={index} cx={x} cy={y} r={index === coords.length - 1 ? 4 : 0} fill="var(--color-primary)" />
      ))}
    </svg>
  );
}

function DashboardSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
      {Array.from({ length: 6 }).map((_, i) => (
        <Skeleton key={i} className="h-28 rounded-xl" />
      ))}
    </div>
  );
}

function DashboardPage() {
  const user = useAuthStore((state) => state.user);
  const canManage = user?.role === "owner" || user?.role === "admin";
  const queryClient = useQueryClient();

  const versionQuery = useQuery({
    queryKey: ["version"],
    queryFn: () => apiClient.get<VersionResponse>("/v1/version"),
    retry: false,
  });
  const readinessQuery = useQuery({
    queryKey: ["readiness"],
    queryFn: () => apiClient.get<ReadinessResponse>("/health/ready"),
    retry: false,
  });

  const dashboardQuery = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => apiClient.get<Dashboard>("/v1/dashboard"),
  });

  const recommendationsQuery = useQuery({
    queryKey: ["recommendations", "preview"],
    queryFn: () =>
      apiClient.get<{ items: Recommendation[] }>("/v1/recommendations?status=active"),
  });

  const refreshMutation = useMutation({
    mutationFn: () => apiClient.post<RecommendationJob>("/v1/recommendations/refresh"),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      void queryClient.invalidateQueries({ queryKey: ["recommendations"] });
    },
  });

  const dashboard = dashboardQuery.data;
  const snapshot = dashboard?.latest_snapshot;
  const allRecommendations = recommendationsQuery.data?.items ?? [];
  const topRecommendations = allRecommendations.slice(0, 5);

  const categoryCounts = allRecommendations.reduce<Record<string, number>>((acc, r) => {
    acc[r.category] = (acc[r.category] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <AppShell title="Dashboard">
      <div className="mx-auto flex max-w-6xl flex-col gap-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">
              Welcome back{user?.name ? `, ${user.name.split(" ")[0]}` : ""}
            </h1>
            <p className="text-sm text-muted-foreground">
              Here&rsquo;s what&rsquo;s happening across your organization&rsquo;s storage.
            </p>
          </div>
          {canManage ? (
            <Button
              variant="outline"
              size="sm"
              disabled={refreshMutation.isPending}
              onClick={() => refreshMutation.mutate()}
            >
              <RefreshCw className={`size-4 ${refreshMutation.isPending ? "animate-spin" : ""}`} />
              {refreshMutation.isPending ? "Refreshing…" : "Refresh recommendations"}
            </Button>
          ) : null}
        </div>

        {dashboardQuery.isLoading && <DashboardSkeleton />}

        {dashboardQuery.isError && (
          <EmptyState
            title="Couldn't load the dashboard"
            description="There was a problem reaching the backend. Try refreshing the page."
          />
        )}

        {dashboard && (
          <>
            {/* What is happening — top-level metrics (§9) */}
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
              <StatCard
                icon={HardDrive}
                label="Storage used"
                value={formatBytes(snapshot?.total_storage_bytes ?? 0)}
              />
              <StatCard icon={FolderTree} label="Files" value={(snapshot?.total_files ?? 0).toLocaleString()} />
              <StatCard
                icon={FolderTree}
                label="Folders"
                value={(snapshot?.total_folders ?? 0).toLocaleString()}
              />
              <StatCard icon={Cloud} label="Connected drives" value={String(dashboard.connector_count)} />
              <StatCard
                icon={BrainCircuit}
                label="Knowledge complete"
                value={`${Math.round((snapshot?.knowledge_completeness_score ?? 0) * 100)}%`}
              />
              <StatCard
                icon={Sparkles}
                label="Active recommendations"
                value={String(snapshot?.active_recommendations ?? allRecommendations.length)}
              />
            </div>

            <div className="grid gap-4 lg:grid-cols-3">
              <Card className="lg:col-span-2">
                <CardHeader className="flex-row items-center justify-between gap-2 space-y-0">
                  <div>
                    <CardTitle>Storage growth</CardTitle>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      Total storage across recent scans
                    </p>
                  </div>
                </CardHeader>
                <CardContent>
                  <StorageTrendChart
                    points={dashboard.snapshot_history.map((s) => s.total_storage_bytes)}
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>What needs attention</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col gap-3">
                  {Object.keys(categoryCounts).length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      Nothing needs attention right now — no active recommendations.
                    </p>
                  ) : (
                    Object.entries(categoryCounts).map(([category, count]) => (
                      <div key={category} className="flex items-center justify-between text-sm">
                        <Badge variant={categoryBadgeVariant(category as Recommendation["category"])}>
                          {categoryLabel(category as Recommendation["category"])}
                        </Badge>
                        <span className="font-medium">{count}</span>
                      </div>
                    ))
                  )}
                  <div className="mt-1 grid grid-cols-2 gap-3 border-t border-border pt-3 text-sm">
                    <div>
                      <p className="text-muted-foreground">Scan</p>
                      <p className="font-medium capitalize">{dashboard.latest_scan_status ?? "—"}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Knowledge</p>
                      <p className="font-medium capitalize">{dashboard.latest_enrichment_status ?? "—"}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">AI embedding</p>
                      <p className="font-medium capitalize">{dashboard.latest_embedding_status ?? "—"}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Recommendations</p>
                      <p className="font-medium capitalize">
                        {dashboard.latest_recommendation_status ?? "—"}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <Card>
                <CardHeader className="flex-row items-center justify-between gap-2 space-y-0">
                  <CardTitle>Recommendation Center</CardTitle>
                  <Link
                    to="/recommendations"
                    className="flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                  >
                    View all <ArrowUpRight className="size-3.5" />
                  </Link>
                </CardHeader>
                <CardContent>
                  {topRecommendations.length === 0 ? (
                    <p className="py-6 text-center text-sm text-muted-foreground">
                      No active recommendations right now.
                    </p>
                  ) : (
                    <ul className="flex flex-col gap-2">
                      {topRecommendations.map((recommendation) => (
                        <li key={recommendation.id}>
                          <Link
                            to="/recommendations/$recommendationId"
                            params={{ recommendationId: recommendation.id }}
                            className="flex items-center justify-between gap-3 rounded-lg border border-transparent p-2.5 text-sm transition-colors hover:border-border hover:bg-secondary/60"
                          >
                            <div className="min-w-0">
                              <p className="truncate font-medium">{recommendation.title}</p>
                              <p className="truncate text-xs text-muted-foreground">
                                {recommendation.estimated_impact}
                              </p>
                            </div>
                            <div className="flex shrink-0 items-center gap-1.5">
                              <Badge variant={categoryBadgeVariant(recommendation.category)}>
                                {categoryLabel(recommendation.category)}
                              </Badge>
                              <Badge variant={riskBadgeVariant(recommendation.risk_level)}>
                                {recommendation.risk_level}
                              </Badge>
                            </div>
                          </Link>
                        </li>
                      ))}
                    </ul>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>AI Insights</CardTitle>
                </CardHeader>
                <CardContent>
                  {dashboard.recent_insights.length === 0 ? (
                    <p className="py-6 text-center text-sm text-muted-foreground">
                      No insights generated yet.
                    </p>
                  ) : (
                    <ul className="flex flex-col gap-3">
                      {dashboard.recent_insights.map((insight) => (
                        <li key={insight.id} className="flex gap-2.5 text-sm">
                          <Sparkles className="mt-0.5 size-4 shrink-0 text-ai" />
                          <div className="min-w-0">
                            <p className="font-medium">{insight.title}</p>
                            <p className="text-muted-foreground">{insight.description}</p>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Recent Activity</CardTitle>
              </CardHeader>
              <CardContent>
                {dashboard.recent_activity.length === 0 ? (
                  <p className="py-6 text-center text-sm text-muted-foreground">No recent activity.</p>
                ) : (
                  <ul className="flex flex-col divide-y divide-border">
                    {dashboard.recent_activity.map((file) => (
                      <li key={file.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                        <Link
                          to="/files/$fileId"
                          params={{ fileId: file.id }}
                          className="truncate font-medium hover:underline"
                        >
                          {file.name}
                        </Link>
                        <span className="shrink-0 text-xs text-muted-foreground">
                          {file.provider_modified_at ? formatRelativeTime(file.provider_modified_at) : "—"}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </>
        )}

        <Card className="border-dashed">
          <CardHeader className="flex-row items-center justify-between gap-2 space-y-0">
            <CardTitle className="flex items-center gap-2 text-muted-foreground">
              <Database className="size-4" /> System status
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                void versionQuery.refetch();
                void readinessQuery.refetch();
              }}
            >
              Recheck
            </Button>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 gap-y-2 text-sm sm:grid-cols-4">
              <dt className="text-muted-foreground">API version</dt>
              <dd>{versionQuery.data?.api_version ?? (versionQuery.isError ? "unreachable" : "loading…")}</dd>
              <dt className="text-muted-foreground">Service version</dt>
              <dd>{versionQuery.data?.service_version ?? "—"}</dd>
              <dt className="text-muted-foreground">Database</dt>
              <dd>{statusLabel(readinessQuery.data?.checks.database, readinessQuery.isError)}</dd>
              <dt className="text-muted-foreground">Redis</dt>
              <dd>{statusLabel(readinessQuery.data?.checks.redis, readinessQuery.isError)}</dd>
            </dl>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
