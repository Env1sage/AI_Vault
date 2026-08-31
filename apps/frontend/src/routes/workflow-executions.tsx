import { useQuery } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { WorkflowExecution } from "@vault/types";
import { AlertOctagon, ChevronLeft, Workflow as WorkflowIcon } from "lucide-react";
import { useState } from "react";

import { AppShell } from "@/components/app-shell/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { apiClient } from "@/lib/api-client";
import { formatRelativeTime } from "@/lib/format-relative-time";
import { executionStatusBadgeVariant, isActiveExecutionStatus } from "@/lib/workflow-style";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/workflow-executions")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: ExecutionHistoryPage,
});

const STATUSES = ["pending", "running", "paused", "completed", "failed", "cancelled"];

function ExecutionHistoryPage() {
  const [status, setStatus] = useState<string>("all");

  const params = new URLSearchParams();
  if (status !== "all") params.set("status", status);

  const executionsQuery = useQuery({
    queryKey: ["workflow-executions", status],
    queryFn: () =>
      apiClient.get<WorkflowExecution[]>(`/v1/workflow-executions?${params.toString()}`),
    refetchInterval: (query) =>
      query.state.data?.some((e) => isActiveExecutionStatus(e.status)) ? 3000 : false,
  });

  const executions = executionsQuery.data ?? [];
  const failedCount = executions.filter((e) => e.status === "failed").length;

  return (
    <AppShell title="Workflow Executions">
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        <Link
          to="/workflows"
          className="flex w-fit items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ChevronLeft className="size-4" /> Back to Workflow Library
        </Link>
        <h1 className="text-xl font-semibold tracking-tight">Execution History</h1>

        <div className="flex flex-wrap gap-2">
          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger className="w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              {STATUSES.map((s) => (
                <SelectItem key={s} value={s} className="capitalize">
                  {s}
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
            Failed runs {failedCount > 0 && status !== "failed" ? `(${failedCount})` : ""}
          </Button>
        </div>

        {executionsQuery.isLoading && (
          <div className="flex flex-col gap-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-16 rounded-xl" />
            ))}
          </div>
        )}
        {executionsQuery.isError && (
          <EmptyState title="Couldn't load execution history" description="Please try again." />
        )}
        {executions.length === 0 && !executionsQuery.isLoading && (
          <EmptyState
            icon={WorkflowIcon}
            title="No workflow executions match these filters"
            description="Trigger a workflow to see it appear here."
          />
        )}

        <ul className="flex flex-col gap-2">
          {executions.map((execution) => (
            <li key={execution.id}>
              <Link
                to="/workflow-executions/$workflowExecutionId"
                params={{ workflowExecutionId: execution.id }}
                className="flex flex-col gap-1 rounded-xl border border-border bg-card p-4 text-sm shadow-clay-sm transition-all hover:-translate-y-0.5 hover:shadow-clay"
              >
                <div className="flex items-center justify-between gap-3">
                  <Badge variant={executionStatusBadgeVariant(execution.status)} className="capitalize">
                    {execution.status}
                  </Badge>
                  <span className="text-xs capitalize text-muted-foreground">{execution.trigger_type}</span>
                </div>
                {execution.error && <p className="text-destructive">{execution.error}</p>}
                <span className="text-xs text-muted-foreground">
                  {formatRelativeTime(execution.created_at)}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </AppShell>
  );
}
