import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiClient } from "./api-client";
import { getAccessToken, registerRefreshHandler, setAccessToken } from "./session";

describe("apiClient.get", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns parsed JSON on a successful response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: "ok" }),
      }),
    );

    const result = await apiClient.get<{ status: string }>("/health/live");

    expect(result).toEqual({ status: "ok" });
  });

  it("throws ApiError with the code/message from the backend's error envelope", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        statusText: "Not Found",
        json: async () => ({
          error: { code: "not_found", message: "widget missing", details: {} },
        }),
      }),
    );

    await expect(apiClient.get("/widgets/1")).rejects.toMatchObject({
      message: "widget missing",
      status: 404,
      code: "not_found",
    });
  });

  it("falls back to statusText when the error body isn't JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 502,
        statusText: "Bad Gateway",
        json: async () => {
          throw new Error("not json");
        },
      }),
    );

    await expect(apiClient.get("/x")).rejects.toMatchObject({
      status: 502,
      code: "unknown_error",
      message: "Bad Gateway",
    });
  });
});

describe("ApiError", () => {
  it("carries status and code alongside the message", () => {
    const error = new ApiError("boom", 500, "internal_error");

    expect(error.status).toBe(500);
    expect(error.code).toBe("internal_error");
    expect(error.name).toBe("ApiError");
  });
});

describe("apiClient request behavior around auth", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    setAccessToken(null);
    registerRefreshHandler(async () => null);
  });

  it("sends credentials so the refresh cookie reaches the backend", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    await apiClient.get("/v1/version");

    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({ credentials: "include" });
  });

  it("attaches the Authorization header when an access token is set", async () => {
    setAccessToken("my-access-token");
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    await apiClient.get("/v1/users/me");

    const headers = fetchMock.mock.calls[0]?.[1]?.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer my-access-token");
  });

  it("omits the Authorization header when there is no access token", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    await apiClient.get("/v1/version");

    const headers = fetchMock.mock.calls[0]?.[1]?.headers as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
  });

  it("on a 401, refreshes once and retries the original request", async () => {
    const unauthorized = { ok: false, status: 401, statusText: "Unauthorized", json: async () => ({}) };
    const success = { ok: true, json: async () => ({ data: "secret" }) };
    const fetchMock = vi.fn().mockResolvedValueOnce(unauthorized).mockResolvedValueOnce(success);
    vi.stubGlobal("fetch", fetchMock);
    registerRefreshHandler(async () => "refreshed-token");

    const result = await apiClient.get<{ data: string }>("/v1/users/me");

    expect(result).toEqual({ data: "secret" });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    const retryHeaders = fetchMock.mock.calls[1]?.[1]?.headers as Record<string, string>;
    expect(retryHeaders.Authorization).toBe("Bearer refreshed-token");
  });

  it("propagates 401 as ApiError when refresh also fails, without retrying forever", async () => {
    const unauthorized = { ok: false, status: 401, statusText: "Unauthorized", json: async () => ({}) };
    const fetchMock = vi.fn().mockResolvedValue(unauthorized);
    vi.stubGlobal("fetch", fetchMock);
    registerRefreshHandler(async () => null);

    await expect(apiClient.get("/v1/users/me")).rejects.toMatchObject({ status: 401 });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(getAccessToken()).toBeNull();
  });

  it("does not attempt a refresh loop for the auth endpoints themselves", async () => {
    const unauthorized = { ok: false, status: 401, statusText: "Unauthorized", json: async () => ({}) };
    const fetchMock = vi.fn().mockResolvedValue(unauthorized);
    vi.stubGlobal("fetch", fetchMock);
    const refreshHandler = vi.fn().mockResolvedValue("should-not-be-used");
    registerRefreshHandler(refreshHandler);

    await expect(apiClient.post("/v1/auth/refresh")).rejects.toMatchObject({ status: 401 });

    expect(refreshHandler).not.toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("returns undefined for a 204 No Content response (logout)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 204 }));

    const result = await apiClient.post("/v1/auth/logout");

    expect(result).toBeUndefined();
  });
});
