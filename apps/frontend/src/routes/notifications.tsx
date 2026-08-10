import { useQuery } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { Notification } from "@vault/types";

import { apiClient } from "@/lib/api-client";
import { formatRelativeTime } from "@/lib/format-relative-time";
import { notificationStatusColor } from "@/lib/workflow-style";
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
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-8">
      <Link to="/dashboard" className="text-sm underline">
        ← Back to dashboard
      </Link>
      <h1 className="text-xl font-semibold">Notifications</h1>
      <p className="text-sm text-neutral-500">
        In-app notifications a workflow sent you — approval requests, run summaries, reports. Email
        delivery is stubbed this phase (no real email provider configured yet): every notification
        below still exists for real, but an "email" channel entry was never actually sent anywhere.
      </p>

      {notificationsQuery.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
      {notificationsQuery.isError && (
        <p className="text-sm text-red-600">Couldn't load notifications.</p>
      )}
      {notifications.length === 0 && !notificationsQuery.isLoading && (
        <p className="text-sm text-neutral-500">No notifications yet.</p>
      )}

      <ul className="flex flex-col gap-2">
        {notifications.map((notification) => (
          <li
            key={notification.id}
            className="flex flex-col gap-1 rounded-lg border border-neutral-200 p-3 text-sm dark:border-neutral-800"
          >
            <div className="flex items-center justify-between gap-3">
              <p className="font-medium">{notification.subject}</p>
              <span className={`text-xs capitalize ${notificationStatusColor(notification.status)}`}>
                {notification.channel} · {notification.status}
              </span>
            </div>
            <p className="text-neutral-500">{notification.body}</p>
            <span className="text-xs text-neutral-400">
              {formatRelativeTime(notification.created_at)}
            </span>
            {notification.workflow_execution_id && (
              <Link
                to="/workflow-executions/$workflowExecutionId"
                params={{ workflowExecutionId: notification.workflow_execution_id }}
                className="text-xs underline"
              >
                view execution
              </Link>
            )}
          </li>
        ))}
      </ul>
    </main>
  );
}
