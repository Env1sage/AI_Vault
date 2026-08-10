import { describe, expect, it } from "vitest";

import { categoryColor, categoryLabel, riskColor } from "./recommendation-style";

describe("categoryLabel", () => {
  it("labels each known category", () => {
    expect(categoryLabel("storage_optimization")).toBe("Storage");
    expect(categoryLabel("knowledge_optimization")).toBe("Knowledge");
    expect(categoryLabel("security")).toBe("Security");
    expect(categoryLabel("collaboration")).toBe("Collaboration");
    expect(categoryLabel("productivity")).toBe("Productivity");
  });
});

describe("categoryColor", () => {
  it("gives security a red-toned color", () => {
    expect(categoryColor("security")).toContain("red");
  });

  it("gives distinct colors to different categories", () => {
    expect(categoryColor("security")).not.toBe(categoryColor("storage_optimization"));
  });
});

describe("riskColor", () => {
  it("highlights high risk in red", () => {
    expect(riskColor("high")).toBe("text-red-600");
  });

  it("highlights medium risk in amber", () => {
    expect(riskColor("medium")).toBe("text-amber-600");
  });

  it("uses a neutral color for low risk", () => {
    expect(riskColor("low")).toBe("text-neutral-500");
  });
});
