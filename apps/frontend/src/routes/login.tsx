import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import { useState } from "react";

import { GoogleSignInButton } from "@/components/google-sign-in-button";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/login")({
  beforeLoad: () => {
    if (useAuthStore.getState().status === "authenticated") {
      throw redirect({ to: "/dashboard" });
    }
  },
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const loginWithGoogle = useAuthStore((state) => state.loginWithGoogle);
  const [error, setError] = useState<string | null>(null);

  async function handleCredential(idToken: string) {
    setError(null);
    try {
      await loginWithGoogle(idToken);
      await navigate({ to: "/dashboard" });
    } catch {
      setError("Sign-in failed. Please try again.");
    }
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <div className="text-center">
        <h1 className="text-2xl font-semibold">AI Project Vault</h1>
        <p className="text-neutral-500">Sign in with your Google account to continue.</p>
      </div>
      <GoogleSignInButton onCredential={handleCredential} />
      {error && <p className="text-sm text-red-600">{error}</p>}
    </main>
  );
}
