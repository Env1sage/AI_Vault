import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { ExecutionJob, ExecutionJobDetail } from "@vault/types";

import { Button } from "@/components/ui/button";
import { ApiError, apiClient } from "@/lib/api-client";
import { isActiveJobStatus, jobStatusColor } from "@/lib/execution-style";
import { formatRelativeTime } from "@/lib/format-relative-time";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/execution-jobs/$executionJobId")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: ExecutionJobDetailPage,
});

function ExecutionJobDetailPage() {
  const { executionJobId } = Route.useParams();
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const canManage = user?.role === "owner" || user?.role === "admin";

  const jobQuery = useQuery({
    queryKey: ["execution-jobs", executionJobId],
    queryFn: () => apiClient.get<ExecutionJobDetail>(`/v1/execution-jobs/${executionJobId}`),
    refetchInterval: (query) =>
      query.state.data && isActiveJobStatus(query.state.data.status) ? 3000 : false,
  });

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ["execution-jobs", executionJobId] });
    void queryClient.invalidateQueries({ queryKey: ["execution-jobs"] });
  }

  const cancelMutation = useMutation({
    mutationFn: () => apiClient.post<ExecutionJob>(`/v1/execution-jobs/${executionJobId}/cancel`),
    onSuccess: invalidate,
  });
  const pauseMutation = useMutation({
    mutationFn: () => apiClient.post<ExecutionJob>(`/v1/execution-jobs/${executionJobId}/pause`),
    onSuccess: invalidate,
  });
  const resumeMutation = useMutation({
    mutationFn: () => apiClient.post<ExecutionJob>(`/v1/execution-jobs/${executionJobId}/resume`),
    onSuccess: invalidate,
  });

  const job = jobQuery.data;
  const anyActionPending =
    cancelMutation.isPending || pauseMutation.isPending || resumeMutation.isPending;
  const anyActionError = cancelMutation.error ?? pauseMutation.error ?? resumeMutation.error;

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-8">
      <Link to="/execution-jobs" className="text-sm underline">
        ← Back to Execution History
      </Link>

      {jobQuery.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
      {jobQuery.isError && (
        <p className="text-sm text-red-600">
          Couldn't load this execution job — you may not have permission to view it.
        </p>
      )}

      {job && (
        <>
          <div>
            <div className="flex items-center gap-2">
              <span className={`font-medium capitalize ${jobStatusColor(job.status)}`}>
                {job.status.replace(/_/g, " ")}
              </span>
              {job.is_rollback && (
                <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-xs dark:bg-neutral-900">
                  rollback job
                </span>
              )}
            </div>
            <h1 className="text-xl font-semibold">
              {job.is_rollback ? "Rollback progress" : "Execution progress"}
            </h1>
            {job.error && <p className="mt-1 text-sm text-red-600">{job.error}</p>}
            <Link
              to="/execution-plans/$executionPlanId"
              params={{ executionPlanId: job.execution_plan_id }}
              className="text-sm underline"
            >
              view plan
            </Link>
          </div>

          {canManage && isActiveJobStatus(job.status) && (
            <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
              <h2 className="mb-3 font-medium">Controls</h2>
              <div className="flex flex-wrap gap-2">
                {job.status === "running" && (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={anyActionPending}
                    onClick={() => pauseMutation.mutate()}
                  >
                    Pause
                  </Button>
                )}
                {job.status === "paused" && (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={anyActionPending}
                    onClick={() => resumeMutation.mutate()}
                  >
                    Resume
                  </Button>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  disabled={anyActionPending}
                  onClick={() => cancelMutation.mutate()}
                >
                  Cancel
                </Button>
              </div>
              {anyActionError && (
                <p className="mt-2 text-sm text-red-600">
                  {anyActionError instanceof ApiError
                    ? anyActionError.message
                    : "Couldn't update this job."}
                </p>
              )}
            </section>
          )}

          <section>
            <h2 className="mb-3 font-medium">Timeline ({job.results.length} steps executed)</h2>
            {job.results.length === 0 ? (
              <p className="text-sm text-neutral-500">
                No steps have executed yet for this job.
              </p>
            ) : (
              <ul className="flex flex-col gap-2">
                {job.results.map((result) => (
                  <li
                    key={result.id}
                    className="rounded-lg border border-neutral-200 p-3 text-sm dark:border-neutral-800"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span
                        className={
                          result.status === "success" ? "font-medium text-green-600" : "font-medium text-red-600"
                        }
                      >
                        {result.status}
                      </span>
                      <span className="text-xs text-neutral-400">
                        {formatRelativeTime(result.executed_at)}
                      </span>
                    </div>
                    <p className="text-xs text-neutral-500">
                      verification: {result.verification_status}
                    </p>
                    {result.error && <p className="text-xs text-red-600">{result.error}</p>}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </main>
  );
}
