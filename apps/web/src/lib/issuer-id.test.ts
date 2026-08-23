import { isValidIssuerId } from "@/lib/issuer-id";

describe("isValidIssuerId", () => {
  it.each(["abc", "issuer_kr_synthetic", `a${"b".repeat(127)}`])(
    "backend SafeId와 같은 유효 ID를 허용한다: %s",
    (value) => {
      expect(isValidIssuerId(value)).toBe(true);
    },
  );

  it.each(["a", "ab", "Issuer_kr", "1issuer", "issuer-with-hyphen", `a${"b".repeat(128)}`])(
    "backend가 거부할 ID를 frontend에서도 차단한다: %s",
    (value) => {
      expect(isValidIssuerId(value)).toBe(false);
    },
  );
});
