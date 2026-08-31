import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { ExecutionJob } from "@vault/types";
import { AlertOctagon, ChevronLeft, PlayCircle } from "lucide-react";
import { useState } from "react";

import { AppShell } from "@/components/app-shell/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, apiClient } from "@/lib/api-client";
import { isActiveJobStatus, jobStatusBadgeVariant } from "@/lib/execution-style";
import { formatRelativeTime } from "@/lib/format-relative-time";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/execution-jobs/")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: ExecutionHistoryPage,
});

const STATUSES = ["pending", "running", "paused", "completed", "partially_completed", "failed", "cancelled"];

function ExecutionHistoryPage() {
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const canManage = user?.role === "owner" || user?.role === "admin";
  const [status, setStatus] = useState<string>("all");

  const params = new URLSearchParams();
  if (status !== "all") params.set("status", status);

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
    <AppShell title="Execution History">
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        <Link
          to="/execution-plans"
          className="flex w-fit items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ChevronLeft className="size-4" /> Back to Execution Center
        </Link>
        <h1 className="text-xl font-semibold tracking-tight">Execution History</h1>

        <div className="flex flex-wrap gap-2">
          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              {STATUSES.map((s) => (
                <SelectItem key={s} value={s} className="capitalize">
                  {s.replace(/_/g, " ")}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            variant={status === "failed" ? "destructive" : "outline"}
            size="sm"
            onClick={() => setStatus("failed")}
          >
            <AlertOctagon className="size-4" />
            Failed jobs {failedCount > 0 && status !== "failed" ? `(${failedCount})` : ""}
          </Button>
        </div>

        {jobsQuery.isLoading && (
          <div className="flex flex-col gap-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-16 rounded-xl" />
            ))}
          </div>
        )}
        {jobsQuery.isError && (
          <EmptyState title="Couldn't load execution jobs" description="Please try again." />
        )}
        {jobs.length === 0 && !jobsQuery.isLoading && (
          <EmptyState
            icon={PlayCircle}
            title="No execution jobs match these filters"
            description="Jobs appear here once an approved plan starts running."
          />
        )}

        <ul className="flex flex-col gap-2">
          {jobs.map((job) => (
            <Card key={job.id} className="flex flex-col gap-2 p-4">
              <div className="flex items-center justify-between gap-3">
                <Link
                  to="/execution-jobs/$executionJobId"
                  params={{ executionJobId: job.id }}
                  className="flex items-center gap-2"
                >
                  <Badge variant={jobStatusBadgeVariant(job.status)} className="capitalize">
                    {job.status.replace(/_/g, " ")}
                  </Badge>
                  {job.is_rollback && <Badge variant="outline">rollback</Badge>}
                </Link>
                {canManage && isActiveJobStatus(job.status) && (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={cancelMutation.isPending}
                    onClick={() => cancelMutation.mutate(job.id)}
                  >
                    {cancelMutation.isPending && cancelMutation.variables === job.id
                      ? "Cancelling…"
                      : "Cancel"}
                  </Button>
                )}
              </div>
              {job.error && <p className="text-sm text-destructive">{job.error}</p>}
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <Link
                  to="/execution-plans/$executionPlanId"
                  params={{ executionPlanId: job.execution_plan_id }}
                  className="text-primary hover:underline"
                >
                  view plan
                </Link>
                <span>{formatRelativeTime(job.created_at)}</span>
              </div>
            </Card>
          ))}
        </ul>

        {cancelMutation.isError && (
          <p className="text-sm text-destructive">
            {cancelMutation.error instanceof ApiError
              ? cancelMutation.error.message
              : "Couldn't cancel this job."}
          </p>
        )}
      </div>
    </AppShell>
  );
}
