import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { CreateWorkflowPolicyRequest, WorkflowPolicy, WorkflowPolicyEffect } from "@vault/types";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, apiClient } from "@/lib/api-client";
import { formatRelativeTime } from "@/lib/format-relative-time";
import { policyStatusColor } from "@/lib/workflow-style";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/workflow-policies")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: PolicyManagerPage,
});

function PolicyManagerPage() {
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const canManage = user?.role === "owner" || user?.role === "admin";

  const [policyKey, setPolicyKey] = useState("");
  const [name, setName] = useState("");
  const [effect, setEffect] = useState<WorkflowPolicyEffect>("require_approval");
  const [maxFiles, setMaxFiles] = useState("");
  const [minConfidence, setMinConfidence] = useState("");

  const policiesQuery = useQuery({
    queryKey: ["workflow-policies"],
    queryFn: () => apiClient.get<WorkflowPolicy[]>("/v1/workflow-policies"),
  });

  const createMutation = useMutation({
    mutationFn: () => {
      const conditions: Record<string, number> = {};
      if (maxFiles.trim()) conditions.max_affected_files = Number(maxFiles);
      if (minConfidence.trim()) conditions.min_confidence = Number(minConfidence);
      return apiClient.post<WorkflowPolicy>("/v1/workflow-policies", {
        policy_key: policyKey,
        name,
        effect,
        conditions,
      } satisfies CreateWorkflowPolicyRequest);
    },
    onSuccess: () => {
      setPolicyKey("");
      setName("");
      setMaxFiles("");
      setMinConfidence("");
      void queryClient.invalidateQueries({ queryKey: ["workflow-policies"] });
    },
  });

  const publishMutation = useMutation({
    mutationFn: (id: string) => apiClient.post(`/v1/workflow-policies/${id}/publish`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["workflow-policies"] }),
  });
  const archiveMutation = useMutation({
    mutationFn: (id: string) => apiClient.post(`/v1/workflow-policies/${id}/archive`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["workflow-policies"] }),
  });

  const policies = policiesQuery.data ?? [];

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-8">
      <Link to="/workflows" className="text-sm underline">
        ← Back to Workflow Library
      </Link>
      <h1 className="text-xl font-semibold">Policy Manager</h1>
      <p className="text-sm text-neutral-500">
        Policies decide what an <code>Execute Action</code> workflow node is allowed to do:{" "}
        <strong>auto-execute</strong> (no human click — attributed to this policy in the audit
        trail, not a person), <strong>require approval</strong> (behaves exactly like Phase 8's
        manual approval flow), or <strong>skip</strong> entirely. Automation never bypasses the
        Approval System — an auto-executed plan still gets a real, audited decision, just from a
        policy instead of a human.
      </p>

      {canManage && (
        <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
          <h2 className="mb-3 font-medium">Create a policy</h2>
          <div className="flex flex-col gap-2">
            <input
              value={policyKey}
              onChange={(event) => setPolicyKey(event.target.value)}
              placeholder="Policy key (stable identifier, e.g. archive-small-batches)"
              className="rounded-md border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-800 dark:bg-neutral-950"
            />
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Display name"
              className="rounded-md border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-800 dark:bg-neutral-950"
            />
            <select
              value={effect}
              onChange={(event) => setEffect(event.target.value as WorkflowPolicyEffect)}
              className="w-fit rounded-md border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-800 dark:bg-neutral-950"
            >
              <option value="require_approval">Require approval</option>
              <option value="auto_execute">Auto-execute</option>
              <option value="skip">Skip</option>
            </select>
            <div className="flex gap-2">
              <input
                value={maxFiles}
                onChange={(event) => setMaxFiles(event.target.value)}
                placeholder="Max affected files (optional)"
                type="number"
                className="flex-1 rounded-md border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-800 dark:bg-neutral-950"
              />
              <input
                value={minConfidence}
                onChange={(event) => setMinConfidence(event.target.value)}
                placeholder="Min confidence 0-1 (optional)"
                type="number"
                step="0.01"
                className="flex-1 rounded-md border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-800 dark:bg-neutral-950"
              />
            </div>
            <Button
              className="w-fit"
              disabled={!policyKey.trim() || !name.trim() || createMutation.isPending}
              onClick={() => createMutation.mutate()}
            >
              {createMutation.isPending ? "Creating…" : "Create draft policy"}
            </Button>
            {createMutation.isError && (
              <p className="text-sm text-red-600">
                {createMutation.error instanceof ApiError
                  ? createMutation.error.message
                  : "Couldn't create this policy."}
              </p>
            )}
          </div>
        </section>
      )}

      {policiesQuery.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
      {policiesQuery.isError && <p className="text-sm text-red-600">Couldn't load policies.</p>}
      {policies.length === 0 && !policiesQuery.isLoading && (
        <p className="text-sm text-neutral-500">No policies yet.</p>
      )}

      <ul className="flex flex-col gap-2">
        {policies.map((policy) => (
          <li
            key={policy.id}
            className="flex flex-col gap-2 rounded-lg border border-neutral-200 p-3 text-sm dark:border-neutral-800"
          >
            <div className="flex items-center justify-between gap-3">
              <div>
                <span className="font-medium">{policy.name}</span>
                <span className="ml-2 text-xs text-neutral-400">v{policy.version}</span>
              </div>
              <span className={`text-xs capitalize ${policyStatusColor(policy.status)}`}>
                {policy.status}
              </span>
            </div>
            <div className="flex items-center gap-3 text-xs text-neutral-500">
              <span className="font-mono">{policy.policy_key}</span>
              <span className="capitalize">{policy.effect.replace(/_/g, " ")}</span>
              <span>{formatRelativeTime(policy.created_at)}</span>
            </div>
            {Object.keys(policy.conditions).length > 0 && (
              <pre className="overflow-x-auto rounded bg-neutral-100 p-2 text-xs dark:bg-neutral-900">
                {JSON.stringify(policy.conditions, null, 2)}
              </pre>
            )}
            {canManage && policy.status === "draft" && (
              <Button
                size="sm"
                className="w-fit"
                disabled={publishMutation.isPending}
                onClick={() => publishMutation.mutate(policy.id)}
              >
                Publish
              </Button>
            )}
            {canManage && policy.status === "published" && (
              <Button
                variant="outline"
                size="sm"
                className="w-fit"
                disabled={archiveMutation.isPending}
                onClick={() => archiveMutation.mutate(policy.id)}
              >
                Archive
              </Button>
            )}
          </li>
        ))}
      </ul>
    </main>
  );
}
