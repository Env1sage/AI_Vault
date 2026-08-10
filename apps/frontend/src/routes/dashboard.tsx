import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import type {
  Dashboard,
  ReadinessResponse,
  Recommendation,
  RecommendationJob,
  VersionResponse,
} from "@vault/types";

import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api-client";
import { formatBytes } from "@/lib/format-bytes";
import { formatRelativeTime } from "@/lib/format-relative-time";
import { categoryColor, categoryLabel, riskColor } from "@/lib/recommendation-style";
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
  if (ok) return "ok";
  if (isError) return "unreachable";
  return "checking…";
}

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-neutral-200 p-3 dark:border-neutral-800">
      <p className="text-xs text-neutral-500">{label}</p>
      <p className="text-lg font-semibold">{value}</p>
    </div>
  );
}

function StorageTrendSparkline({ points }: { points: number[] }) {
  if (points.length < 2) {
    return <p className="text-sm text-neutral-500">Not enough history yet to show a trend.</p>;
  }
  const width = 300;
  const height = 60;
  const max = Math.max(...points);
  const min = Math.min(...points);
  const range = max - min || 1;
  const coords = points.map((value, index) => {
    const x = (index / (points.length - 1)) * width;
    const y = height - ((value - min) / range) * height;
    return `${x},${y}`;
  });

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-16 w-full">
      <polyline
        points={coords.join(" ")}
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        className="text-blue-500"
      />
    </svg>
  );
}

function DashboardPage() {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const canManage = user?.role === "owner" || user?.role === "admin";

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

  async function handleLogout() {
    await logout();
    await navigate({ to: "/login" });
  }

  const dashboard = dashboardQuery.data;
  const snapshot = dashboard?.latest_snapshot;
  const topRecommendations = (recommendationsQuery.data?.items ?? []).slice(0, 5);

  return (
    <main className="mx-auto flex max-w-4xl flex-col gap-6 p-8">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">AI Project Vault</h1>
          <p className="text-neutral-500">Signed in as {user?.name ?? user?.email}</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => void handleLogout()}>
          Log out
        </Button>
      </header>

      <nav className="flex flex-wrap gap-4 text-sm">
        <Link to="/profile" className="underline">
          Profile
        </Link>
        <Link to="/organization" className="underline">
          Organization
        </Link>
        <Link to="/storage-connections" className="underline">
          Storage Connections
        </Link>
        <Link to="/scans" className="underline">
          Scans
        </Link>
        <Link to="/files" className="underline">
          Files
        </Link>
        <Link to="/search" className="underline">
          Search
        </Link>
        <Link to="/chat" className="underline">
          Chat
        </Link>
        <Link to="/recommendations" className="underline">
          Recommendations
        </Link>
        <Link to="/execution-plans" className="underline">
          Execution Center
        </Link>
        <Link to="/approvals" className="underline">
          Approval Queue
        </Link>
        <Link to="/automation" className="underline">
          Automation
        </Link>
      </nav>

      {dashboardQuery.isLoading && <p className="text-sm text-neutral-500">Loading dashboard…</p>}
      {dashboardQuery.isError && (
        <p className="text-sm text-red-600">Couldn't load the dashboard.</p>
      )}

      {dashboard && (
        <>
          <section>
            <h2 className="mb-3 font-medium">Organization Overview</h2>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <StatTile label="Connected providers" value={String(dashboard.connector_count)} />
              <StatTile label="Total files" value={String(snapshot?.total_files ?? 0)} />
              <StatTile label="Total folders" value={String(snapshot?.total_folders ?? 0)} />
              <StatTile
                label="Storage used"
                value={formatBytes(snapshot?.total_storage_bytes ?? 0)}
              />
              <StatTile label="Scan status" value={dashboard.latest_scan_status ?? "—"} />
              <StatTile
                label="Knowledge status"
                value={dashboard.latest_enrichment_status ?? "—"}
              />
              <StatTile label="AI status" value={dashboard.latest_embedding_status ?? "—"} />
              <StatTile
                label="Recommendations status"
                value={dashboard.latest_recommendation_status ?? "—"}
              />
            </div>
          </section>

          <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
            <h2 className="mb-3 font-medium">Storage Health</h2>
            <p className="mb-2 text-sm text-neutral-500">Storage growth over recent runs</p>
            <StorageTrendSparkline
              points={dashboard.snapshot_history.map((s) => s.total_storage_bytes)}
            />
          </section>

          <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
            <h2 className="mb-3 font-medium">Knowledge Health</h2>
            <dl className="grid grid-cols-2 gap-y-2 text-sm sm:grid-cols-4">
              <dt className="text-neutral-500">Classified</dt>
              <dd>{snapshot?.classified_files ?? 0}</dd>
              <dt className="text-neutral-500">Unclassified</dt>
              <dd>{snapshot?.unclassified_files ?? 0}</dd>
              <dt className="text-neutral-500">Pending enrichment</dt>
              <dd>{snapshot?.pending_enrichment_files ?? 0}</dd>
              <dt className="text-neutral-500">Relationships</dt>
              <dd>{snapshot?.relationship_count ?? 0}</dd>
            </dl>
            <p className="mt-3 text-sm text-neutral-500">
              Knowledge completeness:{" "}
              <span className="font-medium text-neutral-900 dark:text-neutral-100">
                {Math.round((snapshot?.knowledge_completeness_score ?? 0) * 100)}%
              </span>
            </p>
          </section>

          <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
            <h2 className="mb-3 font-medium">AI Insights</h2>
            {dashboard.recent_insights.length === 0 ? (
              <p className="text-sm text-neutral-500">No insights generated yet.</p>
            ) : (
              <ul className="flex flex-col gap-2">
                {dashboard.recent_insights.map((insight) => (
                  <li key={insight.id} className="text-sm">
                    <p className="font-medium">{insight.title}</p>
                    <p className="text-neutral-500">{insight.description}</p>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-medium">Recommendation Center</h2>
              <div className="flex items-center gap-3">
                {canManage && (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={refreshMutation.isPending}
                    onClick={() => refreshMutation.mutate()}
                  >
                    {refreshMutation.isPending ? "Refreshing…" : "Refresh recommendations"}
                  </Button>
                )}
                <Link to="/recommendations" className="text-sm underline">
                  View all
                </Link>
              </div>
            </div>
            {topRecommendations.length === 0 ? (
              <p className="text-sm text-neutral-500">No active recommendations right now.</p>
            ) : (
              <ul className="flex flex-col gap-2">
                {topRecommendations.map((recommendation) => (
                  <li key={recommendation.id}>
                    <Link
                      to="/recommendations/$recommendationId"
                      params={{ recommendationId: recommendation.id }}
                      className="flex items-center justify-between gap-3 rounded-lg border border-neutral-200 p-3 text-sm hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900"
                    >
                      <div className="min-w-0">
                        <p className="truncate font-medium">{recommendation.title}</p>
                        <p className="truncate text-neutral-500">
                          {recommendation.estimated_impact}
                        </p>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <span
                          className={`rounded-full px-2 py-1 text-xs font-medium ${categoryColor(recommendation.category)}`}
                        >
                          {categoryLabel(recommendation.category)}
                        </span>
                        <span className={`text-xs ${riskColor(recommendation.risk_level)}`}>
                          {recommendation.risk_level} risk
                        </span>
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
            <h2 className="mb-3 font-medium">Recent Activity</h2>
            {dashboard.recent_activity.length === 0 ? (
              <p className="text-sm text-neutral-500">No recent activity.</p>
            ) : (
              <ul className="flex flex-col gap-2">
                {dashboard.recent_activity.map((file) => (
                  <li
                    key={file.id}
                    className="flex items-center justify-between text-sm"
                  >
                    <span className="truncate">{file.name}</span>
                    <span className="shrink-0 text-neutral-400">
                      {file.provider_modified_at
                        ? formatRelativeTime(file.provider_modified_at)
                        : "—"}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}

      <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
        <h2 className="mb-3 font-medium">Backend connectivity</h2>
        <dl className="grid grid-cols-2 gap-y-2 text-sm">
          <dt className="text-neutral-500">API version</dt>
          <dd>{versionQuery.data?.api_version ?? (versionQuery.isError ? "unreachable" : "loading…")}</dd>

          <dt className="text-neutral-500">Service version</dt>
          <dd>{versionQuery.data?.service_version ?? "—"}</dd>

          <dt className="text-neutral-500">Database</dt>
          <dd>{statusLabel(readinessQuery.data?.checks.database, readinessQuery.isError)}</dd>

          <dt className="text-neutral-500">Redis</dt>
          <dd>{statusLabel(readinessQuery.data?.checks.redis, readinessQuery.isError)}</dd>
        </dl>

        <Button
          className="mt-4"
          variant="outline"
          size="sm"
          onClick={() => {
            void versionQuery.refetch();
            void readinessQuery.refetch();
          }}
        >
          Recheck
        </Button>
      </section>
    </main>
  );
}
