import { describe, expect, it } from "vitest";

import { isActiveIntelligenceStatus, intelligenceStatusColor } from "./intelligence-status";

describe("intelligenceStatusColor", () => {
  it("highlights a completed intelligence job in green", () => {
    expect(intelligenceStatusColor("completed")).toBe("text-green-600");
  });

  it("highlights a failed intelligence job in red", () => {
    expect(intelligenceStatusColor("failed")).toBe("text-red-600");
  });

  it("highlights a running intelligence job in blue", () => {
    expect(intelligenceStatusColor("running")).toBe("text-blue-600");
  });

  it("uses a neutral color for pending and cancelled jobs", () => {
    expect(intelligenceStatusColor("pending")).toBe("text-neutral-500");
    expect(intelligenceStatusColor("cancelled")).toBe("text-neutral-500");
  });
});

describe("isActiveIntelligenceStatus", () => {
  it("treats pending and running as active", () => {
    expect(isActiveIntelligenceStatus("pending")).toBe(true);
    expect(isActiveIntelligenceStatus("running")).toBe(true);
  });

  it("treats completed, failed, and cancelled as inactive", () => {
    expect(isActiveIntelligenceStatus("completed")).toBe(false);
    expect(isActiveIntelligenceStatus("failed")).toBe(false);
    expect(isActiveIntelligenceStatus("cancelled")).toBe(false);
  });
});
