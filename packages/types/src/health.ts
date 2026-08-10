/** Mirrors apps/backend's GET /health/live response. */
export interface LivenessResponse {
  status: "ok";
}

/** Mirrors apps/backend's GET /health/ready response. */
export interface ReadinessResponse {
  status: "ok" | "degraded";
  checks: {
    database: boolean;
    redis: boolean;
  };
}

/** Mirrors apps/backend's GET /v1/version response. */
export interface VersionResponse {
  api_version: string;
  service_version: string;
}
