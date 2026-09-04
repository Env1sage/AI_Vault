import { useQuery } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { Connector, FileListResponse, FileSummary } from "@vault/types";
import {
  ArrowDownAZ,
  ChevronLeft,
  ChevronRight,
  Cloud,
  LayoutGrid,
  List,
  Users,
} from "lucide-react";
import { useMemo, useState } from "react";

import { AppShell } from "@/components/app-shell/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { apiClient } from "@/lib/api-client";
import { fileTypeIconElement, fileTypeLabel } from "@/lib/file-icon";
import { formatBytes } from "@/lib/format-bytes";
import { formatRelativeTime } from "@/lib/format-relative-time";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/files/")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: FilesPage,
});

type SortKey = "name" | "size" | "modified";
type ViewMode = "list" | "grid";

const PAGE_SIZE = 50;

function readViewMode(): ViewMode {
  if (typeof window === "undefined") return "list";
  return window.localStorage.getItem("vault-file-view") === "grid" ? "grid" : "list";
}

function folderOf(path: string, name: string): string {
  const withoutFile = path.endsWith(name) ? path.slice(0, path.length - name.length) : path;
  const trimmed = withoutFile.replace(/\/+$/, "").replace(/^\/+/, "");
  return trimmed.length > 0 ? trimmed : "Root";
}

function FileRow({ file }: { file: FileSummary }) {
  return (
    <Link
      to="/files/$fileId"
      params={{ fileId: file.id }}
      className="group grid grid-cols-[1fr_auto_auto_auto] items-center gap-4 rounded-lg px-3 py-2.5 text-sm transition-colors hover:bg-secondary/60"
    >
      <div className="flex min-w-0 items-center gap-3">
        <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-secondary text-muted-foreground group-hover:bg-card">
          {fileTypeIconElement(file.mime_type, { className: "size-4" })}
        </span>
        <div className="min-w-0">
          <p className="truncate font-medium">{file.name}</p>
          <p className="truncate text-xs text-muted-foreground">{folderOf(file.path, file.name)}</p>
        </div>
      </div>
      <span className="hidden w-24 shrink-0 truncate text-xs text-muted-foreground sm:block">
        {fileTypeLabel(file.mime_type)}
      </span>
      <span className="hidden w-20 shrink-0 text-right text-xs text-muted-foreground md:block">
        {file.size_bytes !== null ? formatBytes(file.size_bytes) : "—"}
      </span>
      <span className="w-24 shrink-0 text-right text-xs text-muted-foreground">
        {file.provider_modified_at ? formatRelativeTime(file.provider_modified_at) : "—"}
      </span>
    </Link>
  );
}

function FileGridCard({ file }: { file: FileSummary }) {
  return (
    <Link
      to="/files/$fileId"
      params={{ fileId: file.id }}
      className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4 shadow-clay-sm transition-all hover:-translate-y-0.5 hover:shadow-clay"
    >
      <div className="flex aspect-video items-center justify-center rounded-lg bg-secondary">
        {fileTypeIconElement(file.mime_type, { className: "size-8 text-muted-foreground" })}
      </div>
      <div className="min-w-0">
        <p className="truncate text-sm font-medium">{file.name}</p>
        <p className="truncate text-xs text-muted-foreground">{folderOf(file.path, file.name)}</p>
      </div>
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{file.size_bytes !== null ? formatBytes(file.size_bytes) : "—"}</span>
        {file.is_shared ? (
          <span className="flex items-center gap-1">
            <Users className="size-3" /> Shared
          </span>
        ) : null}
      </div>
    </Link>
  );
}

function FilesPage() {
  const [viewMode, setViewMode] = useState<ViewMode>(readViewMode);
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("modified");
  const [page, setPage] = useState(0);

  function changeView(mode: ViewMode) {
    setViewMode(mode);
    window.localStorage.setItem("vault-file-view", mode);
  }

  const connectorsQuery = useQuery({
    queryKey: ["connectors"],
    queryFn: () => apiClient.get<Connector[]>("/v1/connectors"),
  });

  const connector = connectorsQuery.data?.find(
    (candidate) => candidate.provider === "google_workspace" && candidate.status === "connected",
  );

  const filesQuery = useQuery({
    queryKey: ["files", connector?.id, page],
    queryFn: () =>
      apiClient.get<FileListResponse>(
        `/v1/connectors/${connector?.id}/files?limit=${PAGE_SIZE}&offset=${page * PAGE_SIZE}`,
      ),
    enabled: connector !== undefined,
  });

  const files = filesQuery.data?.items ?? [];
  const total = filesQuery.data?.total ?? 0;

  const visibleFiles = useMemo(() => {
    const filtered = query.trim()
      ? files.filter((f) => f.name.toLowerCase().includes(query.trim().toLowerCase()))
      : files;
    return [...filtered].sort((a, b) => {
      if (sortKey === "name") return a.name.localeCompare(b.name);
      if (sortKey === "size") return (b.size_bytes ?? 0) - (a.size_bytes ?? 0);
      return (b.provider_modified_at ?? "").localeCompare(a.provider_modified_at ?? "");
    });
  }, [files, query, sortKey]);

  return (
    <AppShell title="Files">
      <div className="mx-auto flex max-w-6xl flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">Files</h1>
            <p className="text-sm text-muted-foreground">
              Everything Vault has scanned across your connected storage.
            </p>
          </div>
        </div>

        {connectorsQuery.isLoading && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-24 rounded-xl" />
            ))}
          </div>
        )}

        {!connectorsQuery.isLoading && connector === undefined && (
          <EmptyState
            icon={Cloud}
            title="No storage connected yet"
            description="Connect Google Workspace to let Vault scan and understand your organization's files."
            action={
              <Button asChild>
                <Link to="/storage-connections">Connect Google Drive</Link>
              </Button>
            }
          />
        )}

        {connector && (
          <>
            <Card className="flex flex-wrap items-center gap-2 p-2">
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Filter files on this page…"
                className="w-full max-w-xs"
              />
              <Select value={sortKey} onValueChange={(v) => setSortKey(v as SortKey)}>
                <SelectTrigger className="w-40">
                  <ArrowDownAZ className="size-4 text-muted-foreground" />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="modified">Last modified</SelectItem>
                  <SelectItem value="name">Name</SelectItem>
                  <SelectItem value="size">Size</SelectItem>
                </SelectContent>
              </Select>

              <div className="ml-auto flex items-center gap-1 rounded-lg bg-secondary p-1">
                <button
                  type="button"
                  onClick={() => changeView("list")}
                  aria-pressed={viewMode === "list"}
                  aria-label="List view"
                  className={cn(
                    "rounded-md p-1.5 transition-colors",
                    viewMode === "list" ? "bg-card shadow-clay-sm" : "text-muted-foreground",
                  )}
                >
                  <List className="size-4" />
                </button>
                <button
                  type="button"
                  onClick={() => changeView("grid")}
                  aria-pressed={viewMode === "grid"}
                  aria-label="Grid view"
                  className={cn(
                    "rounded-md p-1.5 transition-colors",
                    viewMode === "grid" ? "bg-card shadow-clay-sm" : "text-muted-foreground",
                  )}
                >
                  <LayoutGrid className="size-4" />
                </button>
              </div>
            </Card>

            {filesQuery.isLoading && (
              <div className="flex flex-col gap-2">
                {Array.from({ length: 8 }).map((_, i) => (
                  <Skeleton key={i} className="h-12 rounded-lg" />
                ))}
              </div>
            )}

            {filesQuery.isError && (
              <EmptyState title="Couldn't load files" description="Please try again." />
            )}

            {filesQuery.isSuccess && files.length === 0 && (
              <EmptyState
                title="No files yet"
                description="Run a scan to let Vault index this connector's storage."
                action={
                  <Button asChild variant="outline">
                    <Link to="/scans">Go to Scans</Link>
                  </Button>
                }
              />
            )}

            {visibleFiles.length > 0 &&
              (viewMode === "list" ? (
                <Card className="flex flex-col divide-y divide-border p-1">
                  {visibleFiles.map((file) => (
                    <FileRow key={file.id} file={file} />
                  ))}
                </Card>
              ) : (
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
                  {visibleFiles.map((file) => (
                    <FileGridCard key={file.id} file={file} />
                  ))}
                </div>
              ))}

            {total > PAGE_SIZE && (
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>
                  Showing {page * PAGE_SIZE + 1}–{Math.min(total, (page + 1) * PAGE_SIZE)} of{" "}
                  {total.toLocaleString()}
                  <Badge variant="outline" className="ml-2">
                    Page-local filter/sort only
                  </Badge>
                </span>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page === 0}
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                  >
                    <ChevronLeft className="size-4" /> Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={(page + 1) * PAGE_SIZE >= total}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Next <ChevronRight className="size-4" />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
