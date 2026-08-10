import { describe, expect, it } from "vitest";

import { isActiveScanStatus, scanStatusColor } from "./scan-status";

describe("scanStatusColor", () => {
  it("highlights a completed scan in green", () => {
    expect(scanStatusColor("completed")).toBe("text-green-600");
  });

  it("highlights a failed scan in red", () => {
    expect(scanStatusColor("failed")).toBe("text-red-600");
  });

  it("highlights a running scan in blue", () => {
    expect(scanStatusColor("running")).toBe("text-blue-600");
  });

  it("uses a neutral color for pending and cancelled scans", () => {
    expect(scanStatusColor("pending")).toBe("text-neutral-500");
    expect(scanStatusColor("cancelled")).toBe("text-neutral-500");
  });
});

describe("isActiveScanStatus", () => {
  it("treats pending and running as active", () => {
    expect(isActiveScanStatus("pending")).toBe(true);
    expect(isActiveScanStatus("running")).toBe(true);
  });

  it("treats completed, failed, and cancelled as inactive", () => {
    expect(isActiveScanStatus("completed")).toBe(false);
    expect(isActiveScanStatus("failed")).toBe(false);
    expect(isActiveScanStatus("cancelled")).toBe(false);
  });
});
