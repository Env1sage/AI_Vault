import { describe, expect, it } from "vitest";

import {
  actionTypeLabel,
  approvalStatusColor,
  isActiveJobStatus,
  jobStatusColor,
  planStatusColor,
  riskLevelColor,
} from "./execution-style";

describe("planStatusColor", () => {
  it("highlights completed and approved plans in green", () => {
    expect(planStatusColor("completed")).toBe("text-green-600");
    expect(planStatusColor("approved")).toBe("text-green-600");
  });

  it("highlights failed and rejected plans in red", () => {
    expect(planStatusColor("failed")).toBe("text-red-600");
    expect(planStatusColor("rejected")).toBe("text-red-600");
  });

  it("highlights partially completed and changes-requested plans in amber", () => {
    expect(planStatusColor("partially_completed")).toBe("text-amber-600");
    expect(planStatusColor("changes_requested")).toBe("text-amber-600");
  });

  it("highlights an executing plan in blue", () => {
    expect(planStatusColor("executing")).toBe("text-blue-600");
  });

  it("uses a neutral color for expired and rolled-back plans", () => {
    expect(planStatusColor("expired")).toBe("text-neutral-500");
    expect(planStatusColor("rolled_back")).toBe("text-neutral-500");
  });
});

describe("jobStatusColor", () => {
  it("highlights a completed job in green", () => {
    expect(jobStatusColor("completed")).toBe("text-green-600");
  });

  it("highlights a failed job in red", () => {
    expect(jobStatusColor("failed")).toBe("text-red-600");
  });

  it("highlights a running job in blue", () => {
    expect(jobStatusColor("running")).toBe("text-blue-600");
  });

  it("highlights partially-completed and paused jobs in amber", () => {
    expect(jobStatusColor("partially_completed")).toBe("text-amber-600");
    expect(jobStatusColor("paused")).toBe("text-amber-600");
  });

  it("uses a neutral color for a cancelled job", () => {
    expect(jobStatusColor("cancelled")).toBe("text-neutral-500");
  });
});

describe("isActiveJobStatus", () => {
  it("treats pending, running, and paused as active", () => {
    expect(isActiveJobStatus("pending")).toBe(true);
    expect(isActiveJobStatus("running")).toBe(true);
    expect(isActiveJobStatus("paused")).toBe(true);
  });

  it("treats completed, failed, partially_completed, and cancelled as inactive", () => {
    expect(isActiveJobStatus("completed")).toBe(false);
    expect(isActiveJobStatus("failed")).toBe(false);
    expect(isActiveJobStatus("partially_completed")).toBe(false);
    expect(isActiveJobStatus("cancelled")).toBe(false);
  });
});

describe("approvalStatusColor", () => {
  it("highlights an approved request in green and a rejected one in red", () => {
    expect(approvalStatusColor("approved")).toBe("text-green-600");
    expect(approvalStatusColor("rejected")).toBe("text-red-600");
  });

  it("highlights a pending request in blue", () => {
    expect(approvalStatusColor("pending")).toBe("text-blue-600");
  });

  it("highlights changes_requested in amber and expired as neutral", () => {
    expect(approvalStatusColor("changes_requested")).toBe("text-amber-600");
    expect(approvalStatusColor("expired")).toBe("text-neutral-500");
  });
});

describe("riskLevelColor", () => {
  it("highlights high risk in red, medium in amber, low as neutral", () => {
    expect(riskLevelColor("high")).toBe("text-red-600");
    expect(riskLevelColor("medium")).toBe("text-amber-600");
    expect(riskLevelColor("low")).toBe("text-neutral-500");
  });
});

describe("actionTypeLabel", () => {
  it("gives a human label to every known action type", () => {
    expect(actionTypeLabel("move_file")).toBe("Move file");
    expect(actionTypeLabel("move_folder")).toBe("Move folder");
    expect(actionTypeLabel("rename")).toBe("Rename");
    expect(actionTypeLabel("archive")).toContain("Archive");
    expect(actionTypeLabel("remove_duplicate")).toContain("Remove duplicate");
    expect(actionTypeLabel("update_metadata")).toBe("Update metadata");
    expect(actionTypeLabel("permanent_delete")).toContain("Permanently delete");
  });

  it("falls back to the raw value for an unknown action type", () => {
    expect(actionTypeLabel("something_new")).toBe("something_new");
  });
});
