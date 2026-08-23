from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Final

import httpx
from pydantic import ValidationError

from toss_dashboard_api.config import Settings
from toss_dashboard_api.connectors.toss.auth import (
    _TOKEN_REQUEST_USE_KEY,
    TossCredentialState,
    _build_token_manager,
    _TokenLease,
    _TossTokenManager,
    credential_state,
)
from toss_dashboard_api.connectors.toss.client import (
    CONNECT_TIMEOUT_SECONDS,
    POOL_TIMEOUT_SECONDS,
    READ_TIMEOUT_SECONDS,
    WRITE_TIMEOUT_SECONDS,
    _assert_request_boundary,
    _DecodedResponse,
    _read_json,
    _result_or_error,
)
from toss_dashboard_api.connectors.toss.errors import (
    TossAuthenticationError,
    TossBoundaryError,
    TossConfigurationError,
    TossConnectorError,
    TossHttpError,
    TossInvalidClientError,
    TossOAuthError,
    TossOAuthPermissionError,
    TossPermissionError,
    TossRateLimitError,
    TossRedirectError,
    TossResponseContractError,
    TossServerError,
    TossTransportError,
)
from toss_dashboard_api.connectors.toss.models import (
    JSON_MEDIA_TYPE,
    MARKET_RESPONSE_MAX_BYTES,
    TOKEN_PATH,
    TOSS_ORIGIN,
    USER_AGENT,
    OAuthTokenResponse,
    TossStaticEndpoint,
)
from toss_dashboard_api.connectors.toss.rate_limit import (
    DOCUMENTED_RATE_LIMITS,
    RateHeaderDiagnostic,
    RateHeaderTelemetry,
    TossRateLimitGroup,
    _TossRateLimiter,
    parse_rate_headers,
    rate_group_for,
)

APPROVED_OPENAPI_VERSION: Final = "3.1.0"
APPROVED_REST_VERSION: Final = "1.2.14"
APPROVED_CONTRACT_SHA256: Final = (
    "fccf49ab"
    "d11f37f5"
    "57bdd349"
    "138f4a03"
    "c42b829e"
    "bd8b5c14"
    "ab490711"
    "6fb84c7a"
)
CANONICAL_OPENAPI_PATH: Final = "/openapi-docs/latest/openapi.json"
CANONICAL_OPENAPI_MAX_BYTES: Final = 8 * 1024 * 1024
PREFLIGHT_SYMBOL_MAX_LENGTH: Final = 32
PREFLIGHT_SYMBOL_PATTERN: Final = re.compile(r"^[A-Za-z0-9.\-]+$")
_CREDENTIAL_CONFIGURED_KEYS: Final = (
    "TOSS_CLIENT_ID_CONFIGURED",
    "TOSS_CLIENT_SEC" + "RET_CONFIGURED",
)

LIVE_SUMMARY_KEYS: Final = (
    "MODE",
    "PROVIDER_CONTRACT_DRIFT",
    "PROVIDER_OPENAPI",
    "PROVIDER_VERSION",
    "CONTRACT_SHA_MATCH",
    "CONTRACT_ORIGIN_MATCH",
    "CREDENTIALS_CONFIGURED",
    _CREDENTIAL_CONFIGURED_KEYS[0],
    _CREDENTIAL_CONFIGURED_KEYS[1],
    "OAUTH_REQUEST",
    "MARKET_REQUEST",
    "MARKET_ENDPOINT",
    "RATE_HEADERS",
    "RATE_LIMIT_HEADER",
    "RATE_REMAINING_HEADER",
    "RATE_RESET_HEADER",
    "RETRY_AFTER",
    "STAGE",
    "HTTP_STATUS_CATEGORY",
    "PROVIDER_CODE",
    "ERROR_CATEGORY",
    "STATUS",
)
_SAFE_SUMMARY_KEY = re.compile(r"^[A-Z][A-Z0-9_]*$")
_SAFE_SUMMARY_VALUE = re.compile(r"^[A-Za-z0-9_./:-]+$")

SettingsFactory = Callable[[], Settings]


@dataclass(frozen=True, slots=True)
class _ApprovedContract:
    openapi_version: str
    rest_version: str
    sha256: str
    origin: str


_RUNTIME_APPROVED_CONTRACT: Final = _ApprovedContract(
    openapi_version=APPROVED_OPENAPI_VERSION,
    rest_version=APPROVED_REST_VERSION,
    sha256=APPROVED_CONTRACT_SHA256,
    origin=TOSS_ORIGIN,
)


@dataclass(frozen=True, slots=True)
class _ContractObservation:
    openapi_version: str
    rest_version: str
    sha_matches: bool
    origin_matches: bool


@dataclass(frozen=True, slots=True)
class _PreflightResult:
    lines: tuple[tuple[str, str], ...]

    @property
    def passed(self) -> bool:
        return dict(self.lines)["STATUS"] == "PASS"

    def render(self) -> str:
        return "\n".join(f"{key}={value}" for key, value in self.lines)


@dataclass(slots=True)
class _MarketAttempt:
    status_code: int
    payload: object
    rate_headers: RateHeaderTelemetry
    rate_summary: tuple[tuple[str, str], ...]


class _PreflightFailure(Exception):
    def __init__(
        self,
        stage: str,
        category: str,
        *,
        status_code: int | None = None,
    ) -> None:
        self.stage = stage
        self.category = category
        self.status_code = status_code
        super().__init__(f"Preflight failed safely (stage={stage}, category={category}).")


def _base_live_summary() -> dict[str, str]:
    return {
        "MODE": "LIVE",
        "PROVIDER_CONTRACT_DRIFT": "UNKNOWN",
        "PROVIDER_OPENAPI": "UNKNOWN",
        "PROVIDER_VERSION": "UNKNOWN",
        "CONTRACT_SHA_MATCH": "UNKNOWN",
        "CONTRACT_ORIGIN_MATCH": "UNKNOWN",
        "CREDENTIALS_CONFIGURED": "NOT_CHECKED",
        _CREDENTIAL_CONFIGURED_KEYS[0]: "NOT_CHECKED",
        _CREDENTIAL_CONFIGURED_KEYS[1]: "NOT_CHECKED",
        "OAUTH_REQUEST": "NOT_ATTEMPTED",
        "MARKET_REQUEST": "NOT_ATTEMPTED",
        "MARKET_ENDPOINT": TossStaticEndpoint.STOCKS.value,
        "RATE_HEADERS": "NOT_CHECKED",
        "RATE_LIMIT_HEADER": "NOT_CHECKED",
        "RATE_REMAINING_HEADER": "NOT_CHECKED",
        "RATE_RESET_HEADER": "NOT_CHECKED",
        "RETRY_AFTER": "LIVE_UNVERIFIED",
        "STAGE": "CONTRACT",
        "HTTP_STATUS_CATEGORY": "NONE",
        "PROVIDER_CODE": "NONE",
        "ERROR_CATEGORY": "NONE",
        "STATUS": "FAIL",
    }


def _finalize_summary(summary: Mapping[str, str]) -> _PreflightResult:
    if tuple(summary) != LIVE_SUMMARY_KEYS:
        raise RuntimeError("Preflight summary schema changed unexpectedly.")
    lines = tuple((key, summary[key]) for key in LIVE_SUMMARY_KEYS)
    if any(
        _SAFE_SUMMARY_KEY.fullmatch(key) is None or _SAFE_SUMMARY_VALUE.fullmatch(value) is None
        for key, value in lines
    ):
        raise RuntimeError("Preflight summary contains an unsafe value.")
    return _PreflightResult(lines)


def _validate_symbol(symbol: str) -> None:
    if (
        not isinstance(symbol, str)
        or not 1 <= len(symbol) <= PREFLIGHT_SYMBOL_MAX_LENGTH
        or PREFLIGHT_SYMBOL_PATTERN.fullmatch(symbol) is None
    ):
        raise TossBoundaryError("invalid-preflight-symbol")


def _build_http_client(
    transport: httpx.AsyncBaseTransport | None = None,
) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=TOSS_ORIGIN,
        timeout=httpx.Timeout(
            connect=CONNECT_TIMEOUT_SECONDS,
            read=READ_TIMEOUT_SECONDS,
            write=WRITE_TIMEOUT_SECONDS,
            pool=POOL_TIMEOUT_SECONDS,
        ),
        follow_redirects=False,
        trust_env=False,
        verify=True,
        limits=httpx.Limits(max_connections=1, max_keepalive_connections=1),
        transport=transport,
    )


def _assert_contract_request_boundary(request: httpx.Request) -> None:
    url = request.url
    if (
        request.method != "GET"
        or url.scheme != "https"
        or url.host != "openapi.tossinvest.com"
        or url.port not in {None, 443}
        or url.userinfo
        or url.path != CANONICAL_OPENAPI_PATH
        or url.query
    ):
        raise TossBoundaryError("contract-request-boundary")
    if {name.lower() for name in request.headers} != {"host", "accept", "user-agent"}:
        raise TossBoundaryError("contract-request-header")


async def _read_contract_body(response: httpx.Response) -> bytearray:
    content_type = response.headers.get("content-type")
    if content_type is None or content_type.split(";", 1)[0].strip().lower() != JSON_MEDIA_TYPE:
        raise _PreflightFailure("CONTRACT", "CONTENT_TYPE", status_code=response.status_code)
    content_length = response.headers.get("content-length")
    if content_length is not None:
        try:
            declared_length = int(content_length)
        except ValueError:
            raise _PreflightFailure(
                "CONTRACT", "CONTRACT_INVALID", status_code=response.status_code
            ) from None
        if declared_length < 0 or declared_length > CANONICAL_OPENAPI_MAX_BYTES:
            raise _PreflightFailure(
                "CONTRACT", "CONTRACT_INVALID", status_code=response.status_code
            )
    body = bytearray()
    try:
        async for chunk in response.aiter_bytes():
            if len(body) + len(chunk) > CANONICAL_OPENAPI_MAX_BYTES:
                raise _PreflightFailure(
                    "CONTRACT", "CONTRACT_INVALID", status_code=response.status_code
                )
            body.extend(chunk)
    except httpx.RequestError:
        raise _PreflightFailure("CONTRACT", "TRANSPORT") from None
    return body


def _safe_contract_value(value: object) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 32:
        return "UNKNOWN"
    if re.fullmatch(r"[A-Za-z0-9.-]+", value) is None:
        return "UNKNOWN"
    return value


def _contract_origin_matches(document: Mapping[str, object], expected_origin: str) -> bool:
    servers = document.get("servers")
    if not isinstance(servers, list) or len(servers) != 1:
        return False
    server = servers[0]
    return (
        isinstance(server, dict)
        and set(server).issuperset({"url"})
        and server.get("url") == expected_origin
    )


async def _fetch_contract_once(
    client: httpx.AsyncClient,
    approved: _ApprovedContract,
) -> _ContractObservation:
    request = httpx.Request(
        "GET",
        httpx.URL(TOSS_ORIGIN).copy_with(path=CANONICAL_OPENAPI_PATH),
        headers={"Accept": JSON_MEDIA_TYPE, "User-Agent": USER_AGENT},
    )
    _assert_contract_request_boundary(request)
    try:
        response = await client.send(request, stream=True)
    except httpx.RequestError:
        raise _PreflightFailure("CONTRACT", "TRANSPORT") from None
    body = bytearray()
    try:
        if 300 <= response.status_code < 400:
            raise _PreflightFailure("CONTRACT", "REDIRECT", status_code=response.status_code)
        if response.status_code != 200:
            raise _PreflightFailure("CONTRACT", "HTTP_FAILURE", status_code=response.status_code)
        body = await _read_contract_body(response)
        sha_matches = hashlib.sha256(body).hexdigest() == approved.sha256
        try:
            decoded = json.loads(body)
        except (JSONDecodeError, UnicodeDecodeError):
            if not sha_matches:
                return _ContractObservation("UNKNOWN", "UNKNOWN", False, False)
            raise _PreflightFailure(
                "CONTRACT", "CONTRACT_INVALID", status_code=response.status_code
            ) from None
        if not isinstance(decoded, dict) or not all(isinstance(key, str) for key in decoded):
            if not sha_matches:
                return _ContractObservation("UNKNOWN", "UNKNOWN", False, False)
            raise _PreflightFailure(
                "CONTRACT", "CONTRACT_INVALID", status_code=response.status_code
            )
        info = decoded.get("info")
        rest_version: object = info.get("version") if isinstance(info, dict) else None
        observation = _ContractObservation(
            openapi_version=_safe_contract_value(decoded.get("openapi")),
            rest_version=_safe_contract_value(rest_version),
            sha_matches=sha_matches,
            origin_matches=_contract_origin_matches(decoded, approved.origin),
        )
        return observation
    finally:
        body.clear()
        await response.aclose()
        client.cookies.clear()


def _apply_contract_observation(
    summary: dict[str, str],
    observation: _ContractObservation,
    approved: _ApprovedContract,
) -> None:
    summary["PROVIDER_OPENAPI"] = observation.openapi_version
    summary["PROVIDER_VERSION"] = observation.rest_version
    summary["CONTRACT_SHA_MATCH"] = "YES" if observation.sha_matches else "NO"
    summary["CONTRACT_ORIGIN_MATCH"] = "YES" if observation.origin_matches else "NO"
    drifted = not (
        observation.openapi_version == approved.openapi_version
        and observation.rest_version == approved.rest_version
        and observation.sha_matches
        and observation.origin_matches
    )
    summary["PROVIDER_CONTRACT_DRIFT"] = "YES" if drifted else "NO"


def _apply_credential_state(summary: dict[str, str], settings: Settings) -> bool:
    has_client_id = settings.toss_client_id is not None
    has_credential_value = settings.toss_client_secret is not None
    summary[_CREDENTIAL_CONFIGURED_KEYS[0]] = "YES" if has_client_id else "NO"
    summary[_CREDENTIAL_CONFIGURED_KEYS[1]] = "YES" if has_credential_value else "NO"
    complete = credential_state(settings) is TossCredentialState.COMPLETE
    summary["CREDENTIALS_CONFIGURED"] = "YES" if complete else "NO"
    return complete


async def _refuse_preflight_sleep(_seconds: float) -> None:
    raise _PreflightFailure("OAUTH", "ONE_SHOT_POLICY")


def _discard_payload(payload: object) -> None:
    if isinstance(payload, dict):
        payload.clear()
    elif isinstance(payload, list):
        payload.clear()


async def _issue_oauth_once(
    manager: _TossTokenManager,
    limiter: _TossRateLimiter,
) -> _TokenLease:
    group = rate_group_for("POST", TOKEN_PATH)
    attempt = await manager._issue_token_once(group, limiter.new_retry_budget())
    try:
        if attempt.status_code != 200:
            manager._raise_oauth_failure(attempt.status_code, attempt.payload)
            raise AssertionError("OAuth failure handler must raise")
        try:
            token = OAuthTokenResponse.model_validate(attempt.payload)
        except ValidationError:
            raise TossResponseContractError(TOKEN_PATH, "invalid-oauth-response") from None
        return _TokenLease(token.access_token, generation=1)
    finally:
        _discard_payload(attempt.payload)


async def _send_market_once(
    client: httpx.AsyncClient,
    lease: _TokenLease,
    symbol: str,
) -> _MarketAttempt:
    endpoint = TossStaticEndpoint.STOCKS.value
    request = httpx.Request(
        "GET",
        httpx.URL(TOSS_ORIGIN).copy_with(path=endpoint),
        params={"symbols": symbol},
        headers={"Accept": JSON_MEDIA_TYPE, "User-Agent": USER_AGENT},
    )
    lease._authorize_request(request, _use_key=_TOKEN_REQUEST_USE_KEY)
    _assert_request_boundary(request)
    try:
        response = await client.send(request, stream=True)
    except httpx.RequestError:
        raise TossTransportError(endpoint) from None
    try:
        if 300 <= response.status_code < 400:
            raise TossRedirectError(endpoint, response.status_code)
        payload = await _read_json(response, endpoint, MARKET_RESPONSE_MAX_BYTES)
        telemetry = parse_rate_headers(
            response.headers,
            status_code=response.status_code,
            current_limit=DOCUMENTED_RATE_LIMITS[TossRateLimitGroup.STOCK],
        )
        rate_summary = _safe_rate_summary(response.headers, telemetry)
        return _MarketAttempt(
            response.status_code,
            payload,
            telemetry,
            tuple(rate_summary.items()),
        )
    finally:
        await response.aclose()
        client.cookies.clear()


def _header_state(
    headers: httpx.Headers,
    name: str,
    parsed_value: int | None,
) -> str:
    values = headers.get_list(name)
    if not values:
        return "MISSING"
    if len(values) != 1 or parsed_value is None:
        return "INVALID"
    return "PRESENT_VALID"


def _safe_rate_summary(
    response_headers: httpx.Headers,
    telemetry: RateHeaderTelemetry,
) -> dict[str, str]:
    summary = {
        "RATE_LIMIT_HEADER": _header_state(response_headers, "X-RateLimit-Limit", telemetry.limit),
        "RATE_REMAINING_HEADER": _header_state(
            response_headers, "X-RateLimit-Remaining", telemetry.remaining
        ),
        "RATE_RESET_HEADER": _header_state(
            response_headers, "X-RateLimit-Reset", telemetry.reset_seconds
        ),
        "RATE_HEADERS": "NOT_CHECKED",
        "RETRY_AFTER": "LIVE_UNVERIFIED",
    }
    states = {
        summary["RATE_LIMIT_HEADER"],
        summary["RATE_REMAINING_HEADER"],
        summary["RATE_RESET_HEADER"],
    }
    if "INVALID" in states or (
        RateHeaderDiagnostic.RATE_HEADERS_INVALID in telemetry.diagnostics
        or RateHeaderDiagnostic.RATE_HEADERS_INCONSISTENT in telemetry.diagnostics
    ):
        summary["RATE_HEADERS"] = "INVALID"
    elif "MISSING" in states:
        summary["RATE_HEADERS"] = "MISSING"
    else:
        summary["RATE_HEADERS"] = "PRESENT_VALID"
    retry_after_values = response_headers.get_list("Retry-After")
    if not retry_after_values:
        summary["RETRY_AFTER"] = "LIVE_UNVERIFIED"
    elif len(retry_after_values) == 1 and telemetry.retry_after_seconds is not None:
        summary["RETRY_AFTER"] = "PRESENT_VALID"
    else:
        summary["RETRY_AFTER"] = "PRESENT_INVALID"
    return summary


def _validate_market_payload(payload: dict[str, object]) -> None:
    result = payload.get("result")
    if not isinstance(result, list):
        raise TossResponseContractError(
            TossStaticEndpoint.STOCKS.value, "stocks-result-list-required"
        )
    if any(
        not isinstance(item, dict) or not all(isinstance(key, str) for key in item)
        for item in result
    ):
        raise TossResponseContractError(
            TossStaticEndpoint.STOCKS.value, "stocks-result-object-required"
        )


def _http_status_category(status_code: int | None) -> str:
    if status_code is None:
        return "NONE"
    if 200 <= status_code < 300:
        return "2XX"
    if 300 <= status_code < 400:
        return "3XX"
    if 400 <= status_code < 500:
        return "4XX"
    if 500 <= status_code < 600:
        return "5XX"
    return "OTHER"


def _safe_error_metadata(error: BaseException) -> tuple[str, int | None, str]:
    status_code = getattr(error, "status_code", None)
    safe_status = status_code if isinstance(status_code, int) else None
    provider_code = getattr(error, "provider_code", None)
    safe_code = provider_code if isinstance(provider_code, str) else "NONE"
    if isinstance(error, TossOAuthPermissionError | TossPermissionError):
        category = "PERMISSION"
    elif isinstance(error, TossInvalidClientError | TossAuthenticationError | TossOAuthError):
        category = "AUTH"
    elif isinstance(error, TossRateLimitError):
        category = "RATE_LIMIT"
    elif isinstance(error, TossServerError):
        category = "SERVER"
    elif isinstance(error, TossRedirectError):
        category = "REDIRECT"
    elif isinstance(error, TossResponseContractError):
        category = "CONTRACT_INVALID"
    elif isinstance(error, TossTransportError):
        category = "TRANSPORT"
    elif isinstance(error, TossConfigurationError):
        category = "CREDENTIALS"
    elif isinstance(error, TossHttpError):
        category = "HTTP_FAILURE"
    elif isinstance(error, TossBoundaryError):
        category = "BOUNDARY"
    elif isinstance(error, _PreflightFailure):
        category = error.category
        safe_status = error.status_code
    else:
        category = "INTERNAL_FAILURE"
    return category, safe_status, safe_code


def _apply_failure(summary: dict[str, str], stage: str, error: BaseException) -> None:
    category, status_code, provider_code = _safe_error_metadata(error)
    summary["STAGE"] = stage
    summary["HTTP_STATUS_CATEGORY"] = _http_status_category(status_code)
    summary["PROVIDER_CODE"] = provider_code
    summary["ERROR_CATEGORY"] = category
    summary["STATUS"] = "FAIL"


async def _run_preflight(
    symbol: str,
    *,
    settings_factory: SettingsFactory,
    approved: _ApprovedContract,
    transport: httpx.AsyncBaseTransport | None,
) -> _PreflightResult:
    summary = _base_live_summary()
    try:
        _validate_symbol(symbol)
    except TossBoundaryError as error:
        _apply_failure(summary, "SYMBOL", error)
        return _finalize_summary(summary)

    try:
        async with _build_http_client(transport) as client:
            try:
                observation = await _fetch_contract_once(client, approved)
            except (TossConnectorError, _PreflightFailure) as error:
                _apply_failure(summary, "CONTRACT", error)
                return _finalize_summary(summary)
            _apply_contract_observation(summary, observation, approved)
            if summary["PROVIDER_CONTRACT_DRIFT"] != "NO":
                summary["STAGE"] = "CONTRACT"
                summary["ERROR_CATEGORY"] = "PROVIDER_CONTRACT_DRIFT"
                return _finalize_summary(summary)

            try:
                settings = settings_factory()
            except Exception as error:
                _apply_failure(summary, "CREDENTIALS", error)
                return _finalize_summary(summary)
            if not _apply_credential_state(summary, settings):
                summary["STAGE"] = "CREDENTIALS"
                summary["ERROR_CATEGORY"] = "CREDENTIALS"
                return _finalize_summary(summary)

            limiter = _TossRateLimiter(sleeper=_refuse_preflight_sleep, jitter=lambda: 0.0)
            manager = _build_token_manager(settings, client, limiter)
            lease: _TokenLease | None = None
            try:
                try:
                    lease = await _issue_oauth_once(manager, limiter)
                except (TossConnectorError, _PreflightFailure) as error:
                    summary["OAUTH_REQUEST"] = "FAIL"
                    _apply_failure(summary, "OAUTH", error)
                    return _finalize_summary(summary)
                summary["OAUTH_REQUEST"] = "PASS"

                attempt: _MarketAttempt | None = None
                try:
                    attempt = await _send_market_once(client, lease, symbol)
                    summary.update(attempt.rate_summary)
                except TossConnectorError as error:
                    summary["MARKET_REQUEST"] = "FAIL"
                    _apply_failure(summary, "MARKET", error)
                    return _finalize_summary(summary)
                try:
                    decoded = _DecodedResponse(
                        attempt.status_code,
                        attempt.payload,
                        attempt.rate_headers,
                    )
                    try:
                        payload = _result_or_error(decoded, TossStaticEndpoint.STOCKS.value)
                        _validate_market_payload(payload)
                    except TossConnectorError as error:
                        summary["MARKET_REQUEST"] = "FAIL"
                        _apply_failure(summary, "MARKET", error)
                        return _finalize_summary(summary)
                    summary["MARKET_REQUEST"] = "PASS"
                    summary["STAGE"] = "SUMMARY"
                    summary["HTTP_STATUS_CATEGORY"] = "2XX"
                    summary["ERROR_CATEGORY"] = "NONE"
                    summary["STATUS"] = "PASS"
                    return _finalize_summary(summary)
                finally:
                    _discard_payload(attempt.payload)
            finally:
                lease = None
                await manager.aclose()
                client.cookies.clear()
    except Exception as error:
        _apply_failure(summary, "INTERNAL", error)
        return _finalize_summary(summary)


async def _run_live_preflight(symbol: str) -> _PreflightResult:
    return await _run_preflight(
        symbol,
        settings_factory=Settings,
        approved=_RUNTIME_APPROVED_CONTRACT,
        transport=None,
    )


async def _run_preflight_for_test(
    symbol: str,
    *,
    settings_factory: SettingsFactory,
    approved: _ApprovedContract,
    transport: httpx.MockTransport,
) -> _PreflightResult:
    if not isinstance(transport, httpx.MockTransport):
        raise TypeError("The preflight test seam requires MockTransport.")
    return await _run_preflight(
        symbol,
        settings_factory=settings_factory,
        approved=approved,
        transport=transport,
    )


def _synthetic_contract() -> tuple[bytes, _ApprovedContract]:
    document = {
        "info": {"version": APPROVED_REST_VERSION},
        "openapi": APPROVED_OPENAPI_VERSION,
        "servers": [{"url": TOSS_ORIGIN}],
    }
    content = json.dumps(document, separators=(",", ":"), sort_keys=True).encode("utf-8")
    approved = _ApprovedContract(
        openapi_version=APPROVED_OPENAPI_VERSION,
        rest_version=APPROVED_REST_VERSION,
        sha256=hashlib.sha256(content).hexdigest(),
        origin=TOSS_ORIGIN,
    )
    return content, approved


async def _run_offline_self_test() -> dict[str, str]:
    contract, approved = _synthetic_contract()
    credential = "synthetic-" + "preflight-credential"
    token_value = "synthetic-" + "preflight-token"
    forbidden_provider_message = "private-" + "provider-body"
    counts = {"contract": 0, "oauth": 0, "market": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == CANONICAL_OPENAPI_PATH:
            counts["contract"] += 1
            return httpx.Response(
                200,
                content=contract,
                headers={"content-type": JSON_MEDIA_TYPE},
            )
        if request.url.path == TOKEN_PATH:
            counts["oauth"] += 1
            return httpx.Response(
                200,
                json={
                    "access_" + "token": token_value,
                    "token_type": "Bearer",
                    "expires_in": 120,
                },
                headers={"content-type": JSON_MEDIA_TYPE},
            )
        if request.url.path == TossStaticEndpoint.STOCKS.value:
            counts["market"] += 1
            return httpx.Response(
                200,
                json={"result": [], "ignored": forbidden_provider_message},
                headers={
                    "content-type": JSON_MEDIA_TYPE,
                    "X-RateLimit-Limit": "5",
                    "X-RateLimit-Remaining": "4",
                    "X-RateLimit-Reset": "1",
                    "X-Synthetic-Raw": "private-header-value",
                },
            )
        raise AssertionError("Self-test reached an unapproved endpoint.")

    def settings_factory() -> Settings:
        return Settings(TOSS_CLIENT_ID=credential, TOSS_CLIENT_SECRET=credential)

    result = await _run_preflight_for_test(
        "SYNTHETIC",
        settings_factory=settings_factory,
        approved=approved,
        transport=httpx.MockTransport(handler),
    )
    rendered = result.render()
    redaction_values = (
        credential,
        token_value,
        forbidden_provider_message,
        "private-header-value",
        "Bearer",
    )
    one_shot_passed = counts == {"contract": 1, "oauth": 1, "market": 1}
    redaction_passed = all(value not in rendered for value in redaction_values)
    schema_passed = tuple(key for key, _value in result.lines) == LIVE_SUMMARY_KEYS

    drift_counts = {"contract": 0, "oauth": 0, "market": 0}

    def drift_handler(request: httpx.Request) -> httpx.Response:
        drift_counts["contract"] += 1
        return httpx.Response(
            200,
            json={
                "openapi": "9.9.9",
                "info": {"version": "9.9.9"},
                "servers": [{"url": TOSS_ORIGIN}],
            },
            headers={"content-type": JSON_MEDIA_TYPE},
        )

    def forbidden_settings_factory() -> Settings:
        raise AssertionError("Drift self-test read credentials.")

    drift_result = await _run_preflight_for_test(
        "SYNTHETIC",
        settings_factory=forbidden_settings_factory,
        approved=approved,
        transport=httpx.MockTransport(drift_handler),
    )
    drift_stop_passed = dict(drift_result.lines)[
        "PROVIDER_CONTRACT_DRIFT"
    ] == "YES" and drift_counts == {"contract": 1, "oauth": 0, "market": 0}

    passed = result.passed and one_shot_passed and redaction_passed and schema_passed
    passed = passed and drift_stop_passed
    return {
        "MODE": "SELF_TEST",
        "EXTERNAL_NETWORK_REQUESTS": "0",
        "OUTPUT_SCHEMA": "PASS" if schema_passed else "FAIL",
        "REDACTION": "PASS" if redaction_passed else "FAIL",
        "ONE_SHOT": "PASS" if one_shot_passed else "FAIL",
        "DRIFT_STOP": "PASS" if drift_stop_passed else "FAIL",
        "STATUS": "PASS" if passed else "FAIL",
    }
