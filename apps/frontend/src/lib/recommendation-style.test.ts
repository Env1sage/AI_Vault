import { describe, expect, it } from "vitest";

import {
  categoryBadgeVariant,
  categoryColor,
  categoryLabel,
  riskBadgeVariant,
  riskColor,
} from "./recommendation-style";

describe("categoryLabel", () => {
  it("labels each known category", () => {
    expect(categoryLabel("storage_optimization")).toBe("Storage");
    expect(categoryLabel("knowledge_optimization")).toBe("Knowledge");
    expect(categoryLabel("security")).toBe("Security");
    expect(categoryLabel("collaboration")).toBe("Collaboration");
    expect(categoryLabel("productivity")).toBe("Productivity");
  });
});

describe("categoryBadgeVariant", () => {
  it("gives security the destructive badge variant", () => {
    expect(categoryBadgeVariant("security")).toBe("destructive");
  });

  it("gives distinct variants to different categories", () => {
    expect(categoryBadgeVariant("security")).not.toBe(categoryBadgeVariant("storage_optimization"));
  });
});

describe("categoryColor", () => {
  it("gives security a destructive-toned color", () => {
    expect(categoryColor("security")).toContain("destructive");
  });

  it("gives distinct colors to different categories", () => {
    expect(categoryColor("security")).not.toBe(categoryColor("storage_optimization"));
  });
});

describe("riskBadgeVariant", () => {
  it("highlights high risk as destructive", () => {
    expect(riskBadgeVariant("high")).toBe("destructive");
  });

  it("highlights medium risk as warning", () => {
    expect(riskBadgeVariant("medium")).toBe("warning");
  });

  it("uses the default variant for low risk", () => {
    expect(riskBadgeVariant("low")).toBe("default");
  });
});

describe("riskColor", () => {
  it("highlights high risk in the destructive token color", () => {
    expect(riskColor("high")).toBe("text-destructive");
  });

  it("highlights medium risk in the warning token color", () => {
    expect(riskColor("medium")).toBe("text-warning");
  });

  it("uses a muted color for low risk", () => {
    expect(riskColor("low")).toBe("text-muted-foreground");
  });
});
