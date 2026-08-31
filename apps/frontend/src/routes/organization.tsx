import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, redirect } from "@tanstack/react-router";
import type {
  AIProviderConfig,
  AIProviderConfigTestResponse,
  Organization,
} from "@vault/types";
import { Building2, KeyRound } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AppShell } from "@/components/app-shell/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { apiClient } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/organization")({
  beforeLoad: () => {
    const { status, user } = useAuthStore.getState();
    if (status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
    if (user?.role !== "owner" && user?.role !== "admin") {
      throw redirect({ to: "/unauthorized" });
    }
  },
  component: OrganizationPage,
});

const renameSchema = z.object({
  name: z.string().min(1, "Name is required").max(255, "Name is too long"),
});
type RenameForm = z.infer<typeof renameSchema>;

const aiProviderSchema = z.object({
  api_key: z.string(),
  model_name: z.string().min(1, "Model is required").max(200, "Model name is too long"),
});
type AIProviderForm = z.infer<typeof aiProviderSchema>;

function OrganizationPage() {
  const queryClient = useQueryClient();
  const organizationQuery = useQuery({
    queryKey: ["organization"],
    queryFn: () => apiClient.get<Organization>("/v1/organizations/current"),
  });

  const { register, handleSubmit, formState, reset } = useForm<RenameForm>({
    resolver: zodResolver(renameSchema),
    values: organizationQuery.data ? { name: organizationQuery.data.name } : undefined,
  });

  const renameMutation = useMutation({
    mutationFn: (values: RenameForm) =>
      apiClient.patch<Organization>("/v1/organizations/current", values),
    onSuccess: (updated) => {
      queryClient.setQueryData(["organization"], updated);
      reset({ name: updated.name });
    },
  });

  const aiProviderQuery = useQuery({
    queryKey: ["ai-provider-config"],
    queryFn: () => apiClient.get<AIProviderConfig>("/v1/organizations/current/ai-provider"),
  });

  const {
    register: registerAiProvider,
    handleSubmit: handleAiProviderSubmit,
    formState: aiProviderFormState,
    reset: resetAiProviderForm,
    getValues: getAiProviderValues,
  } = useForm<AIProviderForm>({
    resolver: zodResolver(aiProviderSchema),
    values: aiProviderQuery.data
      ? { api_key: "", model_name: aiProviderQuery.data.model_name ?? "" }
      : undefined,
  });

  const saveAiProviderMutation = useMutation({
    mutationFn: (values: AIProviderForm) =>
      apiClient.put<AIProviderConfig>("/v1/organizations/current/ai-provider", {
        api_key: values.api_key.trim() === "" ? null : values.api_key,
        model_name: values.model_name,
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["ai-provider-config"], updated);
      resetAiProviderForm({ api_key: "", model_name: updated.model_name ?? "" });
    },
  });

  const removeAiProviderMutation = useMutation({
    mutationFn: () => apiClient.delete<void>("/v1/organizations/current/ai-provider"),
    onSuccess: () => {
      const cleared: AIProviderConfig = { configured: false, model_name: null };
      queryClient.setQueryData(["ai-provider-config"], cleared);
      resetAiProviderForm({ api_key: "", model_name: "" });
    },
  });

  const testAiProviderMutation = useMutation({
    mutationFn: (values: AIProviderForm) =>
      apiClient.post<AIProviderConfigTestResponse>("/v1/organizations/current/ai-provider/test", {
        api_key: values.api_key.trim() === "" ? null : values.api_key,
        model_name: values.model_name,
      }),
  });

  return (
    <AppShell title="Organization">
      <div className="mx-auto flex max-w-md flex-col gap-4">
        <h1 className="text-xl font-semibold tracking-tight">Organization settings</h1>

        {organizationQuery.isLoading && <Skeleton className="h-48 rounded-2xl" />}

        {organizationQuery.data && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="size-4" /> Details
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form
                className="flex flex-col gap-3"
                onSubmit={handleSubmit((values) => renameMutation.mutate(values))}
              >
                <label className="text-sm font-medium" htmlFor="name">
                  Organization name
                </label>
                <Input id="name" {...register("name")} />
                {formState.errors.name && (
                  <p className="text-sm text-destructive">{formState.errors.name.message}</p>
                )}

                <Button type="submit" disabled={renameMutation.isPending} className="self-start">
                  {renameMutation.isPending ? "Saving…" : "Save"}
                </Button>

                {renameMutation.isSuccess && <p className="text-sm text-success">Saved.</p>}
                {renameMutation.isError && (
                  <p className="text-sm text-destructive">Couldn&rsquo;t save — please try again.</p>
                )}
              </form>
            </CardContent>
          </Card>
        )}

        {aiProviderQuery.isLoading && <Skeleton className="h-48 rounded-2xl" />}

        {aiProviderQuery.data && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <KeyRound className="size-4" /> AI Provider
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form
                className="flex flex-col gap-3"
                onSubmit={handleAiProviderSubmit((values) => saveAiProviderMutation.mutate(values))}
              >
                <p className="text-sm text-muted-foreground">
                  {aiProviderQuery.data.configured
                    ? `Configured via OpenRouter (model ${aiProviderQuery.data.model_name}).`
                    : "Using the instance's default provider."}
                </p>

                <label className="text-sm font-medium" htmlFor="model_name">
                  OpenRouter model
                </label>
                <Input
                  id="model_name"
                  placeholder="z-ai/glm-5.2:free"
                  {...registerAiProvider("model_name")}
                />
                {aiProviderFormState.errors.model_name && (
                  <p className="text-sm text-destructive">
                    {aiProviderFormState.errors.model_name.message}
                  </p>
                )}

                <label className="text-sm font-medium" htmlFor="api_key">
                  OpenRouter API key
                </label>
                <Input
                  id="api_key"
                  type="password"
                  autoComplete="off"
                  placeholder={
                    aiProviderQuery.data.configured
                      ? "Leave blank to keep the saved key"
                      : "sk-or-v1-..."
                  }
                  {...registerAiProvider("api_key")}
                />

                <div className="flex flex-wrap gap-2">
                  <Button
                    type="submit"
                    disabled={saveAiProviderMutation.isPending}
                    className="self-start"
                  >
                    {saveAiProviderMutation.isPending ? "Saving…" : "Save"}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    disabled={testAiProviderMutation.isPending}
                    onClick={() => testAiProviderMutation.mutate(getAiProviderValues())}
                  >
                    {testAiProviderMutation.isPending ? "Testing…" : "Test connection"}
                  </Button>
                  {aiProviderQuery.data.configured && (
                    <Button
                      type="button"
                      variant="destructive"
                      disabled={removeAiProviderMutation.isPending}
                      onClick={() => removeAiProviderMutation.mutate()}
                    >
                      {removeAiProviderMutation.isPending ? "Removing…" : "Remove"}
                    </Button>
                  )}
                </div>

                {saveAiProviderMutation.isSuccess && (
                  <p className="text-sm text-success">Saved.</p>
                )}
                {saveAiProviderMutation.isError && (
                  <p className="text-sm text-destructive">Couldn&rsquo;t save — please try again.</p>
                )}
                {removeAiProviderMutation.isError && (
                  <p className="text-sm text-destructive">
                    Couldn&rsquo;t remove — please try again.
                  </p>
                )}
                {testAiProviderMutation.data && (
                  <p
                    className={
                      testAiProviderMutation.data.success
                        ? "text-sm text-success"
                        : "text-sm text-destructive"
                    }
                  >
                    {testAiProviderMutation.data.success
                      ? "Connection succeeded."
                      : (testAiProviderMutation.data.error ?? "Connection failed.")}
                  </p>
                )}
                {testAiProviderMutation.isError && (
                  <p className="text-sm text-destructive">Couldn&rsquo;t reach the provider.</p>
                )}
              </form>
            </CardContent>
          </Card>
        )}
      </div>
    </AppShell>
  );
}
