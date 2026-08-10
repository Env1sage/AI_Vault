import { useQuery } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { ExecutionPlan } from "@vault/types";
import { useState } from "react";

import { apiClient } from "@/lib/api-client";
import { formatRelativeTime } from "@/lib/format-relative-time";
import { planStatusColor, riskLevelColor } from "@/lib/execution-style";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/execution-plans")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: ExecutionCenterPage,
});

function ExecutionCenterPage() {
  const [status, setStatus] = useState<string>("");

  const params = new URLSearchParams();
  if (status) params.set("status", status);

  const plansQuery = useQuery({
    queryKey: ["execution-plans", status],
    queryFn: () => apiClient.get<ExecutionPlan[]>(`/v1/execution-plans?${params.toString()}`),
  });

  const plans = plansQuery.data ?? [];

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-8">
      <Link to="/dashboard" className="text-sm underline">
        ← Back to dashboard
      </Link>
      <h1 className="text-xl font-semibold">Execution Center</h1>
      <p className="text-sm text-neutral-500">
        Execution plans built from recommendations. Nothing here touches Google Drive until an
        owner or admin approves it in the{" "}
        <Link to="/approvals" className="underline">
          Approval Queue
        </Link>
        .
      </p>

      <div className="flex flex-wrap gap-2">
        <select
          value={status}
          onChange={(event) => setStatus(event.target.value)}
          className="rounded-md border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-800 dark:bg-neutral-950"
        >
          <option value="">All statuses</option>
          <option value="pending_approval">Pending approval</option>
          <option value="approved">Approved</option>
          <option value="executing">Executing</option>
          <option value="completed">Completed</option>
          <option value="partially_completed">Partially completed</option>
          <option value="failed">Failed</option>
          <option value="rejected">Rejected</option>
          <option value="changes_requested">Changes requested</option>
          <option value="expired">Expired</option>
          <option value="rolled_back">Rolled back</option>
        </select>
        <Link
          to="/execution-jobs"
          className="ml-auto rounded-md border border-neutral-200 px-3 py-2 text-sm hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900"
        >
          Execution history
        </Link>
      </div>

      {plansQuery.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
      {plansQuery.isError && <p className="text-sm text-red-600">Couldn't load execution plans.</p>}
      {plans.length === 0 && !plansQuery.isLoading && (
        <p className="text-sm text-neutral-500">
          No execution plans match these filters. Create one from a recommendation's detail page.
        </p>
      )}

      <ul className="flex flex-col gap-2">
        {plans.map((plan) => (
          <li key={plan.id}>
            <Link
              to="/execution-plans/$executionPlanId"
              params={{ executionPlanId: plan.id }}
              className="flex flex-col gap-2 rounded-lg border border-neutral-200 p-3 text-sm hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900"
            >
              <div className="flex items-center justify-between gap-3">
                <span className={`font-medium capitalize ${planStatusColor(plan.status)}`}>
                  {plan.status.replace(/_/g, " ")}
                </span>
                <span className={`shrink-0 text-xs ${riskLevelColor(plan.risk_level)}`}>
                  {plan.risk_level} risk
                </span>
              </div>
              <p className="text-neutral-500">{plan.estimated_impact}</p>
              <div className="flex items-center gap-3 text-xs text-neutral-400">
                <span>{plan.target_provider}</span>
                <span>{plan.rollback_available ? "rollback available" : "not reversible"}</span>
                <span>{formatRelativeTime(plan.created_at)}</span>
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
