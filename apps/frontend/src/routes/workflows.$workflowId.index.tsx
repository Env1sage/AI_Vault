import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type {
  CreateWorkflowTriggerRequest,
  Workflow,
  WorkflowDetail,
  WorkflowExecution,
  WorkflowTrigger,
} from "@vault/types";
import { ChevronLeft, Play, Wrench } from "lucide-react";
import { useState } from "react";

import { AppShell } from "@/components/app-shell/app-shell";
import { toast } from "@/components/ui/toaster";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, apiClient } from "@/lib/api-client";
import { formatRelativeTime } from "@/lib/format-relative-time";
import { workflowStatusBadgeVariant } from "@/lib/workflow-style";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/workflows/$workflowId/")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: WorkflowDetailPage,
});

function TriggerForm({ workflowId }: { workflowId: string }) {
  const queryClient = useQueryClient();
  const [triggerType, setTriggerType] = useState<"scheduled" | "event" | "manual">("scheduled");
  const [cron, setCron] = useState("0 2 * * *");
  const [eventType, setEventType] = useState("scan_completed");

  const createMutation = useMutation({
    mutationFn: () => {
      const config =
        triggerType === "scheduled"
          ? { cron }
          : triggerType === "event"
            ? { event_type: eventType }
            : {};
      return apiClient.post<WorkflowTrigger>(`/v1/workflows/${workflowId}/triggers`, {
        trigger_type: triggerType,
        config,
      } satisfies CreateWorkflowTriggerRequest);
    },
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["workflow-triggers", workflowId] }),
  });

  return (
    <div className="flex flex-col gap-2">
      <Select value={triggerType} onValueChange={(v) => setTriggerType(v as typeof triggerType)}>
        <SelectTrigger className="w-52">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="scheduled">Scheduled (cron)</SelectItem>
          <SelectItem value="event">Event</SelectItem>
          <SelectItem value="manual">Manual only</SelectItem>
        </SelectContent>
      </Select>
      {triggerType === "scheduled" && (
        <Input
          value={cron}
          onChange={(event) => setCron(event.target.value)}
          placeholder="Cron expression, e.g. 0 2 * * *"
          className="w-64"
        />
      )}
      {triggerType === "event" && (
        <Select value={eventType} onValueChange={setEventType}>
          <SelectTrigger className="w-72">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="scan_completed">Scan completed</SelectItem>
            <SelectItem value="enrichment_completed">Enrichment completed</SelectItem>
            <SelectItem value="recommendation_generated">Recommendation generated</SelectItem>
            <SelectItem value="connector_reconnected">Connector reconnected</SelectItem>
            <SelectItem value="file_added">File added (not yet wired)</SelectItem>
            <SelectItem value="file_updated">File updated (not yet wired)</SelectItem>
            <SelectItem value="storage_threshold_exceeded">
              Storage threshold exceeded (not yet wired)
            </SelectItem>
          </SelectContent>
        </Select>
      )}
      <Button
        size="sm"
        className="w-fit"
        disabled={createMutation.isPending}
        onClick={() => createMutation.mutate()}
      >
        {createMutation.isPending ? "Adding…" : "Add trigger"}
      </Button>
      {createMutation.isError && (
        <p className="text-sm text-destructive">
          {createMutation.error instanceof ApiError
            ? createMutation.error.message
            : "Couldn't add this trigger."}
        </p>
      )}
    </div>
  );
}

function WorkflowDetailPage() {
  const { workflowId } = Route.useParams();
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const canManage = user?.role === "owner" || user?.role === "admin";

  const detailQuery = useQuery({
    queryKey: ["workflows", workflowId],
    queryFn: () => apiClient.get<WorkflowDetail>(`/v1/workflows/${workflowId}`),
  });

  const triggersQuery = useQuery({
    queryKey: ["workflow-triggers", workflowId],
    queryFn: () => apiClient.get<WorkflowTrigger[]>(`/v1/workflows/${workflowId}/triggers`),
  });

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ["workflows", workflowId] });
    void queryClient.invalidateQueries({ queryKey: ["workflows"] });
  }

  const publishMutation = useMutation({
    mutationFn: () => apiClient.post(`/v1/workflows/${workflowId}/publish`),
    onSuccess: invalidate,
  });
  const cloneMutation = useMutation({
    mutationFn: () => apiClient.post<Workflow>(`/v1/workflows/${workflowId}/clone`),
    onSuccess: (cloned) => {
      toast.success("Workflow cloned", {
        action: {
          label: "Open copy",
          onClick: () => {
            window.location.href = `/workflows/${cloned.id}`;
          },
        },
      });
    },
  });
  const triggerManualMutation = useMutation({
    mutationFn: () => apiClient.post<WorkflowExecution>(`/v1/workflows/${workflowId}/executions`),
    onSuccess: (execution) => {
      toast.success("Workflow started", {
        action: {
          label: "View progress",
          onClick: () => {
            window.location.href = `/workflow-executions/${execution.id}`;
          },
        },
      });
    },
  });
  const statusMutation = useMutation({
    mutationFn: (status: string) => apiClient.post(`/v1/workflows/${workflowId}/status`, { status }),
    onSuccess: invalidate,
  });
  const setTriggerEnabledMutation = useMutation({
    mutationFn: ({ triggerId, enabled }: { triggerId: string; enabled: boolean }) =>
      apiClient.post(`/v1/workflows/${workflowId}/triggers/${triggerId}/enabled`, { enabled }),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["workflow-triggers", workflowId] }),
  });

  const detail = detailQuery.data;
  const triggers = triggersQuery.data ?? [];

  return (
    <AppShell title="Workflow">
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        <Link
          to="/workflows"
          className="flex w-fit items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ChevronLeft className="size-4" /> Back to Workflow Library
        </Link>

        {detailQuery.isLoading && <Skeleton className="h-64 rounded-2xl" />}
        {detailQuery.isError && <p className="text-sm text-destructive">Couldn&rsquo;t load this workflow.</p>}

        {detail && (
          <>
            <Card clay className="p-6">
              <Badge variant={workflowStatusBadgeVariant(detail.status)} className="w-fit capitalize">
                {detail.status}
              </Badge>
              <h1 className="mt-2 text-lg font-semibold">{detail.name}</h1>
              {detail.description && <p className="text-sm text-muted-foreground">{detail.description}</p>}
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Versions</CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="grid grid-cols-2 gap-y-2 text-sm">
                  <dt className="text-muted-foreground">Published</dt>
                  <dd>
                    {detail.published_version
                      ? `v${detail.published_version.version_number} — ${formatRelativeTime(detail.published_version.published_at ?? detail.published_version.created_at)}`
                      : "None yet"}
                  </dd>
                  <dt className="text-muted-foreground">Draft</dt>
                  <dd>{detail.draft_version ? `v${detail.draft_version.version_number}` : "—"}</dd>
                </dl>
                {canManage && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button variant="outline" size="sm" asChild>
                      <Link to="/workflows/$workflowId/builder" params={{ workflowId }}>
                        <Wrench className="size-4" /> Open builder
                      </Link>
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={publishMutation.isPending}
                      onClick={() => publishMutation.mutate()}
                    >
                      {publishMutation.isPending ? "Publishing…" : "Publish draft"}
                    </Button>
                  </div>
                )}
                {publishMutation.isError && (
                  <p className="mt-2 text-sm text-destructive">
                    {publishMutation.error instanceof ApiError
                      ? publishMutation.error.message
                      : "Couldn't publish this workflow."}
                  </p>
                )}
              </CardContent>
            </Card>

            {canManage && (
              <Card>
                <CardHeader>
                  <CardTitle>Run</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap items-center gap-2">
                    <Button
                      size="sm"
                      disabled={!detail.published_version || triggerManualMutation.isPending}
                      onClick={() => triggerManualMutation.mutate()}
                    >
                      <Play className="size-4" />
                      {triggerManualMutation.isPending ? "Starting…" : "Trigger manually"}
                    </Button>
                    {!detail.published_version && (
                      <span className="text-xs text-muted-foreground">Publish a draft first.</span>
                    )}
                  </div>
                  {triggerManualMutation.isError && (
                    <p className="mt-2 text-sm text-destructive">
                      {triggerManualMutation.error instanceof ApiError
                        ? triggerManualMutation.error.message
                        : "Couldn't trigger this workflow."}
                    </p>
                  )}
                </CardContent>
              </Card>
            )}

            <Card>
              <CardHeader>
                <CardTitle>Triggers</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-4">
                {triggersQuery.isLoading && <Skeleton className="h-4 w-32" />}
                {triggers.length === 0 && !triggersQuery.isLoading && (
                  <p className="text-sm text-muted-foreground">No triggers configured yet.</p>
                )}
                <ul className="flex flex-col gap-2">
                  {triggers.map((trigger) => (
                    <li
                      key={trigger.id}
                      className="flex items-center justify-between rounded-lg border border-border p-2.5 text-sm"
                    >
                      <div>
                        <span className="font-medium capitalize">{trigger.trigger_type}</span>
                        {trigger.trigger_type === "scheduled" && (
                          <span className="ml-2 text-muted-foreground">
                            {String(trigger.config.cron ?? "")}
                          </span>
                        )}
                        {trigger.trigger_type === "event" && (
                          <span className="ml-2 text-muted-foreground">
                            {String(trigger.config.event_type ?? "")}
                          </span>
                        )}
                        {!trigger.enabled && (
                          <Badge variant="outline" className="ml-2">
                            disabled
                          </Badge>
                        )}
                      </div>
                      {canManage && (
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={setTriggerEnabledMutation.isPending}
                          onClick={() =>
                            setTriggerEnabledMutation.mutate({
                              triggerId: trigger.id,
                              enabled: !trigger.enabled,
                            })
                          }
                        >
                          {setTriggerEnabledMutation.isPending &&
                          setTriggerEnabledMutation.variables?.triggerId === trigger.id
                            ? "Updating…"
                            : trigger.enabled
                              ? "Disable"
                              : "Enable"}
                        </Button>
                      )}
                    </li>
                  ))}
                </ul>
                {canManage && <TriggerForm workflowId={workflowId} />}
              </CardContent>
            </Card>

            {canManage && (
              <Card>
                <CardHeader>
                  <CardTitle>Manage</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {detail.status === "active" ? (
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={statusMutation.isPending}
                        onClick={() => statusMutation.mutate("paused")}
                      >
                        {statusMutation.isPending && statusMutation.variables === "paused"
                          ? "Pausing…"
                          : "Pause workflow"}
                      </Button>
                    ) : (
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={statusMutation.isPending}
                        onClick={() => statusMutation.mutate("active")}
                      >
                        {statusMutation.isPending && statusMutation.variables === "active"
                          ? "Activating…"
                          : "Activate workflow"}
                      </Button>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={statusMutation.isPending}
                      onClick={() => statusMutation.mutate("disabled")}
                    >
                      {statusMutation.isPending && statusMutation.variables === "disabled"
                        ? "Disabling…"
                        : "Disable workflow"}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={cloneMutation.isPending}
                      onClick={() => cloneMutation.mutate()}
                    >
                      {cloneMutation.isPending ? "Cloning…" : "Clone"}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
