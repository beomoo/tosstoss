"use strict";

const dns = require("node:dns");
const dnsPromises = require("node:dns/promises");
const dgram = require("node:dgram");
const http = require("node:http");
const http2 = require("node:http2");
const https = require("node:https");
const net = require("node:net");
const tls = require("node:tls");
const { syncBuiltinESMExports } = require("node:module");
const { URL: NativeURL } = require("node:url");

const BLOCKED_NETWORK_CODE = "ERR_OFFLINE_NON_LOOPBACK";
const fetchInitSnapshots = new WeakSet();
const guardedFunctions = new WeakMap();
const guardedFetches = new WeakSet();
const loopbackAddresses = new net.BlockList();
const nativeRequestUrlGetter = Object.getOwnPropertyDescriptor(
  globalThis.Request.prototype,
  "url",
).get;
const nativeUrlHrefGetter = Object.getOwnPropertyDescriptor(
  NativeURL.prototype,
  "href",
).get;

loopbackAddresses.addSubnet("127.0.0.0", 8, "ipv4");
loopbackAddresses.addAddress("::1", "ipv6");

function normalizedHostname(value) {
  if (typeof value !== "string") {
    return null;
  }

  let hostname = value.trim().toLowerCase();
  if (hostname.startsWith("[") && hostname.endsWith("]")) {
    hostname = hostname.slice(1, -1);
  }
  if (hostname.endsWith(".")) {
    hostname = hostname.slice(0, -1);
  }
  return hostname;
}

function isLoopbackHost(value) {
  const hostname = normalizedHostname(value);
  if (hostname === null) {
    return false;
  }
  if (hostname === "localhost") {
    return true;
  }

  const family = net.isIP(hostname);
  if (family === 4) {
    return loopbackAddresses.check(hostname, "ipv4");
  }
  if (family === 6) {
    return loopbackAddresses.check(hostname, "ipv6");
  }
  return false;
}

function isLiteralLoopbackAddress(value) {
  if (typeof value !== "string") {
    return false;
  }
  const family = net.isIP(value);
  if (family === 4) {
    return loopbackAddresses.check(value, "ipv4");
  }
  if (family === 6) {
    return loopbackAddresses.check(value, "ipv6");
  }
  return false;
}

function safeTargetDescription(value) {
  if (value === null) {
    return "null";
  }

  switch (typeof value) {
    case "string":
      return value;
    case "undefined":
      return "undefined";
    case "boolean":
      return value ? "true" : "false";
    case "number":
    case "bigint":
      return `${value}`;
    case "symbol":
      return "<symbol>";
    case "function":
      return "<function>";
    default:
      return "<object>";
  }
}

function blockedNetworkError(apiName, target) {
  const error = new Error(
    `Blocked non-loopback ${apiName} during offline Phase 1 checks: ${safeTargetDescription(target)}`,
  );
  error.code = BLOCKED_NETWORK_CODE;
  return error;
}

function assertLoopbackHost(value, apiName) {
  if (!isLoopbackHost(value)) {
    throw blockedNetworkError(apiName, value);
  }
}

function assertLiteralLoopbackAddress(value, apiName) {
  if (!isLiteralLoopbackAddress(value)) {
    throw blockedNetworkError(apiName, value);
  }
}

function blockedResolverError(apiName, target) {
  const error = new Error(
    `Blocked ${apiName} during offline Phase 1 checks because it may contact a configured DNS resolver: ${safeTargetDescription(target)}`,
  );
  error.code = BLOCKED_NETWORK_CODE;
  return error;
}

function lookupResultAddresses(result) {
  const entries = Array.isArray(result) ? result : [result];
  return entries
    .map((entry) => entry && typeof entry === "object" ? entry.address : entry)
    .filter((address) => typeof address === "string");
}

function createGuardedLookup(lookup, apiName, shouldValidateResult = () => true) {
  const guardedLookup = function guardedLookup(...args) {
    const callbackIndex = args.findLastIndex((argument) => typeof argument === "function");
    if (callbackIndex === -1) {
      return Reflect.apply(lookup, this, args);
    }

    const callback = args[callbackIndex];
    const guardedArgs = [...args];
    guardedArgs[callbackIndex] = function guardedLookupCallback(error, result, ...rest) {
      if (!error && shouldValidateResult(args[0])) {
        try {
          for (const address of lookupResultAddresses(result)) {
            assertLiteralLoopbackAddress(address, `${apiName}.lookup`);
          }
        } catch (lookupError) {
          return Reflect.apply(callback, this, [lookupError]);
        }
      }
      return Reflect.apply(callback, this, [error, result, ...rest]);
    };
    return Reflect.apply(lookup, this, guardedArgs);
  };
  return guardedLookup;
}

function guardSnapshotLookup(options, apiName, shouldValidateResult) {
  if (!options || typeof options !== "object" || typeof options.lookup !== "function") {
    return options;
  }
  options.lookup = createGuardedLookup(options.lookup, apiName, shouldValidateResult);
  return options;
}

function snapshotDataObject(value) {
  return value && typeof value === "object" ? { ...value } : value;
}

function assertNoCustomTransport(options, property, apiName) {
  if (
    options &&
    (typeof options === "object" || typeof options === "function") &&
    property in options
  ) {
    throw blockedNetworkError(apiName, `custom ${property}`);
  }
}

function nativeGetterSnapshot(getter, value) {
  if ((typeof value !== "object" && typeof value !== "function") || value === null) {
    return null;
  }
  try {
    return { matched: true, value: Reflect.apply(getter, value, []) };
  } catch {
    return null;
  }
}

function markGuarded(wrapper, apiName) {
  guardedFunctions.set(wrapper, apiName);
  return wrapper;
}

function snapshotFetchInput(input) {
  if (typeof input === "string") {
    return { implementationInput: input, url: input };
  }

  const requestUrl = nativeGetterSnapshot(nativeRequestUrlGetter, input);
  if (requestUrl !== null) {
    // Request's native internal URL is immutable. Preserve the Request itself
    // so method, headers, and body semantics remain intact.
    return { implementationInput: input, url: requestUrl.value };
  }

  const urlHref = nativeGetterSnapshot(nativeUrlHrefGetter, input);
  if (urlHref !== null) {
    // Pass the captured href rather than a mutable URL object or its toString.
    return { implementationInput: urlHref.value, url: urlHref.value };
  }

  // Fetch coerces non-Request/URL inputs. Coerce exactly once and use that
  // immutable value for both policy inspection and the implementation call.
  const coerced = String(input);
  return { implementationInput: coerced, url: coerced };
}

function snapshotFetchInit(init) {
  if ((typeof init === "object" && init !== null) || typeof init === "function") {
    if (fetchInitSnapshots.has(init)) {
      assertNoCustomTransport(init, "dispatcher", "fetch");
      return init;
    }
    const snapshot = { ...init };
    assertNoCustomTransport(snapshot, "dispatcher", "fetch");
    fetchInitSnapshots.add(snapshot);
    return snapshot;
  }
  return init;
}

function parsedHttpUrl(value) {
  try {
    return new NativeURL(value);
  } catch {
    return null;
  }
}

function assertFetchTarget(url) {
  const parsed = parsedHttpUrl(url);
  if (
    parsed !== null &&
    (parsed.protocol === "http:" || parsed.protocol === "https:") &&
    !isLoopbackHost(parsed.hostname)
  ) {
    throw blockedNetworkError("fetch", parsed.origin);
  }
}

function createGuardedFetch(implementation) {
  const guardedFetch = markGuarded(function guardedFetch(input, init) {
    let snapshot;
    let initSnapshot;
    try {
      snapshot = snapshotFetchInput(input);
      initSnapshot = snapshotFetchInit(init);
      assertFetchTarget(snapshot.url);
    } catch (error) {
      return Promise.reject(error);
    }

    try {
      return Reflect.apply(implementation, this, [
        snapshot.implementationInput,
        initSnapshot,
      ]);
    } catch (error) {
      return Promise.reject(error);
    }
  }, "fetch");
  guardedFetches.add(guardedFetch);
  return guardedFetch;
}

const initialFetch = globalThis.fetch;
if (typeof initialFetch !== "function") {
  throw new Error("The Node.js runtime does not expose global fetch.");
}

let currentGuardedFetch = createGuardedFetch(initialFetch);
const fetchDescriptor = Object.getOwnPropertyDescriptor(globalThis, "fetch");
Object.defineProperty(globalThis, "fetch", {
  configurable: false,
  enumerable: fetchDescriptor ? fetchDescriptor.enumerable : true,
  get() {
    return currentGuardedFetch;
  },
  set(replacement) {
    if (typeof replacement !== "function") {
      throw new TypeError("Node.js fetch can only be replaced with another function.");
    }

    // Next.js captures the current fetch, wraps it, and assigns the wrapper back.
    // A fresh guard generation lets that wrapper call its captured predecessor
    // without recursing through a mutable delegate.
    currentGuardedFetch = guardedFetches.has(replacement)
      ? replacement
      : createGuardedFetch(replacement);
  },
});

function snapshotStringUrlInput(input) {
  if (typeof input === "string") {
    return input;
  }
  const urlHref = nativeGetterSnapshot(nativeUrlHrefGetter, input);
  return urlHref === null ? String(input) : urlHref.value;
}

function assertWebSocketTarget(url) {
  const parsed = parsedHttpUrl(url);
  if (parsed !== null && parsed.hostname && !isLoopbackHost(parsed.hostname)) {
    throw blockedNetworkError("WebSocket", parsed.origin);
  }
}

function snapshotWebSocketOptions(protocols) {
  if (
    protocols === null ||
    (typeof protocols !== "object" && typeof protocols !== "function")
  ) {
    return protocols;
  }

  // WebSocket's second argument is a DOMString, a sequence of DOMStrings, or
  // WebSocketInit. Capture an iterable and each of its values once, then hand
  // the native constructor the same immutable sequence that was inspected.
  const iteratorMethod = protocols[Symbol.iterator];
  if (typeof iteratorMethod === "function") {
    const iterator = Reflect.apply(iteratorMethod, protocols, []);
    const iterable = {
      [Symbol.iterator]() {
        return iterator;
      },
    };
    return Object.freeze(Array.from(iterable, (protocol) => {
      if (typeof protocol === "symbol") {
        throw new TypeError("A WebSocket protocol symbol cannot be converted to a DOMString.");
      }
      return String(protocol);
    }));
  }

  const snapshot = { ...protocols };
  assertNoCustomTransport(snapshot, "dispatcher", "WebSocket");
  return snapshot;
}

const initialWebSocket = globalThis.WebSocket;
if (typeof initialWebSocket !== "function") {
  throw new Error("The Node.js runtime does not expose global WebSocket.");
}

const guardedWebSocket = markGuarded(new Proxy(initialWebSocket, {
  construct(target, args, newTarget) {
    const snapshot = [...args];
    if (snapshot.length > 0) {
      snapshot[0] = snapshotStringUrlInput(snapshot[0]);
      assertWebSocketTarget(snapshot[0]);
    }
    if (snapshot.length > 1) {
      snapshot[1] = snapshotWebSocketOptions(snapshot[1]);
    }
    return Reflect.construct(
      target,
      snapshot,
      newTarget === guardedWebSocket ? target : newTarget,
    );
  },
}), "WebSocket");
Object.defineProperty(initialWebSocket.prototype, "constructor", {
  configurable: true,
  enumerable: false,
  value: guardedWebSocket,
  writable: true,
});
const webSocketDescriptor = Object.getOwnPropertyDescriptor(globalThis, "WebSocket");
Object.defineProperty(globalThis, "WebSocket", {
  // Vitest/jsdom installs its realm-specific WebSocket with defineProperty.
  // Keep the native descriptor replaceable; that implementation still reaches
  // the guarded HTTP/net layers for any actual connection.
  configurable: webSocketDescriptor ? webSocketDescriptor.configurable : true,
  enumerable: webSocketDescriptor ? webSocketDescriptor.enumerable : false,
  value: guardedWebSocket,
  writable: webSocketDescriptor ? webSocketDescriptor.writable : true,
});

function snapshotHttpArgs(args) {
  const snapshot = [...args];
  const urlHref = nativeGetterSnapshot(nativeUrlHrefGetter, snapshot[0]);
  if (urlHref !== null) {
    snapshot[0] = urlHref.value;
  }

  if (typeof snapshot[0] === "string") {
    if (snapshot[1] && typeof snapshot[1] === "object") {
      snapshot[1] = snapshotDataObject(snapshot[1]);
    }
  } else if (snapshot[0] && typeof snapshot[0] === "object") {
    snapshot[0] = snapshotDataObject(snapshot[0]);
  }
  return snapshot;
}

function optionsFromHttpArgs(args) {
  if (typeof args[0] === "string") {
    return args[1] && typeof args[1] === "object" ? args[1] : null;
  }
  return args[0] && typeof args[0] === "object" ? args[0] : null;
}

function urlFromHttpArgs(args) {
  return typeof args[0] === "string" ? parsedHttpUrl(args[0]) : null;
}

function assertHttpTarget(args, apiName) {
  const options = optionsFromHttpArgs(args);
  if (options && options.socketPath !== undefined && options.socketPath !== null) {
    return;
  }

  const parsed = urlFromHttpArgs(args);
  const hostname = options && options.hostname !== undefined
    ? options.hostname
    : options && options.host !== undefined
      ? options.host
      : parsed
        ? parsed.hostname
        : "localhost";
  assertLoopbackHost(hostname, apiName);
}

function guardHttpSnapshotLookup(args, apiName) {
  guardSnapshotLookup(optionsFromHttpArgs(args), apiName);
}

function assertHttpTransport(args, moduleObject, apiName) {
  const options = optionsFromHttpArgs(args);
  if (!options) {
    return;
  }

  assertNoCustomTransport(options, "createConnection", apiName);
  if (!("agent" in options)) {
    return;
  }

  const agent = options.agent;
  if (
    agent === undefined ||
    agent === null ||
    agent === false ||
    agent === moduleObject.globalAgent
  ) {
    return;
  }
  throw blockedNetworkError(apiName, "custom agent");
}

function installHttpGuard(moduleObject, methodName, apiName) {
  const original = moduleObject[methodName];
  const guarded = markGuarded(function guardedHttpCall(...args) {
    const snapshot = snapshotHttpArgs(args);
    assertHttpTarget(snapshot, apiName);
    assertHttpTransport(snapshot, moduleObject, apiName);
    guardHttpSnapshotLookup(snapshot, apiName);
    return Reflect.apply(original, this, snapshot);
  }, apiName);
  moduleObject[methodName] = guarded;
}

installHttpGuard(http, "request", "http.request");
installHttpGuard(http, "get", "http.get");
installHttpGuard(https, "request", "https.request");
installHttpGuard(https, "get", "https.get");

function snapshotHttp2Args(args) {
  const snapshot = [...args];
  const authorityHref = nativeGetterSnapshot(nativeUrlHrefGetter, snapshot[0]);
  if (authorityHref !== null) {
    snapshot[0] = authorityHref.value;
  } else if (snapshot[0] && typeof snapshot[0] === "object") {
    snapshot[0] = snapshotDataObject(snapshot[0]);
  }
  if (snapshot[1] && typeof snapshot[1] === "object") {
    snapshot[1] = snapshotDataObject(snapshot[1]);
  }
  return snapshot;
}

function assertHttp2Target(args) {
  const authority = args[0];
  const options = args[1] && typeof args[1] === "object" ? args[1] : null;
  if (options && typeof options.createConnection === "function") {
    throw blockedNetworkError("http2.connect", "custom createConnection");
  }

  if (typeof authority === "string") {
    const parsed = parsedHttpUrl(authority);
    if (parsed !== null && parsed.hostname) {
      assertLoopbackHost(parsed.hostname, "http2.connect");
    }
    return;
  }

  if (authority && typeof authority === "object") {
    const hostname = authority.hostname !== undefined && authority.hostname !== ""
      ? authority.hostname
      : authority.host !== undefined && authority.host !== ""
        ? authority.host
        : "localhost";
    assertLoopbackHost(hostname, "http2.connect");
  }
}

const originalHttp2Connect = http2.connect;
http2.connect = markGuarded(function guardedHttp2Connect(...args) {
  const snapshot = snapshotHttp2Args(args);
  assertHttp2Target(snapshot);
  const options = snapshot[1] && typeof snapshot[1] === "object"
    ? snapshot[1]
    : null;
  guardSnapshotLookup(options, "http2.connect");
  return Reflect.apply(originalHttp2Connect, this, snapshot);
}, "http2.connect");

function snapshotSocketArgs(args) {
  let current = [...args];
  while (Array.isArray(current[0])) {
    current = [...current[0]];
  }
  return current.map((argument) => snapshotDataObject(argument));
}

function socketOptionSnapshots(args) {
  return args.filter((argument) => argument && typeof argument === "object");
}

function assertSocketTargets(args, apiName, allowExistingSocket) {
  const first = args[0];
  const options = socketOptionSnapshots(args);

  if (
    options.some((option) => option.path !== undefined && option.path !== null) ||
    (
      allowExistingSocket &&
      options.some((option) => option.socket !== undefined && option.socket !== null)
    )
  ) {
    return;
  }

  const tcpPortSignature = typeof first === "number" ||
    (typeof first === "string" && Number(first) >= 0);
  if (typeof first === "string" && !tcpPortSignature) {
    // A non-numeric string first argument is an IPC pipe path.
    return;
  }

  const hostnames = [];
  if (tcpPortSignature && typeof args[1] === "string") {
    hostnames.push(args[1]);
  }
  for (const option of options) {
    if (option.hostname !== undefined) {
      hostnames.push(option.hostname);
    }
    if (option.host !== undefined) {
      hostnames.push(option.host);
    }
  }
  if (hostnames.length === 0) {
    hostnames.push("localhost");
  }
  for (const hostname of hostnames) {
    assertLoopbackHost(hostname, apiName);
  }
}

function guardSocketSnapshotLookups(args, apiName) {
  for (const options of socketOptionSnapshots(args)) {
    guardSnapshotLookup(options, apiName);
  }
}

function installSocketGuard(target, methodName, apiName, allowExistingSocket = false) {
  const original = target[methodName];
  const guarded = markGuarded(function guardedSocketConnect(...args) {
    const snapshot = snapshotSocketArgs(args);
    assertSocketTargets(snapshot, apiName, allowExistingSocket);
    guardSocketSnapshotLookups(snapshot, apiName);
    return Reflect.apply(original, this, snapshot);
  }, apiName);
  target[methodName] = guarded;
}

installSocketGuard(net, "connect", "net.connect");
installSocketGuard(net, "createConnection", "net.createConnection");
installSocketGuard(net.Socket.prototype, "connect", "net.Socket.connect");
installSocketGuard(tls, "connect", "tls.connect", true);

const boundDgramSockets = new WeakSet();
const safeDgramConnections = new WeakSet();

function guardDgramSocketOptions(options, apiName) {
  const snapshot = snapshotDataObject(options);
  return guardSnapshotLookup(snapshot, apiName, isLiteralLoopbackAddress);
}

const originalDgramSocket = dgram.Socket;
const GuardedDgramSocket = markGuarded(function GuardedDgramSocket(type, listener) {
  const guardedType = guardDgramSocketOptions(type, "dgram.Socket");
  const target = !new.target || new.target === GuardedDgramSocket
    ? originalDgramSocket
    : new.target;
  return Reflect.construct(originalDgramSocket, [guardedType, listener], target);
}, "dgram.Socket");
Object.setPrototypeOf(GuardedDgramSocket, originalDgramSocket);
GuardedDgramSocket.prototype = originalDgramSocket.prototype;
dgram.Socket = GuardedDgramSocket;

const originalDgramCreateSocket = dgram.createSocket;
dgram.createSocket = markGuarded(function guardedDgramCreateSocket(type, listener) {
  return Reflect.apply(originalDgramCreateSocket, this, [
    guardDgramSocketOptions(type, "dgram.createSocket"),
    listener,
  ]);
}, "dgram.createSocket");

const originalDgramBind = dgram.Socket.prototype.bind;
dgram.Socket.prototype.bind = markGuarded(function guardedDgramBind(...args) {
  boundDgramSockets.add(this);
  try {
    return Reflect.apply(originalDgramBind, this, args);
  } catch (error) {
    boundDgramSockets.delete(this);
    throw error;
  }
}, "dgram.bind");

function ensureDgramLoopbackBind(socket, address) {
  if (boundDgramSockets.has(socket)) {
    return;
  }
  const bindAddress = net.isIP(address) === 6 ? "::1" : "127.0.0.1";
  boundDgramSockets.add(socket);
  try {
    Reflect.apply(originalDgramBind, socket, [{
      address: bindAddress,
      exclusive: true,
      port: 0,
    }]);
  } catch (error) {
    boundDgramSockets.delete(socket);
    throw error;
  }
}

const originalDgramConnect = dgram.Socket.prototype.connect;
dgram.Socket.prototype.connect = markGuarded(function guardedDgramConnect(...args) {
  const address = typeof args[1] === "string" ? args[1] : null;
  assertLiteralLoopbackAddress(address, "dgram.connect");
  ensureDgramLoopbackBind(this, address);
  const markConnectionSafe = () => safeDgramConnections.add(this);
  this.once("connect", markConnectionSafe);
  try {
    return Reflect.apply(originalDgramConnect, this, args);
  } catch (error) {
    this.off("connect", markConnectionSafe);
    throw error;
  }
}, "dgram.connect");

const originalDgramDisconnect = dgram.Socket.prototype.disconnect;
dgram.Socket.prototype.disconnect = markGuarded(function guardedDgramDisconnect(...args) {
  try {
    return Reflect.apply(originalDgramDisconnect, this, args);
  } finally {
    safeDgramConnections.delete(this);
  }
}, "dgram.disconnect");

function dgramSendAddress(args) {
  if (typeof args[4] === "string") {
    return args[4];
  }
  if (typeof args[2] === "string") {
    return args[2];
  }
  return null;
}

const originalDgramSend = dgram.Socket.prototype.send;
dgram.Socket.prototype.send = markGuarded(function guardedDgramSend(...args) {
  const address = dgramSendAddress(args);
  if (address !== null) {
    assertLiteralLoopbackAddress(address, "dgram.send");
    ensureDgramLoopbackBind(this, address);
  } else if (!safeDgramConnections.has(this)) {
    throw blockedNetworkError("dgram.send", "implicit destination");
  }
  return Reflect.apply(originalDgramSend, this, args);
}, "dgram.send");

const originalDgramSendto = dgram.Socket.prototype.sendto;
dgram.Socket.prototype.sendto = markGuarded(function guardedDgramSendto(...args) {
  assertLiteralLoopbackAddress(args[4], "dgram.sendto");
  return Reflect.apply(originalDgramSendto, this, args);
}, "dgram.sendto");

function dnsMethodNames(target) {
  return Object.getOwnPropertyNames(target).filter((name) =>
    name === "lookup" ||
    name === "lookupService" ||
    name === "reverse" ||
    name.startsWith("resolve")
  );
}

function installDnsCallbackGuards(target, prefix) {
  for (const methodName of dnsMethodNames(target)) {
    if (methodName === "constructor" || typeof target[methodName] !== "function") {
      continue;
    }
    const apiName = `${prefix}.${methodName}`;
    const original = target[methodName];
    target[methodName] = markGuarded(function guardedDnsCallback(...args) {
      if (methodName !== "lookup") {
        throw blockedResolverError(apiName, args[0]);
      }
      assertLoopbackHost(args[0], apiName);
      return Reflect.apply(original, this, args);
    }, apiName);
  }
}

function installDnsPromiseGuards(target, prefix) {
  for (const methodName of dnsMethodNames(target)) {
    if (methodName === "constructor" || typeof target[methodName] !== "function") {
      continue;
    }
    const apiName = `${prefix}.${methodName}`;
    const original = target[methodName];
    target[methodName] = markGuarded(function guardedDnsPromise(...args) {
      try {
        if (methodName !== "lookup") {
          throw blockedResolverError(apiName, args[0]);
        }
        assertLoopbackHost(args[0], apiName);
      } catch (error) {
        return Promise.reject(error);
      }
      return Reflect.apply(original, this, args);
    }, apiName);
  }
}

installDnsCallbackGuards(dns, "dns");
installDnsCallbackGuards(dns.Resolver.prototype, "dns.Resolver");
installDnsPromiseGuards(dnsPromises, "dns.promises");
installDnsPromiseGuards(dnsPromises.Resolver.prototype, "dns.promises.Resolver");

// Keep named `node:` ESM imports aligned with the patched CommonJS exports.
syncBuiltinESMExports();

function assertGuardInstalled(target, methodName) {
  if (!guardedFunctions.has(target[methodName])) {
    throw new Error(`Offline guard failed to install for ${methodName}.`);
  }
}

// Load-time self-canaries are intentionally classifier/installation-only. The
// runtime preflight performs behavioral canaries without real outbound targets.
if (
  !isLoopbackHost("localhost") ||
  !isLoopbackHost("127.0.0.1") ||
  !isLoopbackHost("::1") ||
  isLoopbackHost("phase-01-network-canary.example.invalid")
) {
  throw new Error("Offline guard loopback classifier self-canary failed.");
}
assertGuardInstalled(http, "request");
assertGuardInstalled(https, "get");
assertGuardInstalled(http2, "connect");
assertGuardInstalled(net.Socket.prototype, "connect");
assertGuardInstalled(tls, "connect");
assertGuardInstalled(dgram, "createSocket");
assertGuardInstalled(dgram.Socket.prototype, "connect");
assertGuardInstalled(dgram.Socket.prototype, "send");
assertGuardInstalled(dns, "lookup");
assertGuardInstalled(dnsPromises, "resolve4");
if (!guardedFunctions.has(globalThis.WebSocket)) {
  throw new Error("Offline guard failed to install for WebSocket.");
}

module.exports = Object.freeze({
  BLOCKED_NETWORK_CODE,
  isLoopbackHost,
});
