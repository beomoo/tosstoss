import type {
  AvailabilityStatus,
  FinalityStatus,
  FreshnessStatus,
  RevisionStatus,
} from "@/types/api.contract";

type Status = AvailabilityStatus | FreshnessStatus | FinalityStatus | RevisionStatus;

interface StatusBadgeProps {
  status: Status;
  label?: string | undefined;
}

const statusSymbols: Record<Status, string> = {
  AVAILABLE: "●",
  DEGRADED: "▲",
  ERROR: "!",
  UNAVAILABLE: "×",
  FRESH: "●",
  STALE: "▲",
  EXPIRED: "×",
  UNKNOWN: "?",
  PRELIMINARY: "◇",
  FINAL: "✓",
  REVISED: "↺",
  ORIGINAL: "○",
  AMENDED: "↺",
  SUPERSEDED: "↪",
  MERGED: "◎",
};

export function StatusBadge({ status, label }: StatusBadgeProps) {
  return (
    <span className="status-badge" data-status={status.toLowerCase()} aria-label={`${label ?? "상태"}: ${status}`}>
      <span aria-hidden="true">{statusSymbols[status]}</span>
      <span>{status}</span>
    </span>
  );
}
