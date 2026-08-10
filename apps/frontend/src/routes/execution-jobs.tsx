import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { ExecutionJob } from "@vault/types";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, apiClient } from "@/lib/api-client";
import { isActiveJobStatus, jobStatusColor } from "@/lib/execution-style";
import { formatRelativeTime } from "@/lib/format-relative-time";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/execution-jobs")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: ExecutionHistoryPage,
});

function ExecutionHistoryPage() {
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const canManage = user?.role === "owner" || user?.role === "admin";
  const [status, setStatus] = useState<string>("");

  const params = new URLSearchParams();
  if (status) params.set("status", status);

  const jobsQuery = useQuery({
    queryKey: ["execution-jobs", status],
    queryFn: () => apiClient.get<ExecutionJob[]>(`/v1/execution-jobs?${params.toString()}`),
    refetchInterval: (query) =>
      query.state.data?.some((job) => isActiveJobStatus(job.status)) ? 3000 : false,
  });

  const cancelMutation = useMutation({
    mutationFn: (jobId: string) => apiClient.post<ExecutionJob>(`/v1/execution-jobs/${jobId}/cancel`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["execution-jobs"] }),
  });

  const jobs = jobsQuery.data ?? [];
  const failedCount = jobs.filter(
    (job) => job.status === "failed" || job.status === "partially_completed",
  ).length;

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-8">
      <Link to="/execution-plans" className="text-sm underline">
        ← Back to Execution Center
      </Link>
      <h1 className="text-xl font-semibold">Execution History</h1>

      <div className="flex flex-wrap gap-2">
        <select
          value={status}
          onChange={(event) => setStatus(event.target.value)}
          className="rounded-md border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-800 dark:bg-neutral-950"
        >
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="running">Running</option>
          <option value="paused">Paused</option>
          <option value="completed">Completed</option>
          <option value="partially_completed">Partially completed</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setStatus("failed")}
        >
          Failed jobs {failedCount > 0 && status !== "failed" ? `(${failedCount})` : ""}
        </Button>
      </div>

      {jobsQuery.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
      {jobsQuery.isError && <p className="text-sm text-red-600">Couldn't load execution jobs.</p>}
      {jobs.length === 0 && !jobsQuery.isLoading && (
        <p className="text-sm text-neutral-500">No execution jobs match these filters.</p>
      )}

      <ul className="flex flex-col gap-2">
        {jobs.map((job) => (
          <li
            key={job.id}
            className="flex flex-col gap-2 rounded-lg border border-neutral-200 p-3 text-sm dark:border-neutral-800"
          >
            <div className="flex items-center justify-between gap-3">
              <Link
                to="/execution-jobs/$executionJobId"
                params={{ executionJobId: job.id }}
                className="flex items-center gap-2 underline"
              >
                <span className={`font-medium capitalize ${jobStatusColor(job.status)}`}>
                  {job.status.replace(/_/g, " ")}
                </span>
                {job.is_rollback && (
                  <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-xs dark:bg-neutral-900">
                    rollback
                  </span>
                )}
              </Link>
              {canManage && isActiveJobStatus(job.status) && (
                <Button
                  variant="outline"
                  size="sm"
                  disabled={cancelMutation.isPending}
                  onClick={() => cancelMutation.mutate(job.id)}
                >
                  Cancel
                </Button>
              )}
            </div>
            {job.error && <p className="text-red-600">{job.error}</p>}
            <div className="flex items-center gap-3 text-xs text-neutral-400">
              <Link
                to="/execution-plans/$executionPlanId"
                params={{ executionPlanId: job.execution_plan_id }}
                className="underline"
              >
                view plan
              </Link>
              <span>{formatRelativeTime(job.created_at)}</span>
            </div>
          </li>
        ))}
      </ul>

      {cancelMutation.isError && (
        <p className="text-sm text-red-600">
          {cancelMutation.error instanceof ApiError
            ? cancelMutation.error.message
            : "Couldn't cancel this job."}
        </p>
      )}
    </main>
  );
}
