import { render, screen, within } from "@testing-library/react";

import { CompanyOverview } from "@/components/CompanyOverview";
import { createCompanyOverview } from "@/test/fixtures";

describe("CompanyOverview", () => {
  it("합성 회사, 정밀 Decimal, 시간대와 상태를 함께 표시한다", () => {
    render(<CompanyOverview overview={createCompanyOverview()} />);

    expect(screen.getByRole("heading", { level: 1, name: "합성그리드시스템" })).toBeVisible();
    expect(screen.getByText("999,999,999,999,999,999,999,999.000100 KRW")).toBeVisible();
    expect(screen.getByText("2026-08-15 15:30:00 KST (Asia/Seoul)")).toBeVisible();
    expect(screen.getAllByLabelText("확정 상태: FINAL").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("SAMPLE_RESULT").length).toBeGreaterThanOrEqual(4);
    expect(screen.getByText("USER_ASSUMPTION")).toBeVisible();
  });

  it("null을 0으로 오인하지 않고 악성 공시 문장을 텍스트로 표시한다", () => {
    const { container } = render(<CompanyOverview overview={createCompanyOverview()} />);

    const flowTable = screen.getByRole("table", { name: "합성 국내 단기 수급" });
    expect(within(flowTable).getByText("확인 불가 — 현재 이용 불가")).toBeVisible();
    expect(screen.getByText("<img src=x onerror=alert(1)>")).toBeVisible();
    expect(container.querySelector("img")).not.toBeInTheDocument();
  });

  it("가격 배열이 비어 있으면 명시적인 결측 상태를 표시한다", () => {
    const overview = createCompanyOverview();
    overview.price_bars = [];
    overview.missing_reasons = {
      ...overview.missing_reasons,
      price_bars: "UNAVAILABLE",
    };

    render(<CompanyOverview overview={overview} />);

    const priceSection = screen.getByRole("heading", { name: "최근 가격 샘플" }).closest("section");
    if (priceSection === null) {
      throw new Error("가격 섹션이 렌더링되지 않았습니다.");
    }
    expect(within(priceSection).getByText("확인 불가 — 현재 이용 불가")).toBeVisible();
    expect(screen.queryByText("0 KRW")).not.toBeInTheDocument();
  });

  it("UTC 직렬화 정밀도가 달라도 실제 최신 price bar를 선택한다", () => {
    const overview = createCompanyOverview();
    const older = overview.price_bars?.[0];
    if (older === undefined) {
      throw new Error("가격 fixture가 없습니다.");
    }
    overview.price_bars = [
      older,
      {
        ...older,
        price_bar_id: "price_kr_fixture_002",
        bar_start: "2026-08-15T06:30:00.100000Z",
        open: "41",
        high: "43",
        low: "40",
        close: "42",
        volume: "10",
      },
    ];

    render(<CompanyOverview overview={overview} />);

    const priceSection = screen.getByRole("heading", { name: "최근 가격 샘플" }).closest("section");
    if (priceSection === null) {
      throw new Error("가격 섹션이 렌더링되지 않았습니다.");
    }
    expect(within(priceSection).getByText("42 KRW")).toBeVisible();
    expect(within(priceSection).queryByText("999,999,999,999,999,999,999,999.000100 KRW"))
      .not.toBeInTheDocument();
  });

  it("US 근거 원문이 null이면 계약의 결측 사유를 함께 표시한다", () => {
    const overview = createCompanyOverview();
    const evidence = overview.evidence?.[0];
    if (evidence === undefined) {
      throw new Error("근거 fixture가 없습니다.");
    }
    overview.evidence = [
      {
        ...evidence,
        issuer_id: "issuer_us_synthetic",
        source_excerpt: null,
        source_record_id: null,
        missing_reasons: {
          source_excerpt: "UNAVAILABLE",
          source_record_id: "UNRESOLVED",
        },
      },
    ];

    render(<CompanyOverview overview={overview} />);

    expect(screen.getByText("원문 발췌 확인 불가 — 현재 이용 불가")).toBeVisible();
    expect(screen.getByText("원문 레코드: 확인 불가 — 확인되지 않음")).toBeVisible();
  });
});
