import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { WorkflowDraft, WorkflowNode, WorkflowNodeInput, WorkflowNodeType } from "@vault/types";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, apiClient } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/workflows/$workflowId/builder")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: WorkflowBuilderPage,
});

const _NODE_TYPES: WorkflowNodeType[] = [
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
    <main className="mx-auto flex max-w-3xl flex-col gap-6 p-8">
      <Link to="/workflows/$workflowId" params={{ workflowId }} className="text-sm underline">
        ← Back to workflow
      </Link>
      <h1 className="text-xl font-semibold">Workflow Builder</h1>
      <p className="text-sm text-neutral-500">
        Edits apply to the draft version only — nothing here affects what's currently published or
        running until you publish again. Node graphs are edited as plain JSON this phase, not a
        drag-and-drop canvas; use each node's <code>key</code> in another node's{" "}
        <code>next_nodes</code> to link them (e.g. {"{"}"default": "that-node-key"{"}"}).
      </p>

      {draftQuery.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
      {draftQuery.isError && <p className="text-sm text-red-600">Couldn't load the draft.</p>}

      {draftQuery.data && (
        // Keyed by the version id so navigating to a different draft (or a
        // background refetch producing a genuinely new draft) remounts this
        // form with fresh initial state, instead of needing an effect to
        // sync `draftQuery.data` into local state after the fact.
        <BuilderForm
          key={draftQuery.data.version.id}
          workflowId={workflowId}
          workflowVersionId={draftQuery.data.version.id}
          initialNodes={draftQuery.data.nodes}
        />
      )}
    </main>
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
      // Validate JSON up front so a bad edit doesn't reach the API at all.
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
    <>
      <ul className="flex flex-col gap-4">
        {nodes.map((node) => (
          <li
            key={node.key}
            className="flex flex-col gap-2 rounded-lg border border-neutral-200 p-4 text-sm dark:border-neutral-800"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="rounded bg-neutral-100 px-2 py-1 font-mono text-xs dark:bg-neutral-900">
                {node.key}
              </span>
              <Button variant="ghost" size="sm" onClick={() => removeNode(node.key)}>
                Remove
              </Button>
            </div>
            <div className="flex gap-2">
              <select
                value={node.node_type}
                onChange={(event) =>
                  updateNode(node.key, { node_type: event.target.value as WorkflowNodeType })
                }
                className="rounded-md border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-800 dark:bg-neutral-950"
              >
                {_NODE_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
              <input
                value={node.name}
                onChange={(event) => updateNode(node.key, { name: event.target.value })}
                placeholder="Node name"
                className="flex-1 rounded-md border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-800 dark:bg-neutral-950"
              />
            </div>
            <label className="text-xs text-neutral-500">
              Config (JSON)
              <textarea
                value={node.configText}
                onChange={(event) => updateNode(node.key, { configText: event.target.value })}
                rows={4}
                className="mt-1 w-full rounded-md border border-neutral-200 px-3 py-2 font-mono text-xs dark:border-neutral-800 dark:bg-neutral-950"
              />
            </label>
            <label className="text-xs text-neutral-500">
              Next nodes (outcome → node key)
              <textarea
                value={node.nextNodesText}
                onChange={(event) => updateNode(node.key, { nextNodesText: event.target.value })}
                rows={2}
                className="mt-1 w-full rounded-md border border-neutral-200 px-3 py-2 font-mono text-xs dark:border-neutral-800 dark:bg-neutral-950"
              />
            </label>
          </li>
        ))}
      </ul>

      <div className="flex flex-wrap items-center gap-2">
        <Button variant="outline" onClick={addNode}>
          Add node
        </Button>
        <Button disabled={saveMutation.isPending || nodes.length === 0} onClick={handleSave}>
          {saveMutation.isPending ? "Saving…" : "Save draft"}
        </Button>
      </div>
      {parseError && <p className="text-sm text-red-600">{parseError}</p>}
      {saveMutation.isError && !parseError && (
        <p className="text-sm text-red-600">
          {saveMutation.error instanceof ApiError
            ? saveMutation.error.message
            : "Couldn't save these nodes."}
        </p>
      )}
      {saveMutation.isSuccess && (
        <p className="text-sm text-green-600">
          Draft saved. Go back to the workflow page and publish when ready.
        </p>
      )}
    </>
  );
}
