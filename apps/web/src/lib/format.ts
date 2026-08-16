import type { MissingReason } from "@/types/api.contract";

const DECIMAL_PATTERN = /^-?(?:0|[1-9]\d*)(?:\.\d+)?$/;
const AWARE_TIMESTAMP_PATTERN = /(Z|[+-]\d{2}:\d{2})$/;
const DATE_ONLY_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

const missingReasonLabels: Record<MissingReason, string> = {
  NOT_PROVIDED: "원문에서 제공되지 않음",
  NOT_APPLICABLE: "해당 없음",
  UNAVAILABLE: "현재 이용 불가",
  UNRESOLVED: "확인되지 않음",
  PARSE_ERROR: "형식 해석 실패",
  WITHHELD: "공개되지 않음",
};

export function formatDecimal(value: string, unit?: string): string {
  if (!DECIMAL_PATTERN.test(value)) {
    return "확인 불가 (유효하지 않은 수치)";
  }

  const negative = value.startsWith("-");
  const unsigned = negative ? value.slice(1) : value;
  const [integer = "0", fraction] = unsigned.split(".");
  const grouped = integer.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const decimal = fraction === undefined ? grouped : `${grouped}.${fraction}`;
  const formatted = negative ? `-${decimal}` : decimal;

  return unit === undefined || unit.length === 0 ? formatted : `${formatted} ${unit}`;
}

export function formatDateOnly(value: string): string {
  return DATE_ONLY_PATTERN.test(value) ? value : "확인 불가 (유효하지 않은 날짜)";
}

export function formatTimestamp(value: string | null): string {
  if (value === null) {
    return "확인 불가";
  }
  if (!AWARE_TIMESTAMP_PATTERN.test(value)) {
    return "확인 불가 (시간대 누락)";
  }

  const instant = new Date(value);
  if (Number.isNaN(instant.getTime())) {
    return "확인 불가 (유효하지 않은 시각)";
  }

  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
  }).formatToParts(instant);
  const get = (type: Intl.DateTimeFormatPartTypes): string =>
    parts.find((part) => part.type === type)?.value ?? "??";

  return `${get("year")}-${get("month")}-${get("day")} ${get("hour")}:${get("minute")}:${get("second")} KST (Asia/Seoul)`;
}

export function formatMissingReason(reason?: MissingReason): string {
  return reason === undefined ? "사유 미제공" : missingReasonLabels[reason];
}

export function formatRecordCount(value: number): string {
  if (!Number.isSafeInteger(value) || value < 0) {
    return "확인 불가";
  }
  return new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 0 }).format(value);
}
