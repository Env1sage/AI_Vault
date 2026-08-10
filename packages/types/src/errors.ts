/** Mirrors the error envelope apps/backend's exception handlers return
 * (app/core/error_handlers.py) — kept here manually in Phase 1; see ADR-012
 * for the plan to generate this from the backend's OpenAPI schema instead. */
export interface ApiErrorResponse {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  };
}
