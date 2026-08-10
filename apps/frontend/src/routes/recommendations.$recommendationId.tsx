import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { ExecutionPlan, Recommendation } from "@vault/types";

import { Button } from "@/components/ui/button";
import { ApiError, apiClient } from "@/lib/api-client";
import { formatRelativeTime } from "@/lib/format-relative-time";
import { categoryColor, categoryLabel, riskColor } from "@/lib/recommendation-style";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/recommendations/$recommendationId")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: RecommendationDetailPage,
});

const _MAX_FILES_SHOWN = 20;

function RecommendationDetailPage() {
  const { recommendationId } = Route.useParams();
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const canManage = user?.role === "owner" || user?.role === "admin";

  const recommendationQuery = useQuery({
    queryKey: ["recommendations", recommendationId],
    queryFn: () => apiClient.get<Recommendation>(`/v1/recommendations/${recommendationId}`),
  });

  const createPlanMutation = useMutation({
    mutationFn: () =>
      apiClient.post<ExecutionPlan>("/v1/execution-plans", {
        recommendation_id: recommendationId,
      }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["execution-plans"] }),
  });

  const recommendation = recommendationQuery.data;
  const shownFiles = recommendation?.affected_file_ids.slice(0, _MAX_FILES_SHOWN) ?? [];
  const remainingCount = recommendation
    ? recommendation.affected_file_ids.length - shownFiles.length
    : 0;

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-8">
      <Link to="/recommendations" className="text-sm underline">
        ← Back to recommendations
      </Link>

      {recommendationQuery.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
      {recommendationQuery.isError && (
        <p className="text-sm text-red-600">
          Couldn't load this recommendation — you may not have permission to view it.
        </p>
      )}

      {recommendation && (
        <>
          <div>
            <div className="mb-2 flex items-center gap-2">
              <span
                className={`rounded-full px-2 py-1 text-xs font-medium ${categoryColor(recommendation.category)}`}
              >
                {categoryLabel(recommendation.category)}
              </span>
              {recommendation.status === "resolved" && (
                <span className="rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-800 dark:bg-green-950 dark:text-green-300">
                  resolved
                </span>
              )}
            </div>
            <h1 className="text-xl font-semibold">{recommendation.title}</h1>
            <p className="text-neutral-500">{recommendation.description}</p>
          </div>

          <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
            <dl className="grid grid-cols-2 gap-y-3 text-sm">
              <dt className="text-neutral-500">Confidence</dt>
              <dd>{Math.round(recommendation.confidence * 100)}%</dd>

              <dt className="text-neutral-500">Estimated impact</dt>
              <dd>{recommendation.estimated_impact}</dd>

              <dt className="text-neutral-500">Risk level</dt>
              <dd className={riskColor(recommendation.risk_level)}>{recommendation.risk_level}</dd>

              <dt className="text-neutral-500">Priority score</dt>
              <dd>{recommendation.priority_score.toFixed(1)}</dd>

              <dt className="text-neutral-500">Requires approval</dt>
              <dd>{recommendation.requires_approval ? "Yes" : "No"}</dd>

              <dt className="text-neutral-500">Departments</dt>
              <dd>
                {recommendation.related_departments.length > 0
                  ? recommendation.related_departments.join(", ")
                  : "—"}
              </dd>

              <dt className="text-neutral-500">Generated</dt>
              <dd>{formatRelativeTime(recommendation.created_at)}</dd>
            </dl>
          </section>

          <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
            <h2 className="mb-2 font-medium">Suggested action</h2>
            <p className="text-sm text-neutral-600 dark:text-neutral-300">
              {recommendation.suggested_action}
            </p>
            <p className="mt-2 text-xs text-neutral-400">
              This platform never touches Google Drive automatically. An execution plan below is
              just a reviewable proposal — nothing runs until an owner or admin approves it in the{" "}
              <Link to="/approvals" className="underline">
                Approval Queue
              </Link>
              .
            </p>

            {recommendation.status === "active" && (
              <div className="mt-3">
                {canManage ? (
                  <Button
                    size="sm"
                    disabled={createPlanMutation.isPending}
                    onClick={() => createPlanMutation.mutate()}
                  >
                    {createPlanMutation.isPending ? "Creating plan…" : "Create execution plan"}
                  </Button>
                ) : (
                  <p className="text-xs text-neutral-500">
                    Only owners and admins can create execution plans.
                  </p>
                )}
                {createPlanMutation.isError && (
                  <p className="mt-2 text-sm text-red-600">
                    {createPlanMutation.error instanceof ApiError
                      ? createPlanMutation.error.message
                      : "Couldn't create an execution plan for this recommendation."}
                  </p>
                )}
                {createPlanMutation.isSuccess && (
                  <p className="mt-2 text-sm text-green-600">
                    Execution plan created —{" "}
                    <Link
                      to="/execution-plans/$executionPlanId"
                      params={{ executionPlanId: createPlanMutation.data.id }}
                      className="underline"
                    >
                      review it
                    </Link>
                    .
                  </p>
                )}
              </div>
            )}
          </section>

          <section>
            <h2 className="mb-3 font-medium">
              Affected files ({recommendation.affected_file_ids.length})
            </h2>
            {shownFiles.length === 0 ? (
              <p className="text-sm text-neutral-500">No specific files are attached to this recommendation.</p>
            ) : (
              <ul className="flex flex-col gap-1">
                {shownFiles.map((fileId) => (
                  <li key={fileId}>
                    <Link
                      to="/files/$fileId"
                      params={{ fileId }}
                      className="text-sm underline"
                    >
                      {fileId}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
            {remainingCount > 0 && (
              <p className="mt-2 text-sm text-neutral-500">and {remainingCount} more files.</p>
            )}
          </section>
        </>
      )}
    </main>
  );
}
