import { Outlet, createFileRoute, redirect } from "@tanstack/react-router";

import { useAuthStore } from "@/stores/auth-store";

/** A pure layout route — see chat.tsx's docstring for why this file exists
 * and must not render its own page content. */
export const Route = createFileRoute("/execution-jobs")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: Outlet,
});
