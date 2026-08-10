import { Link, createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { z } from "zod";

import { LoadingScreen } from "@/components/loading-screen";
import { ApiError, apiClient } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";

const searchSchema = z.object({
  code: z.string().optional(),
  state: z.string().optional(),
  error: z.string().optional(),
});

export const Route = createFileRoute("/connectors/google/callback")({
  validateSearch: searchSchema,
  beforeLoad: () => {
    // A full-page navigation to Google and back drops the in-memory access
    // token — main.tsx's bootstrap() already re-ran initialize() against the
    // refresh cookie before this route's beforeLoad runs, so this check
    // reflects the *recovered* session, not a stale pre-redirect one.
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: GoogleConnectorCallbackPage,
});

function GoogleConnectorCallbackPage() {
  const { code, state, error: oauthError } = Route.useSearch();
  const navigate = useNavigate();
  const [exchangeError, setExchangeError] = useState<string | null>(null);

  const validationError = oauthError
    ? "Google sign-in was cancelled or access was denied."
    : !code || !state
      ? "Missing authorization code — please try connecting again."
      : null;
  const errorMessage = validationError ?? exchangeError;

  useEffect(() => {
    if (validationError || !code || !state) {
      return;
    }

    apiClient
      .post("/v1/connectors/google/callback", { code, state })
      .then(() => navigate({ to: "/storage-connections" }))
      .catch((error: unknown) => {
        setExchangeError(error instanceof ApiError ? error.message : "Something went wrong.");
      });
  }, [code, state, validationError, navigate]);

  if (!errorMessage) {
    return <LoadingScreen />;
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-3 p-8 text-center">
      <h1 className="text-lg font-semibold">Couldn't connect Google Workspace</h1>
      <p className="text-sm text-red-600">{errorMessage}</p>
      <Link to="/storage-connections" className="text-sm underline">
        Back to Storage Connections
      </Link>
    </main>
  );
}
