import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { Organization } from "@vault/types";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
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

  return (
    <main className="mx-auto flex max-w-md flex-col gap-4 p-8">
      <Link to="/dashboard" className="text-sm underline">
        ← Back to dashboard
      </Link>
      <h1 className="text-xl font-semibold">Organization settings</h1>

      {organizationQuery.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}

      {organizationQuery.data && (
        <form
          className="flex flex-col gap-3"
          onSubmit={handleSubmit((values) => renameMutation.mutate(values))}
        >
          <label className="text-sm font-medium" htmlFor="name">
            Organization name
          </label>
          <input
            id="name"
            className="rounded-md border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
            {...register("name")}
          />
          {formState.errors.name && (
            <p className="text-sm text-red-600">{formState.errors.name.message}</p>
          )}

          <Button type="submit" disabled={renameMutation.isPending} className="self-start">
            {renameMutation.isPending ? "Saving…" : "Save"}
          </Button>

          {renameMutation.isSuccess && <p className="text-sm text-green-600">Saved.</p>}
          {renameMutation.isError && (
            <p className="text-sm text-red-600">Couldn't save — please try again.</p>
          )}
        </form>
      )}
    </main>
  );
}
