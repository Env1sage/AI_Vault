import { createFileRoute, redirect } from "@tanstack/react-router";

import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/")({
  beforeLoad: () => {
    const { status } = useAuthStore.getState();
    throw redirect({ to: status === "authenticated" ? "/dashboard" : "/login" });
  },
});
