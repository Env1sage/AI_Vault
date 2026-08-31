import { AlertTriangle } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { loadGoogleIdentityScript } from "@/lib/google-identity";
import { Skeleton } from "@/components/ui/skeleton";

interface GoogleSignInButtonProps {
  onCredential: (idToken: string) => void;
}

export function GoogleSignInButton({ onCredential }: GoogleSignInButtonProps) {
  const buttonRef = useRef<HTMLDivElement>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [rendered, setRendered] = useState(false);
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;

  useEffect(() => {
    if (!clientId || !buttonRef.current) return;

    let cancelled = false;

    loadGoogleIdentityScript()
      .then(() => {
        if (cancelled || !buttonRef.current || !window.google) return;

        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: (response) => onCredential(response.credential),
        });
        window.google.accounts.id.renderButton(buttonRef.current, {
          type: "standard",
          theme: "outline",
          size: "large",
          text: "signin_with",
          shape: "pill",
        });
        setRendered(true);
      })
      .catch(() => {
        if (!cancelled) setLoadError("Couldn't load Google sign-in. Please refresh the page.");
      });

    return () => {
      cancelled = true;
    };
  }, [clientId, onCredential]);

  if (!clientId) {
    return (
      <p className="flex items-center gap-2 rounded-lg bg-destructive-muted px-3 py-2 text-sm text-destructive">
        <AlertTriangle className="size-4 shrink-0" />
        Google sign-in is not configured (missing VITE_GOOGLE_CLIENT_ID).
      </p>
    );
  }

  if (loadError) {
    return (
      <p className="flex items-center gap-2 rounded-lg bg-destructive-muted px-3 py-2 text-sm text-destructive">
        <AlertTriangle className="size-4 shrink-0" />
        {loadError}
      </p>
    );
  }

  return (
    <div className="flex min-h-10 items-center justify-center">
      {!rendered ? <Skeleton className="h-10 w-full rounded-full" /> : null}
      <div ref={buttonRef} className={rendered ? "" : "sr-only"} />
    </div>
  );
}
