import { readFileSync } from "node:fs";
import { createSocket } from "node:dgram";
import { createServer } from "node:net";
import { resolve } from "node:path";

import { expect, test, type Page } from "@playwright/test";

const SENTINEL_PATH = resolve(
  process.cwd(),
  "../../var/phase-01-build-sentinel.txt",
);

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
      url.port === "3000" &&
      url.username === "" &&
      url.password === ""
    );
  } catch {
    return false;
  }
}

async function withInspectionTimeout<T>(
  promise: Promise<T>,
  timeoutMs: number,
): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    return await Promise.race([
      promise,
      new Promise<never>((_, reject) => {
        timer = setTimeout(
          () =>
            reject(new Error(`Response inspection exceeded ${timeoutMs}ms.`)),
          timeoutMs,
        );
      }),
    ]);
  } finally {
    if (timer !== undefined) {
      clearTimeout(timer);
    }
  }
}

async function createTcpBoundaryCanary() {
  const hits: string[] = [];
  const server = createServer((socket) => {
    hits.push(`${socket.remoteAddress ?? "unknown"}:${socket.remotePort ?? 0}`);
    socket.destroy();
  });
  await new Promise<void>((resolveListen, rejectListen) => {
    server.once("error", rejectListen);
    server.listen(0, "127.0.0.1", () => {
      server.off("error", rejectListen);
      resolveListen();
    });
  });
  const address = server.address();
  if (address === null || typeof address === "string") {
    await new Promise<void>((resolveClose) =>
      server.close(() => resolveClose()),
    );
    throw new Error("The browser boundary canary did not acquire a TCP port.");
  }
  return { hits, port: address.port, server };
}

async function observePageBoundary(page: Page, sentinel: string) {
  const context = page.context();
  const requestUrls: string[] = [];
  const forbiddenRequestUrls: string[] = [];
  const directBackendRequestUrls: string[] = [];
  const sentinelLeaks: string[] = [];
  const uninspectedResponses: string[] = [];
  const responseInspections: Promise<void>[] = [];
  const inspectedInterceptedUrls = new Set<string>();
  const boundaryCanaryUrls = new Set<string>();
  const sentinelBytes = Buffer.from(sentinel);

  // Playwright's HTTP and WebSocket routing does not mediate peer-to-peer or
  // QUIC transports. Remove those constructors before any application script
  // runs; workers are removed as well so they cannot create an unobserved
  // transport in a separate global scope.
  const blockedTransportConstructors = [
    "RTCPeerConnection",
    "webkitRTCPeerConnection",
    "WebTransport",
    "WebSocketStream",
    "Worker",
    "SharedWorker",
  ];
  await context.addInitScript((constructorNames: string[]) => {
    for (const constructorName of constructorNames) {
      Object.defineProperty(globalThis, constructorName, {
        configurable: false,
        enumerable: false,
        value: undefined,
        writable: false,
      });
    }
  }, blockedTransportConstructors);
  // The page fixture already owns an initial about:blank document. Navigate it
  // once so the context init script is active before the behavioral canaries.
  await page.goto("about:blank");

  const inspectUrl = (url: string) => {
    requestUrls.push(url);
    if (!isAllowedBrowserUrl(url) && !boundaryCanaryUrls.has(url)) {
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

  context.on("request", (request) => {
    inspectUrl(request.url());
  });

  // Install this at context scope before any page code runs so a popup's first
  // navigation cannot escape the offline boundary. Forbidden sockets are
  // closed without creating a server-side connection; allowed local sockets
  // are forwarded while both directions are inspected.
  await context.routeWebSocket(/.*/, async (socket) => {
    const url = socket.url();
    inspectUrl(url);
    if (!isAllowedBrowserUrl(url)) {
      await socket.close({ code: 1008, reason: "Phase 1 offline boundary" });
      return;
    }
    const serverSocket = socket.connectToServer();
    socket.onMessage((payload) => {
      const frame =
        typeof payload === "string" ? Buffer.from(payload) : payload;
      if (frame.includes(sentinelBytes)) {
        sentinelLeaks.push(`websocket-client:${url}`);
      }
      serverSocket.send(payload);
    });
    serverSocket.onMessage((payload) => {
      const frame =
        typeof payload === "string" ? Buffer.from(payload) : payload;
      if (frame.includes(sentinelBytes)) {
        sentinelLeaks.push(`websocket-server:${url}`);
      }
      socket.send(payload);
    });
  });

  // Next.js prefetch responses can remain open until navigation cancels them.
  // Buffer each local RSC fetch before the browser sees it so the exact response
  // (not a replay) is inspected and a timeout aborts the request fail-closed.
  await context.route("**/*", async (route) => {
    const request = route.request();
    if (!isAllowedBrowserUrl(request.url())) {
      await route.abort("blockedbyclient");
      return;
    }
    let url: URL;
    try {
      url = new URL(request.url());
    } catch {
      await route.abort("failed");
      return;
    }
    const isLocalRscFetch =
      request.method() === "GET" &&
      request.resourceType() === "fetch" &&
      url.hostname === "127.0.0.1" &&
      url.port === "3000" &&
      url.searchParams.has("_rsc");
    if (!isLocalRscFetch) {
      await route.continue();
      return;
    }
    try {
      const bufferedResponse = await route.fetch({
        maxRedirects: 0,
        timeout: 5_000,
      });
      const headers = JSON.stringify(bufferedResponse.headers());
      const body = await withInspectionTimeout(bufferedResponse.body(), 5_000);
      if (headers.includes(sentinel) || body.includes(sentinelBytes)) {
        sentinelLeaks.push(`intercepted:${request.url()}`);
      }
      inspectedInterceptedUrls.add(request.url());
      await route.fulfill({ response: bufferedResponse, body });
    } catch {
      uninspectedResponses.push(`intercepted:${request.url()}`);
      await route.abort("failed");
    }
  });

  context.on("response", (response) => {
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
          response.request().method() === "HEAD" ||
          status === 204 ||
          status === 205 ||
          status === 304;
        if (isBodyless) {
          return;
        }
        try {
          const body = await withInspectionTimeout(
            (async () => {
              await response.finished();
              return response.body();
            })(),
            5_000,
          );
          if (body.includes(sentinelBytes)) {
            sentinelLeaks.push(`body:${response.url()}`);
          }
        } catch {
          if (!inspectedInterceptedUrls.has(response.url())) {
            uninspectedResponses.push(`body:${response.url()}`);
          }
        }
      })(),
    );
  });

  return {
    async assertPreNetworkBlocking() {
      const datagramHits: string[] = [];
      const tcpCanaries: Awaited<
        ReturnType<typeof createTcpBoundaryCanary>
      >[] = [];
      const datagramServer = createSocket("udp4");
      let datagramBound = false;
      datagramServer.on("message", (_message, remote) => {
        datagramHits.push(`${remote.address}:${remote.port}`);
      });
      try {
        for (let index = 0; index < 3; index += 1) {
          tcpCanaries.push(await createTcpBoundaryCanary());
        }
        const [httpCanary, websocketCanary, websocketStreamCanary] =
          tcpCanaries;
        if (!httpCanary || !websocketCanary || !websocketStreamCanary) {
          throw new Error(
            "The browser boundary TCP canaries were not initialized.",
          );
        }
        await new Promise<void>((resolveBind, rejectBind) => {
          datagramServer.once("error", rejectBind);
          datagramServer.bind(0, "127.0.0.1", () => {
            datagramServer.off("error", rejectBind);
            datagramBound = true;
            resolveBind();
          });
        });
        const datagramAddress = datagramServer.address();
        if (typeof datagramAddress === "string") {
          throw new Error(
            "The browser boundary canary did not acquire a UDP port.",
          );
        }
        const httpUrl = `http://127.0.0.1:${httpCanary.port}/must-not-connect`;
        const websocketUrl =
          `ws://127.0.0.1:${websocketCanary.port}/must-not-connect`;
        const websocketStreamUrl =
          `ws://127.0.0.1:${websocketStreamCanary.port}/must-not-connect`;
        boundaryCanaryUrls.add(httpUrl);
        boundaryCanaryUrls.add(websocketUrl);
        boundaryCanaryUrls.add(websocketStreamUrl);

        const result = await page.evaluate(
          async ({
            canaryHttpUrl,
            canaryWebsocketUrl,
            canaryWebsocketStreamUrl,
            stunUrl,
            blockedConstructors,
          }) => {
            const http = await fetch(canaryHttpUrl).then(
              () => "completed",
              () => "blocked",
            );
            const websocket = await new Promise<string>((resolveSocket) => {
              const socket = new WebSocket(canaryWebsocketUrl);
              let settled = false;
              const finish = (value: string) => {
                if (settled) return;
                settled = true;
                socket.close();
                resolveSocket(value);
              };
              socket.addEventListener("open", () => finish("opened"), {
                once: true,
              });
              socket.addEventListener("error", () => finish("blocked"), {
                once: true,
              });
              socket.addEventListener("close", () => finish("blocked"), {
                once: true,
              });
              setTimeout(() => finish("timeout"), 1_000);
            });
            let websocketStream = "blocked";
            const websocketStreamConstructor = Reflect.get(
              globalThis,
              "WebSocketStream",
            );
            if (typeof websocketStreamConstructor === "function") {
              websocketStream = "available";
              const StreamConstructor = websocketStreamConstructor as new (
                url: string,
              ) => { close: () => void; opened: Promise<unknown> };
              const stream = new StreamConstructor(canaryWebsocketStreamUrl);
              await Promise.race([
                stream.opened.catch(() => undefined),
                new Promise((resolveWait) => setTimeout(resolveWait, 300)),
              ]);
              stream.close();
            }
            const unavailableConstructors = blockedConstructors.filter(
              (constructorName) =>
                Reflect.get(globalThis, constructorName) === undefined &&
                Object.getOwnPropertyDescriptor(globalThis, constructorName)
                  ?.configurable === false,
            );
            let rtc = "blocked";
            const rtcConstructor = Reflect.get(globalThis, "RTCPeerConnection");
            if (typeof rtcConstructor === "function") {
              rtc = "available";
              const peer = new (rtcConstructor as typeof RTCPeerConnection)({
                iceServers: [{ urls: stunUrl }],
              });
              try {
                peer.createDataChannel("phase-01-boundary-canary");
                await peer.setLocalDescription(await peer.createOffer());
                await new Promise((resolveWait) =>
                  setTimeout(resolveWait, 300),
                );
              } finally {
                peer.close();
              }
            }
            return {
              http,
              rtc,
              unavailableConstructors,
              websocket,
              websocketStream,
            };
          },
          {
            blockedConstructors: blockedTransportConstructors,
            canaryHttpUrl: httpUrl,
            canaryWebsocketUrl: websocketUrl,
            canaryWebsocketStreamUrl: websocketStreamUrl,
            stunUrl: `stun:127.0.0.1:${datagramAddress.port}`,
          },
        );
        expect(
          result.http,
          "금지된 HTTP 요청은 브라우저 전송 전에 차단되어야 합니다.",
        ).toBe("blocked");
        expect(result.websocket).not.toBe("timeout");
        expect(
          result.websocketStream,
          "WebSocketStream must be disabled before application code runs.",
        ).toBe("blocked");
        expect(
          result.rtc,
          "WebRTC must be disabled before application code runs.",
        ).toBe("blocked");
        expect(result.unavailableConstructors).toEqual(
          blockedTransportConstructors,
        );
        await new Promise((resolveWait) => setTimeout(resolveWait, 100));
        expect(
          httpCanary.hits,
          "금지된 HTTP 카나리는 로컬 TCP listener에도 도달하면 안 됩니다.",
        ).toEqual([]);
        expect(
          websocketCanary.hits,
          "금지된 WebSocket 카나리는 로컬 TCP listener에도 도달하면 안 됩니다.",
        ).toEqual([]);
        expect(
          websocketStreamCanary.hits,
          "금지된 WebSocketStream 카나리는 로컬 TCP listener에도 도달하면 안 됩니다.",
        ).toEqual([]);
        expect(
          datagramHits,
          "금지된 WebRTC STUN 카나리는 UDP listener에 도달하면 안 됩니다.",
        ).toEqual([]);
      } finally {
        const closePromises = tcpCanaries.map(
          (canary) =>
            new Promise<void>((resolveClose, rejectClose) => {
              canary.server.close((error) =>
                error ? rejectClose(error) : resolveClose(),
              );
            }),
        );
        if (datagramBound) {
          closePromises.push(
            new Promise<void>((resolveClose) =>
              datagramServer.close(resolveClose),
            ),
          );
        } else {
          datagramServer.removeAllListeners();
        }
        await Promise.all(closePromises);
      }
    },
    async assertClean() {
      await page.waitForLoadState("networkidle");

      let inspected = 0;
      while (inspected < responseInspections.length) {
        const pending = responseInspections.slice(inspected);
        inspected = responseInspections.length;
        await Promise.all(pending);
      }

      expect(
        requestUrls.length,
        "브라우저 요청 URL이 수집되어야 합니다.",
      ).toBeGreaterThan(0);
      const pages = context.pages();
      expect(pages, "Phase 1 화면은 새 popup을 만들면 안 됩니다.").toHaveLength(
        1,
      );
      expect(pages[0]).toBe(page);
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
      expect(
        sentinelLeaks,
        "server-only sentinel이 응답에 포함되면 안 됩니다.",
      ).toEqual([]);
    },
  };
}

test("Phase 1 합성 Company와 모든 issuer의 Data Quality 화면", async ({
  page,
}, testInfo) => {
  const audit = await observePageBoundary(page, readServerOnlySentinel());
  await audit.assertPreNetworkBlocking();

  await page.goto("/");

  await expect(page.getByTestId("fixture-banner")).toBeVisible();
  await expect(page.getByTestId("fixture-banner")).toContainText(
    "실제 투자 데이터 아님",
  );
  await expect(page).toHaveURL(/\/company\/issuer_[a-z0-9_]+$/);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByText("SAMPLE_RESULT").first()).toBeVisible();
  await expect(
    page.getByRole("button", { name: /후속 Phase에서 제공/ }).first(),
  ).toBeDisabled();
  await expect(page.locator('a[href^="javascript:"]')).toHaveCount(0);
  await page.screenshot({
    path: testInfo.outputPath("company.png"),
    fullPage: true,
  });

  await page.getByRole("link", { name: "Data Quality" }).click();
  await expect(page).toHaveURL(/\/data-quality$/);
  await expect(
    page.getByRole("heading", { level: 1, name: "Data Quality" }),
  ).toBeVisible();

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
  await page.screenshot({
    path: testInfo.outputPath("data-quality.png"),
    fullPage: true,
  });
  await audit.assertClean();
});

test("알 수 없는 issuer는 안전한 not-found 화면", async ({ page }) => {
  const audit = await observePageBoundary(page, readServerOnlySentinel());

  await page.goto("/company/issuer_not_in_fixture");

  await expect(page.getByTestId("fixture-banner")).toBeVisible();
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "합성 기업을 찾을 수 없습니다",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Fixture 홈으로" }),
  ).toBeVisible();
  await audit.assertClean();
});
