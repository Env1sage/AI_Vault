import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { CreateWorkflowRequest, Workflow } from "@vault/types";
import { LayoutTemplate, Plus, Workflow as WorkflowIcon } from "lucide-react";
import { useState } from "react";

import { AppShell } from "@/components/app-shell/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
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

export const Route = createFileRoute("/workflows/")({
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
  const [status, setStatus] = useState<string>("all");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const params = new URLSearchParams();
  if (status !== "all") params.set("status", status);

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
    <AppShell title="Workflows">
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Workflow Library</h1>
          <p className="text-sm text-muted-foreground">
            Automation workflows for this organization. Nothing runs, mutates storage, or sends
            real email until you publish a workflow and either trigger it yourself or let a
            schedule/event do it — see{" "}
            <Link to="/workflow-policies" className="text-primary hover:underline">
              Policy Manager
            </Link>{" "}
            for how automated approval works.
          </p>
        </div>

        {canManage && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Plus className="size-4" /> Create a workflow
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              <Input value={name} onChange={(event) => setName(event.target.value)} placeholder="Workflow name" />
              <textarea
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Description (optional)"
                rows={2}
                className="resize-none rounded-lg border border-input bg-card px-3 py-2 text-sm shadow-clay-inset placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              <Button
                className="w-fit"
                disabled={!name.trim() || createMutation.isPending}
                onClick={() => createMutation.mutate()}
              >
                {createMutation.isPending ? "Creating…" : "Create workflow"}
              </Button>
              {createMutation.isError && (
                <p className="text-sm text-destructive">
                  {createMutation.error instanceof ApiError
                    ? createMutation.error.message
                    : "Couldn't create this workflow."}
                </p>
              )}
            </CardContent>
          </Card>
        )}

        <div className="flex flex-wrap items-center gap-2">
          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="paused">Paused</SelectItem>
              <SelectItem value="disabled">Disabled</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" asChild>
            <Link to="/automation-templates">
              <LayoutTemplate className="size-4" /> Templates gallery
            </Link>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <Link to="/workflow-executions">Execution history</Link>
          </Button>
        </div>

        {workflowsQuery.isLoading && (
          <div className="flex flex-col gap-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-16 rounded-xl" />
            ))}
          </div>
        )}
        {workflowsQuery.isError && (
          <EmptyState title="Couldn't load workflows" description="Please try again." />
        )}
        {workflows.length === 0 && !workflowsQuery.isLoading && (
          <EmptyState
            icon={WorkflowIcon}
            title="No workflows match these filters"
            description="Create one above or start from a template."
          />
        )}

        <ul className="flex flex-col gap-2">
          {workflows.map((workflow) => (
            <li key={workflow.id}>
              <Link
                to="/workflows/$workflowId"
                params={{ workflowId: workflow.id }}
                className="flex flex-col gap-1 rounded-xl border border-border bg-card p-4 text-sm shadow-clay-sm transition-all hover:-translate-y-0.5 hover:shadow-clay"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="min-w-0 truncate font-medium">{workflow.name}</p>
                  <Badge variant={workflowStatusBadgeVariant(workflow.status)} className="capitalize">
                    {workflow.status}
                  </Badge>
                </div>
                {workflow.description && (
                  <p className="truncate text-muted-foreground">{workflow.description}</p>
                )}
                <span className="text-xs text-muted-foreground">
                  {formatRelativeTime(workflow.created_at)}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </AppShell>
  );
}
