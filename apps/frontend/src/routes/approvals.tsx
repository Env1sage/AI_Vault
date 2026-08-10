import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type {
  ApprovalDecisionType,
  ApprovalRequest,
  ExecutionPlan,
  ExecutionPlanDetail,
} from "@vault/types";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, apiClient } from "@/lib/api-client";
import { approvalStatusColor, riskLevelColor } from "@/lib/execution-style";
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
    <li className="flex flex-col gap-3 rounded-lg border border-neutral-200 p-3 text-sm dark:border-neutral-800">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2">
          {isPending && canManage && (
            <input
              type="checkbox"
              checked={selected}
              onChange={onToggleSelected}
              className="mt-1"
              aria-label="Select for bulk decision"
            />
          )}
          <div>
            <span className={`font-medium capitalize ${approvalStatusColor(approval.status)}`}>
              {approval.status.replace(/_/g, " ")}
            </span>
            <Link
              to="/execution-plans/$executionPlanId"
              params={{ executionPlanId: approval.execution_plan_id }}
              className="ml-2 text-xs underline"
            >
              view plan
            </Link>
          </div>
        </div>
        <span className="shrink-0 text-xs text-neutral-400">
          expires {formatRelativeTime(approval.expires_at)}
        </span>
      </div>

      {planLoading && <p className="text-xs text-neutral-500">Loading plan…</p>}
      {plan && (
        <div className="flex items-center gap-3 text-xs text-neutral-500">
          <span className={riskLevelColor(plan.risk_level)}>{plan.risk_level} risk</span>
          <span>{plan.estimated_impact}</span>
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
            className="rounded-md border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-800 dark:bg-neutral-950"
          />

          {isHighRisk && (
            <label className="flex items-center gap-2 text-xs text-amber-600">
              <input
                type="checkbox"
                checked={highRiskAck}
                onChange={(event) => setHighRiskAck(event.target.checked)}
              />
              This is a high-risk plan ({plan?.estimated_impact}) — I've reviewed it and want to
              approve it.
            </label>
          )}

          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              disabled={approveDisabled}
              onClick={() => decideMutation.mutate("approve")}
            >
              Approve
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={decideMutation.isPending}
              onClick={() => decideMutation.mutate("request_changes")}
            >
              Request changes
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={decideMutation.isPending}
              onClick={() => decideMutation.mutate("reject")}
            >
              Reject
            </Button>
          </div>

          {decideMutation.isError && (
            <p className="text-sm text-red-600">
              {decideMutation.error instanceof ApiError
                ? decideMutation.error.message
                : "Couldn't record this decision."}
            </p>
          )}
        </>
      )}
    </li>
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
  if (status) params.set("status", status);

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
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-8">
      <Link to="/dashboard" className="text-sm underline">
        ← Back to dashboard
      </Link>
      <h1 className="text-xl font-semibold">Approval Queue</h1>
      <p className="text-sm text-neutral-500">
        Approving a plan enqueues real Google Drive changes. Every decision is recorded with who
        made it, when, and why.
      </p>

      <select
        value={status}
        onChange={(event) => {
          setStatus(event.target.value);
          setSelected(new Set());
        }}
        className="w-fit rounded-md border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-800 dark:bg-neutral-950"
      >
        <option value="pending">Pending</option>
        <option value="approved">Approved</option>
        <option value="rejected">Rejected</option>
        <option value="changes_requested">Changes requested</option>
        <option value="expired">Expired</option>
        <option value="">All statuses</option>
      </select>

      {approvalsQuery.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
      {approvalsQuery.isError && <p className="text-sm text-red-600">Couldn't load approvals.</p>}
      {approvals.length === 0 && !approvalsQuery.isLoading && (
        <p className="text-sm text-neutral-500">No approval requests match these filters.</p>
      )}

      {canManage && status === "pending" && selected.size > 0 && (
        <section className="rounded-lg border border-amber-300 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-950">
          <h2 className="mb-3 font-medium">Bulk decide ({selected.size} selected)</h2>
          <div className="flex flex-col gap-3">
            <select
              value={bulkDecision}
              onChange={(event) => {
                setBulkDecision(event.target.value as ApprovalDecisionType);
                setBulkHighRiskAck(false);
              }}
              className="w-fit rounded-md border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-800 dark:bg-neutral-950"
            >
              <option value="approve">Approve</option>
              <option value="request_changes">Request changes</option>
              <option value="reject">Reject</option>
            </select>
            <textarea
              value={bulkComments}
              onChange={(event) => setBulkComments(event.target.value)}
              placeholder="Comments (optional, applied to all)"
              rows={2}
              className="rounded-md border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-800 dark:bg-neutral-950"
            />
            {bulkDecision === "approve" && selectedHasHighRisk && (
              <label className="flex items-center gap-2 text-xs text-amber-700 dark:text-amber-300">
                <input
                  type="checkbox"
                  checked={bulkHighRiskAck}
                  onChange={(event) => setBulkHighRiskAck(event.target.checked)}
                />
                One or more selected plans is high-risk — I've reviewed them and want to approve.
              </label>
            )}
            <Button
              className="w-fit"
              disabled={bulkDisabled}
              onClick={() => bulkMutation.mutate()}
            >
              {bulkMutation.isPending ? "Submitting…" : `${bulkDecision.replace(/_/g, " ")} all`}
            </Button>
            {bulkMutation.isError && (
              <p className="text-sm text-red-600">
                {bulkMutation.error instanceof ApiError
                  ? bulkMutation.error.message
                  : "Couldn't submit bulk decision."}
              </p>
            )}
          </div>
        </section>
      )}

      <ul className="flex flex-col gap-2">
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
      </ul>
    </main>
  );
}
