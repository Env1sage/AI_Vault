import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type {
  CreateWorkflowTriggerRequest,
  Workflow,
  WorkflowDetail,
  WorkflowExecution,
  WorkflowTrigger,
} from "@vault/types";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, apiClient } from "@/lib/api-client";
import { formatRelativeTime } from "@/lib/format-relative-time";
import { workflowStatusColor } from "@/lib/workflow-style";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/workflows/$workflowId")({
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
      <select
        value={triggerType}
        onChange={(event) => setTriggerType(event.target.value as typeof triggerType)}
        className="w-fit rounded-md border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-800 dark:bg-neutral-950"
      >
        <option value="scheduled">Scheduled (cron)</option>
        <option value="event">Event</option>
        <option value="manual">Manual only</option>
      </select>
      {triggerType === "scheduled" && (
        <input
          value={cron}
          onChange={(event) => setCron(event.target.value)}
          placeholder="Cron expression, e.g. 0 2 * * *"
          className="rounded-md border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-800 dark:bg-neutral-950"
        />
      )}
      {triggerType === "event" && (
        <select
          value={eventType}
          onChange={(event) => setEventType(event.target.value)}
          className="w-fit rounded-md border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-800 dark:bg-neutral-950"
        >
          <option value="scan_completed">Scan completed</option>
          <option value="enrichment_completed">Enrichment completed</option>
          <option value="recommendation_generated">Recommendation generated</option>
          <option value="connector_reconnected">Connector reconnected</option>
          <option value="file_added">File added (not yet wired to a real trigger)</option>
          <option value="file_updated">File updated (not yet wired to a real trigger)</option>
          <option value="storage_threshold_exceeded">
            Storage threshold exceeded (not yet wired to a real trigger)
          </option>
        </select>
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
        <p className="text-sm text-red-600">
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
  });
  const triggerManualMutation = useMutation({
    mutationFn: () =>
      apiClient.post<WorkflowExecution>(`/v1/workflows/${workflowId}/executions`),
  });
  const statusMutation = useMutation({
    mutationFn: (status: string) =>
      apiClient.post(`/v1/workflows/${workflowId}/status`, { status }),
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
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-8">
      <Link to="/workflows" className="text-sm underline">
        ← Back to Workflow Library
      </Link>

      {detailQuery.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
      {detailQuery.isError && (
        <p className="text-sm text-red-600">Couldn't load this workflow.</p>
      )}

      {detail && (
        <>
          <div>
            <span className={`text-sm font-medium capitalize ${workflowStatusColor(detail.status)}`}>
              {detail.status}
            </span>
            <h1 className="text-xl font-semibold">{detail.name}</h1>
            {detail.description && <p className="text-neutral-500">{detail.description}</p>}
          </div>

          <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
            <h2 className="mb-3 font-medium">Versions</h2>
            <dl className="grid grid-cols-2 gap-y-2 text-sm">
              <dt className="text-neutral-500">Published</dt>
              <dd>
                {detail.published_version
                  ? `v${detail.published_version.version_number} — ${formatRelativeTime(detail.published_version.published_at ?? detail.published_version.created_at)}`
                  : "None yet"}
              </dd>
              <dt className="text-neutral-500">Draft</dt>
              <dd>{detail.draft_version ? `v${detail.draft_version.version_number}` : "—"}</dd>
            </dl>
            {canManage && (
              <div className="mt-3 flex flex-wrap gap-2">
                <Link
                  to="/workflows/$workflowId/builder"
                  params={{ workflowId }}
                  className="rounded-md border border-neutral-200 px-3 py-2 text-sm hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900"
                >
                  Open builder
                </Link>
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
              <p className="mt-2 text-sm text-red-600">
                {publishMutation.error instanceof ApiError
                  ? publishMutation.error.message
                  : "Couldn't publish this workflow."}
              </p>
            )}
          </section>

          {canManage && (
            <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
              <h2 className="mb-3 font-medium">Run</h2>
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  size="sm"
                  disabled={!detail.published_version || triggerManualMutation.isPending}
                  onClick={() => triggerManualMutation.mutate()}
                >
                  {triggerManualMutation.isPending ? "Starting…" : "Trigger manually"}
                </Button>
                {!detail.published_version && (
                  <span className="text-xs text-neutral-500">Publish a draft first.</span>
                )}
              </div>
              {triggerManualMutation.isError && (
                <p className="mt-2 text-sm text-red-600">
                  {triggerManualMutation.error instanceof ApiError
                    ? triggerManualMutation.error.message
                    : "Couldn't trigger this workflow."}
                </p>
              )}
              {triggerManualMutation.isSuccess && (
                <p className="mt-2 text-sm text-green-600">
                  Started —{" "}
                  <Link
                    to="/workflow-executions/$workflowExecutionId"
                    params={{ workflowExecutionId: triggerManualMutation.data.id }}
                    className="underline"
                  >
                    view progress
                  </Link>
                  .
                </p>
              )}
            </section>
          )}

          <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
            <h2 className="mb-3 font-medium">Triggers</h2>
            {triggersQuery.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
            {triggers.length === 0 && !triggersQuery.isLoading && (
              <p className="text-sm text-neutral-500">No triggers configured yet.</p>
            )}
            <ul className="mb-4 flex flex-col gap-2">
              {triggers.map((trigger) => (
                <li
                  key={trigger.id}
                  className="flex items-center justify-between rounded-lg border border-neutral-200 p-2 text-sm dark:border-neutral-800"
                >
                  <div>
                    <span className="font-medium capitalize">{trigger.trigger_type}</span>
                    {trigger.trigger_type === "scheduled" && (
                      <span className="ml-2 text-neutral-500">
                        {String(trigger.config.cron ?? "")}
                      </span>
                    )}
                    {trigger.trigger_type === "event" && (
                      <span className="ml-2 text-neutral-500">
                        {String(trigger.config.event_type ?? "")}
                      </span>
                    )}
                    {!trigger.enabled && <span className="ml-2 text-neutral-400">(disabled)</span>}
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
                      {trigger.enabled ? "Disable" : "Enable"}
                    </Button>
                  )}
                </li>
              ))}
            </ul>
            {canManage && <TriggerForm workflowId={workflowId} />}
          </section>

          {canManage && (
            <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
              <h2 className="mb-3 font-medium">Manage</h2>
              <div className="flex flex-wrap gap-2">
                {detail.status === "active" ? (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={statusMutation.isPending}
                    onClick={() => statusMutation.mutate("paused")}
                  >
                    Pause workflow
                  </Button>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={statusMutation.isPending}
                    onClick={() => statusMutation.mutate("active")}
                  >
                    Activate workflow
                  </Button>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  disabled={statusMutation.isPending}
                  onClick={() => statusMutation.mutate("disabled")}
                >
                  Disable workflow
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
              {cloneMutation.isSuccess && (
                <p className="mt-2 text-sm text-green-600">
                  Cloned —{" "}
                  <Link
                    to="/workflows/$workflowId"
                    params={{ workflowId: cloneMutation.data.id }}
                    className="underline"
                  >
                    open the copy
                  </Link>
                  .
                </p>
              )}
            </section>
          )}
        </>
      )}
    </main>
  );
}
