import { useQuery } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { WorkflowExecution } from "@vault/types";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api-client";
import { formatRelativeTime } from "@/lib/format-relative-time";
import { executionStatusColor, isActiveExecutionStatus } from "@/lib/workflow-style";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/workflow-executions")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: ExecutionHistoryPage,
});

function ExecutionHistoryPage() {
  const [status, setStatus] = useState<string>("");

  const params = new URLSearchParams();
  if (status) params.set("status", status);

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
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-8">
      <Link to="/workflows" className="text-sm underline">
        ← Back to Workflow Library
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
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <Button variant="outline" size="sm" onClick={() => setStatus("failed")}>
          Failed runs {failedCount > 0 && status !== "failed" ? `(${failedCount})` : ""}
        </Button>
      </div>

      {executionsQuery.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
      {executionsQuery.isError && (
        <p className="text-sm text-red-600">Couldn't load execution history.</p>
      )}
      {executions.length === 0 && !executionsQuery.isLoading && (
        <p className="text-sm text-neutral-500">No workflow executions match these filters.</p>
      )}

      <ul className="flex flex-col gap-2">
        {executions.map((execution) => (
          <li key={execution.id}>
            <Link
              to="/workflow-executions/$workflowExecutionId"
              params={{ workflowExecutionId: execution.id }}
              className="flex flex-col gap-1 rounded-lg border border-neutral-200 p-3 text-sm hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900"
            >
              <div className="flex items-center justify-between gap-3">
                <span className={`font-medium capitalize ${executionStatusColor(execution.status)}`}>
                  {execution.status}
                </span>
                <span className="text-xs capitalize text-neutral-400">
                  {execution.trigger_type}
                </span>
              </div>
              {execution.error && <p className="text-red-600">{execution.error}</p>}
              <span className="text-xs text-neutral-400">
                {formatRelativeTime(execution.created_at)}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
