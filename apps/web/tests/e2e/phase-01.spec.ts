import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { expect, test, type Page } from "@playwright/test";

const SENTINEL_PATH = resolve(process.cwd(), "../../var/phase-01-build-sentinel.txt");

function readServerOnlySentinel(): string {
  const sentinel = readFileSync(SENTINEL_PATH, "utf8").trim();
  expect(sentinel).toMatch(/^PHASE1_RUNTIME_[0-9a-f]{32}$/);
  return sentinel;
}

function isAllowedBrowserUrl(rawUrl: string): boolean {
  try {
    const url = new URL(rawUrl);
    return (
      (url.protocol === "http:" || url.protocol === "ws:") &&
      url.hostname === "127.0.0.1" &&
      url.username === "" &&
      url.password === ""
    );
  } catch {
    return false;
  }
}

function observePageBoundary(page: Page, sentinel: string) {
  const requestUrls: string[] = [];
  const forbiddenRequestUrls: string[] = [];
  const directBackendRequestUrls: string[] = [];
  const sentinelLeaks: string[] = [];
  const uninspectedResponses: string[] = [];
  const responseInspections: Promise<void>[] = [];
  const sentinelBytes = Buffer.from(sentinel);

  const inspectUrl = (url: string) => {
    requestUrls.push(url);
    if (!isAllowedBrowserUrl(url)) {
      forbiddenRequestUrls.push(url);
    }
    try {
      if (new URL(url).port === "8000") {
        directBackendRequestUrls.push(url);
      }
    } catch {
      // Invalid URLs are already recorded as forbidden.
    }
  };

  page.on("request", (request) => {
    inspectUrl(request.url());
  });

  page.on("websocket", (socket) => {
    inspectUrl(socket.url());
    socket.on("framereceived", ({ payload }) => {
      const frame = typeof payload === "string" ? Buffer.from(payload) : payload;
      if (frame.includes(sentinelBytes)) {
        sentinelLeaks.push(`websocket:${socket.url()}`);
      }
    });
  });

  page.on("response", (response) => {
    responseInspections.push(
      (async () => {
        try {
          const headers = JSON.stringify(await response.allHeaders());
          if (headers.includes(sentinel)) {
            sentinelLeaks.push(`headers:${response.url()}`);
          }
        } catch {
          uninspectedResponses.push(`headers:${response.url()}`);
        }

        const status = response.status();
        const isBodyless =
          status === 204 || status === 205 || status === 304 || (status >= 300 && status < 400);
        if (isBodyless) {
          return;
        }
        try {
          await response.finished();
          const body = await response.body();
          if (body.includes(sentinelBytes)) {
            sentinelLeaks.push(`body:${response.url()}`);
          }
        } catch {
          try {
            const url = response.url();
            if (response.request().method() !== "GET" || !isAllowedBrowserUrl(url)) {
              throw new Error("Only local GET responses may use the inspection fallback.");
            }
            const fallback = await fetch(url, { method: "GET", redirect: "error" });
            const fallbackHeaders = JSON.stringify(Object.fromEntries(fallback.headers.entries()));
            const fallbackBody = Buffer.from(await fallback.arrayBuffer());
            if (fallbackHeaders.includes(sentinel) || fallbackBody.includes(sentinelBytes)) {
              sentinelLeaks.push(`fallback:${url}`);
            }
          } catch {
            uninspectedResponses.push(`body:${response.url()}`);
          }
        }
      })(),
    );
  });

  return {
    async assertClean() {
      await page.waitForLoadState("networkidle");

      let inspected = 0;
      while (inspected < responseInspections.length) {
        const pending = responseInspections.slice(inspected);
        inspected = responseInspections.length;
        await Promise.all(pending);
      }

      expect(requestUrls.length, "브라우저 요청 URL이 수집되어야 합니다.").toBeGreaterThan(0);
      expect(
        forbiddenRequestUrls,
        "브라우저는 http/ws 127.0.0.1 경계 밖으로 요청하면 안 됩니다.",
      ).toEqual([]);
      expect(
        directBackendRequestUrls,
        "브라우저가 127.0.0.1:8000 backend를 직접 호출하면 안 됩니다.",
      ).toEqual([]);
      expect(await page.content()).not.toContain(sentinel);
      expect(
        uninspectedResponses,
        "bodyless 상태가 아닌 모든 페이지 응답을 sentinel 검사해야 합니다.",
      ).toEqual([]);
      expect(sentinelLeaks, "server-only sentinel이 응답에 포함되면 안 됩니다.").toEqual([]);
    },
  };
}

test("Phase 1 합성 Company와 모든 issuer의 Data Quality 화면", async ({ page }, testInfo) => {
  const audit = observePageBoundary(page, readServerOnlySentinel());

  await page.goto("/");

  await expect(page.getByTestId("fixture-banner")).toBeVisible();
  await expect(page.getByTestId("fixture-banner")).toContainText("실제 투자 데이터 아님");
  await expect(page).toHaveURL(/\/company\/issuer_[a-z0-9_]+$/);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByText("SAMPLE_RESULT").first()).toBeVisible();
  await expect(page.getByRole("button", { name: /후속 Phase에서 제공/ }).first()).toBeDisabled();
  await expect(page.locator('a[href^="javascript:"]')).toHaveCount(0);
  await page.screenshot({ path: testInfo.outputPath("company.png"), fullPage: true });

  await page.getByRole("link", { name: "Data Quality" }).click();
  await expect(page).toHaveURL(/\/data-quality$/);
  await expect(page.getByRole("heading", { level: 1, name: "Data Quality" })).toBeVisible();

  const krIssuer = page.getByTestId("quality-issuer-issuer_kr_synthetic");
  await expect(krIssuer).toBeVisible();
  await expect(krIssuer.getByLabel("가용성: AVAILABLE")).toBeVisible();
  await expect(krIssuer.getByLabel("신선도: FRESH")).toBeVisible();
  await expect(krIssuer.getByLabel("가용성: DEGRADED")).toBeVisible();
  await expect(krIssuer.getByLabel("신선도: STALE")).toBeVisible();

  const usIssuer = page.getByTestId("quality-issuer-issuer_us_synthetic");
  await expect(usIssuer).toBeVisible();
  await expect(usIssuer.getByLabel("가용성: ERROR")).toBeVisible();
  await expect(usIssuer.getByLabel("가용성: UNAVAILABLE")).toBeVisible();
  await expect(usIssuer.getByText(/마지막 정상 데이터는 보존됨/)).toBeVisible();

  await expect(page.locator('a[href^="javascript:"]')).toHaveCount(0);
  await page.screenshot({ path: testInfo.outputPath("data-quality.png"), fullPage: true });
  await audit.assertClean();
});

test("알 수 없는 issuer는 안전한 not-found 화면", async ({ page }) => {
  const audit = observePageBoundary(page, readServerOnlySentinel());

  await page.goto("/company/issuer_not_in_fixture");

  await expect(page.getByTestId("fixture-banner")).toBeVisible();
  await expect(
    page.getByRole("heading", { level: 1, name: "합성 기업을 찾을 수 없습니다" }),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "Fixture 홈으로" })).toBeVisible();
  await audit.assertClean();
});
