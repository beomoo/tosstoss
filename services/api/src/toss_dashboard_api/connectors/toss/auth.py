from __future__ import annotations

import asyncio
import json
import math
import random
import time
from collections.abc import Callable
from enum import StrEnum
from json import JSONDecodeError
from typing import Any

import httpx
from pydantic import SecretStr, ValidationError

from toss_dashboard_api.config import Settings
from toss_dashboard_api.connectors.toss.errors import (
    TossConfigurationError,
    TossContentTypeError,
    TossInvalidClientError,
    TossLifecycleError,
    TossOAuthError,
    TossOAuthPermissionError,
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
    FORM_MEDIA_TYPE,
    JSON_MEDIA_TYPE,
    OAUTH_RESPONSE_MAX_BYTES,
    TOKEN_PATH,
    TOSS_ORIGIN,
    USER_AGENT,
    OAuthErrorResponse,
    OAuthTokenResponse,
    ProviderErrorEnvelope,
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
    RetryDisposition,
    TossRateLimitGroup,
    _RateLimitWaitDeferred,
    _RetryBudget,
    _TossRateLimiter,
    rate_group_for,
)

TOKEN_SAFETY_MARGIN_SECONDS = 30.0
_TOKEN_MANAGER_CONSTRUCTION_KEY = object()
_TOKEN_REQUEST_USE_KEY = object()
_DEFAULT_JITTER_SOURCE = random.Random().random


class TossCredentialState(StrEnum):
    UNAVAILABLE = "missing-credentials"
    PARTIAL = "partial-credentials"
    COMPLETE = "complete"


class _TokenLease:
    __slots__ = ("__token", "generation")

    def __init__(self, token: SecretStr, generation: int) -> None:
        self.__token = token
        self.generation = generation

    def _authorize_request(self, request: httpx.Request, *, _use_key: object) -> None:
        if _use_key is not _TOKEN_REQUEST_USE_KEY:
            raise TypeError("Token leases are connector-internal.")
        request.headers["Authorization"] = "Bearer " + self.__token.get_secret_value()

    def __repr__(self) -> str:
        return f"_TokenLease(generation={self.generation})"

    __str__ = __repr__


class _OAuthAttempt:
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


def credential_state(settings: Settings) -> TossCredentialState:
    has_client_id = settings.toss_client_id is not None
    has_secret = settings.toss_client_secret is not None
    if has_client_id and has_secret:
        return TossCredentialState.COMPLETE
    if has_client_id or has_secret:
        return TossCredentialState.PARTIAL
    return TossCredentialState.UNAVAILABLE


class _TossTokenManager:
    """Async single-flight, memory-only OAuth token manager."""

    def __init__(
        self,
        settings: Settings,
        http_client: httpx.AsyncClient,
        rate_limiter: _TossRateLimiter,
        *,
        _construction_key: object,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if _construction_key is not _TOKEN_MANAGER_CONSTRUCTION_KEY:
            raise TypeError("Token manager construction is connector-internal.")
        self._settings = settings
        self._http_client = http_client
        self._rate_limiter = rate_limiter
        self._monotonic = monotonic
        self._lock = asyncio.Lock()
        self._lease: _TokenLease | None = None
        self._expires_at = 0.0
        self._generation = 0
        self._closed = False

    async def get_token(self) -> _TokenLease:
        self._ensure_open()
        lease = self._valid_cached_lease()
        if lease is not None:
            return lease
        async with self._lock:
            self._ensure_open()
            lease = self._valid_cached_lease()
            if lease is not None:
                return lease
            token = await self._issue_token()
            self._generation += 1
            lease = _TokenLease(token.access_token, self._generation)
            margin = min(TOKEN_SAFETY_MARGIN_SECONDS, token.expires_in * 0.1)
            self._expires_at = self._monotonic() + token.expires_in - margin
            self._lease = lease
            return lease

    async def invalidate(self) -> None:
        async with self._lock:
            self._lease = None
            self._expires_at = 0.0

    async def invalidate_if_current(self, generation: int) -> bool:
        async with self._lock:
            if self._lease is None or self._lease.generation != generation:
                return False
            self._lease = None
            self._expires_at = 0.0
            return True

    async def aclose(self) -> None:
        async with self._lock:
            self._closed = True
            self._lease = None
            self._expires_at = 0.0

    def _ensure_open(self) -> None:
        if self._closed:
            raise TossLifecycleError

    def _valid_cached_lease(self) -> _TokenLease | None:
        if self._lease is not None and self._monotonic() < self._expires_at:
            return self._lease
        return None

    def _credentials(self) -> tuple[str, str]:
        state = credential_state(self._settings)
        if state is not TossCredentialState.COMPLETE:
            raise TossConfigurationError(state.value)
        configured_id = self._settings.toss_client_id
        configured_secret = self._settings.toss_client_secret
        if configured_id is None or configured_secret is None:
            raise TossConfigurationError(TossCredentialState.UNAVAILABLE.value)
        return configured_id.get_secret_value(), configured_secret.get_secret_value()

    async def _issue_token(self) -> OAuthTokenResponse:
        group = rate_group_for("POST", TOKEN_PATH)
        budget = self._rate_limiter.new_retry_budget()
        while True:
            attempt = await self._issue_token_once(group, budget)
            if attempt.status_code == 200:
                try:
                    return OAuthTokenResponse.model_validate(attempt.payload)
                except ValidationError:
                    raise TossResponseContractError(TOKEN_PATH, "invalid-oauth-response") from None
            if await self._retry_provider_failure(attempt, group, budget):
                continue
            self._raise_oauth_failure(attempt.status_code, attempt.payload)
            raise AssertionError("OAuth failure handler must raise")

    async def _issue_token_once(
        self,
        group: TossRateLimitGroup,
        budget: _RetryBudget,
    ) -> _OAuthAttempt:
        client_identifier, credential_value = self._credentials()
        try:
            await self._rate_limiter.acquire(
                group,
                retry_budget=budget if budget.attempt_count > 1 else None,
            )
        except _RateLimitWaitDeferred as error:
            raise TossRetryDeferredError(
                endpoint=TOKEN_PATH,
                rate_group=group.value,
                status_code=429,
                provider_code=None,
                request_id=None,
                attempt_count=budget.attempt_count,
                retry_after_seconds=math.ceil(error.retry_after_seconds),
            ) from None
        url = httpx.URL(TOSS_ORIGIN).copy_with(path=TOKEN_PATH)
        request = httpx.Request(
            "POST",
            url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_identifier,
                "client_secret": credential_value,
            },
            headers={
                "Accept": JSON_MEDIA_TYPE,
                "Content-Type": FORM_MEDIA_TYPE,
                "User-Agent": USER_AGENT,
            },
        )
        try:
            response = await self._http_client.send(request, stream=True)
        except httpx.RequestError:
            raise TossTransportError(TOKEN_PATH) from None
        try:
            if 300 <= response.status_code < 400:
                raise TossRedirectError(TOKEN_PATH, response.status_code)
            payload = await _read_json(response, TOKEN_PATH, OAUTH_RESPONSE_MAX_BYTES)
            if response.status_code == 429 or response.status_code in RETRYABLE_TRANSIENT_STATUSES:
                try:
                    ProviderErrorEnvelope.model_validate(payload)
                except ValidationError:
                    raise TossResponseContractError(
                        TOKEN_PATH, "invalid-oauth-error-response"
                    ) from None
            rate_headers = await self._rate_limiter.observe(
                group,
                response.headers,
                status_code=response.status_code,
            )
            return _OAuthAttempt(response.status_code, payload, rate_headers)
        finally:
            await response.aclose()
            self._http_client.cookies.clear()

    async def _retry_provider_failure(
        self,
        attempt: _OAuthAttempt,
        group: TossRateLimitGroup,
        budget: _RetryBudget,
    ) -> bool:
        if attempt.status_code != 429 and attempt.status_code not in RETRYABLE_TRANSIENT_STATUSES:
            return False
        try:
            envelope = ProviderErrorEnvelope.model_validate(attempt.payload)
        except ValidationError:
            raise TossResponseContractError(TOKEN_PATH, "invalid-oauth-error-response") from None
        provider_code = envelope.error.code
        retryable = (
            attempt.status_code == 429 and provider_code in RETRYABLE_RATE_PROVIDER_CODES
        ) or (
            attempt.status_code in RETRYABLE_TRANSIENT_STATUSES
            and provider_code in RETRYABLE_TRANSIENT_PROVIDER_CODES
        )
        if not retryable:
            return False

        retry_after = (
            attempt.rate_headers.retry_after_seconds if attempt.status_code == 429 else None
        )
        reset_seconds = (
            attempt.rate_headers.reset_seconds
            if attempt.status_code == 429 and attempt.rate_headers.remaining == 0
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
                await self._rate_limiter.block_for(group, retry_after)
            raise TossRetryExhaustedError(
                endpoint=TOKEN_PATH,
                rate_group=group.value,
                status_code=attempt.status_code,
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
            await self._rate_limiter.block_for(group, deferred_seconds)
            raise TossRetryDeferredError(
                endpoint=TOKEN_PATH,
                rate_group=group.value,
                status_code=attempt.status_code,
                provider_code=safe_code,
                request_id=request_id,
                attempt_count=budget.attempt_count,
                retry_after_seconds=safe_deferred_seconds,
            )
        delay = decision.delay_seconds
        if delay is None:
            raise AssertionError("retry timing requires a delay")
        budget.record_retry(delay)
        await self._rate_limiter.sleep_for_retry(group, delay)
        return True

    @staticmethod
    def _raise_oauth_failure(status_code: int, payload: object) -> None:
        try:
            oauth_error = OAuthErrorResponse.model_validate(payload)
        except ValidationError:
            if status_code in {429} or status_code >= 500:
                try:
                    envelope = ProviderErrorEnvelope.model_validate(payload)
                except ValidationError:
                    raise TossResponseContractError(
                        TOKEN_PATH, "invalid-oauth-error-response"
                    ) from None
                kwargs: dict[str, Any] = {
                    "endpoint": TOKEN_PATH,
                    "status_code": status_code,
                    "provider_code": safe_provider_code(envelope.error.code),
                    "request_id": safe_request_id(envelope.error.requestId),
                }
                if status_code == 429:
                    raise TossRateLimitError(**kwargs) from None
                raise TossServerError(**kwargs) from None
            raise TossResponseContractError(TOKEN_PATH, "invalid-oauth-error-response") from None
        if oauth_error.error == "invalid_client":
            raise TossInvalidClientError(status_code, oauth_error.error)
        if oauth_error.error == "access_denied" or status_code == 403:
            raise TossOAuthPermissionError(status_code, oauth_error.error)
        raise TossOAuthError(status_code, oauth_error.error)


def _build_token_manager(
    settings: Settings,
    http_client: httpx.AsyncClient,
    rate_limiter: _TossRateLimiter,
    *,
    monotonic: Callable[[], float] = time.monotonic,
) -> _TossTokenManager:
    return _TossTokenManager(
        settings,
        http_client,
        rate_limiter,
        _construction_key=_TOKEN_MANAGER_CONSTRUCTION_KEY,
        monotonic=monotonic,
    )


class _TokenManagerTestContext:
    """Own the auth-only transport used by token-manager unit tests."""

    def __init__(
        self,
        settings: Settings,
        transport: httpx.MockTransport,
        *,
        monotonic: Callable[[], float] = time.monotonic,
        sleeper: AsyncSleeper = asyncio.sleep,
        jitter: JitterSource = _DEFAULT_JITTER_SOURCE,
    ) -> None:
        if not isinstance(transport, httpx.MockTransport):
            raise TypeError("The token-manager test seam requires MockTransport.")
        self._http_client = httpx.AsyncClient(
            follow_redirects=False,
            trust_env=False,
            verify=True,
            transport=transport,
        )
        self._rate_limiter = _TossRateLimiter(
            monotonic=monotonic,
            sleeper=sleeper,
            jitter=jitter,
        )
        self._manager = _build_token_manager(
            settings,
            self._http_client,
            self._rate_limiter,
            monotonic=monotonic,
        )

    async def __aenter__(self) -> _TossTokenManager:
        return self._manager

    async def __aexit__(self, *_args: object) -> None:
        await self._manager.aclose()
        self._http_client.cookies.clear()
        await self._http_client.aclose()


def _token_manager_test_seam(
    settings: Settings,
    transport: httpx.MockTransport,
    *,
    monotonic: Callable[[], float] | None = None,
    sleeper: AsyncSleeper | None = None,
    jitter: JitterSource | None = None,
) -> _TokenManagerTestContext:
    return _TokenManagerTestContext(
        settings,
        transport,
        monotonic=monotonic if monotonic is not None else time.monotonic,
        sleeper=sleeper if sleeper is not None else asyncio.sleep,
        jitter=jitter if jitter is not None else _DEFAULT_JITTER_SOURCE,
    )


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
