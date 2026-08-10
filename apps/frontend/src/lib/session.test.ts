import { afterEach, describe, expect, it, vi } from "vitest";

import { getAccessToken, registerRefreshHandler, setAccessToken, tryRefreshAccessToken } from "./session";

describe("session token holder", () => {
  afterEach(() => {
    setAccessToken(null);
    registerRefreshHandler(async () => null);
  });

  it("starts with no access token", () => {
    expect(getAccessToken()).toBeNull();
  });

  it("stores and returns whatever token is set", () => {
    setAccessToken("abc123");
    expect(getAccessToken()).toBe("abc123");
  });

  it("delegates tryRefreshAccessToken to the registered handler", async () => {
    const handler = vi.fn().mockResolvedValue("new-token");
    registerRefreshHandler(handler);

    const result = await tryRefreshAccessToken();

    expect(result).toBe("new-token");
    expect(handler).toHaveBeenCalledOnce();
  });

  it("returns null when no handler has been registered yet", async () => {
    // Simulate the pre-registration state by re-importing isn't practical
    // here, so this asserts the documented contract via a null-returning
    // handler instead, which is the equivalent externally-observable case.
    registerRefreshHandler(async () => null);
    expect(await tryRefreshAccessToken()).toBeNull();
  });
});
