import { describe, expect, it } from "vitest";

import { enrichmentStatusColor, isActiveEnrichmentStatus } from "./enrichment-status";

describe("enrichmentStatusColor", () => {
  it("highlights a completed enrichment job in green", () => {
    expect(enrichmentStatusColor("completed")).toBe("text-green-600");
  });

  it("highlights a failed enrichment job in red", () => {
    expect(enrichmentStatusColor("failed")).toBe("text-red-600");
  });

  it("highlights a running enrichment job in blue", () => {
    expect(enrichmentStatusColor("running")).toBe("text-blue-600");
  });

  it("uses a neutral color for pending and cancelled jobs", () => {
    expect(enrichmentStatusColor("pending")).toBe("text-neutral-500");
    expect(enrichmentStatusColor("cancelled")).toBe("text-neutral-500");
  });
});

describe("isActiveEnrichmentStatus", () => {
  it("treats pending and running as active", () => {
    expect(isActiveEnrichmentStatus("pending")).toBe(true);
    expect(isActiveEnrichmentStatus("running")).toBe(true);
  });

  it("treats completed, failed, and cancelled as inactive", () => {
    expect(isActiveEnrichmentStatus("completed")).toBe(false);
    expect(isActiveEnrichmentStatus("failed")).toBe(false);
    expect(isActiveEnrichmentStatus("cancelled")).toBe(false);
  });
});
