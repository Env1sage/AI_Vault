import { describe, expect, it } from "vitest";

import { assistantToolLabel } from "./assistant-tool";

describe("assistantToolLabel", () => {
  it("maps a known tool name to a friendly label", () => {
    expect(assistantToolLabel("get_storage_overview")).toBe("Storage overview");
    expect(assistantToolLabel("get_duplicate_summary")).toBe("Duplicate summary");
    expect(assistantToolLabel("get_inactive_files")).toBe("Inactive files");
  });

  it("falls back to the raw tool name when unrecognized", () => {
    expect(assistantToolLabel("some_future_tool")).toBe("some_future_tool");
  });
});
