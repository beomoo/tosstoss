from __future__ import annotations

import asyncio
import math
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
import pytest

from toss_dashboard_api.config import Settings
from toss_dashboard_api.connectors.toss.auth import _token_manager_test_seam
from toss_dashboard_api.connectors.toss.client import TossHttpClient
from toss_dashboard_api.connectors.toss.errors import (
    TossHttpError,
    TossPermissionError,
    TossResponseContractError,
    TossRetryDeferredError,
    TossRetryExhaustedError,
    TossServerError,
    TossTransportError,
)
from toss_dashboard_api.connectors.toss.models import (
    TOKEN_PATH,
    TossStaticEndpoint,
    TossSymbolEndpoint,
)
from toss_dashboard_api.connectors.toss.rate_limit import (
    DOCUMENTED_RATE_LIMITS,
    ENDPOINT_RATE_GROUPS,
    MAX_CUMULATIVE_RETRY_SLEEP_SECONDS,
    MAX_SINGLE_RETRY_SLEEP_SECONDS,
    MAX_TOTAL_ATTEMPTS,
    RateHeaderDiagnostic,
    RetryDisposition,
    TossRateLimitGroup,
    _RetryBudget,
    _TossRateLimiter,
    parse_rate_headers,
    rate_group_for,
)

Handler = Callable[[httpx.Request], Awaitable[httpx.Response] | httpx.Response]


class FakeTime:
    def __init__(self) -> None:
        self.value = 1_000.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.value

    async def sleep(self, seconds: float) -> None:
        assert 0.0 <= seconds <= MAX_SINGLE_RETRY_SLEEP_SECONDS
        self.sleeps.append(seconds)
        self.value += seconds
        await asyncio.sleep(0)

    def advance(self, seconds: float) -> None:
        self.value += seconds


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


def error_payload(code: str, *, message: str = "not retained") -> dict[str, object]:
    return {
        "error": {
            "requestId": "01HXYZABCDEFG123456789",
            "code": code,
            "message": message,
        }
    }


def headers(
    *,
    limit: str = "5",
    remaining: str = "4",
    reset: str = "1",
    retry_after: str | None = None,
) -> dict[str, str]:
    values = {
        "X-RateLimit-Limit": limit,
        "X-RateLimit-Remaining": remaining,
        "X-RateLimit-Reset": reset,
    }
    if retry_after is not None:
        values["Retry-After"] = retry_after
    return values


def response(
    status_code: int,
    payload: object,
    *,
    rate_headers: dict[str, str] | None = None,
    extra_headers: dict[str, str] | None = None,
) -> httpx.Response:
    response_headers = {"content-type": "application/json; charset=utf-8"}
    if rate_headers is not None:
        response_headers.update(rate_headers)
    if extra_headers is not None:
        response_headers.update(extra_headers)
    return httpx.Response(status_code, json=payload, headers=response_headers)


def client(handler: Handler, fake_time: FakeTime | None = None) -> tuple[TossHttpClient, FakeTime]:
    clock = fake_time or FakeTime()
    connector = TossHttpClient._for_test(
        settings(),
        httpx.MockTransport(handler),
        monotonic=clock,
        sleeper=clock.sleep,
        jitter=lambda: 0.0,
    )
    return connector, clock


def test_endpoint_to_rate_group_mapping_is_exact_and_has_no_fallback() -> None:
    expected = {
        ("POST", TOKEN_PATH): TossRateLimitGroup.AUTH,
        ("GET", TossStaticEndpoint.STOCKS.value): TossRateLimitGroup.STOCK,
        ("GET", TossStaticEndpoint.STOCKS_ALL.value): TossRateLimitGroup.STOCK_ALL,
        ("GET", TossStaticEndpoint.PRICES.value): TossRateLimitGroup.MARKET_DATA,
        ("GET", TossStaticEndpoint.CANDLES.value): TossRateLimitGroup.MARKET_DATA_CHART,
        (
            "GET",
            TossSymbolEndpoint.INVESTOR_TRADING.value,
        ): TossRateLimitGroup.STOCK_TRADING_TREND,
        (
            "GET",
            TossSymbolEndpoint.PROGRAM_TRADES.value,
        ): TossRateLimitGroup.STOCK_TRADING_TREND,
        (
            "GET",
            TossSymbolEndpoint.SHORT_SELLING.value,
        ): TossRateLimitGroup.STOCK_TRADING_TREND,
        (
            "GET",
            TossSymbolEndpoint.CREDIT_TRADES.value,
        ): TossRateLimitGroup.STOCK_TRADING_TREND,
        (
            "GET",
            TossSymbolEndpoint.SECURITIES_LENDING.value,
        ): TossRateLimitGroup.STOCK_TRADING_TREND,
        ("GET", TossStaticEndpoint.MARKET_CALENDAR_KR.value): TossRateLimitGroup.MARKET_INFO,
        ("GET", TossStaticEndpoint.MARKET_CALENDAR_US.value): TossRateLimitGroup.MARKET_INFO,
    }
    assert dict(ENDPOINT_RATE_GROUPS) == expected
    assert all(rate_group_for(*key) is group for key, group in expected.items())
    with pytest.raises(ValueError):
        rate_group_for("GET", "/api/v1/unknown")
    with pytest.raises(ValueError):
        rate_group_for("get", TossStaticEndpoint.STOCKS.value)


def test_all_seven_callable_groups_and_documented_limits_are_fixed() -> None:
    assert set(DOCUMENTED_RATE_LIMITS) == set(TossRateLimitGroup)
    assert dict(DOCUMENTED_RATE_LIMITS) == {
        TossRateLimitGroup.AUTH: 5,
        TossRateLimitGroup.STOCK: 5,
        TossRateLimitGroup.STOCK_ALL: 1,
        TossRateLimitGroup.STOCK_TRADING_TREND: 10,
        TossRateLimitGroup.MARKET_INFO: 3,
        TossRateLimitGroup.MARKET_DATA: 15,
        TossRateLimitGroup.MARKET_DATA_CHART: 20,
    }


def test_same_group_uses_one_bucket_and_enforces_documented_limit() -> None:
    clock = FakeTime()
    limiter = _TossRateLimiter(monotonic=clock, sleeper=clock.sleep, jitter=lambda: 0.0)

    async def scenario() -> None:
        for _ in range(10):
            await limiter.acquire(TossRateLimitGroup.STOCK_TRADING_TREND)
        await limiter.acquire(TossRateLimitGroup.STOCK_TRADING_TREND)

    run(scenario())
    assert clock.sleeps == [0.1]


def test_different_endpoint_templates_share_the_client_group_bucket() -> None:
    clock = FakeTime()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == TOKEN_PATH:
            return response(200, token_payload())
        return response(200, {"result": []})

    async def scenario() -> None:
        connector, _clock = client(handler, clock)
        endpoints = list(TossSymbolEndpoint)
        async with connector:
            for _ in range(2):
                for endpoint in endpoints:
                    await connector.get_symbol(endpoint, "005930")
            await connector.get_symbol(TossSymbolEndpoint.INVESTOR_TRADING, "005930")

    run(scenario())
    assert clock.sleeps == [0.1]


def test_different_groups_do_not_block_each_other() -> None:
    clock = FakeTime()
    limiter = _TossRateLimiter(monotonic=clock, sleeper=clock.sleep, jitter=lambda: 0.0)

    async def scenario() -> None:
        await limiter.acquire(TossRateLimitGroup.STOCK_ALL)
        await limiter.acquire(TossRateLimitGroup.MARKET_INFO)

    run(scenario())
    assert clock.sleeps == []


def test_documented_one_tps_limit_throttles_before_transport_time() -> None:
    clock = FakeTime()
    limiter = _TossRateLimiter(monotonic=clock, sleeper=clock.sleep, jitter=lambda: 0.0)

    async def scenario() -> None:
        await limiter.acquire(TossRateLimitGroup.STOCK_ALL)
        await limiter.acquire(TossRateLimitGroup.STOCK_ALL)

    run(scenario())
    assert clock.sleeps == [1.0]


def test_lower_observed_limit_immediately_reduces_effective_limit() -> None:
    clock = FakeTime()
    limiter = _TossRateLimiter(monotonic=clock, sleeper=clock.sleep, jitter=lambda: 0.0)

    async def scenario() -> None:
        await limiter.observe(
            TossRateLimitGroup.STOCK,
            headers(limit="2", remaining="2"),
            status_code=200,
        )
        snapshot = await limiter.snapshot(TossRateLimitGroup.STOCK)
        assert (snapshot.documented_limit, snapshot.observed_limit, snapshot.effective_limit) == (
            5,
            2,
            2,
        )
        await limiter.acquire(TossRateLimitGroup.STOCK)
        await limiter.acquire(TossRateLimitGroup.STOCK)
        await limiter.acquire(TossRateLimitGroup.STOCK)

    run(scenario())
    assert clock.sleeps == [0.5]


def test_higher_observed_limit_never_expands_documented_ceiling() -> None:
    limiter = _TossRateLimiter(jitter=lambda: 0.0)

    async def scenario() -> None:
        await limiter.observe(
            TossRateLimitGroup.STOCK,
            headers(limit="50", remaining="50"),
            status_code=200,
        )
        snapshot = await limiter.snapshot(TossRateLimitGroup.STOCK)
        assert snapshot.observed_limit == 50
        assert snapshot.effective_limit == 5

    run(scenario())


def test_valid_remaining_and_reset_are_parsed_and_observed() -> None:
    limiter = _TossRateLimiter(jitter=lambda: 0.0)

    async def scenario() -> None:
        telemetry = await limiter.observe(
            TossRateLimitGroup.MARKET_INFO,
            headers(limit="3", remaining="2", reset="7"),
            status_code=200,
        )
        snapshot = await limiter.snapshot(TossRateLimitGroup.MARKET_INFO)
        assert (telemetry.remaining, telemetry.reset_seconds) == (2, 7)
        assert (snapshot.remaining, snapshot.reset_seconds) == (2, 7)

    run(scenario())


@pytest.mark.parametrize(
    "value",
    ["0", "-1", "NaN", "Infinity", "1.5", "10001", " 5"],
)
def test_malformed_limit_is_rejected_safely(value: str) -> None:
    telemetry = parse_rate_headers(
        headers(limit=value, remaining="0"),
        status_code=200,
        current_limit=5,
    )
    assert telemetry.limit is None
    assert RateHeaderDiagnostic.RATE_HEADERS_INVALID in telemetry.diagnostics


@pytest.mark.parametrize("value", ["-1", "NaN", "Infinity", "1.5", "10001", " 4"])
def test_malformed_remaining_is_rejected_safely(value: str) -> None:
    telemetry = parse_rate_headers(
        headers(remaining=value),
        status_code=200,
        current_limit=5,
    )
    assert telemetry.remaining is None
    assert RateHeaderDiagnostic.RATE_HEADERS_INVALID in telemetry.diagnostics


def test_remaining_above_limit_is_inconsistent_and_rejected() -> None:
    telemetry = parse_rate_headers(
        headers(limit="5", remaining="6"),
        status_code=200,
        current_limit=5,
    )
    assert telemetry.remaining is None
    assert RateHeaderDiagnostic.RATE_HEADERS_INCONSISTENT in telemetry.diagnostics


@pytest.mark.parametrize("value", ["-1", "NaN", "Infinity", "1.5", "86401", " 1"])
def test_malformed_reset_is_rejected_safely(value: str) -> None:
    telemetry = parse_rate_headers(
        headers(reset=value),
        status_code=200,
        current_limit=5,
    )
    assert telemetry.reset_seconds is None
    assert RateHeaderDiagnostic.RATE_HEADERS_INVALID in telemetry.diagnostics


@pytest.mark.parametrize("value", ["-1", "NaN", "Infinity", "1.5", "86401", " 1"])
def test_retry_after_uses_strict_seconds_parsing(value: str) -> None:
    telemetry = parse_rate_headers(
        headers(remaining="0", retry_after=value),
        status_code=429,
        current_limit=5,
    )
    assert telemetry.retry_after_seconds is None
    assert RateHeaderDiagnostic.RATE_HEADERS_INVALID in telemetry.diagnostics


def test_missing_rate_headers_do_not_fail_a_valid_success_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == TOKEN_PATH:
            return response(200, token_payload())
        return response(200, {"result": []})

    async def scenario() -> None:
        connector, _clock = client(handler)
        async with connector:
            assert await connector.get(TossStaticEndpoint.PRICES) == {"result": []}
            snapshot = await connector._rate_limit_snapshot_for_test(TossRateLimitGroup.MARKET_DATA)
            assert snapshot.last_diagnostics == frozenset(
                {RateHeaderDiagnostic.RATE_HEADERS_MISSING}
            )

    run(scenario())


def test_429_valid_retry_after_has_priority_over_backoff() -> None:
    get_calls = 0
    clock = FakeTime()

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal get_calls
        if request.url.path == TOKEN_PATH:
            return response(200, token_payload())
        get_calls += 1
        if get_calls == 1:
            return response(
                429,
                error_payload("rate-limit-exceeded"),
                rate_headers=headers(remaining="0", reset="1", retry_after="3"),
            )
        return response(200, {"result": []}, rate_headers=headers())

    async def scenario() -> None:
        connector, _clock = client(handler, clock)
        async with connector:
            assert await connector.get(TossStaticEndpoint.STOCKS) == {"result": []}

    run(scenario())
    assert get_calls == 2
    assert clock.sleeps == [3.0]


@pytest.mark.parametrize("retry_after", [None, "NaN"])
def test_429_without_valid_retry_after_uses_exponential_backoff(
    retry_after: str | None,
) -> None:
    get_calls = 0
    clock = FakeTime()

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal get_calls
        if request.url.path == TOKEN_PATH:
            return response(200, token_payload())
        get_calls += 1
        if get_calls < 3:
            return response(
                429,
                error_payload("edge-rate-limit-exceeded"),
                rate_headers=headers(
                    remaining="0",
                    reset="0",
                    retry_after=retry_after,
                ),
            )
        return response(200, {"result": []}, rate_headers=headers())

    async def scenario() -> None:
        connector, _clock = client(handler, clock)
        async with connector:
            assert await connector.get(TossStaticEndpoint.STOCKS) == {"result": []}

    run(scenario())
    assert get_calls == 3
    assert clock.sleeps == [1.0, 2.0]


def test_jitter_is_deterministic_and_bounded_by_retry_ceilings() -> None:
    budget = _RetryBudget(lambda: 1.0)
    first = budget.next_timing(retry_after_seconds=None)
    assert first.disposition is RetryDisposition.RETRY
    assert first.delay_seconds == 2.0
    budget.record_retry(first.delay_seconds)
    second = budget.next_timing(retry_after_seconds=None)
    assert second.disposition is RetryDisposition.RETRY
    assert second.delay_seconds == 4.0
    assert second.delay_seconds <= MAX_SINGLE_RETRY_SLEEP_SECONDS

    invalid_jitter_budget = _RetryBudget(lambda: math.nan)
    assert invalid_jitter_budget.next_timing(retry_after_seconds=None).delay_seconds == 1.0


def test_max_attempts_are_enforced() -> None:
    budget = _RetryBudget(lambda: 0.0)
    for expected_delay in (1.0, 2.0):
        decision = budget.next_timing(retry_after_seconds=None)
        assert decision.delay_seconds == expected_delay
        budget.record_retry(expected_delay)
    assert budget.attempt_count == MAX_TOTAL_ATTEMPTS
    assert budget.next_timing(retry_after_seconds=None).disposition is RetryDisposition.EXHAUSTED


def test_max_single_wait_and_cumulative_wait_are_enforced() -> None:
    budget = _RetryBudget(lambda: 0.0)
    single = budget.next_timing(retry_after_seconds=int(MAX_SINGLE_RETRY_SLEEP_SECONDS + 1))
    assert single.disposition is RetryDisposition.DEFER

    first = budget.next_timing(retry_after_seconds=20)
    assert first.disposition is RetryDisposition.RETRY
    budget.record_retry(20.0)
    cumulative = budget.next_timing(retry_after_seconds=20)
    assert cumulative.disposition is RetryDisposition.DEFER
    assert budget.cumulative_sleep_seconds <= MAX_CUMULATIVE_RETRY_SLEEP_SECONDS


def test_excessive_retry_after_returns_deferred_without_sleep_or_retry() -> None:
    get_calls = 0
    clock = FakeTime()

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal get_calls
        if request.url.path == TOKEN_PATH:
            return response(200, token_payload())
        get_calls += 1
        return response(
            429,
            error_payload("rate-limit-exceeded"),
            rate_headers=headers(remaining="0", reset="1", retry_after="31"),
        )

    async def scenario() -> None:
        connector, _clock = client(handler, clock)
        async with connector:
            with pytest.raises(TossRetryDeferredError) as captured:
                await connector.get(TossStaticEndpoint.STOCKS)
            assert captured.value.retry_after_seconds == 31
            assert captured.value.attempt_count == 1
            snapshot = await connector._rate_limit_snapshot_for_test(TossRateLimitGroup.STOCK)
            assert snapshot.blocked_for_seconds == 31.0

    run(scenario())
    assert get_calls == 1
    assert clock.sleeps == []


@pytest.mark.parametrize("provider_code", ["internal-error", "maintenance"])
def test_transient_500_retries_then_succeeds(provider_code: str) -> None:
    get_calls = 0
    clock = FakeTime()

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal get_calls
        if request.url.path == TOKEN_PATH:
            return response(200, token_payload())
        get_calls += 1
        if get_calls == 1:
            return response(500, error_payload(provider_code), rate_headers=headers())
        return response(200, {"result": []}, rate_headers=headers())

    async def scenario() -> None:
        connector, _clock = client(handler, clock)
        async with connector:
            assert await connector.get(TossStaticEndpoint.STOCKS) == {"result": []}

    run(scenario())
    assert get_calls == 2
    assert clock.sleeps == [1.0]


def test_repeated_500_returns_typed_retry_exhaustion() -> None:
    get_calls = 0
    clock = FakeTime()

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal get_calls
        if request.url.path == TOKEN_PATH:
            return response(200, token_payload())
        get_calls += 1
        return response(500, error_payload("internal-error"), rate_headers=headers())

    async def scenario() -> None:
        connector, _clock = client(handler, clock)
        async with connector:
            with pytest.raises(TossRetryExhaustedError) as captured:
                await connector.get(TossStaticEndpoint.STOCKS)
            assert captured.value.attempt_count == MAX_TOTAL_ATTEMPTS
            assert captured.value.rate_group == TossRateLimitGroup.STOCK.value

    run(scenario())
    assert get_calls == MAX_TOTAL_ATTEMPTS
    assert clock.sleeps == [1.0, 2.0]


@pytest.mark.parametrize("status_code", [502, 503, 504])
def test_exact_transient_status_allowlist_retries(status_code: int) -> None:
    get_calls = 0
    clock = FakeTime()

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal get_calls
        if request.url.path == TOKEN_PATH:
            return response(200, token_payload())
        get_calls += 1
        if get_calls == 1:
            return response(status_code, error_payload("internal-error"), rate_headers=headers())
        return response(200, {"result": []}, rate_headers=headers())

    async def scenario() -> None:
        connector, _clock = client(handler, clock)
        async with connector:
            assert await connector.get(TossStaticEndpoint.STOCKS) == {"result": []}

    run(scenario())
    assert get_calls == 2
    assert clock.sleeps == [1.0]


def test_501_is_not_in_the_transient_retry_allowlist() -> None:
    get_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal get_calls
        if request.url.path == TOKEN_PATH:
            return response(200, token_payload())
        get_calls += 1
        return response(501, error_payload("internal-error"), rate_headers=headers())

    async def scenario() -> None:
        connector, clock = client(handler)
        async with connector:
            with pytest.raises(TossServerError):
                await connector.get(TossStaticEndpoint.STOCKS)
        assert clock.sleeps == []

    run(scenario())
    assert get_calls == 1


@pytest.mark.parametrize(
    ("status_code", "provider_code", "error_type"),
    [
        (400, "invalid-request", TossHttpError),
        (403, "forbidden", TossPermissionError),
        (404, "stock-not-found", TossHttpError),
        (422, "invalid-request", TossHttpError),
    ],
)
def test_request_permission_and_not_found_errors_are_not_retried(
    status_code: int,
    provider_code: str,
    error_type: type[TossHttpError],
) -> None:
    get_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal get_calls
        if request.url.path == TOKEN_PATH:
            return response(200, token_payload())
        get_calls += 1
        return response(status_code, error_payload(provider_code), rate_headers=headers())

    async def scenario() -> None:
        connector, clock = client(handler)
        async with connector:
            with pytest.raises(error_type):
                await connector.get(TossStaticEndpoint.STOCKS)
        assert clock.sleeps == []

    run(scenario())
    assert get_calls == 1


def test_unknown_transient_semantics_are_not_retried() -> None:
    get_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal get_calls
        if request.url.path == TOKEN_PATH:
            return response(200, token_payload())
        get_calls += 1
        return response(500, error_payload("unknown-code"), rate_headers=headers())

    async def scenario() -> None:
        connector, clock = client(handler)
        async with connector:
            with pytest.raises(TossServerError) as captured:
                await connector.get(TossStaticEndpoint.STOCKS)
            assert captured.value.provider_code is None
        assert clock.sleeps == []

    run(scenario())
    assert get_calls == 1


def test_malformed_provider_error_is_not_retried() -> None:
    get_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal get_calls
        if request.url.path == TOKEN_PATH:
            return response(200, token_payload())
        get_calls += 1
        return response(
            500,
            {"error": {"requestId": "safe", "code": "internal-error"}},
            rate_headers=headers(),
        )

    async def scenario() -> None:
        connector, clock = client(handler)
        async with connector:
            with pytest.raises(TossResponseContractError):
                await connector.get(TossStaticEndpoint.STOCKS)
        assert clock.sleeps == []

    run(scenario())
    assert get_calls == 1


def test_malformed_json_is_not_retried() -> None:
    get_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal get_calls
        if request.url.path == TOKEN_PATH:
            return response(200, token_payload())
        get_calls += 1
        return httpx.Response(
            500,
            content=b"{",
            headers={"content-type": "application/json"} | headers(),
        )

    async def scenario() -> None:
        connector, clock = client(handler)
        async with connector:
            with pytest.raises(TossResponseContractError) as captured:
                await connector.get(TossStaticEndpoint.STOCKS)
            assert captured.value.reason == "malformed-json"
        assert clock.sleeps == []

    run(scenario())
    assert get_calls == 1


def test_transport_error_behavior_is_preserved_without_retry() -> None:
    get_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal get_calls
        if request.url.path == TOKEN_PATH:
            return response(200, token_payload())
        get_calls += 1
        raise httpx.ConnectError("not exposed", request=request)

    async def scenario() -> None:
        connector, clock = client(handler)
        async with connector:
            with pytest.raises(TossTransportError):
                await connector.get(TossStaticEndpoint.STOCKS)
        assert clock.sleeps == []

    run(scenario())
    assert get_calls == 1


def test_oauth_429_retry_remains_single_flight_for_100_callers() -> None:
    token_calls = 0
    clock = FakeTime()

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal token_calls
        token_calls += 1
        if token_calls == 1:
            return response(
                429,
                error_payload("rate-limit-exceeded"),
                rate_headers=headers(remaining="0", retry_after="1"),
            )
        return response(200, token_payload())

    async def scenario() -> None:
        async with _token_manager_test_seam(
            settings(),
            httpx.MockTransport(handler),
            monotonic=clock,
            sleeper=clock.sleep,
            jitter=lambda: 0.0,
        ) as manager:
            leases = await asyncio.gather(*(manager.get_token() for _ in range(100)))
            assert len({id(lease) for lease in leases}) == 1
            assert {lease.generation for lease in leases} == {1}

    run(scenario())
    assert token_calls == 2
    assert clock.sleeps == [1.0]


@pytest.mark.parametrize("provider_code", ["internal-error", "maintenance"])
def test_oauth_transient_500_retries_within_auth_budget(provider_code: str) -> None:
    token_calls = 0
    clock = FakeTime()

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal token_calls
        token_calls += 1
        if token_calls == 1:
            return response(500, error_payload(provider_code), rate_headers=headers())
        return response(200, token_payload())

    async def scenario() -> None:
        async with _token_manager_test_seam(
            settings(),
            httpx.MockTransport(handler),
            monotonic=clock,
            sleeper=clock.sleep,
            jitter=lambda: 0.0,
        ) as manager:
            assert (await manager.get_token()).generation == 1

    run(scenario())
    assert token_calls == 2
    assert clock.sleeps == [1.0]


def test_concurrent_same_group_calls_preserve_limiter_integrity() -> None:
    clock = FakeTime()
    limiter = _TossRateLimiter(monotonic=clock, sleeper=clock.sleep, jitter=lambda: 0.0)

    async def scenario() -> None:
        await asyncio.gather(*(limiter.acquire(TossRateLimitGroup.STOCK_ALL) for _ in range(20)))
        snapshot = await limiter.snapshot(TossRateLimitGroup.STOCK_ALL)
        assert snapshot.effective_limit == 1

    run(scenario())
    assert len(clock.sleeps) == 19
    assert set(clock.sleeps) == {1.0}


def test_cancellation_during_limiter_wait_does_not_corrupt_state() -> None:
    clock = FakeTime()
    started = asyncio.Event()
    never_release = asyncio.Event()

    async def blocking_sleep(_seconds: float) -> None:
        started.set()
        await never_release.wait()

    limiter = _TossRateLimiter(
        monotonic=clock,
        sleeper=blocking_sleep,
        jitter=lambda: 0.0,
    )

    async def scenario() -> None:
        await limiter.acquire(TossRateLimitGroup.STOCK_ALL)
        waiter = asyncio.create_task(limiter.acquire(TossRateLimitGroup.STOCK_ALL))
        await started.wait()
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter
        clock.advance(1.0)
        await asyncio.wait_for(
            limiter.acquire(TossRateLimitGroup.STOCK_ALL),
            timeout=1.0,
        )

    run(scenario())


def test_401_refresh_with_oauth_429_keeps_one_get_replay() -> None:
    token_calls = 0
    get_calls = 0
    clock = FakeTime()

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal token_calls, get_calls
        if request.url.path == TOKEN_PATH:
            token_calls += 1
            if token_calls == 2:
                return response(
                    429,
                    error_payload("rate-limit-exceeded"),
                    rate_headers=headers(remaining="0", retry_after="1"),
                )
            return response(200, token_payload(f"lease-{token_calls}"))
        get_calls += 1
        if get_calls == 1:
            return response(401, error_payload("expired-token"), rate_headers=headers())
        return response(200, {"result": []}, rate_headers=headers())

    async def scenario() -> None:
        connector, _clock = client(handler, clock)
        async with connector:
            assert await connector.get(TossStaticEndpoint.STOCKS) == {"result": []}

    run(scenario())
    assert (token_calls, get_calls) == (3, 2)
    assert clock.sleeps == [1.0]


def test_rate_state_and_retry_error_retain_no_secret_header_or_body() -> None:
    body_canary = "provider-" + "body-canary"
    header_canary = "response-" + "secret-canary"
    get_calls = 0
    captured_error: TossRetryExhaustedError | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal get_calls
        if request.url.path == TOKEN_PATH:
            return response(200, token_payload())
        get_calls += 1
        return response(
            429,
            error_payload("rate-limit-exceeded", message=body_canary),
            rate_headers=headers(remaining="0", reset="0"),
            extra_headers={
                "Authorization": header_canary,
                "Cookie": header_canary,
                "Set-Cookie": f"fixture={header_canary}",
                "X-Untrusted": header_canary,
            },
        )

    async def scenario() -> None:
        nonlocal captured_error
        connector, _clock = client(handler)
        async with connector:
            with pytest.raises(TossRetryExhaustedError) as captured:
                await connector.get(TossStaticEndpoint.STOCKS)
            captured_error = captured.value
            snapshot = await connector._rate_limit_snapshot_for_test(TossRateLimitGroup.STOCK)
            rendered_state = repr(snapshot)
            assert body_canary not in rendered_state
            assert header_canary not in rendered_state
            assert len(connector._http_client.cookies) == 0

    run(scenario())
    assert captured_error is not None
    rendered_error = repr(captured_error)
    assert body_canary not in rendered_error
    assert header_canary not in rendered_error
    assert "credential-value" not in rendered_error
    assert get_calls == MAX_TOTAL_ATTEMPTS
