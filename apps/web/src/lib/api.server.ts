import "server-only";

import type {
  CompanyOverviewResponse,
  DataQualityResponse,
  HealthResponse,
  SecuritiesResponse,
  SystemStatusResponse,
} from "@/types/api.contract";

const CONTRACT_VERSION = "0.1.0";
const DATA_MODE = "FIXTURE";
const DEFAULT_BACKEND_ORIGIN = "http://127.0.0.1:8000";
const REQUEST_TIMEOUT_MS = 4_000;
const ISSUER_ID_PATTERN = /^[A-Za-z0-9_-]{1,100}$/;

export class BackendRequestError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string) {
    super("요청한 fixture 데이터를 안전하게 불러오지 못했습니다.");
    this.name = "BackendRequestError";
    this.status = status;
    this.code = code;
  }
}

function getBackendOrigin(): URL {
  const configuredOrigin = process.env["DASHBOARD_API_BASE_URL"] ?? DEFAULT_BACKEND_ORIGIN;
  let parsed: URL;
  try {
    parsed = new URL(configuredOrigin);
  } catch {
    throw new BackendRequestError(503, "BACKEND_ORIGIN_REJECTED");
  }
  if (
    parsed.protocol !== "http:" ||
    parsed.hostname !== "127.0.0.1" ||
    parsed.username.length > 0 ||
    parsed.password.length > 0 ||
    parsed.search.length > 0 ||
    parsed.hash.length > 0 ||
    (parsed.pathname !== "/" && parsed.pathname !== "")
  ) {
    throw new BackendRequestError(503, "BACKEND_ORIGIN_REJECTED");
  }
  return parsed;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function errorCodeFromPayload(payload: unknown): string {
  if (!isRecord(payload) || !isRecord(payload["error"])) {
    return "BACKEND_REQUEST_FAILED";
  }
  const code = payload["error"]["code"];
  return typeof code === "string" && /^[A-Z0-9_]{1,80}$/.test(code)
    ? code
    : "BACKEND_REQUEST_FAILED";
}

function assertFixtureContract(payload: unknown): void {
  if (!isRecord(payload)) {
    throw new BackendRequestError(502, "INVALID_BACKEND_RESPONSE");
  }
  if (payload["contract_version"] !== CONTRACT_VERSION || payload["data_mode"] !== DATA_MODE) {
    throw new BackendRequestError(502, "INCOMPATIBLE_BACKEND_CONTRACT");
  }
}

function assertServerOnlyRuntimeBoundary(): void {
  const sentinel = process.env["PHASE1_SERVER_ONLY_SENTINEL"];
  if (sentinel === "") {
    throw new BackendRequestError(503, "SERVER_RUNTIME_CONFIGURATION_INVALID");
  }
}

async function fetchFixtureJson<T>(path: string): Promise<T> {
  assertServerOnlyRuntimeBoundary();
  const url = new URL(path, getBackendOrigin());
  let response: Response;
  try {
    response = await fetch(url, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch {
    throw new BackendRequestError(503, "BACKEND_UNAVAILABLE");
  }

  let payload: unknown;
  const contentType = response.headers.get("content-type")?.toLowerCase() ?? "";
  if (!contentType.startsWith("application/json")) {
    throw new BackendRequestError(502, "INVALID_BACKEND_RESPONSE");
  }
  try {
    payload = await response.json();
  } catch {
    throw new BackendRequestError(502, "INVALID_BACKEND_RESPONSE");
  }

  if (!response.ok) {
    throw new BackendRequestError(response.status, errorCodeFromPayload(payload));
  }
  assertFixtureContract(payload);
  return payload as T;
}

function issuerPath(issuerId: string): string {
  if (!ISSUER_ID_PATTERN.test(issuerId)) {
    throw new BackendRequestError(404, "ISSUER_NOT_FOUND");
  }
  return encodeURIComponent(issuerId);
}

export function getHealth(): Promise<HealthResponse> {
  return fetchFixtureJson<HealthResponse>("/health");
}

export function getSystemStatus(): Promise<SystemStatusResponse> {
  return fetchFixtureJson<SystemStatusResponse>("/api/v1/system/status");
}

export function getSecurities(): Promise<SecuritiesResponse> {
  return fetchFixtureJson<SecuritiesResponse>("/api/v1/securities");
}

export function getCompanyOverview(issuerId: string): Promise<CompanyOverviewResponse> {
  return fetchFixtureJson<CompanyOverviewResponse>(
    `/api/v1/companies/${issuerPath(issuerId)}/overview`,
  );
}

export function getCompanyDataQuality(issuerId: string): Promise<DataQualityResponse> {
  return fetchFixtureJson<DataQualityResponse>(
    `/api/v1/companies/${issuerPath(issuerId)}/data-quality`,
  );
}
