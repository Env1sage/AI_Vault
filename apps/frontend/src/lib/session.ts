/** Holds the in-memory access token and the refresh callback the auth store
 * registers at startup. A neutral leaf module so api-client.ts (attaches the
 * token, retries on 401) and the auth store (owns the token's lifecycle)
 * don't import each other. The access token deliberately lives only here —
 * never in localStorage — the refresh token is an httpOnly cookie the
 * browser manages and this module never sees. */

type RefreshHandler = () => Promise<string | null>;

let accessToken: string | null = null;
let refreshHandler: RefreshHandler | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function registerRefreshHandler(handler: RefreshHandler): void {
  refreshHandler = handler;
}

/** Returns the new access token on success, or null if refresh failed (no
 * active session). Callers must treat null as "the user is logged out." */
export async function tryRefreshAccessToken(): Promise<string | null> {
  if (!refreshHandler) return null;
  return refreshHandler();
}
