import { useQuery } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { ApprovalRequest, Workflow, WorkflowExecution } from "@vault/types";

import { apiClient } from "@/lib/api-client";
import { formatRelativeTime } from "@/lib/format-relative-time";
import { executionStatusColor, workflowStatusColor } from "@/lib/workflow-style";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/automation")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: AutomationDashboardPage,
});

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-neutral-200 p-3 dark:border-neutral-800">
      <p className="text-xs text-neutral-500">{label}</p>
      <p className="text-lg font-semibold">{value}</p>
    </div>
  );
}

function AutomationDashboardPage() {
  const workflowsQuery = useQuery({
    queryKey: ["workflows", "active"],
    queryFn: () => apiClient.get<Workflow[]>("/v1/workflows?status=active"),
  });
  const pendingApprovalsQuery = useQuery({
    queryKey: ["approvals", "pending"],
    queryFn: () => apiClient.get<ApprovalRequest[]>("/v1/approvals?status=pending"),
  });
  const recentExecutionsQuery = useQuery({
    queryKey: ["workflow-executions", "recent"],
    queryFn: () => apiClient.get<WorkflowExecution[]>("/v1/workflow-executions"),
  });

  const activeWorkflows = workflowsQuery.data ?? [];
  const pendingApprovals = pendingApprovalsQuery.data ?? [];
  const recentExecutions = (recentExecutionsQuery.data ?? []).slice(0, 5);
  const failedRecent = (recentExecutionsQuery.data ?? []).filter(
    (e) => e.status === "failed",
  ).length;

  return (
    <main className="mx-auto flex max-w-4xl flex-col gap-6 p-8">
      <Link to="/dashboard" className="text-sm underline">
        ← Back to dashboard
      </Link>
      <h1 className="text-xl font-semibold">Automation Dashboard</h1>
      <p className="text-neutral-500">
        Automation is structured execution of the policies you configure — not autonomous
        intelligence. Every automated action still produces the same audited approval decision a
        human's would, just attributed to a policy instead of a person.
      </p>

      <nav className="flex flex-wrap gap-4 text-sm">
        <Link to="/workflows" className="underline">
          Workflow Library
        </Link>
        <Link to="/workflow-executions" className="underline">
          Execution History
        </Link>
        <Link to="/workflow-policies" className="underline">
          Policy Manager
        </Link>
        <Link to="/automation-templates" className="underline">
          Templates Gallery
        </Link>
        <Link to="/notifications" className="underline">
          Notifications
        </Link>
      </nav>

      <section>
        <h2 className="mb-3 font-medium">Overview</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatTile label="Active workflows" value={String(activeWorkflows.length)} />
          <StatTile label="Pending approvals" value={String(pendingApprovals.length)} />
          <StatTile label="Recent runs" value={String(recentExecutionsQuery.data?.length ?? 0)} />
          <StatTile label="Failed runs" value={String(failedRecent)} />
        </div>
      </section>

      <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-medium">Recent executions</h2>
          <Link to="/workflow-executions" className="text-sm underline">
            View all
          </Link>
        </div>
        {recentExecutions.length === 0 ? (
          <p className="text-sm text-neutral-500">No workflow executions yet.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {recentExecutions.map((execution) => (
              <li key={execution.id}>
                <Link
                  to="/workflow-executions/$workflowExecutionId"
                  params={{ workflowExecutionId: execution.id }}
                  className="flex items-center justify-between gap-3 rounded-lg border border-neutral-200 p-3 text-sm hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900"
                >
                  <span className={`font-medium capitalize ${executionStatusColor(execution.status)}`}>
                    {execution.status}
                  </span>
                  <span className="text-xs text-neutral-400">
                    {formatRelativeTime(execution.created_at)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-medium">Active workflows</h2>
          <Link to="/workflows" className="text-sm underline">
            View all
          </Link>
        </div>
        {activeWorkflows.length === 0 ? (
          <p className="text-sm text-neutral-500">No active workflows yet.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {activeWorkflows.slice(0, 5).map((workflow) => (
              <li key={workflow.id}>
                <Link
                  to="/workflows/$workflowId"
                  params={{ workflowId: workflow.id }}
                  className="flex items-center justify-between gap-3 rounded-lg border border-neutral-200 p-3 text-sm hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900"
                >
                  <span className="truncate font-medium">{workflow.name}</span>
                  <span className={`text-xs capitalize ${workflowStatusColor(workflow.status)}`}>
                    {workflow.status}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
