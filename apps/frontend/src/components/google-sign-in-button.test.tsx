import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { GoogleSignInButton } from "./google-sign-in-button";

describe("GoogleSignInButton", () => {
  it("shows a configuration error when VITE_GOOGLE_CLIENT_ID is unset", () => {
    // Test env never sets this, mirroring a misconfigured deployment.
    render(<GoogleSignInButton onCredential={vi.fn()} />);

    expect(screen.getByText(/not configured/i)).toBeInTheDocument();
  });
});
