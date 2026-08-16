import { render, screen } from "@testing-library/react";

import { DataField } from "@/components/DataField";

describe("DataField", () => {
  it("null을 0으로 바꾸지 않고 결측 사유를 표시한다", () => {
    render(
      <dl>
        <DataField label="순금액" value={null} missingReason="UNAVAILABLE" />
      </dl>,
    );

    expect(screen.getByText("확인 불가 — 현재 이용 불가")).toBeVisible();
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });

  it("악성 HTML처럼 보이는 값을 텍스트로 escape한다", () => {
    const malicious = "<img src=x onerror=alert(1)>";
    const { container } = render(
      <dl>
        <DataField label="원문" value={malicious} />
      </dl>,
    );

    expect(screen.getByText(malicious)).toBeVisible();
    expect(container.querySelector("img")).not.toBeInTheDocument();
  });
});
