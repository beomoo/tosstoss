import { toSafeHttpsUrl } from "@/lib/safe-url";

describe("toSafeHttpsUrl", () => {
  it("https URL만 정규화해 반환한다", () => {
    expect(toSafeHttpsUrl("https://localhost/source?id=fixture")).toBe(
      "https://localhost/source?id=fixture",
    );
  });

  it.each([
    "http://localhost",
    "javascript:alert(1)",
    "data:text/html,unsafe",
    "file:///C:/fixture.json",
    "fixture://market/price",
    "https://" + "user:password@localhost/source",
    "not-a-url",
    "",
  ])("위험하거나 클릭 불가한 URL을 거부한다: %s", (value) => {
    expect(toSafeHttpsUrl(value)).toBeNull();
  });

  it("null과 undefined를 거부한다", () => {
    expect(toSafeHttpsUrl(null)).toBeNull();
    expect(toSafeHttpsUrl(undefined)).toBeNull();
  });
});
