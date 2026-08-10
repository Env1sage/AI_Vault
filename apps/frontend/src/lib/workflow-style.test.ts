import { describe, expect, it } from "vitest";

import {
  executionStatusColor,
  isActiveExecutionStatus,
  nodeExecutionStatusColor,
  nodeTypeLabel,
  notificationStatusColor,
  policyStatusColor,
  workflowStatusColor,
} from "./workflow-style";

describe("workflowStatusColor", () => {
  it("highlights active in green, paused in amber, disabled as neutral", () => {
    expect(workflowStatusColor("active")).toBe("text-green-600");
    expect(workflowStatusColor("paused")).toBe("text-amber-600");
    expect(workflowStatusColor("disabled")).toBe("text-neutral-500");
  });
});

describe("executionStatusColor", () => {
  it("highlights completed in green and failed in red", () => {
    expect(executionStatusColor("completed")).toBe("text-green-600");
    expect(executionStatusColor("failed")).toBe("text-red-600");
  });

  it("highlights running in blue and paused in amber", () => {
    expect(executionStatusColor("running")).toBe("text-blue-600");
    expect(executionStatusColor("paused")).toBe("text-amber-600");
  });

  it("uses a neutral color for a cancelled execution", () => {
    expect(executionStatusColor("cancelled")).toBe("text-neutral-500");
  });
});

describe("isActiveExecutionStatus", () => {
  it("treats pending, running, and paused as active", () => {
    expect(isActiveExecutionStatus("pending")).toBe(true);
    expect(isActiveExecutionStatus("running")).toBe(true);
    expect(isActiveExecutionStatus("paused")).toBe(true);
  });

  it("treats completed, failed, and cancelled as inactive", () => {
    expect(isActiveExecutionStatus("completed")).toBe(false);
    expect(isActiveExecutionStatus("failed")).toBe(false);
    expect(isActiveExecutionStatus("cancelled")).toBe(false);
  });
});

describe("nodeExecutionStatusColor", () => {
  it("highlights completed in green and failed in red", () => {
    expect(nodeExecutionStatusColor("completed")).toBe("text-green-600");
    expect(nodeExecutionStatusColor("failed")).toBe("text-red-600");
  });

  it("highlights both waiting statuses in amber", () => {
    expect(nodeExecutionStatusColor("waiting_approval")).toBe("text-amber-600");
    expect(nodeExecutionStatusColor("waiting_delay")).toBe("text-amber-600");
  });

  it("uses a neutral color for a skipped node", () => {
    expect(nodeExecutionStatusColor("skipped")).toBe("text-neutral-500");
  });
});

describe("policyStatusColor", () => {
  it("highlights published in green, draft in amber, archived as neutral", () => {
    expect(policyStatusColor("published")).toBe("text-green-600");
    expect(policyStatusColor("draft")).toBe("text-amber-600");
    expect(policyStatusColor("archived")).toBe("text-neutral-500");
  });
});

describe("notificationStatusColor", () => {
  it("highlights sent in green, failed in red, pending in amber", () => {
    expect(notificationStatusColor("sent")).toBe("text-green-600");
    expect(notificationStatusColor("failed")).toBe("text-red-600");
    expect(notificationStatusColor("pending")).toBe("text-amber-600");
  });
});

describe("nodeTypeLabel", () => {
  it("gives a human label to every known node type", () => {
    expect(nodeTypeLabel("trigger")).toBe("Trigger");
    expect(nodeTypeLabel("ai_evaluation")).toBe("AI Evaluation");
    expect(nodeTypeLabel("execute_action")).toBe("Execute Action");
    expect(nodeTypeLabel("end")).toBe("End");
  });

  it("falls back to the raw value for an unknown node type", () => {
    expect(nodeTypeLabel("something_new")).toBe("something_new");
  });
});
