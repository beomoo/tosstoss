import type { MissingReason } from "@/types/api.contract";
import { formatMissingReason } from "@/lib/format";

interface DataFieldProps {
  label: string;
  value: string | null | undefined;
  missingReason?: MissingReason | undefined;
  note?: string | undefined;
}

export function DataField({ label, value, missingReason, note }: DataFieldProps) {
  const isMissing = value === null || value === undefined;

  return (
    <div className="data-field" data-state={isMissing ? "missing" : "available"}>
      <dt>{label}</dt>
      <dd>
        {isMissing ? (
          <span className="missing-value">확인 불가 — {formatMissingReason(missingReason)}</span>
        ) : (
          value
        )}
        {note === undefined ? null : <small>{note}</small>}
      </dd>
    </div>
  );
}
