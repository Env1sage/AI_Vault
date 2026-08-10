import { describe, expect, it } from "vitest";

import { connectorStatusColor } from "./connector-status";

describe("connectorStatusColor", () => {
  it("highlights a connected connector in green", () => {
    expect(connectorStatusColor("connected")).toBe("text-green-600");
  });

  it("highlights an errored connector in red", () => {
    expect(connectorStatusColor("error")).toBe("text-red-600");
  });

  it("uses a neutral color for pending and disconnected states", () => {
    expect(connectorStatusColor("pending")).toBe("text-neutral-500");
    expect(connectorStatusColor("disconnected")).toBe("text-neutral-500");
  });
});
