import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import type { AutomationTemplate, Workflow } from "@vault/types";

import { Button } from "@/components/ui/button";
import { ApiError, apiClient } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/automation-templates")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: TemplatesGalleryPage,
});

function TemplatesGalleryPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const canManage = user?.role === "owner" || user?.role === "admin";

  const templatesQuery = useQuery({
    queryKey: ["automation-templates"],
    queryFn: () => apiClient.get<AutomationTemplate[]>("/v1/automation-templates"),
  });

  const applyMutation = useMutation({
    mutationFn: (templateId: string) =>
      apiClient.post<Workflow>(`/v1/automation-templates/${templateId}/apply`, {}),
    onSuccess: (workflow) => {
      void queryClient.invalidateQueries({ queryKey: ["workflows"] });
      void navigate({ to: "/workflows/$workflowId", params: { workflowId: workflow.id } });
    },
  });

  const templates = templatesQuery.data ?? [];
  const byCategory = templates.reduce<Record<string, AutomationTemplate[]>>((acc, template) => {
    (acc[template.category] ??= []).push(template);
    return acc;
  }, {});

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-8">
      <Link to="/workflows" className="text-sm underline">
        ← Back to Workflow Library
      </Link>
      <h1 className="text-xl font-semibold">Templates Gallery</h1>
      <p className="text-sm text-neutral-500">
        Applying a template creates a new draft workflow with these nodes already in place.
        Templates referencing an <code>Execute Action</code> node leave the policy unassigned —
        pick or create one in the{" "}
        <Link to="/workflow-policies" className="underline">
          Policy Manager
        </Link>{" "}
        and finish configuring it in the builder before publishing.
      </p>

      {templatesQuery.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
      {templatesQuery.isError && (
        <p className="text-sm text-red-600">Couldn't load templates.</p>
      )}

      {Object.entries(byCategory).map(([category, categoryTemplates]) => (
        <section key={category}>
          <h2 className="mb-3 font-medium capitalize">{category.replace(/_/g, " ")}</h2>
          <ul className="flex flex-col gap-2">
            {categoryTemplates.map((template) => (
              <li
                key={template.id}
                className="flex flex-col gap-2 rounded-lg border border-neutral-200 p-3 text-sm dark:border-neutral-800"
              >
                <p className="font-medium">{template.name}</p>
                {template.description && (
                  <p className="text-neutral-500">{template.description}</p>
                )}
                {canManage && (
                  <Button
                    size="sm"
                    className="w-fit"
                    disabled={applyMutation.isPending}
                    onClick={() => applyMutation.mutate(template.id)}
                  >
                    {applyMutation.isPending ? "Applying…" : "Use this template"}
                  </Button>
                )}
              </li>
            ))}
          </ul>
        </section>
      ))}

      {applyMutation.isError && (
        <p className="text-sm text-red-600">
          {applyMutation.error instanceof ApiError
            ? applyMutation.error.message
            : "Couldn't apply this template."}
        </p>
      )}
    </main>
  );
}
