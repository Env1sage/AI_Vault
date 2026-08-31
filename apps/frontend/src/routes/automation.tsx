import { useQuery } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { ApprovalRequest, Workflow, WorkflowExecution } from "@vault/types";
import {
  Bell,
  ClipboardCheck,
  LayoutTemplate,
  ShieldCheck,
  Workflow as WorkflowIcon,
  Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { AppShell } from "@/components/app-shell/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api-client";
import { formatRelativeTime } from "@/lib/format-relative-time";
import { executionStatusBadgeVariant, workflowStatusBadgeVariant } from "@/lib/workflow-style";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/automation")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: AutomationDashboardPage,
});

function StatTile({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string }) {
  return (
    <Card clay className="flex flex-col gap-2 p-4">
      <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <Icon className="size-4" />
      </div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-xl font-semibold">{value}</p>
    </Card>
  );
}

const QUICK_LINKS = [
  { to: "/workflows", label: "Workflow Library", icon: WorkflowIcon },
  { to: "/workflow-policies", label: "Policy Manager", icon: ShieldCheck },
  { to: "/automation-templates", label: "Templates", icon: LayoutTemplate },
  { to: "/notifications", label: "Notifications", icon: Bell },
];

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
  const failedRecent = (recentExecutionsQuery.data ?? []).filter((e) => e.status === "failed").length;

  return (
    <AppShell title="Automation">
      <div className="mx-auto flex max-w-5xl flex-col gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Automation Dashboard</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Automation is structured execution of the policies you configure — not autonomous
            intelligence. Every automated action still produces the same audited approval
            decision a human&rsquo;s would, just attributed to a policy instead of a person.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          {QUICK_LINKS.map((link) => (
            <Button key={link.to} variant="outline" size="sm" asChild>
              <Link to={link.to}>
                <link.icon className="size-4" /> {link.label}
              </Link>
            </Button>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatTile icon={Zap} label="Active workflows" value={String(activeWorkflows.length)} />
          <StatTile icon={ClipboardCheck} label="Pending approvals" value={String(pendingApprovals.length)} />
          <StatTile
            icon={WorkflowIcon}
            label="Recent runs"
            value={String(recentExecutionsQuery.data?.length ?? 0)}
          />
          <StatTile icon={Bell} label="Failed runs" value={String(failedRecent)} />
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader className="flex-row items-center justify-between gap-2 space-y-0">
              <CardTitle>Recent executions</CardTitle>
              <Link to="/workflow-executions" className="text-xs font-medium text-primary hover:underline">
                View all
              </Link>
            </CardHeader>
            <CardContent>
              {recentExecutions.length === 0 ? (
                <p className="py-6 text-center text-sm text-muted-foreground">No workflow executions yet.</p>
              ) : (
                <ul className="flex flex-col divide-y divide-border">
                  {recentExecutions.map((execution) => (
                    <li key={execution.id}>
                      <Link
                        to="/workflow-executions/$workflowExecutionId"
                        params={{ workflowExecutionId: execution.id }}
                        className="flex items-center justify-between gap-3 py-2.5 text-sm"
                      >
                        <Badge variant={executionStatusBadgeVariant(execution.status)} className="capitalize">
                          {execution.status}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {formatRelativeTime(execution.created_at)}
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center justify-between gap-2 space-y-0">
              <CardTitle>Active workflows</CardTitle>
              <Link to="/workflows" className="text-xs font-medium text-primary hover:underline">
                View all
              </Link>
            </CardHeader>
            <CardContent>
              {activeWorkflows.length === 0 ? (
                <p className="py-6 text-center text-sm text-muted-foreground">No active workflows yet.</p>
              ) : (
                <ul className="flex flex-col divide-y divide-border">
                  {activeWorkflows.slice(0, 5).map((workflow) => (
                    <li key={workflow.id}>
                      <Link
                        to="/workflows/$workflowId"
                        params={{ workflowId: workflow.id }}
                        className="flex items-center justify-between gap-3 py-2.5 text-sm"
                      >
                        <span className="truncate font-medium">{workflow.name}</span>
                        <Badge variant={workflowStatusBadgeVariant(workflow.status)} className="capitalize">
                          {workflow.status}
                        </Badge>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}
