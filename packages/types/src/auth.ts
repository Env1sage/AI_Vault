/** Mirrors apps/backend's GET /users/me and the `user` field of /auth/*
 * responses (app/presentation/api/v1/schemas.py's UserProfileResponse). */
export interface UserProfile {
  id: string;
  email: string;
  name: string;
  avatar_url: string | null;
  role: "owner" | "admin" | "member";
  organization_id: string;
  created_at: string;
  last_login_at: string | null;
}

/** Mirrors apps/backend's GET/PATCH /organizations/current
 * (OrganizationResponse). */
export interface Organization {
  id: string;
  name: string;
  slug: string;
  created_at: string;
  updated_at: string;
}

export interface OrganizationUpdateRequest {
  name: string;
}

/** Mirrors apps/backend's POST /auth/login and /auth/refresh
 * (SessionResponse) — the refresh token itself is never in this body, it's
 * an httpOnly cookie the browser manages. */
export interface AuthSession {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: UserProfile;
}

export interface GoogleLoginRequest {
  id_token: string;
}
