import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { ApprovalRequest, ExecutionJob, ExecutionPlanDetail } from "@vault/types";

import { Button } from "@/components/ui/button";
import { ApiError, apiClient } from "@/lib/api-client";
import { actionTypeLabel, planStatusColor, riskLevelColor } from "@/lib/execution-style";
import { formatBytes } from "@/lib/format-bytes";
import { formatRelativeTime } from "@/lib/format-relative-time";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/execution-plans/$executionPlanId")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: ExecutionPlanDetailPage,
});

function ExecutionPlanDetailPage() {
  const { executionPlanId } = Route.useParams();
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const canManage = user?.role === "owner" || user?.role === "admin";

  const planQuery = useQuery({
    queryKey: ["execution-plans", executionPlanId],
    queryFn: () => apiClient.get<ExecutionPlanDetail>(`/v1/execution-plans/${executionPlanId}`),
  });

  const approvalsQuery = useQuery({
    queryKey: ["approvals"],
    queryFn: () => apiClient.get<ApprovalRequest[]>("/v1/approvals"),
  });

  const approval = approvalsQuery.data?.find((a) => a.execution_plan_id === executionPlanId);

  const rollbackMutation = useMutation({
    mutationFn: () =>
      apiClient.post<ExecutionJob>(`/v1/execution-plans/${executionPlanId}/rollback`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["execution-plans", executionPlanId] });
      void queryClient.invalidateQueries({ queryKey: ["execution-jobs"] });
    },
  });

  const plan = planQuery.data;

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-8">
      <Link to="/execution-plans" className="text-sm underline">
        ← Back to Execution Center
      </Link>

      {planQuery.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
      {planQuery.isError && (
        <p className="text-sm text-red-600">
          Couldn't load this execution plan — you may not have permission to view it.
        </p>
      )}

      {plan && (
        <>
          <div>
            <span className={`font-medium capitalize ${planStatusColor(plan.status)}`}>
              {plan.status.replace(/_/g, " ")}
            </span>
            <h1 className="text-xl font-semibold">Execution plan</h1>
            <p className="text-neutral-500">{plan.estimated_impact}</p>
          </div>

          <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
            <h2 className="mb-3 font-medium">Risk summary</h2>
            <dl className="grid grid-cols-2 gap-y-3 text-sm">
              <dt className="text-neutral-500">Risk level</dt>
              <dd className={`font-medium ${riskLevelColor(plan.risk_level)}`}>
                {plan.risk_level}
              </dd>

              <dt className="text-neutral-500">Steps</dt>
              <dd>{plan.steps.length}</dd>

              <dt className="text-neutral-500">Estimated storage savings</dt>
              <dd>
                {plan.estimated_storage_savings_bytes !== null
                  ? formatBytes(plan.estimated_storage_savings_bytes)
                  : "—"}
              </dd>

              <dt className="text-neutral-500">Rollback</dt>
              <dd>{plan.rollback_available ? "Available" : "Not reversible"}</dd>

              <dt className="text-neutral-500">Target provider</dt>
              <dd>{plan.target_provider}</dd>

              <dt className="text-neutral-500">Required permissions</dt>
              <dd>{plan.required_permissions.join(", ")}</dd>

              <dt className="text-neutral-500">Created</dt>
              <dd>{formatRelativeTime(plan.created_at)}</dd>
            </dl>
          </section>

          <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
            <h2 className="mb-3 font-medium">Approval</h2>
            {approvalsQuery.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
            {approval ? (
              <Link
                to="/approvals"
                className="text-sm underline"
              >
                View in Approval Queue — status: {approval.status.replace(/_/g, " ")}
              </Link>
            ) : (
              !approvalsQuery.isLoading && (
                <p className="text-sm text-neutral-500">No approval request found for this plan.</p>
              )
            )}
          </section>

          {canManage && plan.rollback_available && (
            <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
              <h2 className="mb-3 font-medium">Rollback</h2>
              <p className="mb-3 text-sm text-neutral-500">
                Reverses every step of this plan that was actually executed and hasn't already
                been rolled back — moved files move back, renamed files restore, archived files
                un-trash.
              </p>
              <Button
                variant="outline"
                disabled={rollbackMutation.isPending}
                onClick={() => rollbackMutation.mutate()}
              >
                {rollbackMutation.isPending ? "Starting rollback…" : "Start rollback"}
              </Button>
              {rollbackMutation.isError && (
                <p className="mt-2 text-sm text-red-600">
                  {rollbackMutation.error instanceof ApiError
                    ? rollbackMutation.error.message
                    : "Couldn't start rollback."}
                </p>
              )}
              {rollbackMutation.isSuccess && (
                <p className="mt-2 text-sm text-green-600">
                  Rollback job started —{" "}
                  <Link
                    to="/execution-jobs/$executionJobId"
                    params={{ executionJobId: rollbackMutation.data.id }}
                    className="underline"
                  >
                    view progress
                  </Link>
                  .
                </p>
              )}
            </section>
          )}

          <section>
            <h2 className="mb-3 font-medium">Steps ({plan.steps.length})</h2>
            <ul className="flex flex-col gap-2">
              {plan.steps.map((step) => (
                <li
                  key={step.id}
                  className="rounded-lg border border-neutral-200 p-3 text-sm dark:border-neutral-800"
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-medium">{actionTypeLabel(step.action_type)}</span>
                    <span className="text-xs capitalize text-neutral-400">{step.status}</span>
                  </div>
                  <Link
                    to="/files/$fileId"
                    params={{ fileId: step.target_file_id }}
                    className="text-xs text-neutral-500 underline"
                  >
                    {step.target_file_id}
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </main>
  );
}
