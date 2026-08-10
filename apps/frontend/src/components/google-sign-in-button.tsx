import { useEffect, useRef, useState } from "react";

import { loadGoogleIdentityScript } from "@/lib/google-identity";

interface GoogleSignInButtonProps {
  onCredential: (idToken: string) => void;
}

export function GoogleSignInButton({ onCredential }: GoogleSignInButtonProps) {
  const buttonRef = useRef<HTMLDivElement>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
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
          shape: "rectangular",
        });
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
      <p className="text-sm text-red-600">
        Google sign-in is not configured (missing VITE_GOOGLE_CLIENT_ID).
      </p>
    );
  }

  if (loadError) {
    return <p className="text-sm text-red-600">{loadError}</p>;
  }

  return <div ref={buttonRef} />;
}
