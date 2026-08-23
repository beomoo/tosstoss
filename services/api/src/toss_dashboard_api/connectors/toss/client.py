from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from json import JSONDecodeError
from typing import Any, Self

import httpx
from pydantic import ValidationError

from toss_dashboard_api.config import Settings
from toss_dashboard_api.connectors.toss.auth import (
    TokenLease,
    TossTokenManager,
    _build_token_manager,
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
    ) -> Self:
        instance = cls.__new__(cls)
        instance._initialize(settings, transport=transport, monotonic=monotonic)
        return instance

    def _initialize(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None,
        monotonic: Callable[[], float] | None,
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
        if monotonic is None:
            self._token_manager = _build_token_manager(settings, self._http_client)
        else:
            self._token_manager = _build_token_manager(
                settings, self._http_client, monotonic=monotonic
            )
        self._closed = False

    @property
    def token_manager(self) -> TossTokenManager:
        return self._token_manager

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
        await self._token_manager.aclose()
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

    async def _authenticated_get(
        self,
        endpoint_template: str,
        path: str,
        params: Mapping[str, QueryValue],
    ) -> dict[str, object]:
        lease = await self._token_manager.get_token()
        response = await self._send_get(endpoint_template, path, params, lease)
        if _is_refreshable_auth_error(response):
            await self._token_manager.invalidate_if_current(lease.generation)
            lease = await self._token_manager.get_token()
            response = await self._send_get(endpoint_template, path, params, lease)
        return _result_or_error(response, endpoint_template)

    async def _send_get(
        self,
        endpoint_template: str,
        path: str,
        params: Mapping[str, QueryValue],
        lease: TokenLease,
    ) -> _DecodedResponse:
        url = httpx.URL(TOSS_ORIGIN).copy_with(path=path)
        request = httpx.Request(
            "GET",
            url,
            params=dict(params),
            headers={
                "Accept": JSON_MEDIA_TYPE,
                "Authorization": f"Bearer {lease._authorization_value()}",
                "User-Agent": USER_AGENT,
            },
        )
        _assert_request_boundary(request)
        try:
            response = await self._http_client.send(request, stream=True)
        except httpx.RequestError:
            raise TossTransportError(endpoint_template) from None
        try:
            if 300 <= response.status_code < 400:
                raise TossRedirectError(endpoint_template, response.status_code)
            payload = await _read_json(response, endpoint_template, MARKET_RESPONSE_MAX_BYTES)
            return _DecodedResponse(response.status_code, payload)
        finally:
            await response.aclose()
            self._http_client.cookies.clear()


class _DecodedResponse:
    __slots__ = ("payload", "status_code")

    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self.payload = payload


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
