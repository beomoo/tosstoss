const PHASE1_RUNTIME_SENTINEL_PATTERN = /^PHASE1_RUNTIME_[0-9a-f]{32}$/;

export function isValidPhase1RuntimeSentinel(value: unknown): value is string {
  return typeof value === "string" && PHASE1_RUNTIME_SENTINEL_PATTERN.test(value);
}
