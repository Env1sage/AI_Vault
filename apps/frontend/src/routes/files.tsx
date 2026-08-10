import { useQuery } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { Connector, FileListResponse } from "@vault/types";

import { apiClient } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/files")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: FilesPage,
});

function FilesPage() {
  const connectorsQuery = useQuery({
    queryKey: ["connectors"],
    queryFn: () => apiClient.get<Connector[]>("/v1/connectors"),
  });

  const connector = connectorsQuery.data?.find(
    (candidate) => candidate.provider === "google_workspace" && candidate.status === "connected",
  );

  const filesQuery = useQuery({
    queryKey: ["files", connector?.id],
    queryFn: () =>
      apiClient.get<FileListResponse>(`/v1/connectors/${connector?.id}/files?limit=100`),
    enabled: connector !== undefined,
  });

  const files = filesQuery.data?.items ?? [];

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-8">
      <Link to="/scans" className="text-sm underline">
        ← Back to scans
      </Link>
      <h1 className="text-xl font-semibold">Files</h1>

      {connectorsQuery.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
      {!connectorsQuery.isLoading && connector === undefined && (
        <p className="text-sm text-neutral-500">
          Connect Google Workspace first — see{" "}
          <Link to="/storage-connections" className="underline">
            Storage Connections
          </Link>
          .
        </p>
      )}

      {connector && (
        <>
          {filesQuery.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
          {filesQuery.isError && (
            <p className="text-sm text-red-600">Couldn't load files.</p>
          )}
          {files.length === 0 && !filesQuery.isLoading && (
            <p className="text-sm text-neutral-500">
              No files yet — run a scan from the{" "}
              <Link to="/scans" className="underline">
                Scans
              </Link>{" "}
              page first.
            </p>
          )}

          <ul className="flex flex-col gap-2">
            {files.map((file) => (
              <li key={file.id}>
                <Link
                  to="/files/$fileId"
                  params={{ fileId: file.id }}
                  className="flex items-center justify-between rounded-lg border border-neutral-200 p-3 text-sm hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900"
                >
                  <div>
                    <p className="font-medium">{file.name}</p>
                    <p className="text-neutral-500">{file.path}</p>
                  </div>
                  <span className="text-neutral-400">
                    {file.owner_email ?? "—"}
                  </span>
                </Link>
              </li>
            ))}
          </ul>

          {filesQuery.data && filesQuery.data.total > files.length && (
            <p className="text-xs text-neutral-400">
              Showing {files.length} of {filesQuery.data.total} files.
            </p>
          )}
        </>
      )}
    </main>
  );
}
