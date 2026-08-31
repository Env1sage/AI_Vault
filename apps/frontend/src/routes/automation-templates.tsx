import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import type { AutomationTemplate, Workflow } from "@vault/types";
import { ChevronLeft, LayoutTemplate } from "lucide-react";

import { AppShell } from "@/components/app-shell/app-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
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
    <AppShell title="Templates Gallery">
      <div className="mx-auto flex max-w-4xl flex-col gap-4">
        <Link
          to="/workflows"
          className="flex w-fit items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ChevronLeft className="size-4" /> Back to Workflow Library
        </Link>
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Templates Gallery</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Applying a template creates a new draft workflow with these nodes already in place.
            Templates referencing an <code>Execute Action</code> node leave the policy unassigned
            — pick or create one in the{" "}
            <Link to="/workflow-policies" className="text-primary hover:underline">
              Policy Manager
            </Link>{" "}
            and finish configuring it in the builder before publishing.
          </p>
        </div>

        {templatesQuery.isLoading && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-28 rounded-xl" />
            ))}
          </div>
        )}
        {templatesQuery.isError && (
          <EmptyState title="Couldn't load templates" description="Please try again." />
        )}
        {templates.length === 0 && !templatesQuery.isLoading && (
          <EmptyState icon={LayoutTemplate} title="No templates available" description="Check back later." />
        )}

        {Object.entries(byCategory).map(([category, categoryTemplates]) => (
          <div key={category}>
            <h2 className="mb-3 text-sm font-semibold capitalize text-muted-foreground">
              {category.replace(/_/g, " ")}
            </h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {categoryTemplates.map((template) => (
                <Card key={template.id} className="flex flex-col gap-2 p-4">
                  <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <LayoutTemplate className="size-4" />
                  </div>
                  <p className="font-medium">{template.name}</p>
                  {template.description && (
                    <p className="flex-1 text-sm text-muted-foreground">{template.description}</p>
                  )}
                  {canManage && (
                    <Button
                      size="sm"
                      className="mt-2 w-fit"
                      disabled={applyMutation.isPending}
                      onClick={() => applyMutation.mutate(template.id)}
                    >
                      {applyMutation.isPending ? "Applying…" : "Use this template"}
                    </Button>
                  )}
                </Card>
              ))}
            </div>
          </div>
        ))}

        {applyMutation.isError && (
          <p className="text-sm text-destructive">
            {applyMutation.error instanceof ApiError
              ? applyMutation.error.message
              : "Couldn't apply this template."}
          </p>
        )}
      </div>
    </AppShell>
  );
}
