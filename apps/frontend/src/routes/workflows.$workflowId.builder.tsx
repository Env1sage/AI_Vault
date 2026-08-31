import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { WorkflowDraft, WorkflowNode, WorkflowNodeInput, WorkflowNodeType } from "@vault/types";
import { ChevronLeft, Plus, Save, Trash2 } from "lucide-react";
import { useState } from "react";

import { AppShell } from "@/components/app-shell/app-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
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
import { nodeTypeLabel } from "@/lib/workflow-style";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/workflows/$workflowId/builder")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: WorkflowBuilderPage,
});

const NODE_TYPES: WorkflowNodeType[] = [
  "trigger",
  "condition",
  "decision",
  "ai_evaluation",
  "approval",
  "execute_action",
  "delay",
  "notification",
  "end",
];

interface EditableNode {
  key: string;
  node_type: WorkflowNodeType;
  name: string;
  configText: string;
  nextNodesText: string;
}

function toEditable(nodes: WorkflowNode[]): EditableNode[] {
  return nodes.map((node) => ({
    key: node.id,
    node_type: node.node_type,
    name: node.name,
    configText: JSON.stringify(node.config, null, 2),
    nextNodesText: JSON.stringify(node.next_nodes, null, 2),
  }));
}

function WorkflowBuilderPage() {
  const { workflowId } = Route.useParams();

  const draftQuery = useQuery({
    queryKey: ["workflow-draft", workflowId],
    queryFn: () => apiClient.post<WorkflowDraft>(`/v1/workflows/${workflowId}/draft`),
  });

  return (
    <AppShell title="Workflow Builder">
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        <Link
          to="/workflows/$workflowId"
          params={{ workflowId }}
          className="flex w-fit items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ChevronLeft className="size-4" /> Back to workflow
        </Link>
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Workflow Builder</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Edits apply to the draft version only — nothing here affects what&rsquo;s currently
            published or running until you publish again. Node graphs are edited as plain JSON
            this phase, not a drag-and-drop canvas; use each node&rsquo;s <code>key</code> in
            another node&rsquo;s <code>next_nodes</code> to link them (e.g.{" "}
            {'{"default": "that-node-key"}'}).
          </p>
        </div>

        {draftQuery.isLoading && <Skeleton className="h-64 rounded-2xl" />}
        {draftQuery.isError && (
          <p className="text-sm text-destructive">Couldn&rsquo;t load the draft.</p>
        )}

        {draftQuery.data && (
          <BuilderForm
            key={draftQuery.data.version.id}
            workflowId={workflowId}
            workflowVersionId={draftQuery.data.version.id}
            initialNodes={draftQuery.data.nodes}
          />
        )}
      </div>
    </AppShell>
  );
}

function BuilderForm({
  workflowId,
  workflowVersionId,
  initialNodes,
}: {
  workflowId: string;
  workflowVersionId: string;
  initialNodes: WorkflowNode[];
}) {
  const queryClient = useQueryClient();
  const [nodes, setNodes] = useState<EditableNode[]>(() => toEditable(initialNodes));
  const [parseError, setParseError] = useState<string | null>(null);
  const [nextKey, setNextKey] = useState(0);

  const saveMutation = useMutation({
    mutationFn: () => {
      const parsed: WorkflowNodeInput[] = nodes.map((node) => ({
        key: node.key,
        node_type: node.node_type,
        name: node.name,
        config: JSON.parse(node.configText || "{}"),
        next_nodes: JSON.parse(node.nextNodesText || "{}"),
      }));
      return apiClient.put<WorkflowNode[]>(
        `/v1/workflows/${workflowId}/versions/${workflowVersionId}/nodes`,
        { nodes: parsed },
      );
    },
    onSuccess: () => {
      setParseError(null);
      void queryClient.invalidateQueries({ queryKey: ["workflow-draft", workflowId] });
      void queryClient.invalidateQueries({ queryKey: ["workflows", workflowId] });
    },
    onError: (error) => {
      if (!(error instanceof ApiError)) {
        setParseError("One of the node's config/next_nodes fields isn't valid JSON.");
      }
    },
  });

  function updateNode(key: string, patch: Partial<EditableNode>) {
    setNodes((prev) => prev.map((node) => (node.key === key ? { ...node, ...patch } : node)));
  }

  function removeNode(key: string) {
    setNodes((prev) => prev.filter((node) => node.key !== key));
  }

  function addNode() {
    const key = `new-${nextKey}`;
    setNextKey((n) => n + 1);
    setNodes((prev) => [
      ...prev,
      { key, node_type: "condition", name: "New node", configText: "{}", nextNodesText: "{}" },
    ]);
  }

  function handleSave() {
    setParseError(null);
    try {
      for (const node of nodes) {
        JSON.parse(node.configText || "{}");
        JSON.parse(node.nextNodesText || "{}");
      }
    } catch {
      setParseError("One of the node's config/next_nodes fields isn't valid JSON.");
      return;
    }
    saveMutation.mutate();
  }

  return (
    <div className="flex flex-col gap-4">
      <ul className="flex flex-col gap-3">
        {nodes.map((node) => (
          <Card key={node.key} className="flex flex-col gap-3 p-4">
            <div className="flex items-center justify-between gap-2">
              <span className="rounded-md bg-secondary px-2 py-1 font-mono text-xs">{node.key}</span>
              <Button variant="ghost" size="sm" onClick={() => removeNode(node.key)}>
                <Trash2 className="size-4" /> Remove
              </Button>
            </div>
            <div className="flex gap-2">
              <Select
                value={node.node_type}
                onValueChange={(value) => updateNode(node.key, { node_type: value as WorkflowNodeType })}
              >
                <SelectTrigger className="w-44">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {NODE_TYPES.map((type) => (
                    <SelectItem key={type} value={type}>
                      {nodeTypeLabel(type)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Input
                value={node.name}
                onChange={(event) => updateNode(node.key, { name: event.target.value })}
                placeholder="Node name"
                className="flex-1"
              />
            </div>
            <label className="text-xs text-muted-foreground">
              Config (JSON)
              <textarea
                value={node.configText}
                onChange={(event) => updateNode(node.key, { configText: event.target.value })}
                rows={4}
                className="mt-1 w-full resize-y rounded-lg border border-input bg-card px-3 py-2 font-mono text-xs shadow-clay-inset focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </label>
            <label className="text-xs text-muted-foreground">
              Next nodes (outcome → node key)
              <textarea
                value={node.nextNodesText}
                onChange={(event) => updateNode(node.key, { nextNodesText: event.target.value })}
                rows={2}
                className="mt-1 w-full resize-y rounded-lg border border-input bg-card px-3 py-2 font-mono text-xs shadow-clay-inset focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </label>
          </Card>
        ))}
      </ul>

      <div className="flex flex-wrap items-center gap-2">
        <Button variant="outline" onClick={addNode}>
          <Plus className="size-4" /> Add node
        </Button>
        <Button disabled={saveMutation.isPending || nodes.length === 0} onClick={handleSave}>
          <Save className="size-4" />
          {saveMutation.isPending ? "Saving…" : "Save draft"}
        </Button>
      </div>
      {parseError && <p className="text-sm text-destructive">{parseError}</p>}
      {saveMutation.isError && !parseError && (
        <p className="text-sm text-destructive">
          {saveMutation.error instanceof ApiError
            ? saveMutation.error.message
            : "Couldn't save these nodes."}
        </p>
      )}
      {saveMutation.isSuccess && (
        <p className="text-sm text-success">
          Draft saved. Go back to the workflow page and publish when ready.
        </p>
      )}
    </div>
  );
}
