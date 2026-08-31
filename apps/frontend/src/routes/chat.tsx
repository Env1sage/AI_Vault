import { Outlet, createFileRoute, redirect } from "@tanstack/react-router";

import { useAuthStore } from "@/stores/auth-store";

/** A pure layout route — TanStack Router's flat file convention nests
 * `chat.$conversationId.tsx` and `chat.index.tsx` under this file because
 * they share the `chat.` prefix, so this component's only job is to render
 * the matched child via `<Outlet />`. Without it, neither child route's
 * content is ever displayed even though the URL and route match are
 * otherwise correct. */
export const Route = createFileRoute("/chat")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: Outlet,
});
