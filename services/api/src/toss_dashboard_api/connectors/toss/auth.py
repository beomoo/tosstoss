from __future__ import annotations

import asyncio
import json
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

TOKEN_SAFETY_MARGIN_SECONDS = 30.0
_TOKEN_MANAGER_CONSTRUCTION_KEY = object()


class TossCredentialState(StrEnum):
    UNAVAILABLE = "missing-credentials"
    PARTIAL = "partial-credentials"
    COMPLETE = "complete"


class TokenLease:
    __slots__ = ("__token", "generation")

    def __init__(self, token: SecretStr, generation: int) -> None:
        self.__token = token
        self.generation = generation

    def _authorization_value(self) -> str:
        return self.__token.get_secret_value()

    def __repr__(self) -> str:
        return f"TokenLease(generation={self.generation})"

    __str__ = __repr__


def credential_state(settings: Settings) -> TossCredentialState:
    has_client_id = settings.toss_client_id is not None
    has_secret = settings.toss_client_secret is not None
    if has_client_id and has_secret:
        return TossCredentialState.COMPLETE
    if has_client_id or has_secret:
        return TossCredentialState.PARTIAL
    return TossCredentialState.UNAVAILABLE


class TossTokenManager:
    """Async single-flight, memory-only OAuth token manager."""

    def __init__(
        self,
        settings: Settings,
        http_client: httpx.AsyncClient,
        *,
        _construction_key: object,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if _construction_key is not _TOKEN_MANAGER_CONSTRUCTION_KEY:
            raise TypeError("TossTokenManager is owned by TossHttpClient.")
        self._settings = settings
        self._http_client = http_client
        self._monotonic = monotonic
        self._lock = asyncio.Lock()
        self._lease: TokenLease | None = None
        self._expires_at = 0.0
        self._generation = 0
        self._closed = False

    async def get_token(self) -> TokenLease:
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
            lease = TokenLease(token.access_token, self._generation)
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

    def _valid_cached_lease(self) -> TokenLease | None:
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
        client_identifier, credential_value = self._credentials()
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
            if response.status_code == 200:
                try:
                    return OAuthTokenResponse.model_validate(payload)
                except ValidationError:
                    raise TossResponseContractError(TOKEN_PATH, "invalid-oauth-response") from None
            self._raise_oauth_failure(response.status_code, payload)
            raise AssertionError("OAuth failure handler must raise")
        finally:
            await response.aclose()
            self._http_client.cookies.clear()

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
    *,
    monotonic: Callable[[], float] = time.monotonic,
) -> TossTokenManager:
    return TossTokenManager(
        settings,
        http_client,
        _construction_key=_TOKEN_MANAGER_CONSTRUCTION_KEY,
        monotonic=monotonic,
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
