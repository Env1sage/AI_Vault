import { useQuery } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";
import type { UserProfile } from "@vault/types";

import { apiClient } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/profile")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: ProfilePage,
});

function ProfilePage() {
  const profileQuery = useQuery({
    queryKey: ["me"],
    queryFn: () => apiClient.get<UserProfile>("/v1/users/me"),
  });

  return (
    <main className="mx-auto flex max-w-md flex-col gap-4 p-8">
      <Link to="/dashboard" className="text-sm underline">
        ← Back to dashboard
      </Link>
      <h1 className="text-xl font-semibold">Profile</h1>

      {profileQuery.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
      {profileQuery.isError && <p className="text-sm text-red-600">Couldn't load your profile.</p>}

      {profileQuery.data && (
        <dl className="grid grid-cols-2 gap-y-2 text-sm">
          <dt className="text-neutral-500">Name</dt>
          <dd>{profileQuery.data.name}</dd>

          <dt className="text-neutral-500">Email</dt>
          <dd>{profileQuery.data.email}</dd>

          <dt className="text-neutral-500">Role</dt>
          <dd className="capitalize">{profileQuery.data.role}</dd>

          <dt className="text-neutral-500">Last login</dt>
          <dd>
            {profileQuery.data.last_login_at
              ? new Date(profileQuery.data.last_login_at).toLocaleString()
              : "—"}
          </dd>
        </dl>
      )}
    </main>
  );
}
