import type { AuthSession, UserProfile } from "@vault/types";
import { create } from "zustand";

import { apiClient } from "@/lib/api-client";
import { registerRefreshHandler, setAccessToken } from "@/lib/session";

type AuthStatus = "idle" | "loading" | "authenticated" | "unauthenticated";

interface AuthState {
  status: AuthStatus;
  user: UserProfile | null;
  initialize: () => Promise<void>;
  loginWithGoogle: (idToken: string) => Promise<void>;
  logout: () => Promise<void>;
}

/** Shared by `initialize()` (cold-load session recovery) and the refresh
 * handler api-client registers for itself (silent recovery after a 401) —
 * one implementation, two callers. */
async function refreshSession(): Promise<string | null> {
  try {
    const session = await apiClient.post<AuthSession>("/v1/auth/refresh");
    setAccessToken(session.access_token);
    useAuthStore.setState({ status: "authenticated", user: session.user });
    return session.access_token;
  } catch {
    setAccessToken(null);
    useAuthStore.setState({ status: "unauthenticated", user: null });
    return null;
  }
}

export const useAuthStore = create<AuthState>((set) => ({
  status: "idle",
  user: null,

  initialize: async () => {
    set({ status: "loading" });
    await refreshSession();
  },

  loginWithGoogle: async (idToken: string) => {
    const session = await apiClient.post<AuthSession>("/v1/auth/login", { id_token: idToken });
    setAccessToken(session.access_token);
    set({ status: "authenticated", user: session.user });
  },

  logout: async () => {
    try {
      await apiClient.post<void>("/v1/auth/logout");
    } finally {
      setAccessToken(null);
      set({ status: "unauthenticated", user: null });
    }
  },
}));

registerRefreshHandler(refreshSession);
