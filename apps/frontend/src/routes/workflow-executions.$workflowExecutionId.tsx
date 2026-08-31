import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { WorkflowExecution, WorkflowExecutionDetail } from "@vault/types";
import { ChevronLeft, Pause, Play, XCircle } from "lucide-react";

import { AppShell } from "@/components/app-shell/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, apiClient } from "@/lib/api-client";
import { formatRelativeTime } from "@/lib/format-relative-time";
import {
  executionStatusBadgeVariant,
  isActiveExecutionStatus,
  nodeExecutionStatusBadgeVariant,
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
    <AppShell title="Workflow execution">
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        <Link
          to="/workflow-executions"
          className="flex w-fit items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ChevronLeft className="size-4" /> Back to Execution History
        </Link>

        {detailQuery.isLoading && <Skeleton className="h-56 rounded-2xl" />}
        {detailQuery.isError && (
          <p className="text-sm text-destructive">Couldn&rsquo;t load this execution.</p>
        )}

        {execution && (
          <>
            <Card clay className="p-6">
              <div className="flex items-center gap-2">
                <Badge variant={executionStatusBadgeVariant(execution.status)} className="capitalize">
                  {execution.status}
                </Badge>
                <Badge variant="outline" className="capitalize">
                  {execution.trigger_type} trigger
                </Badge>
              </div>
              <h1 className="mt-2 text-lg font-semibold">Workflow execution</h1>
              {execution.error && <p className="mt-1 text-sm text-destructive">{execution.error}</p>}
              <Link
                to="/workflows/$workflowId"
                params={{ workflowId: execution.workflow_id }}
                className="text-sm text-primary hover:underline"
              >
                view workflow
              </Link>
            </Card>

            {canManage && isActiveExecutionStatus(execution.status) && (
              <Card>
                <CardHeader>
                  <CardTitle>Controls</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {execution.status === "running" && (
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={anyActionPending}
                        onClick={() => pauseMutation.mutate()}
                      >
                        <Pause className="size-4" /> {pauseMutation.isPending ? "Pausing…" : "Pause"}
                      </Button>
                    )}
                    {execution.status === "paused" && (
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
                        : "Couldn't update this execution."}
                    </p>
                  )}
                </CardContent>
              </Card>
            )}

            <Card>
              <CardHeader>
                <CardTitle>Execution log ({execution.node_executions.length} nodes run)</CardTitle>
              </CardHeader>
              <CardContent>
                {execution.node_executions.length === 0 ? (
                  <EmptyState title="No nodes have run yet" description="Check back shortly." />
                ) : (
                  <ul className="flex flex-col divide-y divide-border">
                    {execution.node_executions.map((nodeExecution) => (
                      <li key={nodeExecution.id} className="py-2.5 text-sm">
                        <div className="flex items-center justify-between gap-3">
                          <Badge
                            variant={nodeExecutionStatusBadgeVariant(nodeExecution.status)}
                            className="capitalize"
                          >
                            {nodeExecution.status.replace(/_/g, " ")}
                          </Badge>
                          {nodeExecution.started_at && (
                            <span className="text-xs text-muted-foreground">
                              {formatRelativeTime(nodeExecution.started_at)}
                            </span>
                          )}
                        </div>
                        {nodeExecution.error && (
                          <p className="mt-1 text-xs text-destructive">{nodeExecution.error}</p>
                        )}
                        {Object.keys(nodeExecution.output_context).length > 0 && (
                          <pre className="mt-1.5 overflow-x-auto rounded-lg bg-secondary p-2 text-xs">
                            {JSON.stringify(nodeExecution.output_context, null, 2)}
                          </pre>
                        )}
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
