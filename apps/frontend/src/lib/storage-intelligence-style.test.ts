import { describe, expect, it } from "vitest";

import { analysisStatusBadgeVariant, analysisStatusLabel, confidenceLabel } from "./storage-intelligence-style";

describe("analysisStatusBadgeVariant", () => {
  it("marks a completed analysis as success", () => {
    expect(analysisStatusBadgeVariant("completed")).toBe("success");
  });

  it("marks a failed analysis as destructive", () => {
    expect(analysisStatusBadgeVariant("failed")).toBe("destructive");
  });

  it("marks a running analysis as primary", () => {
    expect(analysisStatusBadgeVariant("running")).toBe("primary");
  });

  it("uses the default variant for pending", () => {
    expect(analysisStatusBadgeVariant("pending")).toBe("default");
  });
});

describe("analysisStatusLabel", () => {
  it("labels completed as Complete", () => {
    expect(analysisStatusLabel("completed")).toBe("Complete");
  });

  it("labels running as an in-progress message", () => {
    expect(analysisStatusLabel("running")).toBe("Analyzing…");
  });
});

describe("confidenceLabel", () => {
  it("labels 0.86 as high confidence", () => {
    expect(confidenceLabel(0.86)).toBe("High confidence");
  });

  it("labels 0.65 as medium confidence", () => {
    expect(confidenceLabel(0.65)).toBe("Medium confidence");
  });

  it("labels 0.4 as low confidence", () => {
    expect(confidenceLabel(0.4)).toBe("Low confidence");
  });

  it("treats exactly 0.8 as high confidence (inclusive boundary)", () => {
    expect(confidenceLabel(0.8)).toBe("High confidence");
  });

  it("treats exactly 0.5 as medium confidence (inclusive boundary)", () => {
    expect(confidenceLabel(0.5)).toBe("Medium confidence");
  });
});
