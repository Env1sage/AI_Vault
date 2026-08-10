import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { Connector, EmbeddingJob, EnrichmentJob, ScanJob } from "@vault/types";

import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api-client";
import { embeddingStatusColor, isActiveEmbeddingStatus } from "@/lib/embedding-status";
import { enrichmentStatusColor, isActiveEnrichmentStatus } from "@/lib/enrichment-status";
import { formatRelativeTime } from "@/lib/format-relative-time";
import { isActiveScanStatus, scanStatusColor } from "@/lib/scan-status";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/scans")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: ScansPage,
});

function ScansPage() {
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const canManage = user?.role === "owner" || user?.role === "admin";

  const connectorsQuery = useQuery({
    queryKey: ["connectors"],
    queryFn: () => apiClient.get<Connector[]>("/v1/connectors"),
  });

  const connector = connectorsQuery.data?.find(
    (candidate) => candidate.provider === "google_workspace" && candidate.status === "connected",
  );

  const scansQuery = useQuery({
    queryKey: ["scans", connector?.id],
    queryFn: () => apiClient.get<ScanJob[]>(`/v1/connectors/${connector?.id}/scans`),
    enabled: connector !== undefined,
    refetchInterval: (query) =>
      query.state.data?.some((job) => isActiveScanStatus(job.status)) ? 3000 : false,
  });

  const startMutation = useMutation({
    mutationFn: () => apiClient.post<ScanJob>(`/v1/connectors/${connector?.id}/scans`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["scans", connector?.id] }),
  });

  const cancelMutation = useMutation({
    mutationFn: (scanJobId: string) => apiClient.post<ScanJob>(`/v1/scans/${scanJobId}/cancel`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["scans", connector?.id] }),
  });

  const enrichmentQuery = useQuery({
    queryKey: ["enrichment", connector?.id],
    queryFn: () =>
      apiClient.get<EnrichmentJob[]>(`/v1/connectors/${connector?.id}/enrichment`),
    enabled: connector !== undefined,
    refetchInterval: (query) =>
      query.state.data?.some((job) => isActiveEnrichmentStatus(job.status)) ? 3000 : false,
  });

  const startEnrichmentMutation = useMutation({
    mutationFn: () => apiClient.post<EnrichmentJob>(`/v1/connectors/${connector?.id}/enrichment`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["enrichment", connector?.id] }),
  });

  const cancelEnrichmentMutation = useMutation({
    mutationFn: (enrichmentJobId: string) =>
      apiClient.post<EnrichmentJob>(`/v1/enrichment/${enrichmentJobId}/cancel`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["enrichment", connector?.id] }),
  });

  const embeddingQuery = useQuery({
    queryKey: ["embedding", connector?.id],
    queryFn: () => apiClient.get<EmbeddingJob[]>(`/v1/connectors/${connector?.id}/embedding`),
    enabled: connector !== undefined,
    refetchInterval: (query) =>
      query.state.data?.some((job) => isActiveEmbeddingStatus(job.status)) ? 3000 : false,
  });

  const startEmbeddingMutation = useMutation({
    mutationFn: () => apiClient.post<EmbeddingJob>(`/v1/connectors/${connector?.id}/embedding`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["embedding", connector?.id] }),
  });

  const cancelEmbeddingMutation = useMutation({
    mutationFn: (embeddingJobId: string) =>
      apiClient.post<EmbeddingJob>(`/v1/embedding/${embeddingJobId}/cancel`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["embedding", connector?.id] }),
  });

  const jobs = scansQuery.data ?? [];
  const activeJob = jobs.find((job) => isActiveScanStatus(job.status));
  const lastCompletedJob = jobs.find((job) => job.status === "completed");

  const enrichmentJobs = enrichmentQuery.data ?? [];
  const activeEnrichmentJob = enrichmentJobs.find((job) => isActiveEnrichmentStatus(job.status));
  const lastCompletedEnrichmentJob = enrichmentJobs.find((job) => job.status === "completed");

  const embeddingJobs = embeddingQuery.data ?? [];
  const activeEmbeddingJob = embeddingJobs.find((job) => isActiveEmbeddingStatus(job.status));
  const lastCompletedEmbeddingJob = embeddingJobs.find((job) => job.status === "completed");

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-8">
      <Link to="/dashboard" className="text-sm underline">
        ← Back to dashboard
      </Link>
      <h1 className="text-xl font-semibold">Scans</h1>

      {connectorsQuery.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
      {connectorsQuery.isError && (
        <p className="text-sm text-red-600">Couldn't load storage connections.</p>
      )}

      {!connectorsQuery.isLoading && connector === undefined && (
        <p className="text-sm text-neutral-500">
          Connect Google Workspace first — see{" "}
          <Link to="/storage-connections" className="underline">
            Storage Connections
          </Link>
          .
        </p>
      )}

      {connector && (
        <>
          <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
            <h2 className="mb-3 font-medium">Current status</h2>

            {activeJob ? (
              <div className="flex flex-col gap-2 text-sm">
                <p>
                  <span className={`font-medium capitalize ${scanStatusColor(activeJob.status)}`}>
                    {activeJob.status}
                  </span>
                  {activeJob.progress?.current_source_name
                    ? ` — scanning ${activeJob.progress.current_source_name}`
                    : ""}
                </p>
                {activeJob.progress && (
                  <p className="text-neutral-500">
                    {activeJob.progress.sources_completed}/{activeJob.progress.sources_discovered}{" "}
                    sources · {activeJob.progress.folders_discovered} folders ·{" "}
                    {activeJob.progress.files_discovered} files
                  </p>
                )}
                {canManage && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-fit"
                    disabled={cancelMutation.isPending}
                    onClick={() => cancelMutation.mutate(activeJob.id)}
                  >
                    {cancelMutation.isPending ? "Cancelling…" : "Cancel scan"}
                  </Button>
                )}
              </div>
            ) : (
              <div className="flex flex-col gap-3 text-sm">
                <p className="text-neutral-500">
                  {lastCompletedJob
                    ? `Last successful scan: ${formatRelativeTime(lastCompletedJob.completed_at ?? lastCompletedJob.created_at)}`
                    : "No scans yet."}
                </p>
                {canManage && (
                  <Button
                    className="w-fit"
                    disabled={startMutation.isPending}
                    onClick={() => startMutation.mutate()}
                  >
                    {startMutation.isPending ? "Starting…" : "Start scan"}
                  </Button>
                )}
                {startMutation.isError && (
                  <p className="text-sm text-red-600">Couldn't start a scan. Please try again.</p>
                )}
              </div>
            )}
          </section>

          <section>
            <h2 className="mb-3 font-medium">Scan history</h2>
            {scansQuery.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
            {scansQuery.isError && (
              <p className="text-sm text-red-600">Couldn't load scan history.</p>
            )}
            {jobs.length === 0 && !scansQuery.isLoading && (
              <p className="text-sm text-neutral-500">No scans have run yet.</p>
            )}
            <ul className="flex flex-col gap-2">
              {jobs.map((job) => (
                <li
                  key={job.id}
                  className="flex items-center justify-between rounded-lg border border-neutral-200 p-3 text-sm dark:border-neutral-800"
                >
                  <div>
                    <span className={`font-medium capitalize ${scanStatusColor(job.status)}`}>
                      {job.status}
                    </span>
                    <span className="ml-2 text-neutral-500">{job.scan_type}</span>
                    {job.error && <p className="mt-1 text-red-600">{job.error}</p>}
                  </div>
                  <span className="text-neutral-400">{formatRelativeTime(job.created_at)}</span>
                </li>
              ))}
            </ul>
          </section>

          <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-medium">Enrichment</h2>
              <Link to="/files" className="text-sm underline">
                Browse files
              </Link>
            </div>

            {activeEnrichmentJob ? (
              <div className="flex flex-col gap-2 text-sm">
                <p>
                  <span
                    className={`font-medium capitalize ${enrichmentStatusColor(activeEnrichmentJob.status)}`}
                  >
                    {activeEnrichmentJob.status}
                  </span>
                  {activeEnrichmentJob.progress?.current_file_name
                    ? ` — enriching ${activeEnrichmentJob.progress.current_file_name}`
                    : ""}
                </p>
                {activeEnrichmentJob.progress && (
                  <p className="text-neutral-500">
                    {activeEnrichmentJob.progress.files_processed}/
                    {activeEnrichmentJob.progress.files_pending} files ·{" "}
                    {activeEnrichmentJob.progress.files_failed} failed
                  </p>
                )}
                {canManage && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-fit"
                    disabled={cancelEnrichmentMutation.isPending}
                    onClick={() => cancelEnrichmentMutation.mutate(activeEnrichmentJob.id)}
                  >
                    {cancelEnrichmentMutation.isPending ? "Cancelling…" : "Cancel enrichment"}
                  </Button>
                )}
              </div>
            ) : (
              <div className="flex flex-col gap-3 text-sm">
                <p className="text-neutral-500">
                  {lastCompletedEnrichmentJob
                    ? `Last enrichment: ${formatRelativeTime(
                        lastCompletedEnrichmentJob.completed_at ??
                          lastCompletedEnrichmentJob.created_at,
                      )}`
                    : "No enrichment has run yet."}
                </p>
                {canManage && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-fit"
                    disabled={startEnrichmentMutation.isPending}
                    onClick={() => startEnrichmentMutation.mutate()}
                  >
                    {startEnrichmentMutation.isPending ? "Starting…" : "Re-run enrichment"}
                  </Button>
                )}
                {startEnrichmentMutation.isError && (
                  <p className="text-sm text-red-600">
                    Couldn't start enrichment. Please try again.
                  </p>
                )}
              </div>
            )}
          </section>

          <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-medium">Embedding</h2>
              <Link to="/search" className="text-sm underline">
                Search
              </Link>
            </div>

            {activeEmbeddingJob ? (
              <div className="flex flex-col gap-2 text-sm">
                <p>
                  <span
                    className={`font-medium capitalize ${embeddingStatusColor(activeEmbeddingJob.status)}`}
                  >
                    {activeEmbeddingJob.status}
                  </span>
                  {activeEmbeddingJob.progress?.current_file_name
                    ? ` — embedding ${activeEmbeddingJob.progress.current_file_name}`
                    : ""}
                </p>
                {activeEmbeddingJob.progress && (
                  <p className="text-neutral-500">
                    {activeEmbeddingJob.progress.files_processed}/
                    {activeEmbeddingJob.progress.files_pending} files ·{" "}
                    {activeEmbeddingJob.progress.files_failed} failed
                  </p>
                )}
                {canManage && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-fit"
                    disabled={cancelEmbeddingMutation.isPending}
                    onClick={() => cancelEmbeddingMutation.mutate(activeEmbeddingJob.id)}
                  >
                    {cancelEmbeddingMutation.isPending ? "Cancelling…" : "Cancel embedding"}
                  </Button>
                )}
              </div>
            ) : (
              <div className="flex flex-col gap-3 text-sm">
                <p className="text-neutral-500">
                  {lastCompletedEmbeddingJob
                    ? `Last embedding run: ${formatRelativeTime(
                        lastCompletedEmbeddingJob.completed_at ??
                          lastCompletedEmbeddingJob.created_at,
                      )}`
                    : "No embedding run yet."}
                </p>
                {canManage && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-fit"
                    disabled={startEmbeddingMutation.isPending}
                    onClick={() => startEmbeddingMutation.mutate()}
                  >
                    {startEmbeddingMutation.isPending ? "Starting…" : "Re-run embedding"}
                  </Button>
                )}
                {startEmbeddingMutation.isError && (
                  <p className="text-sm text-red-600">
                    Couldn't start embedding. Please try again.
                  </p>
                )}
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
}
