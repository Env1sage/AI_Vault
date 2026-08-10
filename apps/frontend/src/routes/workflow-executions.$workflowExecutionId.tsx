import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { WorkflowExecution, WorkflowExecutionDetail } from "@vault/types";

import { Button } from "@/components/ui/button";
import { ApiError, apiClient } from "@/lib/api-client";
import { formatRelativeTime } from "@/lib/format-relative-time";
import {
  executionStatusColor,
  isActiveExecutionStatus,
  nodeExecutionStatusColor,
} from "@/lib/workflow-style";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/workflow-executions/$workflowExecutionId")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: WorkflowExecutionDetailPage,
});

function WorkflowExecutionDetailPage() {
  const { workflowExecutionId } = Route.useParams();
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const canManage = user?.role === "owner" || user?.role === "admin";

  const detailQuery = useQuery({
    queryKey: ["workflow-executions", workflowExecutionId],
    queryFn: () =>
      apiClient.get<WorkflowExecutionDetail>(`/v1/workflow-executions/${workflowExecutionId}`),
    refetchInterval: (query) =>
      query.state.data && isActiveExecutionStatus(query.state.data.status) ? 3000 : false,
  });

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ["workflow-executions", workflowExecutionId] });
    void queryClient.invalidateQueries({ queryKey: ["workflow-executions"] });
  }

  const cancelMutation = useMutation({
    mutationFn: () =>
      apiClient.post<WorkflowExecution>(`/v1/workflow-executions/${workflowExecutionId}/cancel`),
    onSuccess: invalidate,
  });
  const pauseMutation = useMutation({
    mutationFn: () =>
      apiClient.post<WorkflowExecution>(`/v1/workflow-executions/${workflowExecutionId}/pause`),
    onSuccess: invalidate,
  });
  const resumeMutation = useMutation({
    mutationFn: () =>
      apiClient.post<WorkflowExecution>(`/v1/workflow-executions/${workflowExecutionId}/resume`),
    onSuccess: invalidate,
  });

  const execution = detailQuery.data;
  const anyActionPending =
    cancelMutation.isPending || pauseMutation.isPending || resumeMutation.isPending;
  const anyActionError = cancelMutation.error ?? pauseMutation.error ?? resumeMutation.error;

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-8">
      <Link to="/workflow-executions" className="text-sm underline">
        ← Back to Execution History
      </Link>

      {detailQuery.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
      {detailQuery.isError && (
        <p className="text-sm text-red-600">Couldn't load this execution.</p>
      )}

      {execution && (
        <>
          <div>
            <div className="flex items-center gap-2">
              <span className={`font-medium capitalize ${executionStatusColor(execution.status)}`}>
                {execution.status}
              </span>
              <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-xs capitalize dark:bg-neutral-900">
                {execution.trigger_type} trigger
              </span>
            </div>
            <h1 className="text-xl font-semibold">Workflow execution</h1>
            {execution.error && <p className="mt-1 text-sm text-red-600">{execution.error}</p>}
            <Link
              to="/workflows/$workflowId"
              params={{ workflowId: execution.workflow_id }}
              className="text-sm underline"
            >
              view workflow
            </Link>
          </div>

          {canManage && isActiveExecutionStatus(execution.status) && (
            <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
              <h2 className="mb-3 font-medium">Controls</h2>
              <div className="flex flex-wrap gap-2">
                {execution.status === "running" && (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={anyActionPending}
                    onClick={() => pauseMutation.mutate()}
                  >
                    Pause
                  </Button>
                )}
                {execution.status === "paused" && (
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
                    : "Couldn't update this execution."}
                </p>
              )}
            </section>
          )}

          <section>
            <h2 className="mb-3 font-medium">
              Execution log ({execution.node_executions.length} nodes run)
            </h2>
            {execution.node_executions.length === 0 ? (
              <p className="text-sm text-neutral-500">No nodes have run yet for this execution.</p>
            ) : (
              <ul className="flex flex-col gap-2">
                {execution.node_executions.map((nodeExecution) => (
                  <li
                    key={nodeExecution.id}
                    className="rounded-lg border border-neutral-200 p-3 text-sm dark:border-neutral-800"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span
                        className={`font-medium capitalize ${nodeExecutionStatusColor(nodeExecution.status)}`}
                      >
                        {nodeExecution.status.replace(/_/g, " ")}
                      </span>
                      {nodeExecution.started_at && (
                        <span className="text-xs text-neutral-400">
                          {formatRelativeTime(nodeExecution.started_at)}
                        </span>
                      )}
                    </div>
                    {nodeExecution.error && (
                      <p className="text-xs text-red-600">{nodeExecution.error}</p>
                    )}
                    {Object.keys(nodeExecution.output_context).length > 0 && (
                      <pre className="mt-1 overflow-x-auto rounded bg-neutral-100 p-2 text-xs dark:bg-neutral-900">
                        {JSON.stringify(nodeExecution.output_context, null, 2)}
                      </pre>
                    )}
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
