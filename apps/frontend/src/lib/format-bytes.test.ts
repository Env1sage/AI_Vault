import { describe, expect, it } from "vitest";

import { formatBytes } from "./format-bytes";

describe("formatBytes", () => {
  it("formats zero bytes", () => {
    expect(formatBytes(0)).toBe("0 B");
  });

  it("formats a small byte count with no decimal", () => {
    expect(formatBytes(512)).toBe("512 B");
  });

  it("formats kilobytes with one decimal", () => {
    expect(formatBytes(2048)).toBe("2.0 KB");
  });

  it("formats gigabytes", () => {
    expect(formatBytes(5 * 1024 * 1024 * 1024)).toBe("5.0 GB");
  });
});
