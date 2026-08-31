/** Mirrors apps/backend's per-organization AI provider endpoints
 * (app/presentation/api/v1/schemas.py's AIProviderConfig* schemas). */
export interface AIProviderConfig {
  configured: boolean;
  model_name: string | null;
}

export interface AIProviderConfigUpdateRequest {
  api_key: string | null;
  model_name: string;
}

export interface AIProviderConfigTestRequest {
  api_key: string | null;
  model_name: string;
}

export interface AIProviderConfigTestResponse {
  success: boolean;
  error: string | null;
}
