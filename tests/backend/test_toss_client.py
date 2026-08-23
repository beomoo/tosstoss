from __future__ import annotations

import asyncio
import inspect
import ssl
from collections.abc import Awaitable, Callable
from typing import Any, cast

import httpx
import pytest

from toss_dashboard_api.config import Settings
from toss_dashboard_api.connectors.toss.client import TossHttpClient
from toss_dashboard_api.connectors.toss.errors import (
    TossAuthenticationError,
    TossBoundaryError,
    TossContentTypeError,
    TossHttpError,
    TossLifecycleError,
    TossPermissionError,
    TossRedirectError,
    TossResponseContractError,
    TossResponseTooLargeError,
    TossRetryExhaustedError,
)
from toss_dashboard_api.connectors.toss.models import (
    MARKET_RESPONSE_MAX_BYTES,
    TOKEN_PATH,
    TOSS_ORIGIN,
    TossStaticEndpoint,
    TossSymbolEndpoint,
)

Handler = Callable[[httpx.Request], Awaitable[httpx.Response] | httpx.Response]


class InstantTime:
    def __init__(self) -> None:
        self.value = 100.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.value

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.value += seconds
        await asyncio.sleep(0)


def run(awaitable: Awaitable[Any]) -> Any:
    return asyncio.run(awaitable)


def settings() -> Settings:
    credential_value = "synthetic-" + "credential-value"
    return Settings(
        toss_client_id=credential_value,
        toss_client_secret=credential_value,
    )


def token_payload(value: str = "lease-one") -> dict[str, object]:
    return {
        "access_" + "token": value,
        "token_type": "Bearer",
        "expires_in": 120,
    }


def error_payload(code: str, message: str = "provider message") -> dict[str, object]:
    return {
        "error": {
            "requestId": "01HXYZABCDEFG123456789",
            "code": code,
            "message": message,
        }
    }


def response(status_code: int, payload: object) -> httpx.Response:
    return httpx.Response(
        status_code,
        json=payload,
        headers={"content-type": "application/json; charset=utf-8"},
    )


def client(handler: Handler, *, time_source: InstantTime | None = None) -> TossHttpClient:
    instant_time = time_source or InstantTime()
    return TossHttpClient._for_test(
        settings(),
        httpx.MockTransport(handler),
        monotonic=instant_time,
        sleeper=instant_time.sleep,
        jitter=lambda: 0.0,
    )


class SuccessProvider:
    def __init__(self) -> None:
        self.token_calls = 0
        self.get_calls = 0
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path == TOKEN_PATH:
            self.token_calls += 1
            return response(200, token_payload(f"lease-{self.token_calls}"))
        self.get_calls += 1
        return response(200, {"result": []})


def test_exact_origin_and_fixed_client_configuration() -> None:
    provider = SuccessProvider()
    connector = client(provider)
    try:
        assert connector.origin == TOSS_ORIGIN
        assert connector._http_client.base_url == httpx.URL(TOSS_ORIGIN)
        assert connector._http_client.trust_env is False
        assert connector._http_client.follow_redirects is False
        timeout = connector._http_client.timeout
        assert (timeout.connect, timeout.read, timeout.write, timeout.pool) == (5.0, 10.0, 5.0, 5.0)
    finally:
        run(connector.aclose())


def test_tls_verification_is_enabled_and_has_no_public_disable_option() -> None:
    connector = TossHttpClient(settings())
    try:
        assert set(inspect.signature(TossHttpClient).parameters) == {"settings"}
        transport = connector._http_client._transport
        ssl_context = transport._pool._ssl_context
        assert ssl_context.verify_mode == ssl.CERT_REQUIRED
        assert ssl_context.check_hostname is True
    finally:
        run(connector.aclose())


@pytest.mark.parametrize(
    "untrusted_endpoint",
    [
        "https://evil.example/api/v1/stocks",
        "http://openapi.tossinvest.com/api/v1/stocks",
        "https://user:" + "password@openapi.tossinvest.com/api/v1/stocks",
        "https://openapi.tossinvest.com.evil.example/api/v1/stocks",
    ],
)
def test_arbitrary_origin_variants_are_rejected_before_transport(
    untrusted_endpoint: str,
) -> None:
    provider = SuccessProvider()

    async def scenario() -> None:
        async with client(provider) as connector:
            with pytest.raises(TossBoundaryError):
                await connector.get(cast(Any, untrusted_endpoint))

    run(scenario())
    assert provider.token_calls == 0
    assert provider.get_calls == 0


@pytest.mark.parametrize("endpoint", list(TossStaticEndpoint))
def test_every_exact_static_get_path_is_allowed(endpoint: TossStaticEndpoint) -> None:
    provider = SuccessProvider()

    async def scenario() -> None:
        async with client(provider) as connector:
            assert await connector.get(endpoint) == {"result": []}

    run(scenario())
    get_request = provider.requests[-1]
    assert get_request.method == "GET"
    assert get_request.url.path == endpoint.value
    assert get_request.url.host == "openapi.tossinvest.com"


@pytest.mark.parametrize("endpoint", list(TossSymbolEndpoint))
def test_every_exact_symbol_get_path_is_allowed(endpoint: TossSymbolEndpoint) -> None:
    provider = SuccessProvider()

    async def scenario() -> None:
        async with client(provider) as connector:
            assert await connector.get_symbol(endpoint, "005930") == {"result": []}

    run(scenario())
    get_request = provider.requests[-1]
    assert get_request.method == "GET"
    assert get_request.url.path == endpoint.value.replace("{symbol}", "005930")


@pytest.mark.parametrize(
    "symbol",
    [
        "",
        "../stocks",
        "A/B",
        "A\\B",
        "A?x=1",
        "A#fragment",
        "%2e%2e",
        "https://evil.example",
        "file:payload",
    ],
)
def test_symbol_cannot_escape_the_path_boundary(symbol: str) -> None:
    provider = SuccessProvider()

    async def scenario() -> None:
        async with client(provider) as connector:
            with pytest.raises(TossBoundaryError):
                await connector.get_symbol(TossSymbolEndpoint.INVESTOR_TRADING, symbol)

    run(scenario())
    assert provider.token_calls == 0


@pytest.mark.parametrize(
    "unknown_path",
    [
        "/api/v1/unknown",
        "/api/v1/accounts",
        "/api/v1/holdings",
        "/api/v1/orders",
        "/api/v1/conditional-orders",
    ],
)
def test_unknown_account_and_order_paths_are_rejected(unknown_path: str) -> None:
    provider = SuccessProvider()

    async def scenario() -> None:
        async with client(provider) as connector:
            with pytest.raises(TossBoundaryError):
                await connector.get(cast(Any, unknown_path))

    run(scenario())
    assert provider.token_calls == 0


def test_public_api_has_no_arbitrary_method_url_or_header_surface() -> None:
    assert not hasattr(TossHttpClient, "request")
    assert not hasattr(TossHttpClient, "post")
    assert not hasattr(TossHttpClient, "put")
    assert not hasattr(TossHttpClient, "patch")
    assert not hasattr(TossHttpClient, "delete")
    assert not hasattr(TossHttpClient, "set_rate_limit")
    assert not hasattr(TossHttpClient, "disable_rate_limit")
    assert not hasattr(TossHttpClient, "set_retry_count")
    assert not hasattr(TossHttpClient, "disable_tls")
    assert not hasattr(TossHttpClient, "set_base_url")
    assert not hasattr(TossHttpClient, "raw_headers")
    get_parameters = inspect.signature(TossHttpClient.get).parameters
    symbol_parameters = inspect.signature(TossHttpClient.get_symbol).parameters
    assert "url" not in get_parameters
    assert "method" not in get_parameters
    assert "headers" not in get_parameters
    assert "headers" not in symbol_parameters


def test_only_token_post_and_allowlisted_get_headers_are_constructed() -> None:
    provider = SuccessProvider()

    async def scenario() -> None:
        async with client(provider) as connector:
            await connector.get(TossStaticEndpoint.PRICES, params={"symbols": "005930"})

    run(scenario())
    token_request, get_request = provider.requests
    assert token_request.method == "POST"
    assert token_request.url.path == TOKEN_PATH
    assert "authorization" not in token_request.headers
    assert "cookie" not in token_request.headers
    assert get_request.method == "GET"
    assert get_request.url.path == TossStaticEndpoint.PRICES
    assert set(get_request.headers) == {"host", "accept", "authorization", "user-agent"}
    assert "x-tossinvest-account" not in get_request.headers
    assert "cookie" not in get_request.headers


def test_query_requires_an_exact_structured_mapping() -> None:
    provider = SuccessProvider()

    async def scenario() -> None:
        async with client(provider) as connector:
            with pytest.raises(TossBoundaryError):
                await connector.get(
                    TossStaticEndpoint.PRICES,
                    params=cast(Any, "symbols=005930"),
                )
            with pytest.raises(TossBoundaryError):
                await connector.get(
                    TossStaticEndpoint.PRICES,
                    params={"Authorization": "prohibited"},
                )
            with pytest.raises(TossBoundaryError):
                await connector.get(
                    TossStaticEndpoint.PRICES,
                    params={"symbols": cast(Any, ["005930"])},
                )

    run(scenario())
    assert provider.token_calls == 0


def test_redirect_is_not_followed() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if request.url.path == TOKEN_PATH:
            return response(200, token_payload())
        return httpx.Response(
            302,
            headers={"location": "https://evil.example/redirected"},
        )

    async def scenario() -> None:
        async with client(handler) as connector:
            with pytest.raises(TossRedirectError):
                await connector.get(TossStaticEndpoint.STOCKS)

    run(scenario())
    assert calls == 2


def test_client_context_manager_closes_resources() -> None:
    provider = SuccessProvider()
    connector = client(provider)

    async def scenario() -> None:
        async with connector:
            await connector.get(TossStaticEndpoint.STOCKS)
            assert connector.is_closed is False
        assert connector.is_closed is True
        assert connector._http_client.is_closed is True
        with pytest.raises(TossLifecycleError):
            await connector.get(TossStaticEndpoint.STOCKS)
        await connector.aclose()

    run(scenario())


def test_cookie_response_state_is_never_replayed() -> None:
    market_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal market_calls
        assert "cookie" not in request.headers
        if request.url.path == TOKEN_PATH:
            result = response(200, token_payload())
            result.headers["set-cookie"] = "fixture=session"
            return result
        market_calls += 1
        result = response(200, {"result": []})
        result.headers["set-cookie"] = "fixture=market"
        return result

    async def scenario() -> None:
        async with client(handler) as connector:
            await connector.get(TossStaticEndpoint.STOCKS)
            await connector.get(TossStaticEndpoint.STOCKS)
            assert len(connector._http_client.cookies) == 0

    run(scenario())
    assert market_calls == 2


def test_auth_then_get_and_cached_token_integration() -> None:
    provider = SuccessProvider()

    async def scenario() -> None:
        async with client(provider) as connector:
            for _ in range(3):
                assert await connector.get(TossStaticEndpoint.STOCKS) == {"result": []}

    run(scenario())
    assert provider.token_calls == 1
    assert provider.get_calls == 3


def test_expired_token_causes_one_reissue_and_one_get_replay() -> None:
    token_calls = 0
    get_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal token_calls, get_calls
        if request.url.path == TOKEN_PATH:
            token_calls += 1
            return response(200, token_payload(f"lease-{token_calls}"))
        get_calls += 1
        if get_calls == 1:
            return response(401, error_payload("expired-token"))
        return response(200, {"result": []})

    async def scenario() -> None:
        async with client(handler) as connector:
            assert await connector.get(TossStaticEndpoint.STOCKS) == {"result": []}

    run(scenario())
    assert (token_calls, get_calls) == (2, 2)


def test_second_refreshable_401_stops_without_a_third_issuance() -> None:
    token_calls = 0
    get_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal token_calls, get_calls
        if request.url.path == TOKEN_PATH:
            token_calls += 1
            return response(200, token_payload(f"lease-{token_calls}"))
        get_calls += 1
        return response(401, error_payload("invalid-token"))

    async def scenario() -> None:
        async with client(handler) as connector:
            with pytest.raises(TossAuthenticationError) as captured:
                await connector.get(TossStaticEndpoint.STOCKS)
            assert captured.value.provider_code == "invalid-token"

    run(scenario())
    assert (token_calls, get_calls) == (2, 2)


def test_non_refreshable_401_does_not_reissue() -> None:
    token_calls = 0
    get_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal token_calls, get_calls
        if request.url.path == TOKEN_PATH:
            token_calls += 1
            return response(200, token_payload())
        get_calls += 1
        return response(401, error_payload("login-user-not-found"))

    async def scenario() -> None:
        async with client(handler) as connector:
            with pytest.raises(TossAuthenticationError):
                await connector.get(TossStaticEndpoint.STOCKS)

    run(scenario())
    assert (token_calls, get_calls) == (1, 1)


@pytest.mark.parametrize(
    ("status_code", "code", "error_type"),
    [
        (403, "forbidden", TossPermissionError),
        (429, "rate-limit-exceeded", TossRetryExhaustedError),
        (500, "internal-error", TossRetryExhaustedError),
    ],
)
def test_403_is_not_retried_and_retryable_failures_exhaust_safely(
    status_code: int,
    code: str,
    error_type: type[TossHttpError],
) -> None:
    provider = SuccessProvider()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == TOKEN_PATH:
            return provider(request)
        provider.get_calls += 1
        return response(status_code, error_payload(code))

    async def scenario() -> None:
        async with client(handler) as connector:
            with pytest.raises(error_type):
                await connector.get(TossStaticEndpoint.STOCKS)

    run(scenario())
    assert provider.token_calls == 1
    assert provider.get_calls == (1 if status_code == 403 else 3)


def test_market_html_response_is_a_content_type_contract_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == TOKEN_PATH:
            return response(200, token_payload())
        return httpx.Response(200, text="<html></html>", headers={"content-type": "text/html"})

    async def scenario() -> None:
        async with client(handler) as connector:
            with pytest.raises(TossContentTypeError):
                await connector.get(TossStaticEndpoint.STOCKS)

    run(scenario())


def test_market_malformed_json_is_wrapped() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == TOKEN_PATH:
            return response(200, token_payload())
        return httpx.Response(
            200,
            content=b"{",
            headers={"content-type": "application/json"},
        )

    async def scenario() -> None:
        async with client(handler) as connector:
            with pytest.raises(TossResponseContractError) as captured:
                await connector.get(TossStaticEndpoint.STOCKS)
            assert captured.value.reason == "malformed-json"

    run(scenario())


def test_declared_oversized_response_is_rejected_before_body_trust() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == TOKEN_PATH:
            return response(200, token_payload())
        return httpx.Response(
            200,
            content=b"{}",
            headers={
                "content-type": "application/json",
                "content-length": str(MARKET_RESPONSE_MAX_BYTES + 1),
            },
        )

    async def scenario() -> None:
        async with client(handler) as connector:
            with pytest.raises(TossResponseTooLargeError) as captured:
                await connector.get(TossStaticEndpoint.STOCKS_ALL)
            assert captured.value.limit_bytes == MARKET_RESPONSE_MAX_BYTES

    run(scenario())


def test_error_body_message_and_unknown_code_are_not_exposed() -> None:
    body_canary = "sensitive-" + "provider-body"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == TOKEN_PATH:
            return response(200, token_payload())
        return response(400, error_payload("unknown-provider-code", body_canary))

    async def scenario() -> None:
        async with client(handler) as connector:
            with pytest.raises(TossHttpError) as captured:
                await connector.get(TossStaticEndpoint.STOCKS)
            assert captured.value.provider_code is None
            assert body_canary not in str(captured.value)
            assert body_canary not in repr(captured.value)

    run(scenario())


def test_concurrent_expired_requests_share_one_refresh_generation() -> None:
    request_count = 24
    token_calls = 0
    old_token_gets = 0
    new_token_gets = 0
    all_old_requests_arrived = asyncio.Event()

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal token_calls, old_token_gets, new_token_gets
        if request.url.path == TOKEN_PATH:
            token_calls += 1
            return response(200, token_payload(f"lease-{token_calls}"))
        if request.headers["authorization"].endswith("lease-1"):
            old_token_gets += 1
            if old_token_gets == request_count:
                all_old_requests_arrived.set()
            await all_old_requests_arrived.wait()
            return response(401, error_payload("expired-token"))
        new_token_gets += 1
        return response(200, {"result": []})

    async def scenario() -> None:
        async with client(handler) as connector:
            results = await asyncio.gather(
                *(connector.get(TossStaticEndpoint.STOCKS) for _ in range(request_count))
            )
            assert results == [{"result": []}] * request_count

    run(scenario())
    assert token_calls == 2
    assert old_token_gets == request_count
    assert new_token_gets == request_count


def test_late_previous_generation_401_does_not_invalidate_the_new_token() -> None:
    token_calls = 0
    old_requests = 0
    new_requests = 0
    both_old_requests_arrived = asyncio.Event()
    new_token_issued = asyncio.Event()

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal token_calls, old_requests, new_requests
        if request.url.path == TOKEN_PATH:
            token_calls += 1
            if token_calls == 2:
                new_token_issued.set()
            return response(200, token_payload(f"lease-{token_calls}"))
        if request.headers["authorization"].endswith("lease-1"):
            old_requests += 1
            request_index = old_requests
            if old_requests == 2:
                both_old_requests_arrived.set()
            await both_old_requests_arrived.wait()
            if request_index == 2:
                await new_token_issued.wait()
            return response(401, error_payload("expired-token"))
        new_requests += 1
        return response(200, {"result": []})

    async def scenario() -> None:
        async with client(handler) as connector:
            results = await asyncio.gather(
                connector.get(TossStaticEndpoint.STOCKS),
                connector.get(TossStaticEndpoint.STOCKS),
            )
            assert results == [{"result": []}, {"result": []}]

    run(scenario())
    assert token_calls == 2
    assert old_requests == 2
    assert new_requests == 2
