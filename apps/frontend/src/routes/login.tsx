import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import { AlertCircle, FileText, Folder, Lock, Sparkles } from "lucide-react";
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
    <main className="grid min-h-screen md:grid-cols-2">
      {/* Brand panel — deep navy/midnight, hidden on mobile (redesign brief §22) */}
      <div className="relative hidden flex-col justify-between overflow-hidden bg-sidebar px-12 py-10 text-sidebar-foreground md:flex">
        <div
          className="pointer-events-none absolute inset-0 opacity-40"
          style={{
            backgroundImage:
              "radial-gradient(circle at 20% 20%, rgb(111 147 239 / 0.18), transparent 45%), radial-gradient(circle at 80% 70%, rgb(157 144 255 / 0.14), transparent 40%)",
          }}
          aria-hidden="true"
        />

        <div className="relative flex items-center gap-2">
          <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-sm font-bold text-primary-foreground">
            V
          </span>
          <span className="text-sm font-semibold">AI Project Vault</span>
        </div>

        <div className="relative flex max-w-md flex-col gap-6">
          <h1 className="text-3xl font-semibold leading-tight text-white">
            Your company&rsquo;s intelligent storage &amp; knowledge layer.
          </h1>
          <p className="text-sm leading-relaxed text-sidebar-muted-foreground">
            Vault scans, understands, and organizes what your organization already has in Google
            Workspace — then asks before it changes anything.
          </p>

          {/* Abstract "organized knowledge" motif — geometric, no fabricated product data */}
          <div className="mt-2 flex flex-col gap-2.5" aria-hidden="true">
            {[
              { icon: Folder, label: "Marketing / Campaigns", w: "w-40" },
              { icon: FileText, label: "Q3 Board Deck.pdf", w: "w-52" },
              { icon: Sparkles, label: "AI grouped 3 similar assets", w: "w-44", accent: true },
            ].map((row) => (
              <div
                key={row.label}
                className={`flex items-center gap-2.5 rounded-lg border px-3 py-2 text-xs ${row.w} ${
                  row.accent
                    ? "border-ai/30 bg-ai/10 text-ai"
                    : "border-sidebar-border bg-sidebar-accent/60 text-sidebar-foreground/80"
                }`}
              >
                <row.icon className="size-3.5 shrink-0" />
                <span className="truncate">{row.label}</span>
              </div>
            ))}
          </div>
        </div>

        <p className="relative flex items-center gap-1.5 text-xs text-sidebar-muted-foreground">
          <Lock className="size-3.5" /> Secure • Private • AI Powered
        </p>
      </div>

      {/* Login card panel */}
      <div className="flex flex-1 flex-col items-center justify-center px-6 py-16">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex flex-col items-center gap-2 text-center md:hidden">
            <span className="flex size-9 items-center justify-center rounded-lg bg-primary text-sm font-bold text-primary-foreground">
              V
            </span>
            <h1 className="text-lg font-semibold">AI Project Vault</h1>
          </div>

          <div className="rounded-2xl border border-border bg-card p-8 shadow-clay-lg">
            <h2 className="text-lg font-semibold">Welcome back</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Sign in with your Google account to continue.
            </p>

            <div className="mt-6">
              <GoogleSignInButton onCredential={handleCredential} />
            </div>

            {error ? (
              <p
                role="alert"
                className="mt-4 flex items-center gap-2 rounded-lg bg-destructive-muted px-3 py-2 text-sm text-destructive"
              >
                <AlertCircle className="size-4 shrink-0" />
                {error}
              </p>
            ) : null}
          </div>

          <p className="mt-6 flex items-center justify-center gap-1.5 text-xs text-muted-foreground md:hidden">
            <Lock className="size-3.5" /> Secure • Private • AI Powered
          </p>
        </div>
      </div>
    </main>
  );
}
