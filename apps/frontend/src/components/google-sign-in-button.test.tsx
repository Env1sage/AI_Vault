import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { GoogleSignInButton } from "./google-sign-in-button";

describe("GoogleSignInButton", () => {
  beforeEach(() => {
    // Explicitly stub rather than relying on the var being absent — a
    // developer's local .env (gitignored, not present in CI) can set a real
    // VITE_GOOGLE_CLIENT_ID that would otherwise mask this scenario.
    vi.stubEnv("VITE_GOOGLE_CLIENT_ID", "");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("shows a configuration error when VITE_GOOGLE_CLIENT_ID is unset", () => {
    render(<GoogleSignInButton onCredential={vi.fn()} />);

    expect(screen.getByText(/not configured/i)).toBeInTheDocument();
  });
});
