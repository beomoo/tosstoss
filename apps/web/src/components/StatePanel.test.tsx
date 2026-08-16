import { render, screen } from "@testing-library/react";

import { StatePanel } from "@/components/StatePanel";

describe("StatePanel", () => {
  it.each([
    ["loading", "불러오는 중"],
    ["empty", "항목 없음"],
    ["error", "안전한 오류"],
    ["not-found", "찾을 수 없음"],
  ] as const)("%s 상태를 텍스트와 의미론으로 표시한다", (kind, title) => {
    render(<StatePanel kind={kind} title={title} message="상태 설명" />);

    expect(screen.getByRole(kind === "error" ? "alert" : "status")).toHaveAttribute(
      "data-state",
      kind,
    );
    expect(screen.getByRole("heading", { name: title })).toBeVisible();
    expect(screen.getByText("상태 설명")).toBeVisible();
  });
});
