import { render, screen } from "@testing-library/react";

import { DataQualityGrid } from "@/components/DataQualityGrid";
import { createDataQualityStatus } from "@/test/fixtures";

describe("DataQualityGrid", () => {
  it("ERROR 상태에서도 마지막 정상 시각과 독립 상태 축을 보존한다", () => {
    render(
      <DataQualityGrid
        statuses={[
          createDataQualityStatus({
            availability_status: "ERROR",
            freshness_status: "STALE",
            finality_status: "REVISED",
            revision_status: "AMENDED",
            error_code: "FIXTURE_SOURCE_ERROR",
            error_message: "합성 소스 오류",
            missing_reasons: {},
          }),
        ]}
      />,
    );

    expect(screen.getByLabelText("가용성: ERROR")).toBeVisible();
    expect(screen.getByLabelText("신선도: STALE")).toBeVisible();
    expect(screen.getByLabelText("확정 상태: REVISED")).toBeVisible();
    expect(screen.getByLabelText("정정 상태: AMENDED")).toBeVisible();
    expect(screen.getByText(/마지막 정상 데이터는 보존됨/)).toHaveTextContent(
      "2026-08-16 09:10:00 KST (Asia/Seoul)",
    );
  });

  it("https 출처만 링크로 만들고 fixture locator는 텍스트로 남긴다", () => {
    const { rerender } = render(
      <DataQualityGrid statuses={[createDataQualityStatus({ source_locator: "fixture://market/price" })]} />,
    );
    expect(screen.queryByRole("link", { name: "HTTPS 원문 열기" })).not.toBeInTheDocument();
    expect(screen.getByText("출처: fixture://market/price")).toBeVisible();

    rerender(
      <DataQualityGrid
        statuses={[
          createDataQualityStatus({ source_locator: "https://localhost/synthetic-source" }),
        ]}
      />,
    );
    expect(screen.getByRole("link", { name: "HTTPS 원문 열기" })).toHaveAttribute(
      "href",
      "https://localhost/synthetic-source",
    );
  });

  it("javascript URL을 클릭 가능한 링크로 만들지 않는다", () => {
    render(
      <DataQualityGrid
        statuses={[createDataQualityStatus({ source_locator: "javascript:alert(1)" })]}
      />,
    );

    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByText("출처: javascript:alert(1)")).toBeVisible();
  });

  it("빈 응답을 정상적인 empty 상태로 표시한다", () => {
    render(<DataQualityGrid statuses={[]} />);

    expect(screen.getByRole("status")).toHaveAttribute("data-state", "empty");
    expect(screen.getByRole("heading", { name: "데이터 품질 항목이 없습니다" })).toBeVisible();
  });
});
