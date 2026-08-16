import { render, screen } from "@testing-library/react";

import { FixtureBanner } from "@/components/FixtureBanner";

describe("FixtureBanner", () => {
  it("명확한 fixture 경고를 항상 읽을 수 있게 표시한다", () => {
    render(<FixtureBanner />);

    const banner = screen.getByLabelText("Fixture 데이터 안내");
    expect(banner).toBeVisible();
    expect(banner).toHaveTextContent("FIXTURE");
    expect(banner).toHaveTextContent("실제 투자 데이터 아님");
    expect(banner).toHaveTextContent("계산 엔진이 아닌 Phase 1 화면 골격");
  });
});
