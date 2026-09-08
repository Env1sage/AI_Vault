import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type {
  ApprovalDecisionType,
  ApprovalRequest,
  ExecutionPlan,
  ExecutionPlanDetail,
} from "@vault/types";
import { AlertTriangle, ClipboardCheck } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { AppShell } from "@/components/app-shell/app-shell";
import { ApiError, apiClient } from "@/lib/api-client";
import { approvalStatusBadgeVariant, riskLevelBadgeVariant } from "@/lib/execution-style";
import { formatRelativeTime } from "@/lib/format-relative-time";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/approvals")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: ApprovalQueuePage,
});

function ApprovalRow({
  approval,
  plan,
  planLoading,
  canManage,
  selected,
  onToggleSelected,
}: {
  approval: ApprovalRequest;
  plan: ExecutionPlan | undefined;
  planLoading: boolean;
  canManage: boolean;
  selected: boolean;
  onToggleSelected: () => void;
}) {
  const queryClient = useQueryClient();
  const [comments, setComments] = useState("");
  const [highRiskAck, setHighRiskAck] = useState(false);
  const isHighRisk = plan?.risk_level === "high";
  const isPending = approval.status === "pending";

  const decideMutation = useMutation({
    mutationFn: (decision: ApprovalDecisionType) =>
      apiClient.post<ApprovalRequest>(`/v1/approvals/${approval.id}/decide`, {
        decision,
        comments: comments.trim() || undefined,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["approvals"] });
      void queryClient.invalidateQueries({ queryKey: ["execution-plans"] });
      void queryClient.invalidateQueries({ queryKey: ["execution-jobs"] });
    },
  });

  const approveDisabled = decideMutation.isPending || (isHighRisk && !highRiskAck);

  return (
    <Card className="flex flex-col gap-3 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          {isPending && canManage && (
            <input
              type="checkbox"
              checked={selected}
              onChange={onToggleSelected}
              className="mt-1 size-4 accent-primary"
              aria-label="Select for bulk decision"
            />
          )}
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <Badge variant={approvalStatusBadgeVariant(approval.status)} className="capitalize">
                {approval.status.replace(/_/g, " ")}
              </Badge>
              <Link
                to="/execution-plans/$executionPlanId"
                params={{ executionPlanId: approval.execution_plan_id }}
                className="text-xs text-primary hover:underline"
              >
                view plan
              </Link>
            </div>
          </div>
        </div>
        <span className="shrink-0 text-xs text-muted-foreground">
          expires {formatRelativeTime(approval.expires_at)}
        </span>
      </div>

      {planLoading && <Skeleton className="h-4 w-48" />}
      {plan && (
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <Badge variant={riskLevelBadgeVariant(plan.risk_level)}>{plan.risk_level} risk</Badge>
          <span>{plan.estimated_impact}</span>
          <span>·</span>
          <span>{plan.target_provider}</span>
        </div>
      )}

      {isPending && canManage && (
        <>
          <textarea
            value={comments}
            onChange={(event) => setComments(event.target.value)}
            placeholder="Comments (optional)"
            rows={2}
            className="w-full resize-none rounded-lg border border-input bg-card px-3 py-2 text-sm shadow-clay-inset placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />

          {isHighRisk && (
            <label className="flex items-start gap-2 rounded-lg bg-warning-muted p-2.5 text-xs text-warning">
              <AlertTriangle className="mt-0.5 size-3.5 shrink-0" />
              <span className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={highRiskAck}
                  onChange={(event) => setHighRiskAck(event.target.checked)}
                  className="size-3.5 accent-warning"
                />
                This is a high-risk plan ({plan?.estimated_impact}) — I&rsquo;ve reviewed it and
                want to approve it.
              </span>
            </label>
          )}

          <div className="flex flex-wrap gap-2">
            <Button size="sm" disabled={approveDisabled} onClick={() => decideMutation.mutate("approve")}>
              {decideMutation.isPending && decideMutation.variables === "approve"
                ? "Approving…"
                : "Approve"}
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={decideMutation.isPending}
              onClick={() => decideMutation.mutate("request_changes")}
            >
              {decideMutation.isPending && decideMutation.variables === "request_changes"
                ? "Requesting…"
                : "Request changes"}
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={decideMutation.isPending}
              onClick={() => decideMutation.mutate("reject")}
            >
              {decideMutation.isPending && decideMutation.variables === "reject"
                ? "Rejecting…"
                : "Reject"}
            </Button>
          </div>

          {decideMutation.isError && (
            <p className="text-sm text-destructive">
              {decideMutation.error instanceof ApiError
                ? decideMutation.error.message
                : "Couldn't record this decision."}
            </p>
          )}
        </>
      )}
    </Card>
  );
}

function ApprovalQueuePage() {
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const canManage = user?.role === "owner" || user?.role === "admin";

  const [status, setStatus] = useState<string>("pending");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkDecision, setBulkDecision] = useState<ApprovalDecisionType>("approve");
  const [bulkComments, setBulkComments] = useState("");
  const [bulkHighRiskAck, setBulkHighRiskAck] = useState(false);

  const params = new URLSearchParams();
  if (status !== "all") params.set("status", status);

  const approvalsQuery = useQuery({
    queryKey: ["approvals", status],
    queryFn: () => apiClient.get<ApprovalRequest[]>(`/v1/approvals?${params.toString()}`),
  });

  const approvals = approvalsQuery.data ?? [];

  const planQueries = useQueries({
    queries: approvals.map((approval) => ({
      queryKey: ["execution-plans", approval.execution_plan_id],
      queryFn: () =>
        apiClient.get<ExecutionPlanDetail>(`/v1/execution-plans/${approval.execution_plan_id}`),
    })),
  });

  const plansByPlanId = new Map(
    approvals.map((approval, index) => [approval.execution_plan_id, planQueries[index]?.data]),
  );

  const selectedApprovals = approvals.filter((approval) => selected.has(approval.id));
  const selectedHasHighRisk = selectedApprovals.some(
    (approval) => plansByPlanId.get(approval.execution_plan_id)?.risk_level === "high",
  );

  const bulkMutation = useMutation({
    mutationFn: () =>
      apiClient.post<ApprovalRequest[]>("/v1/approvals/bulk-decide", {
        approval_request_ids: Array.from(selected),
        decision: bulkDecision,
        comments: bulkComments.trim() || undefined,
      }),
    onSuccess: () => {
      setSelected(new Set());
      setBulkHighRiskAck(false);
      void queryClient.invalidateQueries({ queryKey: ["approvals"] });
      void queryClient.invalidateQueries({ queryKey: ["execution-plans"] });
      void queryClient.invalidateQueries({ queryKey: ["execution-jobs"] });
    },
  });

  function toggleSelected(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  const bulkDisabled =
    bulkMutation.isPending ||
    selected.size === 0 ||
    (bulkDecision === "approve" && selectedHasHighRisk && !bulkHighRiskAck);

  return (
    <AppShell title="Approvals">
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Approval Queue</h1>
          <p className="text-sm text-muted-foreground">
            Plans normally execute immediately — nothing to approve. A plan only lands here when
            something blocked its auto-execution (e.g. a connector needing reconnection); deciding
            it here enqueues real Google Drive changes, recorded with who made it, when, and why.
          </p>
        </div>

        <Select
          value={status}
          onValueChange={(value) => {
            setStatus(value);
            setSelected(new Set());
          }}
        >
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="approved">Approved</SelectItem>
            <SelectItem value="rejected">Rejected</SelectItem>
            <SelectItem value="changes_requested">Changes requested</SelectItem>
            <SelectItem value="expired">Expired</SelectItem>
            <SelectItem value="all">All statuses</SelectItem>
          </SelectContent>
        </Select>

        {approvalsQuery.isLoading && (
          <div className="flex flex-col gap-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-24 rounded-xl" />
            ))}
          </div>
        )}
        {approvalsQuery.isError && (
          <EmptyState title="Couldn't load approvals" description="Please try again." />
        )}
        {approvals.length === 0 && !approvalsQuery.isLoading && (
          <EmptyState
            icon={ClipboardCheck}
            title="Nothing to review"
            description="No approval requests match these filters."
          />
        )}

        {canManage && status === "pending" && selected.size > 0 && (
          <Card className="border-warning/30 bg-warning-muted/40 p-4">
            <h2 className="mb-3 text-sm font-semibold">Bulk decide ({selected.size} selected)</h2>
            <div className="flex flex-col gap-3">
              <Select
                value={bulkDecision}
                onValueChange={(value) => {
                  setBulkDecision(value as ApprovalDecisionType);
                  setBulkHighRiskAck(false);
                }}
              >
                <SelectTrigger className="w-48">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="approve">Approve</SelectItem>
                  <SelectItem value="request_changes">Request changes</SelectItem>
                  <SelectItem value="reject">Reject</SelectItem>
                </SelectContent>
              </Select>
              <textarea
                value={bulkComments}
                onChange={(event) => setBulkComments(event.target.value)}
                placeholder="Comments (optional, applied to all)"
                rows={2}
                className="resize-none rounded-lg border border-input bg-card px-3 py-2 text-sm shadow-clay-inset placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              {bulkDecision === "approve" && selectedHasHighRisk && (
                <label className="flex items-center gap-2 text-xs text-warning">
                  <input
                    type="checkbox"
                    checked={bulkHighRiskAck}
                    onChange={(event) => setBulkHighRiskAck(event.target.checked)}
                    className="size-3.5 accent-warning"
                  />
                  One or more selected plans is high-risk — I&rsquo;ve reviewed them and want to
                  approve.
                </label>
              )}
              <Button className="w-fit" disabled={bulkDisabled} onClick={() => bulkMutation.mutate()}>
                {bulkMutation.isPending ? "Submitting…" : `${bulkDecision.replace(/_/g, " ")} all`}
              </Button>
              {bulkMutation.isError && (
                <p className="text-sm text-destructive">
                  {bulkMutation.error instanceof ApiError
                    ? bulkMutation.error.message
                    : "Couldn't submit bulk decision."}
                </p>
              )}
            </div>
          </Card>
        )}

        <div className="flex flex-col gap-3">
          {approvals.map((approval, index) => (
            <ApprovalRow
              key={approval.id}
              approval={approval}
              plan={planQueries[index]?.data}
              planLoading={planQueries[index]?.isLoading ?? false}
              canManage={canManage}
              selected={selected.has(approval.id)}
              onToggleSelected={() => toggleSelected(approval.id)}
            />
          ))}
        </div>
      </div>
    </AppShell>
  );
}
