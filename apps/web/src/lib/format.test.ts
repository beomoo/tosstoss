import {
  formatDateOnly,
  formatDecimal,
  formatMissingReason,
  formatRecordCount,
  formatTimestamp,
} from "@/lib/format";

describe("format", () => {
  it("Decimal 문자열을 Number로 변환하지 않고 자릿수를 보존한다", () => {
    expect(formatDecimal("999999999999999999999999.000100", "KRW")).toBe(
      "999,999,999,999,999,999,999,999.000100 KRW",
    );
    expect(formatDecimal("-0.0040")).toBe("-0.0040");
    expect(formatDecimal("1e9")).toBe("확인 불가 (유효하지 않은 수치)");
  });

  it("aware timestamp를 고정된 Asia/Seoul 레이블과 함께 표시한다", () => {
    expect(formatTimestamp("2026-08-16T00:00:00Z")).toBe(
      "2026-08-16 09:00:00 KST (Asia/Seoul)",
    );
    expect(formatTimestamp("2026-08-16T09:00:00+09:00")).toBe(
      "2026-08-16 09:00:00 KST (Asia/Seoul)",
    );
    expect(formatTimestamp("2026-08-16T09:00:00")).toBe("확인 불가 (시간대 누락)");
    expect(formatTimestamp(null)).toBe("확인 불가");
  });

  it("date-only와 결측 사유, 레코드 수를 별도 형식으로 표시한다", () => {
    expect(formatDateOnly("2026-08-16")).toBe("2026-08-16");
    expect(formatDateOnly("2026-08-16T00:00:00Z")).toBe("확인 불가 (유효하지 않은 날짜)");
    expect(formatMissingReason("UNRESOLVED")).toBe("확인되지 않음");
    expect(formatRecordCount(1234567)).toBe("1,234,567");
    expect(formatRecordCount(-1)).toBe("확인 불가");
  });
});
