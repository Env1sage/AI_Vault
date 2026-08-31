import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { CreateWorkflowPolicyRequest, WorkflowPolicy, WorkflowPolicyEffect } from "@vault/types";
import { ChevronLeft, Plus, ShieldCheck } from "lucide-react";
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
import { policyStatusBadgeVariant } from "@/lib/workflow-style";
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
    <AppShell title="Policy Manager">
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        <Link
          to="/workflows"
          className="flex w-fit items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ChevronLeft className="size-4" /> Back to Workflow Library
        </Link>
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Policy Manager</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Policies decide what an <code>Execute Action</code> workflow node is allowed to do:{" "}
            <strong className="text-foreground">auto-execute</strong> (no human click —
            attributed to this policy in the audit trail, not a person),{" "}
            <strong className="text-foreground">require approval</strong> (behaves exactly like
            the manual approval flow), or <strong className="text-foreground">skip</strong>{" "}
            entirely. Automation never bypasses the Approval System — an auto-executed plan still
            gets a real, audited decision, just from a policy instead of a human.
          </p>
        </div>

        {canManage && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Plus className="size-4" /> Create a policy
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              <Input
                value={policyKey}
                onChange={(event) => setPolicyKey(event.target.value)}
                placeholder="Policy key (stable identifier, e.g. archive-small-batches)"
              />
              <Input value={name} onChange={(event) => setName(event.target.value)} placeholder="Display name" />
              <Select value={effect} onValueChange={(v) => setEffect(v as WorkflowPolicyEffect)}>
                <SelectTrigger className="w-48">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="require_approval">Require approval</SelectItem>
                  <SelectItem value="auto_execute">Auto-execute</SelectItem>
                  <SelectItem value="skip">Skip</SelectItem>
                </SelectContent>
              </Select>
              <div className="flex gap-2">
                <Input
                  value={maxFiles}
                  onChange={(event) => setMaxFiles(event.target.value)}
                  placeholder="Max affected files (optional)"
                  type="number"
                  className="flex-1"
                />
                <Input
                  value={minConfidence}
                  onChange={(event) => setMinConfidence(event.target.value)}
                  placeholder="Min confidence 0-1 (optional)"
                  type="number"
                  step="0.01"
                  className="flex-1"
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
                <p className="text-sm text-destructive">
                  {createMutation.error instanceof ApiError
                    ? createMutation.error.message
                    : "Couldn't create this policy."}
                </p>
              )}
            </CardContent>
          </Card>
        )}

        {policiesQuery.isLoading && (
          <div className="flex flex-col gap-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-20 rounded-xl" />
            ))}
          </div>
        )}
        {policiesQuery.isError && (
          <EmptyState title="Couldn't load policies" description="Please try again." />
        )}
        {policies.length === 0 && !policiesQuery.isLoading && (
          <EmptyState icon={ShieldCheck} title="No policies yet" description="Create one above." />
        )}

        <ul className="flex flex-col gap-2">
          {policies.map((policy) => (
            <Card key={policy.id} className="flex flex-col gap-2 p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <span className="font-medium">{policy.name}</span>
                  <span className="ml-2 text-xs text-muted-foreground">v{policy.version}</span>
                </div>
                <Badge variant={policyStatusBadgeVariant(policy.status)} className="capitalize">
                  {policy.status}
                </Badge>
              </div>
              <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                <span className="font-mono">{policy.policy_key}</span>
                <span className="capitalize">{policy.effect.replace(/_/g, " ")}</span>
                <span>{formatRelativeTime(policy.created_at)}</span>
              </div>
              {Object.keys(policy.conditions).length > 0 && (
                <pre className="overflow-x-auto rounded-lg bg-secondary p-2 text-xs">
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
                  {publishMutation.isPending && publishMutation.variables === policy.id
                    ? "Publishing…"
                    : "Publish"}
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
                  {archiveMutation.isPending && archiveMutation.variables === policy.id
                    ? "Archiving…"
                    : "Archive"}
                </Button>
              )}
            </Card>
          ))}
        </ul>
      </div>
    </AppShell>
  );
}
