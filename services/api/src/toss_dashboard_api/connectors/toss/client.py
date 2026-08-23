from __future__ import annotations

import json
import math
import re
from collections.abc import Callable, Mapping
from json import JSONDecodeError
from typing import Any, Self

import httpx
from pydantic import ValidationError

from toss_dashboard_api.config import Settings
from toss_dashboard_api.connectors.toss.auth import (
    _TOKEN_REQUEST_USE_KEY,
    _build_token_manager,
    _TokenLease,
)
from toss_dashboard_api.connectors.toss.errors import (
    TossAuthenticationError,
    TossBoundaryError,
    TossContentTypeError,
    TossHttpError,
    TossLifecycleError,
    TossPermissionError,
    TossRateLimitError,
    TossRedirectError,
    TossResponseContractError,
    TossResponseTooLargeError,
    TossRetryDeferredError,
    TossRetryExhaustedError,
    TossServerError,
    TossTransportError,
)
from toss_dashboard_api.connectors.toss.models import (
    JSON_MEDIA_TYPE,
    MARKET_RESPONSE_MAX_BYTES,
    REFRESHABLE_AUTH_CODES,
    STATIC_QUERY_KEYS,
    SYMBOL_QUERY_KEYS,
    TOSS_ORIGIN,
    USER_AGENT,
    ProviderErrorEnvelope,
    QueryParams,
    QueryValue,
    TossStaticEndpoint,
    TossSymbolEndpoint,
    safe_provider_code,
    safe_request_id,
)
from toss_dashboard_api.connectors.toss.rate_limit import (
    RETRYABLE_RATE_PROVIDER_CODES,
    RETRYABLE_TRANSIENT_PROVIDER_CODES,
    RETRYABLE_TRANSIENT_STATUSES,
    AsyncSleeper,
    JitterSource,
    RateHeaderTelemetry,
    RateLimitSnapshot,
    RetryDisposition,
    TossRateLimitGroup,
    _RateLimitWaitDeferred,
    _RetryBudget,
    _TossRateLimiter,
    rate_group_for,
)

CONNECT_TIMEOUT_SECONDS = 5.0
READ_TIMEOUT_SECONDS = 10.0
WRITE_TIMEOUT_SECONDS = 5.0
POOL_TIMEOUT_SECONDS = 5.0
SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9.\-]+$")


class TossHttpClient:
    """Application-owned exact-origin client with one token manager and no raw URL API."""

    def __init__(self, settings: Settings) -> None:
        self._initialize(settings, transport=None, monotonic=None)

    @classmethod
    def _for_test(
        cls,
        settings: Settings,
        transport: httpx.AsyncBaseTransport,
        *,
        monotonic: Callable[[], float] | None = None,
        sleeper: AsyncSleeper | None = None,
        jitter: JitterSource | None = None,
    ) -> Self:
        instance = cls.__new__(cls)
        instance._initialize(
            settings,
            transport=transport,
            monotonic=monotonic,
            sleeper=sleeper,
            jitter=jitter,
        )
        return instance

    def _initialize(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None,
        monotonic: Callable[[], float] | None,
        sleeper: AsyncSleeper | None = None,
        jitter: JitterSource | None = None,
    ) -> None:
        timeout = httpx.Timeout(
            connect=CONNECT_TIMEOUT_SECONDS,
            read=READ_TIMEOUT_SECONDS,
            write=WRITE_TIMEOUT_SECONDS,
            pool=POOL_TIMEOUT_SECONDS,
        )
        self._http_client = httpx.AsyncClient(
            base_url=TOSS_ORIGIN,
            timeout=timeout,
            follow_redirects=False,
            trust_env=False,
            verify=True,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            transport=transport,
        )
        self.__rate_limiter = _TossRateLimiter(
            monotonic=monotonic,
            sleeper=sleeper,
            jitter=jitter,
        )
        if monotonic is None:
            self.__token_manager = _build_token_manager(
                settings,
                self._http_client,
                self.__rate_limiter,
            )
        else:
            self.__token_manager = _build_token_manager(
                settings,
                self._http_client,
                self.__rate_limiter,
                monotonic=monotonic,
            )
        self._closed = False

    @property
    def origin(self) -> str:
        return str(self._http_client.base_url).rstrip("/")

    @property
    def is_closed(self) -> bool:
        return self._closed

    async def __aenter__(self) -> Self:
        self._ensure_open()
        return self

    async def __aexit__(self, *_args: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        await self.__token_manager.aclose()
        self._http_client.cookies.clear()
        await self._http_client.aclose()

    async def get(
        self,
        endpoint: TossStaticEndpoint,
        *,
        params: QueryParams | None = None,
    ) -> dict[str, object]:
        self._ensure_open()
        if not isinstance(endpoint, TossStaticEndpoint):
            raise TossBoundaryError("unknown-static-endpoint")
        query = _validated_query(params, STATIC_QUERY_KEYS[endpoint])
        return await self._authenticated_get(endpoint.value, endpoint.value, query)

    async def get_symbol(
        self,
        endpoint: TossSymbolEndpoint,
        symbol: str,
        *,
        params: QueryParams | None = None,
    ) -> dict[str, object]:
        self._ensure_open()
        if not isinstance(endpoint, TossSymbolEndpoint):
            raise TossBoundaryError("unknown-symbol-endpoint")
        if not isinstance(symbol, str) or SYMBOL_PATTERN.fullmatch(symbol) is None:
            raise TossBoundaryError("invalid-symbol")
        query = _validated_query(params, SYMBOL_QUERY_KEYS)
        path = endpoint.value.replace("{symbol}", symbol)
        return await self._authenticated_get(endpoint.value, path, query)

    def _ensure_open(self) -> None:
        if self._closed:
            raise TossLifecycleError

    async def _rate_limit_snapshot_for_test(self, group: TossRateLimitGroup) -> RateLimitSnapshot:
        return await self.__rate_limiter.snapshot(group)

    async def _authenticated_get(
        self,
        endpoint_template: str,
        path: str,
        params: Mapping[str, QueryValue],
    ) -> dict[str, object]:
        lease = await self.__token_manager.get_token()
        response = await self._send_get(endpoint_template, path, params, lease)
        if _is_refreshable_auth_error(response):
            await self.__token_manager.invalidate_if_current(lease.generation)
            lease = await self.__token_manager.get_token()
            response = await self._send_get(endpoint_template, path, params, lease)
        return _result_or_error(response, endpoint_template)

    async def _send_get(
        self,
        endpoint_template: str,
        path: str,
        params: Mapping[str, QueryValue],
        lease: _TokenLease,
    ) -> _DecodedResponse:
        try:
            group = rate_group_for("GET", endpoint_template)
        except ValueError:
            raise TossBoundaryError("unknown-rate-group") from None
        budget = self.__rate_limiter.new_retry_budget()
        while True:
            response = await self._send_get_once(
                endpoint_template,
                path,
                params,
                lease,
                group,
                budget,
            )
            if await self._retry_provider_failure(
                response,
                endpoint_template,
                group,
                budget,
            ):
                continue
            return response

    async def _send_get_once(
        self,
        endpoint_template: str,
        path: str,
        params: Mapping[str, QueryValue],
        lease: _TokenLease,
        group: TossRateLimitGroup,
        budget: _RetryBudget,
    ) -> _DecodedResponse:
        try:
            await self.__rate_limiter.acquire(
                group,
                retry_budget=budget if budget.attempt_count > 1 else None,
            )
        except _RateLimitWaitDeferred as error:
            raise TossRetryDeferredError(
                endpoint=endpoint_template,
                rate_group=group.value,
                status_code=429,
                provider_code=None,
                request_id=None,
                attempt_count=budget.attempt_count,
                retry_after_seconds=math.ceil(error.retry_after_seconds),
            ) from None
        url = httpx.URL(TOSS_ORIGIN).copy_with(path=path)
        request = httpx.Request(
            "GET",
            url,
            params=dict(params),
            headers={
                "Accept": JSON_MEDIA_TYPE,
                "User-Agent": USER_AGENT,
            },
        )
        lease._authorize_request(request, _use_key=_TOKEN_REQUEST_USE_KEY)
        _assert_request_boundary(request)
        try:
            response = await self._http_client.send(request, stream=True)
        except httpx.RequestError:
            raise TossTransportError(endpoint_template) from None
        try:
            if 300 <= response.status_code < 400:
                raise TossRedirectError(endpoint_template, response.status_code)
            payload = await _read_json(response, endpoint_template, MARKET_RESPONSE_MAX_BYTES)
            if response.status_code == 429 or response.status_code in RETRYABLE_TRANSIENT_STATUSES:
                try:
                    ProviderErrorEnvelope.model_validate(payload)
                except ValidationError:
                    raise TossResponseContractError(
                        endpoint_template, "invalid-error-response"
                    ) from None
            rate_headers = await self.__rate_limiter.observe(
                group,
                response.headers,
                status_code=response.status_code,
            )
            return _DecodedResponse(response.status_code, payload, rate_headers)
        finally:
            await response.aclose()
            self._http_client.cookies.clear()

    async def _retry_provider_failure(
        self,
        response: _DecodedResponse,
        endpoint: str,
        group: TossRateLimitGroup,
        budget: _RetryBudget,
    ) -> bool:
        if response.status_code != 429 and response.status_code not in RETRYABLE_TRANSIENT_STATUSES:
            return False
        try:
            envelope = ProviderErrorEnvelope.model_validate(response.payload)
        except ValidationError:
            raise TossResponseContractError(endpoint, "invalid-error-response") from None
        provider_code = envelope.error.code
        retryable = (
            response.status_code == 429 and provider_code in RETRYABLE_RATE_PROVIDER_CODES
        ) or (
            response.status_code in RETRYABLE_TRANSIENT_STATUSES
            and provider_code in RETRYABLE_TRANSIENT_PROVIDER_CODES
        )
        if not retryable:
            return False

        retry_after = (
            response.rate_headers.retry_after_seconds if response.status_code == 429 else None
        )
        reset_seconds = (
            response.rate_headers.reset_seconds
            if response.status_code == 429 and response.rate_headers.remaining == 0
            else None
        )
        decision = budget.next_timing(
            retry_after_seconds=retry_after,
            reset_seconds=reset_seconds,
        )
        safe_code = safe_provider_code(provider_code)
        request_id = safe_request_id(envelope.error.requestId)
        if decision.disposition is RetryDisposition.EXHAUSTED:
            if retry_after is not None:
                await self.__rate_limiter.block_for(group, retry_after)
            raise TossRetryExhaustedError(
                endpoint=endpoint,
                rate_group=group.value,
                status_code=response.status_code,
                provider_code=safe_code,
                request_id=request_id,
                attempt_count=budget.attempt_count,
                retry_after_seconds=retry_after,
            )
        if decision.disposition is RetryDisposition.DEFER:
            deferred_seconds = decision.delay_seconds
            if deferred_seconds is None:
                raise AssertionError("deferred retry requires a safe delay")
            safe_deferred_seconds = math.ceil(deferred_seconds)
            await self.__rate_limiter.block_for(group, deferred_seconds)
            raise TossRetryDeferredError(
                endpoint=endpoint,
                rate_group=group.value,
                status_code=response.status_code,
                provider_code=safe_code,
                request_id=request_id,
                attempt_count=budget.attempt_count,
                retry_after_seconds=safe_deferred_seconds,
            )
        delay = decision.delay_seconds
        if delay is None:
            raise AssertionError("retry timing requires a delay")
        budget.record_retry(delay)
        await self.__rate_limiter.sleep_for_retry(group, delay)
        return True


class _DecodedResponse:
    __slots__ = ("payload", "rate_headers", "status_code")

    def __init__(
        self,
        status_code: int,
        payload: object,
        rate_headers: RateHeaderTelemetry,
    ) -> None:
        self.status_code = status_code
        self.payload = payload
        self.rate_headers = rate_headers


def _validated_query(
    params: QueryParams | None,
    allowed_keys: frozenset[str],
) -> dict[str, QueryValue]:
    if params is None:
        return {}
    if isinstance(params, str | bytes) or not isinstance(params, Mapping):
        raise TossBoundaryError("query-must-be-a-mapping")
    result: dict[str, QueryValue] = {}
    for key, value in params.items():
        if not isinstance(key, str) or key not in allowed_keys:
            raise TossBoundaryError("unknown-query-parameter")
        if type(value) not in {str, int, bool}:
            raise TossBoundaryError("invalid-query-value")
        result[key] = value
    return result


def _assert_request_boundary(request: httpx.Request) -> None:
    url = request.url
    if (
        request.method != "GET"
        or url.scheme != "https"
        or url.host != "openapi.tossinvest.com"
        or url.port not in {None, 443}
        or url.userinfo
    ):
        raise TossBoundaryError("request-origin-or-method")
    application_headers = {name.lower() for name in request.headers}
    if application_headers != {"host", "accept", "authorization", "user-agent"}:
        raise TossBoundaryError("prohibited-header")


def _is_refreshable_auth_error(response: _DecodedResponse) -> bool:
    if response.status_code != 401:
        return False
    try:
        envelope = ProviderErrorEnvelope.model_validate(response.payload)
    except ValidationError:
        return False
    return envelope.error.code in REFRESHABLE_AUTH_CODES


def _result_or_error(response: _DecodedResponse, endpoint: str) -> dict[str, object]:
    if 200 <= response.status_code < 300:
        if not isinstance(response.payload, dict) or not all(
            isinstance(key, str) for key in response.payload
        ):
            raise TossResponseContractError(endpoint, "json-object-required")
        return response.payload
    try:
        envelope = ProviderErrorEnvelope.model_validate(response.payload)
    except ValidationError:
        raise TossResponseContractError(endpoint, "invalid-error-response") from None
    kwargs: dict[str, Any] = {
        "endpoint": endpoint,
        "status_code": response.status_code,
        "provider_code": safe_provider_code(envelope.error.code),
        "request_id": safe_request_id(envelope.error.requestId),
    }
    if response.status_code == 401:
        raise TossAuthenticationError(**kwargs)
    if response.status_code == 403:
        raise TossPermissionError(**kwargs)
    if response.status_code == 429:
        raise TossRateLimitError(**kwargs)
    if response.status_code >= 500:
        raise TossServerError(**kwargs)
    raise TossHttpError(**kwargs)


def _is_json_content_type(value: str | None) -> bool:
    if value is None:
        return False
    return value.split(";", 1)[0].strip().lower() == JSON_MEDIA_TYPE


async def _read_json(response: httpx.Response, endpoint: str, limit_bytes: int) -> object:
    if not _is_json_content_type(response.headers.get("content-type")):
        raise TossContentTypeError(endpoint)
    content_length = response.headers.get("content-length")
    if content_length is not None:
        try:
            declared_length = int(content_length)
        except ValueError:
            raise TossResponseContractError(endpoint, "invalid-content-length") from None
        if declared_length < 0:
            raise TossResponseContractError(endpoint, "invalid-content-length")
        if declared_length > limit_bytes:
            raise TossResponseTooLargeError(endpoint, limit_bytes)
    body = bytearray()
    try:
        async for chunk in response.aiter_bytes():
            if len(body) + len(chunk) > limit_bytes:
                raise TossResponseTooLargeError(endpoint, limit_bytes)
            body.extend(chunk)
    except httpx.RequestError:
        raise TossTransportError(endpoint) from None
    try:
        return json.loads(body)
    except (JSONDecodeError, UnicodeDecodeError):
        raise TossResponseContractError(endpoint, "malformed-json") from None
