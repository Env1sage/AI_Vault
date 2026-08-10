import { useQuery } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { FileDetail } from "@vault/types";

import { apiClient } from "@/lib/api-client";
import { formatRelativeTime } from "@/lib/format-relative-time";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/files/$fileId")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: FileDetailPage,
});

function FileDetailPage() {
  const { fileId } = Route.useParams();

  const fileQuery = useQuery({
    queryKey: ["files", "detail", fileId],
    queryFn: () => apiClient.get<FileDetail>(`/v1/files/${fileId}`),
  });

  const file = fileQuery.data;

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-8">
      <Link to="/files" className="text-sm underline">
        ← Back to files
      </Link>

      {fileQuery.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
      {fileQuery.isError && <p className="text-sm text-red-600">Couldn't load this file.</p>}

      {file && (
        <>
          <div>
            <h1 className="text-xl font-semibold break-all">{file.name}</h1>
            <p className="text-sm text-neutral-500 break-all">{file.path}</p>
          </div>

          <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
            <h2 className="mb-3 font-medium">Metadata</h2>
            {file.metadata ? (
              <dl className="grid grid-cols-2 gap-y-2 text-sm">
                <dt className="text-neutral-500">Extension</dt>
                <dd>{file.metadata.normalized_extension ?? "—"}</dd>

                <dt className="text-neutral-500">MIME validated</dt>
                <dd>
                  {file.metadata.mime_type_validated
                    ? "yes"
                    : `no — ${file.metadata.mime_mismatch_reason ?? "mismatch"}`}
                </dd>

                <dt className="text-neutral-500">Naming pattern</dt>
                <dd>{file.metadata.naming_pattern ?? "—"}</dd>

                <dt className="text-neutral-500">Version</dt>
                <dd>{file.metadata.version_label ?? "—"}</dd>

                <dt className="text-neutral-500">Owner</dt>
                <dd>{file.metadata.owner_summary ?? "—"}</dd>

                <dt className="text-neutral-500">Sharing</dt>
                <dd>{file.metadata.sharing_summary ?? "—"}</dd>

                <dt className="text-neutral-500">Language</dt>
                <dd>{file.metadata.language ?? "unknown"}</dd>

                <dt className="text-neutral-500">Enriched</dt>
                <dd>{formatRelativeTime(file.metadata.enriched_at)}</dd>
              </dl>
            ) : (
              <p className="text-sm text-neutral-500">Not enriched yet.</p>
            )}
          </section>

          <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
            <h2 className="mb-3 font-medium">Classification</h2>
            {file.classification ? (
              <p className="text-sm">
                <span className="font-medium">{file.classification.document_type}</span>
                <span className="ml-2 text-neutral-500">
                  {Math.round(file.classification.confidence * 100)}% confidence ·{" "}
                  {file.classification.method}
                </span>
              </p>
            ) : (
              <p className="text-sm text-neutral-500">Not classified yet.</p>
            )}
          </section>

          <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
            <h2 className="mb-3 font-medium">Enrichment status</h2>
            {file.extraction ? (
              <p className="text-sm">
                <span className="font-medium capitalize">{file.extraction.status}</span>
                {file.extraction.extractor_name && (
                  <span className="ml-2 text-neutral-500">
                    via {file.extraction.extractor_name}
                    {file.extraction.char_count !== null
                      ? ` · ${file.extraction.char_count} characters`
                      : ""}
                  </span>
                )}
                {file.extraction.error && (
                  <span className="ml-2 text-red-600">{file.extraction.error}</span>
                )}
              </p>
            ) : (
              <p className="text-sm text-neutral-500">Content not processed yet.</p>
            )}
          </section>

          {file.knowledge_attributes.length > 0 && (
            <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
              <h2 className="mb-3 font-medium">Knowledge attributes</h2>
              <ul className="flex flex-wrap gap-2 text-sm">
                {file.knowledge_attributes.map((attribute) => (
                  <li
                    key={`${attribute.attribute_type}-${attribute.value}`}
                    className="rounded-full bg-neutral-100 px-3 py-1 dark:bg-neutral-800"
                  >
                    {attribute.attribute_type}: {attribute.value}
                    <span className="ml-1 text-neutral-500">
                      ({Math.round(attribute.confidence * 100)}%)
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section>
            <h2 className="mb-3 font-medium">Related files</h2>
            {file.related_files.length === 0 && (
              <p className="text-sm text-neutral-500">No relationships discovered yet.</p>
            )}
            <ul className="flex flex-col gap-2">
              {file.related_files.map((related) => (
                <li key={`${related.file_id}-${related.relationship_type}`}>
                  <Link
                    to="/files/$fileId"
                    params={{ fileId: related.file_id }}
                    className="flex items-center justify-between rounded-lg border border-neutral-200 p-3 text-sm hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900"
                  >
                    <div>
                      <p className="font-medium">{related.name}</p>
                      <p className="text-neutral-500">{related.path}</p>
                    </div>
                    <span className="text-neutral-400">
                      {related.relationship_type.replaceAll("_", " ")} ·{" "}
                      {Math.round(related.confidence * 100)}%
                    </span>
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
