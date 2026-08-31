/** Mirrors apps/backend's connector endpoints
 * (app/presentation/api/v1/schemas.py's ConnectorResponse) — never includes
 * token values, those never leave the backend. */
export interface Connector {
  id: string;
  provider: "google_workspace";
  status: "pending" | "connected" | "error" | "disconnected" | "reauth_required";
  account_email: string | null;
  workspace_domain: string | null;
  last_verified_at: string | null;
  last_failed_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface InitiateConnectResponse {
  authorize_url: string;
}

export interface CompleteConnectRequest {
  code: string;
  state: string;
}
