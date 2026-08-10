import { describe, expect, it } from "vitest";

import { formatRelativeTime } from "./format-relative-time";

const NOW = new Date("2026-07-29T12:00:00Z");

describe("formatRelativeTime", () => {
  it("says 'just now' for anything under a minute", () => {
    expect(formatRelativeTime("2026-07-29T11:59:30Z", NOW)).toBe("just now");
  });

  it("formats minutes, singular and plural", () => {
    expect(formatRelativeTime("2026-07-29T11:59:00Z", NOW)).toBe("1 minute ago");
    expect(formatRelativeTime("2026-07-29T11:55:00Z", NOW)).toBe("5 minutes ago");
  });

  it("formats hours, singular and plural", () => {
    expect(formatRelativeTime("2026-07-29T11:00:00Z", NOW)).toBe("1 hour ago");
    expect(formatRelativeTime("2026-07-29T09:00:00Z", NOW)).toBe("3 hours ago");
  });

  it("formats days, singular and plural", () => {
    expect(formatRelativeTime("2026-07-28T12:00:00Z", NOW)).toBe("1 day ago");
    expect(formatRelativeTime("2026-07-24T12:00:00Z", NOW)).toBe("5 days ago");
  });

  it("falls back to a locale date beyond 30 days", () => {
    const iso = "2026-05-01T12:00:00Z";
    expect(formatRelativeTime(iso, NOW)).toBe(new Date(iso).toLocaleDateString());
  });
});
