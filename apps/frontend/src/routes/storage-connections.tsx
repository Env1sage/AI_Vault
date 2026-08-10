import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { Connector, InitiateConnectResponse } from "@vault/types";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api-client";
import { connectorStatusColor } from "@/lib/connector-status";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/storage-connections")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: StorageConnectionsPage,
});

function StorageConnectionsPage() {
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const canManage = user?.role === "owner" || user?.role === "admin";
  const [confirmingDisconnectId, setConfirmingDisconnectId] = useState<string | null>(null);

  const connectorsQuery = useQuery({
    queryKey: ["connectors"],
    queryFn: () => apiClient.get<Connector[]>("/v1/connectors"),
  });

  const connectMutation = useMutation({
    mutationFn: () => apiClient.post<InitiateConnectResponse>("/v1/connectors/google/connect"),
    onSuccess: (data) => {
      // A real top-level navigation, not a fetch — Google must redirect the
      // whole browser tab, and our SPA state is deliberately gone until the
      // /connectors/google/callback route reloads it (see that route's note).
      window.location.href = data.authorize_url;
    },
  });

  const disconnectMutation = useMutation({
    mutationFn: (connectorId: string) =>
      apiClient.post<Connector>(`/v1/connectors/${connectorId}/disconnect`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["connectors"] });
      setConfirmingDisconnectId(null);
    },
  });

  const verifyMutation = useMutation({
    mutationFn: (connectorId: string) =>
      apiClient.post<Connector>(`/v1/connectors/${connectorId}/verify`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["connectors"] }),
  });

  const hasActiveGoogleConnector = connectorsQuery.data?.some(
    (connector) => connector.provider === "google_workspace" && connector.status !== "disconnected",
  );

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-8">
      <Link to="/dashboard" className="text-sm underline">
        ← Back to dashboard
      </Link>
      <h1 className="text-xl font-semibold">Storage Connections</h1>

      {connectorsQuery.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
      {connectorsQuery.isError && (
        <p className="text-sm text-red-600">Couldn't load storage connections.</p>
      )}
      {connectorsQuery.data?.length === 0 && (
        <p className="text-sm text-neutral-500">No storage connected yet.</p>
      )}

      {connectorsQuery.data?.map((connector) => (
        <div
          key={connector.id}
          className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Google Workspace</p>
              <p className="text-sm text-neutral-500">
                {connector.account_email ?? "—"}
                {connector.workspace_domain ? ` (${connector.workspace_domain})` : ""}
              </p>
              <p className="text-xs text-neutral-400">
                Last synced: {connector.last_verified_at ? "not yet available" : "never"}
              </p>
            </div>
            <span className={`text-sm font-medium capitalize ${connectorStatusColor(connector.status)}`}>
              {connector.status}
            </span>
          </div>

          {connector.last_error && (
            <p className="mt-2 text-sm text-red-600">{connector.last_error}</p>
          )}

          <div className="mt-3 flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={verifyMutation.isPending}
              onClick={() => verifyMutation.mutate(connector.id)}
            >
              {verifyMutation.isPending ? "Verifying…" : "Verify"}
            </Button>

            {canManage &&
              connector.status !== "disconnected" &&
              (confirmingDisconnectId === connector.id ? (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={disconnectMutation.isPending}
                    onClick={() => disconnectMutation.mutate(connector.id)}
                  >
                    {disconnectMutation.isPending ? "Disconnecting…" : "Confirm disconnect"}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setConfirmingDisconnectId(null)}
                  >
                    Cancel
                  </Button>
                </>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setConfirmingDisconnectId(connector.id)}
                >
                  Disconnect
                </Button>
              ))}
          </div>
        </div>
      ))}

      {canManage && !hasActiveGoogleConnector && (
        <Button onClick={() => connectMutation.mutate()} disabled={connectMutation.isPending}>
          {connectMutation.isPending ? "Redirecting…" : "Connect Google Workspace"}
        </Button>
      )}
      {connectMutation.isError && (
        <p className="text-sm text-red-600">Couldn't start the connection. Please try again.</p>
      )}
    </main>
  );
}
