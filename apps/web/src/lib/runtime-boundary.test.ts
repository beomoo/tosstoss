import { describe, expect, it } from "vitest";

import { isValidPhase1RuntimeSentinel } from "@/lib/runtime-boundary";

describe("isValidPhase1RuntimeSentinel", () => {
  it("rejects an unset sentinel", () => {
    expect(isValidPhase1RuntimeSentinel(undefined)).toBe(false);
  });

  it("rejects an empty sentinel", () => {
    expect(isValidPhase1RuntimeSentinel("")).toBe(false);
  });

  it("rejects garbage", () => {
    expect(isValidPhase1RuntimeSentinel("garbage")).toBe(false);
  });

  it("accepts only the exact Phase 1 runtime sentinel format", () => {
    expect(
      isValidPhase1RuntimeSentinel("PHASE1_RUNTIME_0123456789abcdef0123456789abcdef"),
    ).toBe(true);

    for (const invalidValue of [
      "PHASE1_RUNTIME_0123456789abcdef0123456789abcde",
      "PHASE1_RUNTIME_0123456789abcdef0123456789abcdef0",
      "PHASE1_RUNTIME_0123456789ABCDEF0123456789ABCDEF",
      "phase1_runtime_0123456789abcdef0123456789abcdef",
      " PHASE1_RUNTIME_0123456789abcdef0123456789abcdef",
      "PHASE1_RUNTIME_0123456789abcdef0123456789abcdef\n",
    ]) {
      expect(isValidPhase1RuntimeSentinel(invalidValue)).toBe(false);
    }
  });
});
