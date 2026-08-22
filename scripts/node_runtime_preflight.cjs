"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const dns = require("node:dns");
const dnsPromises = require("node:dns/promises");
const dgram = require("node:dgram");
const { once } = require("node:events");
const http = require("node:http");
const http2 = require("node:http2");
const https = require("node:https");
const net = require("node:net");
const tls = require("node:tls");

const BLOCKED_NETWORK_CODE = "ERR_OFFLINE_NON_LOOPBACK";
const externalHostname = "phase-01-network-canary.example.invalid";
const externalHttpUrl = `http://${externalHostname}/`;
const externalHttpsUrl = `https://${externalHostname}/`;

function assertSynchronouslyBlocked(label, createResource) {
  let resource;
  try {
    assert.throws(
      () => {
        resource = createResource();
      },
      { code: BLOCKED_NETWORK_CODE },
      `${label} must reject before starting network activity.`,
    );
  } finally {
    resource?.destroy?.();
  }
}

function localOnlyCanaryLookup(_hostname, options, callback) {
  const done = typeof options === "function" ? options : callback;
  const error = new Error("Offline canary lookup fallback was reached.");
  error.code = "ERR_OFFLINE_CANARY_LOOKUP_REACHED";
  process.nextTick(done, error);
}

function listenOnLoopback(server) {
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      server.off("error", reject);
      resolve(server.address().port);
    });
  });
}

function closeServer(server) {
  return new Promise((resolve, reject) => {
    server.close((error) => error ? reject(error) : resolve());
  });
}

function closeDgramSocket(socket) {
  return new Promise((resolve, reject) => {
    try {
      socket.close(resolve);
    } catch (error) {
      if (error.code === "ERR_SOCKET_DGRAM_NOT_RUNNING") {
        resolve();
      } else {
        reject(error);
      }
    }
  });
}

function sendDgram(send) {
  return new Promise((resolve, reject) => {
    send((error) => error ? reject(error) : resolve());
  });
}

function waitForWebSocketOpen(webSocket) {
  return new Promise((resolve, reject) => {
    webSocket.addEventListener("open", resolve, { once: true });
    webSocket.addEventListener("error", (event) => {
      reject(event.error || new Error("Loopback WebSocket failed to open."));
    }, { once: true });
  });
}

function hasBlockedNetworkCode(error) {
  let current = error;
  while (current) {
    if (current.code === BLOCKED_NETWORK_CODE) {
      return true;
    }
    current = current.cause;
  }
  return false;
}

function requestText(url, useGet) {
  return new Promise((resolve, reject) => {
    const onResponse = (response) => {
      const chunks = [];
      response.on("data", (chunk) => chunks.push(chunk));
      response.once("error", reject);
      response.once("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    };
    const request = useGet
      ? http.get(url, onResponse)
      : http.request(url, onResponse);
    request.once("error", reject);
    if (!useGet) {
      request.end();
    }
  });
}

function requestOptionsText(options) {
  return new Promise((resolve, reject) => {
    const request = http.request(options, (response) => {
      const chunks = [];
      response.on("data", (chunk) => chunks.push(chunk));
      response.once("error", reject);
      response.once("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    });
    request.once("error", reject);
    request.end();
  });
}

async function verifySocketOptionSnapshot(label, port, createSocket, extraOptions = {}) {
  let hostReads = 0;
  let lookupReads = 0;
  let lookupCalls = 0;
  const options = {
    ...extraOptions,
    port,
    get host() {
      hostReads += 1;
      return hostReads === 1 ? "127.0.0.1" : externalHostname;
    },
    get lookup() {
      lookupReads += 1;
      return (...args) => {
        lookupCalls += 1;
        const callback = args.findLast((argument) => typeof argument === "function");
        const error = new Error(`${label} lookup snapshot fallback was reached.`);
        error.code = "ERR_OFFLINE_CANARY_LOOKUP_REACHED";
        process.nextTick(callback, error);
      };
    },
  };

  await new Promise((resolve, reject) => {
    let socket;
    try {
      socket = createSocket(options);
    } catch (error) {
      reject(error);
      return;
    }
    socket.once("connect", () => {
      socket.destroy();
      resolve();
    });
    socket.once("error", reject);
  });

  assert.equal(hostReads, 1, `${label} must read host exactly once.`);
  assert.equal(lookupReads, 1, `${label} must read lookup exactly once.`);
  assert.equal(lookupCalls, 0, `${label} must retain the literal-IP snapshot.`);
}

async function verifyExternalRejection() {
  const fetchBeforeReplacement = globalThis.fetch;
  const fetchSnapshotLoopbackUrl = "http://127.0.0.1/fetch-snapshot-canary";
  let replacementCalls = 0;
  const replacementInputs = [];
  const replacementInits = [];

  // This has the same capture/wrap/assign shape as Next's fetch patch. If the
  // outer guard were missing, the fallback rejects without touching a resolver.
  globalThis.fetch = function nextStyleFetchReplacement(input, init) {
    replacementCalls += 1;
    replacementInputs.push(input);
    replacementInits.push(init);
    const inputUrl = typeof input === "string" ? input : input?.url;
    if (inputUrl === fetchSnapshotLoopbackUrl) {
      return Promise.resolve(new Response("fetch-snapshot-ok"));
    }
    if (typeof inputUrl === "string" && inputUrl.includes(externalHostname)) {
      const error = new Error("Fetch replacement reached the external canary.");
      error.code = "ERR_OFFLINE_CANARY_FETCH_REACHED";
      return Promise.reject(error);
    }
    return Reflect.apply(fetchBeforeReplacement, this, [input, init]);
  };

  try {
    await assert.rejects(
      globalThis.fetch(externalHttpsUrl),
      { code: BLOCKED_NETWORK_CODE },
    );
    assert.equal(
      replacementCalls,
      0,
      "The fetch guard must reject before invoking a replacement implementation.",
    );

    let objectCoercions = 0;
    const spoofedObject = {
      url: fetchSnapshotLoopbackUrl,
      toString() {
        objectCoercions += 1;
        return externalHttpsUrl;
      },
    };
    await assert.rejects(
      globalThis.fetch(spoofedObject),
      { code: BLOCKED_NETWORK_CODE },
    );
    assert.equal(objectCoercions, 1, "An ordinary fetch input must be coerced once.");
    assert.equal(
      replacementCalls,
      0,
      "A plain object's spoofed url property must not reach the fetch replacement.",
    );

    let safeObjectCoercions = 0;
    const safeCoercedObject = {
      url: externalHttpsUrl,
      toString() {
        safeObjectCoercions += 1;
        return fetchSnapshotLoopbackUrl;
      },
    };
    const safeObjectResponse = await globalThis.fetch(safeCoercedObject);
    assert.equal(await safeObjectResponse.text(), "fetch-snapshot-ok");
    assert.equal(safeObjectCoercions, 1);
    assert.equal(replacementInputs.at(-1), fetchSnapshotLoopbackUrl);

    let urlToStringCalls = 0;
    const overriddenUrl = new URL(fetchSnapshotLoopbackUrl);
    overriddenUrl.toString = () => {
      urlToStringCalls += 1;
      return externalHttpsUrl;
    };
    const overriddenUrlResponse = await globalThis.fetch(overriddenUrl);
    assert.equal(await overriddenUrlResponse.text(), "fetch-snapshot-ok");
    assert.equal(urlToStringCalls, 0, "Fetch must use URL's native href getter.");
    assert.equal(replacementInputs.at(-1), fetchSnapshotLoopbackUrl);

    const nextMarker = { revalidate: 60 };
    let nextReads = 0;
    const nextInit = {
      cache: "no-store",
      get next() {
        nextReads += 1;
        return nextMarker;
      },
    };
    const nextInitResponse = await globalThis.fetch(fetchSnapshotLoopbackUrl, nextInit);
    assert.equal(await nextInitResponse.text(), "fetch-snapshot-ok");
    assert.equal(nextReads, 1, "Fetch init fields must be snapshotted exactly once.");
    assert.notEqual(replacementInits.at(-1), nextInit);
    assert.equal(Object.getPrototypeOf(replacementInits.at(-1)), Object.prototype);
    assert.equal(replacementInits.at(-1).next, nextMarker);

    const shadowedRequest = new Request(externalHttpsUrl);
    Object.defineProperty(shadowedRequest, "url", {
      configurable: true,
      value: fetchSnapshotLoopbackUrl,
    });
    const requestReplacementCalls = replacementCalls;
    await assert.rejects(
      globalThis.fetch(shadowedRequest),
      { code: BLOCKED_NETWORK_CODE },
    );
    assert.equal(
      replacementCalls,
      requestReplacementCalls,
      "A Request's spoofed own url must not reach the fetch replacement.",
    );

    for (const [label, createResource] of [
      ["http.request", () => http.request(externalHttpUrl, { lookup: localOnlyCanaryLookup })],
      ["http.get", () => http.get(externalHttpUrl, { lookup: localOnlyCanaryLookup })],
      ["https.request", () => https.request(externalHttpsUrl, { lookup: localOnlyCanaryLookup })],
      ["https.get", () => https.get(externalHttpsUrl, { lookup: localOnlyCanaryLookup })],
      ["net.connect", () => net.connect({ host: externalHostname, lookup: localOnlyCanaryLookup, port: 443 })],
      ["net.createConnection", () => net.createConnection({ host: externalHostname, lookup: localOnlyCanaryLookup, port: 443 })],
      ["tls.connect", () => tls.connect({ host: externalHostname, lookup: localOnlyCanaryLookup, port: 443 })],
    ]) {
      assertSynchronouslyBlocked(label, createResource);
    }

    for (const [label, createRequest] of [
      ["http.request", (options) => http.request(options)],
      ["https.request", (options) => https.request(options)],
    ]) {
      let createConnectionReads = 0;
      let createConnectionCalls = 0;
      assertSynchronouslyBlocked(`${label} custom createConnection`, () =>
        createRequest({
          host: "127.0.0.1",
          port: 9,
          get createConnection() {
            createConnectionReads += 1;
            return () => {
              createConnectionCalls += 1;
              throw new Error(`${label} createConnection canary was reached.`);
            };
          },
        })
      );
      assert.equal(createConnectionReads, 1);
      assert.equal(createConnectionCalls, 0);

      let agentReads = 0;
      let addRequestCalls = 0;
      assertSynchronouslyBlocked(`${label} custom agent`, () =>
        createRequest({
          host: "127.0.0.1",
          port: 9,
          get agent() {
            agentReads += 1;
            return {
              addRequest() {
                addRequestCalls += 1;
                throw new Error(`${label} agent canary was reached.`);
              },
            };
          },
        })
      );
      assert.equal(agentReads, 1);
      assert.equal(addRequestCalls, 0);
    }

    const directSocket = new net.Socket();
    try {
      assert.throws(
        () => directSocket.connect({
          host: externalHostname,
          lookup: localOnlyCanaryLookup,
          port: 443,
        }),
        { code: BLOCKED_NETWORK_CODE },
      );
    } finally {
      directSocket.destroy();
    }

    let blockedTargetCoercions = 0;
    const nonStringBlockedTarget = {
      [Symbol.toPrimitive]() {
        blockedTargetCoercions += 1;
        throw new Error("Blocked target Symbol.toPrimitive canary was reached.");
      },
      toString() {
        blockedTargetCoercions += 1;
        throw new Error("Blocked target toString canary was reached.");
      },
    };
    assertSynchronouslyBlocked(
      "net.connect non-string error target",
      () => net.connect({ host: nonStringBlockedTarget, port: 443 }),
    );
    assert.throws(
      () => dns.lookup(nonStringBlockedTarget, () => {}),
      { code: BLOCKED_NETWORK_CODE },
    );
    assert.throws(
      () => dns.resolve4(nonStringBlockedTarget, () => {}),
      { code: BLOCKED_NETWORK_CODE },
    );
    assert.equal(
      blockedTargetCoercions,
      0,
      "Blocked error paths must not coerce attacker-controlled targets.",
    );

    assert.throws(
      () => new WebSocket(`wss://${externalHostname}/`),
      { code: BLOCKED_NETWORK_CODE },
    );
    let webSocketUrlToStringCalls = 0;
    const externalWebSocketUrl = new URL(`wss://${externalHostname}/`);
    externalWebSocketUrl.toString = () => {
      webSocketUrlToStringCalls += 1;
      return "ws://127.0.0.1/";
    };
    assert.throws(
      () => new WebSocket(externalWebSocketUrl),
      { code: BLOCKED_NETWORK_CODE },
    );
    assert.equal(webSocketUrlToStringCalls, 0);

    let webSocketDispatcherCalls = 0;
    assert.throws(
      () => new WebSocket("ws://127.0.0.1:9/", {
        dispatcher: {
          dispatch() {
            webSocketDispatcherCalls += 1;
            throw new Error("WebSocket dispatcher canary was reached.");
          },
        },
      }),
      { code: BLOCKED_NETWORK_CODE },
    );
    assert.equal(webSocketDispatcherCalls, 0);

    assert.throws(
      () => http2.connect(`https://${externalHostname}/`),
      { code: BLOCKED_NETWORK_CODE },
    );
    let http2AuthorityToStringCalls = 0;
    const externalHttp2Authority = new URL(`https://${externalHostname}/`);
    externalHttp2Authority.toString = () => {
      http2AuthorityToStringCalls += 1;
      return "http://127.0.0.1/";
    };
    assert.throws(
      () => http2.connect(externalHttp2Authority),
      { code: BLOCKED_NETWORK_CODE },
    );
    assert.equal(http2AuthorityToStringCalls, 0);

    let http2CreateConnectionCalls = 0;
    assert.throws(
      () => http2.connect("http://127.0.0.1:9/", {
        createConnection() {
          http2CreateConnectionCalls += 1;
          throw new Error("HTTP/2 createConnection canary was reached.");
        },
      }),
      { code: BLOCKED_NETWORK_CODE },
    );
    assert.equal(http2CreateConnectionCalls, 0);

    const udpSocket = dgram.createSocket("udp4");
    try {
      assert.throws(
        () => udpSocket.connect(9, externalHostname),
        { code: BLOCKED_NETWORK_CODE },
      );
      assert.throws(
        () => udpSocket.send("blocked", 9, externalHostname),
        { code: BLOCKED_NETWORK_CODE },
      );
      assert.throws(
        () => udpSocket.sendto(
          Buffer.from("blocked"),
          0,
          7,
          9,
          externalHostname,
        ),
        { code: BLOCKED_NETWORK_CODE },
      );
      assert.throws(
        () => udpSocket.sendto(
          Buffer.from("blocked"),
          0,
          7,
          9,
          nonStringBlockedTarget,
        ),
        { code: BLOCKED_NETWORK_CODE },
      );
      assert.equal(blockedTargetCoercions, 0);
    } finally {
      await closeDgramSocket(udpSocket);
    }

    const esmHttp = await import("node:http");
    assertSynchronouslyBlocked(
      "ESM node:http request",
      () => esmHttp.request(externalHttpUrl, { lookup: localOnlyCanaryLookup }),
    );
    const esmHttp2 = await import("node:http2");
    assert.throws(
      () => esmHttp2.connect(`https://${externalHostname}/`),
      { code: BLOCKED_NETWORK_CODE },
    );

    // Numeric input makes a missing lookup guard local to the OS parser and
    // cannot trigger a DNS query, while still being a non-loopback target.
    assert.throws(
      () => dns.lookup("192.0.2.1", () => {}),
      { code: BLOCKED_NETWORK_CODE },
    );
    await assert.rejects(
      dnsPromises.lookup("192.0.2.1"),
      { code: BLOCKED_NETWORK_CODE },
    );

    // These loopback-looking queries must be rejected before c-ares can consult
    // whatever resolver configuration the host happens to use.
    assert.throws(
      () => dns.resolve4("localhost", () => {}),
      { code: BLOCKED_NETWORK_CODE },
    );
    await assert.rejects(
      dnsPromises.resolve4("localhost"),
      { code: BLOCKED_NETWORK_CODE },
    );
    assert.throws(
      () => dns.reverse("127.0.0.1", () => {}),
      { code: BLOCKED_NETWORK_CODE },
    );
    assert.throws(
      () => dns.lookupService("127.0.0.1", 80, () => {}),
      { code: BLOCKED_NETWORK_CODE },
    );
    await assert.rejects(
      dnsPromises.reverse("127.0.0.1"),
      { code: BLOCKED_NETWORK_CODE },
    );
    await assert.rejects(
      dnsPromises.lookupService("127.0.0.1", 80),
      { code: BLOCKED_NETWORK_CODE },
    );

    const callbackResolver = new dns.Resolver();
    assert.throws(
      () => callbackResolver.resolve4("localhost", () => {}),
      { code: BLOCKED_NETWORK_CODE },
    );

    const promiseResolver = new dnsPromises.Resolver();
    await assert.rejects(
      promiseResolver.resolve4("localhost"),
      { code: BLOCKED_NETWORK_CODE },
    );

    return {
      fetchBeforeReplacement,
      getReplacementCalls: () => replacementCalls,
      replacementCallsBeforeLoopback: replacementCalls,
    };
  } catch (error) {
    globalThis.fetch = fetchBeforeReplacement;
    throw error;
  }
}

async function verifyLoopbackAllowance(fetchState) {
  const webSocketSockets = new Set();
  const webSocketProtocolOffers = [];
  const httpServer = http.createServer((request, response) => {
    if (request.url === "/fetch-redirect-canary") {
      response.writeHead(302, {
        "connection": "close",
        "location": externalHttpUrl,
      });
      response.end();
      return;
    }
    response.writeHead(200, {
      "connection": "close",
      "content-type": "text/plain; charset=utf-8",
    });
    response.end("loopback-ok");
  });
  httpServer.on("upgrade", (request, socket) => {
    const key = request.headers["sec-websocket-key"];
    if (typeof key !== "string") {
      socket.destroy();
      return;
    }
    const accept = crypto
      .createHash("sha1")
      .update(`${key}258EAFA5-E914-47DA-95CA-C5AB0DC85B11`)
      .digest("base64");
    webSocketSockets.add(socket);
    socket.once("close", () => webSocketSockets.delete(socket));
    const offeredProtocols = request.headers["sec-websocket-protocol"];
    webSocketProtocolOffers.push(offeredProtocols);
    const selectedProtocol = typeof offeredProtocols === "string"
      ? offeredProtocols.split(",", 1)[0].trim()
      : null;
    socket.write(
      "HTTP/1.1 101 Switching Protocols\r\n" +
      "Upgrade: websocket\r\n" +
      "Connection: Upgrade\r\n" +
      `Sec-WebSocket-Accept: ${accept}\r\n` +
      (selectedProtocol === null
        ? "\r\n"
        : `Sec-WebSocket-Protocol: ${selectedProtocol}\r\n\r\n`),
    );
  });
  const httpPort = await listenOnLoopback(httpServer);
  const loopbackUrl = `http://127.0.0.1:${httpPort}/offline-canary`;

  try {
    const fetchResponse = await globalThis.fetch(loopbackUrl);
    assert.equal(fetchResponse.status, 200);
    assert.equal(await fetchResponse.text(), "loopback-ok");
    assert.equal(
      fetchState.getReplacementCalls(),
      fetchState.replacementCallsBeforeLoopback + 1,
      "A Next-style fetch replacement must remain callable for loopback URLs.",
    );

    const redirectUrl = `http://127.0.0.1:${httpPort}/fetch-redirect-canary`;
    await assert.rejects(
      globalThis.fetch(redirectUrl),
      (error) => {
        assert.ok(
          hasBlockedNetworkCode(error),
          `Redirect failure must retain ${BLOCKED_NETWORK_CODE}.`,
        );
        return true;
      },
    );

    let dispatcherReads = 0;
    let dispatcherCalls = 0;
    const replacementCallsBeforeDispatcher = fetchState.getReplacementCalls();
    await assert.rejects(
      globalThis.fetch(redirectUrl, {
        next: { revalidate: 0 },
        get dispatcher() {
          dispatcherReads += 1;
          return {
            dispatch() {
              dispatcherCalls += 1;
              throw new Error("Fetch dispatcher redirect canary was reached.");
            },
          };
        },
      }),
      { code: BLOCKED_NETWORK_CODE },
    );
    assert.equal(dispatcherReads, 1, "Fetch dispatcher must be snapshotted once.");
    assert.equal(dispatcherCalls, 0, "Fetch dispatcher must fail closed before dispatch.");
    assert.equal(fetchState.getReplacementCalls(), replacementCallsBeforeDispatcher);

    assert.equal(await requestText(loopbackUrl, false), "loopback-ok");
    assert.equal(await requestText(loopbackUrl, true), "loopback-ok");

    let httpUrlToStringCalls = 0;
    const overriddenHttpUrl = new URL(loopbackUrl);
    overriddenHttpUrl.toString = () => {
      httpUrlToStringCalls += 1;
      return externalHttpUrl;
    };
    assert.equal(await requestText(overriddenHttpUrl, true), "loopback-ok");
    assert.equal(httpUrlToStringCalls, 0, "HTTP must pass a native href snapshot.");

    let httpHostnameReads = 0;
    let httpLookupReads = 0;
    let httpLookupCalls = 0;
    const httpSnapshotOptions = {
      path: "/http-options-snapshot-canary",
      port: httpPort,
      get hostname() {
        httpHostnameReads += 1;
        return httpHostnameReads === 1 ? "127.0.0.1" : externalHostname;
      },
      get lookup() {
        httpLookupReads += 1;
        return (...args) => {
          httpLookupCalls += 1;
          const callback = args.findLast((argument) => typeof argument === "function");
          const error = new Error("HTTP lookup snapshot fallback was reached.");
          error.code = "ERR_OFFLINE_CANARY_LOOKUP_REACHED";
          process.nextTick(callback, error);
        };
      },
    };
    assert.equal(await requestOptionsText(httpSnapshotOptions), "loopback-ok");
    assert.equal(httpHostnameReads, 1, "HTTP must read hostname exactly once.");
    assert.equal(httpLookupReads, 1, "HTTP must read lookup exactly once.");
    assert.equal(httpLookupCalls, 0, "HTTP must retain its literal-IP snapshot.");

    for (const agent of [null, false, http.globalAgent]) {
      assert.equal(
        await requestOptionsText({
          agent,
          host: "127.0.0.1",
          path: "/http-agent-semantics-canary",
          port: httpPort,
        }),
        "loopback-ok",
      );
    }

    await verifySocketOptionSnapshot(
      "net.connect",
      httpPort,
      (options) => net.connect(options),
    );
    await verifySocketOptionSnapshot(
      "net.createConnection",
      httpPort,
      (options) => net.createConnection(options),
    );
    await verifySocketOptionSnapshot(
      "net.Socket.connect",
      httpPort,
      (options) => new net.Socket().connect(options),
    );

    const webSocketUrl = `ws://127.0.0.1:${httpPort}/websocket-canary`;
    assert.throws(() => WebSocket(webSocketUrl), TypeError);
    assert.throws(() => new WebSocket(), TypeError);
    const webSocketDescriptor = Object.getOwnPropertyDescriptor(globalThis, "WebSocket");
    assert.equal(
      webSocketDescriptor?.configurable,
      true,
      "The WebSocket guard must remain replaceable by isolated jsdom realms.",
    );
    let loopbackWebSocketToStringCalls = 0;
    const loopbackWebSocketUrl = new URL(webSocketUrl);
    loopbackWebSocketUrl.toString = () => {
      loopbackWebSocketToStringCalls += 1;
      return `wss://${externalHostname}/`;
    };
    class CanaryWebSocket extends WebSocket {}
    let setIteratorReads = 0;
    const setProtocols = new Set(["set-snapshot-protocol"]);
    Object.defineProperty(setProtocols, Symbol.iterator, {
      configurable: true,
      get() {
        setIteratorReads += 1;
        return Set.prototype.values;
      },
    });
    const webSocket = new CanaryWebSocket(loopbackWebSocketUrl, setProtocols);
    setProtocols.clear();
    setProtocols.add("mutated-set-protocol");
    assert.ok(webSocket instanceof CanaryWebSocket);
    assert.ok(webSocket instanceof WebSocket);
    assert.equal(webSocket.constructor, CanaryWebSocket);
    assert.equal(WebSocket.CONNECTING, 0);
    await waitForWebSocketOpen(webSocket);
    assert.equal(loopbackWebSocketToStringCalls, 0);
    assert.equal(webSocket.url, webSocketUrl);
    assert.equal(setIteratorReads, 1, "WebSocket must capture a Set iterator once.");
    assert.equal(webSocket.protocol, "set-snapshot-protocol");

    let arrayIteratorReads = 0;
    let arrayElementReads = 0;
    const arrayProtocols = [];
    Object.defineProperty(arrayProtocols, "0", {
      configurable: true,
      enumerable: true,
      get() {
        arrayElementReads += 1;
        return arrayElementReads === 1
          ? "array-snapshot-protocol"
          : "mutated-array-protocol";
      },
    });
    arrayProtocols.length = 1;
    Object.defineProperty(arrayProtocols, Symbol.iterator, {
      configurable: true,
      get() {
        arrayIteratorReads += 1;
        return Array.prototype[Symbol.iterator];
      },
    });
    const arrayWebSocket = new WebSocket(webSocketUrl, arrayProtocols);
    Object.defineProperty(arrayProtocols, "0", {
      configurable: true,
      enumerable: true,
      value: "mutated-array-protocol",
      writable: true,
    });
    await waitForWebSocketOpen(arrayWebSocket);
    assert.equal(arrayIteratorReads, 1, "WebSocket must capture an array iterator once.");
    assert.equal(arrayElementReads, 1, "WebSocket must capture each protocol once.");
    assert.equal(arrayWebSocket.protocol, "array-snapshot-protocol");
    assert.deepEqual(webSocketProtocolOffers, [
      "set-snapshot-protocol",
      "array-snapshot-protocol",
    ]);

    await new Promise((resolve, reject) => {
      const socket = net.createConnection({ host: "127.0.0.1", port: httpPort });
      socket.once("connect", () => {
        socket.end();
        resolve();
      });
      socket.once("error", reject);
    });
  } finally {
    for (const socket of webSocketSockets) {
      socket.destroy();
    }
    await closeServer(httpServer);
  }

  const http2Server = http2.createServer();
  http2Server.on("stream", (stream) => {
    stream.respond({ ":status": 200 });
    stream.end("http2-ok");
  });
  const http2Port = await listenOnLoopback(http2Server);
  const http2Clients = new Set();
  try {
    const loopbackAuthorityText = `http://127.0.0.1:${http2Port}/`;
    let authorityToStringCalls = 0;
    const loopbackAuthority = new URL(loopbackAuthorityText);
    loopbackAuthority.toString = () => {
      authorityToStringCalls += 1;
      return `https://${externalHostname}/`;
    };
    const client = http2.connect(loopbackAuthority);
    http2Clients.add(client);
    await once(client, "connect");
    assert.equal(authorityToStringCalls, 0, "HTTP/2 must pass a native href snapshot.");
    const request = client.request({ ":path": "/" });
    request.setEncoding("utf8");
    let responseBody = "";
    request.on("data", (chunk) => {
      responseBody += chunk;
    });
    request.end();
    await once(request, "end");
    assert.equal(responseBody, "http2-ok");
    client.destroy();
    http2Clients.delete(client);

    let authorityHostnameReads = 0;
    let http2LookupReads = 0;
    let http2LookupCalls = 0;
    const getterAuthority = {
      port: String(http2Port),
      protocol: "http:",
      get hostname() {
        authorityHostnameReads += 1;
        return authorityHostnameReads === 1 ? "127.0.0.1" : externalHostname;
      },
    };
    const getterOptions = {
      get lookup() {
        http2LookupReads += 1;
        return (...args) => {
          http2LookupCalls += 1;
          const callback = args.findLast((argument) => typeof argument === "function");
          const error = new Error("HTTP/2 lookup snapshot fallback was reached.");
          error.code = "ERR_OFFLINE_CANARY_LOOKUP_REACHED";
          process.nextTick(callback, error);
        };
      },
    };
    const getterClient = http2.connect(getterAuthority, getterOptions);
    http2Clients.add(getterClient);
    await once(getterClient, "connect");
    assert.equal(authorityHostnameReads, 1, "HTTP/2 must read hostname once.");
    assert.equal(http2LookupReads, 1, "HTTP/2 must read lookup once.");
    assert.equal(http2LookupCalls, 0, "HTTP/2 must retain its literal-IP snapshot.");
    getterClient.destroy();
    http2Clients.delete(getterClient);
  } finally {
    for (const client of http2Clients) {
      client.destroy();
    }
    await closeServer(http2Server);
  }

  const callbackLookup = await new Promise((resolve, reject) => {
    dns.lookup("localhost", { all: true }, (error, addresses) => {
      if (error) {
        reject(error);
      } else {
        resolve(addresses);
      }
    });
  });
  assert.ok(callbackLookup.length > 0);
  assert.ok(callbackLookup.every(({ address }) =>
    address === "::1" || address.startsWith("127.")
  ));
  assert.deepEqual(
    await dnsPromises.lookup("127.0.0.1"),
    { address: "127.0.0.1", family: 4 },
  );

  const udpServer = dgram.createSocket("udp4");
  const udpClient = dgram.createSocket({
    type: "udp4",
    lookup(hostname, options, callback) {
      const done = typeof options === "function" ? options : callback;
      process.nextTick(done, null, hostname, 4);
    },
  });
  const connectedUdpClient = dgram.createSocket("udp4");
  try {
    udpServer.bind(0, "127.0.0.1");
    await once(udpServer, "listening");
    const udpPort = udpServer.address().port;

    let received = once(udpServer, "message");
    await sendDgram((done) =>
      udpClient.send("udp-send-ok", udpPort, "127.0.0.1", done)
    );
    let [message] = await received;
    assert.equal(message.toString("utf8"), "udp-send-ok");

    await new Promise((resolve, reject) => {
      connectedUdpClient.once("error", reject);
      connectedUdpClient.connect(udpPort, "127.0.0.1", resolve);
    });
    received = once(udpServer, "message");
    await sendDgram((done) => connectedUdpClient.send("udp-connect-ok", done));
    [message] = await received;
    assert.equal(message.toString("utf8"), "udp-connect-ok");

    const sendtoPayload = Buffer.from("udp-sendto-ok");
    received = once(udpServer, "message");
    await sendDgram((done) => udpClient.sendto(
      sendtoPayload,
      0,
      sendtoPayload.length,
      udpPort,
      "127.0.0.1",
      done,
    ));
    [message] = await received;
    assert.equal(message.toString("utf8"), "udp-sendto-ok");
  } finally {
    await Promise.all([
      closeDgramSocket(connectedUdpClient),
      closeDgramSocket(udpClient),
      closeDgramSocket(udpServer),
    ]);
  }

  const rawSockets = new Set();
  const rawServer = net.createServer((socket) => {
    rawSockets.add(socket);
    socket.once("close", () => rawSockets.delete(socket));
  });
  const rawPort = await listenOnLoopback(rawServer);
  try {
    await verifySocketOptionSnapshot(
      "tls.connect",
      rawPort,
      (options) => tls.connect(options),
      { rejectUnauthorized: false },
    );

    await new Promise((resolve, reject) => {
      const client = tls.connect({
        host: "127.0.0.1",
        port: rawPort,
        rejectUnauthorized: false,
      });
      client.once("connect", () => {
        client.destroy();
        resolve();
      });
      client.once("error", reject);
    });

    for (const agent of [undefined, null, false, https.globalAgent]) {
      let loopbackHttpsRequest;
      assert.doesNotThrow(() => {
        loopbackHttpsRequest = https.request({
          agent,
          host: "127.0.0.1",
          port: rawPort,
          rejectUnauthorized: false,
        });
      });
      loopbackHttpsRequest.on("error", () => {});
      loopbackHttpsRequest.destroy();
    }
  } finally {
    for (const socket of rawSockets) {
      socket.destroy();
    }
    await closeServer(rawServer);
  }

  globalThis.fetch = fetchState.fetchBeforeReplacement;
}

async function main() {
  assert.equal(process.platform, "win32", "Phase 1 requires Windows.");
  assert.equal(process.arch, "x64", "Phase 1 requires Windows x64.");
  require("@next/swc-win32-x64-msvc");

  for (const prohibitedPackage of ["@img/sharp-wasm32", "@emnapi/runtime"]) {
    assert.throws(
      () => require.resolve(prohibitedPackage),
      { code: "MODULE_NOT_FOUND" },
      `${prohibitedPackage} must not remain as an extraneous package.`,
    );
  }

  const sharp = require("sharp");
  const png = await sharp({
    create: {
      background: { alpha: 1, b: 0, g: 0, r: 0 },
      channels: 4,
      height: 1,
      width: 1,
    },
  }).png().toBuffer();
  assert.deepEqual([...png.subarray(0, 8)], [137, 80, 78, 71, 13, 10, 26, 10]);

  const fetchState = await verifyExternalRejection();
  try {
    await verifyLoopbackAllowance(fetchState);
  } finally {
    globalThis.fetch = fetchState.fetchBeforeReplacement;
  }
  process.stdout.write("Native Node runtime and offline network guards verified.\n");
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
