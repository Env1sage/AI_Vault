import { useQuery } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { Notification } from "@vault/types";
import { Bell } from "lucide-react";

import { AppShell } from "@/components/app-shell/app-shell";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { apiClient } from "@/lib/api-client";
import { formatRelativeTime } from "@/lib/format-relative-time";
import { notificationStatusBadgeVariant } from "@/lib/workflow-style";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/notifications")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: NotificationsPage,
});

function NotificationsPage() {
  const notificationsQuery = useQuery({
    queryKey: ["notifications"],
    queryFn: () => apiClient.get<Notification[]>("/v1/notifications"),
  });

  const notifications = notificationsQuery.data ?? [];

  return (
    <AppShell title="Notifications">
      <div className="mx-auto flex max-w-2xl flex-col gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Notifications</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            In-app notifications a workflow sent you — approval requests, run summaries, reports.
            Email delivery is stubbed this phase (no real email provider configured yet): every
            notification below still exists for real, but an &ldquo;email&rdquo; channel entry was
            never actually sent anywhere.
          </p>
        </div>

        {notificationsQuery.isLoading && (
          <div className="flex flex-col gap-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-20 rounded-xl" />
            ))}
          </div>
        )}
        {notificationsQuery.isError && (
          <EmptyState title="Couldn't load notifications" description="Please try again." />
        )}
        {notifications.length === 0 && !notificationsQuery.isLoading && (
          <EmptyState icon={Bell} title="No notifications yet" description="You're all caught up." />
        )}

        <ul className="flex flex-col gap-2">
          {notifications.map((notification) => (
            <Card key={notification.id} className="flex flex-col gap-1 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="font-medium">{notification.subject}</p>
                <Badge variant={notificationStatusBadgeVariant(notification.status)} className="capitalize">
                  {notification.channel} · {notification.status}
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground">{notification.body}</p>
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <span>{formatRelativeTime(notification.created_at)}</span>
                {notification.workflow_execution_id && (
                  <Link
                    to="/workflow-executions/$workflowExecutionId"
                    params={{ workflowExecutionId: notification.workflow_execution_id }}
                    className="text-primary hover:underline"
                  >
                    view execution
                  </Link>
                )}
              </div>
            </Card>
          ))}
        </ul>
      </div>
    </AppShell>
  );
}
