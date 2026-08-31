import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { ExecutionJob, ExecutionJobDetail } from "@vault/types";
import { CheckCircle2, ChevronLeft, Pause, Play, XCircle } from "lucide-react";

import { AppShell } from "@/components/app-shell/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, apiClient } from "@/lib/api-client";
import { isActiveJobStatus, jobStatusBadgeVariant } from "@/lib/execution-style";
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
    <AppShell title="Execution job">
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        <Link
          to="/execution-jobs"
          className="flex w-fit items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ChevronLeft className="size-4" /> Back to Execution History
        </Link>

        {jobQuery.isLoading && <Skeleton className="h-56 rounded-2xl" />}
        {jobQuery.isError && (
          <p className="text-sm text-destructive">
            Couldn&rsquo;t load this execution job — you may not have permission to view it.
          </p>
        )}

        {job && (
          <>
            <Card clay className="p-6">
              <div className="flex items-center gap-2">
                <Badge variant={jobStatusBadgeVariant(job.status)} className="capitalize">
                  {job.status.replace(/_/g, " ")}
                </Badge>
                {job.is_rollback && <Badge variant="outline">rollback job</Badge>}
              </div>
              <h1 className="mt-2 text-lg font-semibold">
                {job.is_rollback ? "Rollback progress" : "Execution progress"}
              </h1>
              {job.error && <p className="mt-1 text-sm text-destructive">{job.error}</p>}
              <Link
                to="/execution-plans/$executionPlanId"
                params={{ executionPlanId: job.execution_plan_id }}
                className="text-sm text-primary hover:underline"
              >
                view plan
              </Link>
            </Card>

            {canManage && isActiveJobStatus(job.status) && (
              <Card>
                <CardHeader>
                  <CardTitle>Controls</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {job.status === "running" && (
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={anyActionPending}
                        onClick={() => pauseMutation.mutate()}
                      >
                        <Pause className="size-4" /> {pauseMutation.isPending ? "Pausing…" : "Pause"}
                      </Button>
                    )}
                    {job.status === "paused" && (
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={anyActionPending}
                        onClick={() => resumeMutation.mutate()}
                      >
                        <Play className="size-4" /> {resumeMutation.isPending ? "Resuming…" : "Resume"}
                      </Button>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={anyActionPending}
                      onClick={() => cancelMutation.mutate()}
                    >
                      <XCircle className="size-4" /> {cancelMutation.isPending ? "Cancelling…" : "Cancel"}
                    </Button>
                  </div>
                  {anyActionError && (
                    <p className="mt-2 text-sm text-destructive">
                      {anyActionError instanceof ApiError
                        ? anyActionError.message
                        : "Couldn't update this job."}
                    </p>
                  )}
                </CardContent>
              </Card>
            )}

            <Card>
              <CardHeader>
                <CardTitle>Timeline ({job.results.length} steps executed)</CardTitle>
              </CardHeader>
              <CardContent>
                {job.results.length === 0 ? (
                  <EmptyState title="No steps executed yet" description="Check back shortly." />
                ) : (
                  <ul className="flex flex-col divide-y divide-border">
                    {job.results.map((result) => (
                      <li key={result.id} className="flex flex-col gap-1 py-2.5 text-sm">
                        <div className="flex items-center justify-between gap-3">
                          <span
                            className={`flex items-center gap-1.5 font-medium ${
                              result.status === "success" ? "text-success" : "text-destructive"
                            }`}
                          >
                            {result.status === "success" ? (
                              <CheckCircle2 className="size-4" />
                            ) : (
                              <XCircle className="size-4" />
                            )}
                            {result.status}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {formatRelativeTime(result.executed_at)}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          verification: {result.verification_status}
                        </p>
                        {result.error && <p className="text-xs text-destructive">{result.error}</p>}
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </AppShell>
  );
}
