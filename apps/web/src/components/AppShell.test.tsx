import { render, screen } from "@testing-library/react";

import { AppShell } from "@/components/AppShell";

describe("AppShell", () => {
  it("현재 Phase 링크만 활성화하고 미래 메뉴는 비활성화한다", () => {
    render(<AppShell backendState="ONLINE">본문</AppShell>);

    expect(screen.getByRole("link", { name: "Company" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Data Quality" })).toHaveAttribute(
      "href",
      "/data-quality",
    );
    expect(screen.getAllByRole("button")).toHaveLength(5);
    for (const button of screen.getAllByRole("button")) {
      expect(button).toBeDisabled();
    }
    expect(screen.getByLabelText("서버 상태: Backend 정상")).toBeVisible();
  });
});
