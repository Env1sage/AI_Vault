import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { CreateWorkflowRequest, Workflow } from "@vault/types";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, apiClient } from "@/lib/api-client";
import { formatRelativeTime } from "@/lib/format-relative-time";
import { workflowStatusColor } from "@/lib/workflow-style";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/workflows")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: WorkflowLibraryPage,
});

function WorkflowLibraryPage() {
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const canManage = user?.role === "owner" || user?.role === "admin";
  const [status, setStatus] = useState<string>("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const params = new URLSearchParams();
  if (status) params.set("status", status);

  const workflowsQuery = useQuery({
    queryKey: ["workflows", status],
    queryFn: () => apiClient.get<Workflow[]>(`/v1/workflows?${params.toString()}`),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      apiClient.post<Workflow>("/v1/workflows", {
        name,
        description: description.trim() || undefined,
      } satisfies CreateWorkflowRequest),
    onSuccess: () => {
      setName("");
      setDescription("");
      void queryClient.invalidateQueries({ queryKey: ["workflows"] });
    },
  });

  const workflows = workflowsQuery.data ?? [];

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-8">
      <Link to="/dashboard" className="text-sm underline">
        ← Back to dashboard
      </Link>
      <h1 className="text-xl font-semibold">Workflow Library</h1>
      <p className="text-sm text-neutral-500">
        Automation workflows for this organization. Nothing runs, mutates storage, or sends real
        email until you publish a workflow and either trigger it yourself or let a schedule/event
        do it — see{" "}
        <Link to="/workflow-policies" className="underline">
          Policy Manager
        </Link>{" "}
        for how automated approval works.
      </p>

      {canManage && (
        <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
          <h2 className="mb-3 font-medium">Create a workflow</h2>
          <div className="flex flex-col gap-2">
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Workflow name"
              className="rounded-md border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-800 dark:bg-neutral-950"
            />
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Description (optional)"
              rows={2}
              className="rounded-md border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-800 dark:bg-neutral-950"
            />
            <Button
              className="w-fit"
              disabled={!name.trim() || createMutation.isPending}
              onClick={() => createMutation.mutate()}
            >
              {createMutation.isPending ? "Creating…" : "Create workflow"}
            </Button>
            {createMutation.isError && (
              <p className="text-sm text-red-600">
                {createMutation.error instanceof ApiError
                  ? createMutation.error.message
                  : "Couldn't create this workflow."}
              </p>
            )}
          </div>
        </section>
      )}

      <div className="flex flex-wrap gap-2">
        <select
          value={status}
          onChange={(event) => setStatus(event.target.value)}
          className="rounded-md border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-800 dark:bg-neutral-950"
        >
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="paused">Paused</option>
          <option value="disabled">Disabled</option>
        </select>
        <Link
          to="/automation-templates"
          className="rounded-md border border-neutral-200 px-3 py-2 text-sm hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900"
        >
          Templates gallery
        </Link>
        <Link
          to="/workflow-executions"
          className="rounded-md border border-neutral-200 px-3 py-2 text-sm hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900"
        >
          Execution history
        </Link>
      </div>

      {workflowsQuery.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
      {workflowsQuery.isError && <p className="text-sm text-red-600">Couldn't load workflows.</p>}
      {workflows.length === 0 && !workflowsQuery.isLoading && (
        <p className="text-sm text-neutral-500">
          No workflows match these filters. Create one above or start from a template.
        </p>
      )}

      <ul className="flex flex-col gap-2">
        {workflows.map((workflow) => (
          <li key={workflow.id}>
            <Link
              to="/workflows/$workflowId"
              params={{ workflowId: workflow.id }}
              className="flex flex-col gap-1 rounded-lg border border-neutral-200 p-3 text-sm hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900"
            >
              <div className="flex items-center justify-between gap-3">
                <p className="min-w-0 truncate font-medium">{workflow.name}</p>
                <span className={`shrink-0 text-xs capitalize ${workflowStatusColor(workflow.status)}`}>
                  {workflow.status}
                </span>
              </div>
              {workflow.description && (
                <p className="truncate text-neutral-500">{workflow.description}</p>
              )}
              <span className="text-xs text-neutral-400">
                {formatRelativeTime(workflow.created_at)}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
