import type { AuthSession, UserProfile } from "@vault/types";
import { afterEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/lib/api-client";
import { getAccessToken } from "@/lib/session";

import { useAuthStore } from "./auth-store";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

const mockedPost = vi.mocked(apiClient.post);

function fakeUser(overrides: Partial<UserProfile> = {}): UserProfile {
  return {
    id: "user-1",
    email: "founder@example.com",
    name: "Ada Founder",
    avatar_url: null,
    role: "owner",
    organization_id: "org-1",
    created_at: "2026-01-01T00:00:00Z",
    last_login_at: null,
    ...overrides,
  };
}

function fakeSession(overrides: Partial<AuthSession> = {}): AuthSession {
  return {
    access_token: "access-token-123",
    token_type: "bearer",
    expires_in: 900,
    user: fakeUser(),
    ...overrides,
  };
}

describe("useAuthStore", () => {
  afterEach(() => {
    mockedPost.mockReset();
    useAuthStore.setState({ status: "idle", user: null });
  });

  it("initialize() marks the store authenticated when the refresh cookie is valid", async () => {
    mockedPost.mockResolvedValueOnce(fakeSession());

    await useAuthStore.getState().initialize();

    expect(useAuthStore.getState().status).toBe("authenticated");
    expect(useAuthStore.getState().user?.email).toBe("founder@example.com");
    expect(getAccessToken()).toBe("access-token-123");
  });

  it("initialize() marks the store unauthenticated when there's no valid session", async () => {
    mockedPost.mockRejectedValueOnce(new Error("401"));

    await useAuthStore.getState().initialize();

    expect(useAuthStore.getState().status).toBe("unauthenticated");
    expect(useAuthStore.getState().user).toBeNull();
    expect(getAccessToken()).toBeNull();
  });

  it("loginWithGoogle() stores the returned session on success", async () => {
    mockedPost.mockResolvedValueOnce(fakeSession({ access_token: "new-token" }));

    await useAuthStore.getState().loginWithGoogle("some-id-token");

    expect(mockedPost).toHaveBeenCalledWith("/v1/auth/login", { id_token: "some-id-token" });
    expect(useAuthStore.getState().status).toBe("authenticated");
    expect(getAccessToken()).toBe("new-token");
  });

  it("loginWithGoogle() propagates the error and leaves the store unauthenticated on failure", async () => {
    mockedPost.mockRejectedValueOnce(new Error("bad credential"));

    await expect(useAuthStore.getState().loginWithGoogle("bad-token")).rejects.toThrow();

    expect(useAuthStore.getState().status).not.toBe("authenticated");
  });

  it("logout() clears the store even if the API call fails", async () => {
    useAuthStore.setState({ status: "authenticated", user: fakeUser() });
    mockedPost.mockRejectedValueOnce(new Error("network error"));

    await expect(useAuthStore.getState().logout()).rejects.toThrow();

    expect(useAuthStore.getState().status).toBe("unauthenticated");
    expect(useAuthStore.getState().user).toBeNull();
    expect(getAccessToken()).toBeNull();
  });

  it("logout() clears the store on success", async () => {
    useAuthStore.setState({ status: "authenticated", user: fakeUser() });
    mockedPost.mockResolvedValueOnce(undefined);

    await useAuthStore.getState().logout();

    expect(useAuthStore.getState().status).toBe("unauthenticated");
    expect(useAuthStore.getState().user).toBeNull();
  });
});
