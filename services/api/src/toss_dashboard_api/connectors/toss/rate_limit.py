from __future__ import annotations

import asyncio
import math
import random
import re
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

from toss_dashboard_api.connectors.toss.models import (
    TOKEN_PATH,
    TossStaticEndpoint,
    TossSymbolEndpoint,
)

MAX_TOTAL_ATTEMPTS = 3
MAX_SINGLE_RETRY_SLEEP_SECONDS = 30.0
MAX_CUMULATIVE_RETRY_SLEEP_SECONDS = 30.0
INITIAL_BACKOFF_SECONDS = 1.0
MAX_RATE_LIMIT_HEADER_VALUE = 10_000
MAX_SECONDS_HEADER_VALUE = 86_400
MIN_THROTTLE_SLEEP_SECONDS = 0.000_001
TOKEN_EPSILON = 0.000_000_001
RETRYABLE_TRANSIENT_STATUSES = frozenset({500, 502, 503, 504})
RETRYABLE_TRANSIENT_PROVIDER_CODES = frozenset({"internal-error", "maintenance"})
RETRYABLE_RATE_PROVIDER_CODES = frozenset({"edge-rate-limit-exceeded", "rate-limit-exceeded"})

_INTEGER_HEADER_PATTERN = re.compile(r"^[0-9]+$")
_RATE_HEADER_NAMES = (
    "X-RateLimit-Limit",
    "X-RateLimit-Remaining",
    "X-RateLimit-Reset",
    "Retry-After",
)
_RATE_HEADER_LOOKUP = MappingProxyType(
    {header_name.lower(): header_name for header_name in _RATE_HEADER_NAMES}
)
_DEFAULT_JITTER = random.Random()

MonotonicClock = Callable[[], float]
AsyncSleeper = Callable[[float], Awaitable[None]]
JitterSource = Callable[[], float]


class TossRateLimitGroup(StrEnum):
    AUTH = "AUTH"
    STOCK = "STOCK"
    STOCK_ALL = "STOCK_ALL"
    STOCK_TRADING_TREND = "STOCK_TRADING_TREND"
    MARKET_INFO = "MARKET_INFO"
    MARKET_DATA = "MARKET_DATA"
    MARKET_DATA_CHART = "MARKET_DATA_CHART"


DOCUMENTED_RATE_LIMITS: Mapping[TossRateLimitGroup, int] = MappingProxyType(
    {
        TossRateLimitGroup.AUTH: 5,
        TossRateLimitGroup.STOCK: 5,
        TossRateLimitGroup.STOCK_ALL: 1,
        TossRateLimitGroup.STOCK_TRADING_TREND: 10,
        TossRateLimitGroup.MARKET_INFO: 3,
        TossRateLimitGroup.MARKET_DATA: 15,
        TossRateLimitGroup.MARKET_DATA_CHART: 20,
    }
)

ENDPOINT_RATE_GROUPS: Mapping[tuple[str, str], TossRateLimitGroup] = MappingProxyType(
    {
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
)


def rate_group_for(method: str, endpoint_template: str) -> TossRateLimitGroup:
    try:
        return ENDPOINT_RATE_GROUPS[(method, endpoint_template)]
    except KeyError:
        raise ValueError("unknown Toss endpoint rate group") from None


class RateHeaderDiagnostic(StrEnum):
    RATE_HEADERS_MISSING = "RATE_HEADERS_MISSING"
    RATE_HEADERS_INVALID = "RATE_HEADERS_INVALID"
    RATE_HEADERS_INCONSISTENT = "RATE_HEADERS_INCONSISTENT"


@dataclass(frozen=True, slots=True)
class RateHeaderTelemetry:
    limit: int | None
    remaining: int | None
    reset_seconds: int | None
    retry_after_seconds: int | None
    diagnostics: frozenset[RateHeaderDiagnostic]


@dataclass(frozen=True, slots=True)
class RateLimitSnapshot:
    group: TossRateLimitGroup
    documented_limit: int
    observed_limit: int | None
    effective_limit: int
    remaining: int | None
    reset_seconds: int | None
    retry_after_seconds: int | None
    last_diagnostics: frozenset[RateHeaderDiagnostic]
    diagnostic_counts: tuple[tuple[RateHeaderDiagnostic, int], ...]
    blocked_for_seconds: float


def parse_rate_headers(
    headers: Mapping[str, str],
    *,
    status_code: int,
    current_limit: int,
) -> RateHeaderTelemetry:
    selected = _select_rate_headers(headers)
    diagnostics: set[RateHeaderDiagnostic] = set()
    required_names = _RATE_HEADER_NAMES[:3]
    if any(name not in selected for name in required_names) or (
        status_code == 429 and "Retry-After" not in selected
    ):
        diagnostics.add(RateHeaderDiagnostic.RATE_HEADERS_MISSING)

    limit = _parse_header_integer(
        selected.get("X-RateLimit-Limit"),
        minimum=1,
        maximum=MAX_RATE_LIMIT_HEADER_VALUE,
        diagnostics=diagnostics,
    )
    remaining = _parse_header_integer(
        selected.get("X-RateLimit-Remaining"),
        minimum=0,
        maximum=MAX_RATE_LIMIT_HEADER_VALUE,
        diagnostics=diagnostics,
    )
    reset_seconds = _parse_header_integer(
        selected.get("X-RateLimit-Reset"),
        minimum=0,
        maximum=MAX_SECONDS_HEADER_VALUE,
        diagnostics=diagnostics,
    )
    retry_after_seconds = _parse_header_integer(
        selected.get("Retry-After"),
        minimum=0,
        maximum=MAX_SECONDS_HEADER_VALUE,
        diagnostics=diagnostics,
    )

    consistency_limit = limit if limit is not None else current_limit
    if remaining is not None and (
        remaining > consistency_limit or (status_code == 429 and remaining != 0)
    ):
        remaining = None
        diagnostics.add(RateHeaderDiagnostic.RATE_HEADERS_INCONSISTENT)

    return RateHeaderTelemetry(
        limit=limit,
        remaining=remaining,
        reset_seconds=reset_seconds,
        retry_after_seconds=retry_after_seconds,
        diagnostics=frozenset(diagnostics),
    )


def _select_rate_headers(headers: Mapping[str, str]) -> dict[str, str | None]:
    selected: dict[str, str | None] = {}
    for name, value in headers.items():
        canonical_name = _RATE_HEADER_LOOKUP.get(name.lower())
        if canonical_name is None:
            continue
        if canonical_name in selected:
            selected[canonical_name] = None
            continue
        selected[canonical_name] = value if isinstance(value, str) else None
    return selected


def _parse_header_integer(
    value: str | None,
    *,
    minimum: int,
    maximum: int,
    diagnostics: set[RateHeaderDiagnostic],
) -> int | None:
    if value is None:
        return None
    if _INTEGER_HEADER_PATTERN.fullmatch(value) is None:
        diagnostics.add(RateHeaderDiagnostic.RATE_HEADERS_INVALID)
        return None
    parsed = int(value)
    if parsed < minimum or parsed > maximum:
        diagnostics.add(RateHeaderDiagnostic.RATE_HEADERS_INVALID)
        return None
    return parsed


class RetryDisposition(StrEnum):
    RETRY = "RETRY"
    DEFER = "DEFER"
    EXHAUSTED = "EXHAUSTED"


@dataclass(frozen=True, slots=True)
class RetryTimingDecision:
    disposition: RetryDisposition
    delay_seconds: float | None


class _RetryBudget:
    def __init__(self, jitter: JitterSource) -> None:
        self._jitter = jitter
        self.attempt_count = 1
        self.cumulative_sleep_seconds = 0.0

    def next_timing(self, *, retry_after_seconds: int | None) -> RetryTimingDecision:
        if self.attempt_count >= MAX_TOTAL_ATTEMPTS:
            return RetryTimingDecision(RetryDisposition.EXHAUSTED, None)

        if retry_after_seconds is not None:
            delay = float(retry_after_seconds)
            if (
                delay > MAX_SINGLE_RETRY_SLEEP_SECONDS
                or self.cumulative_sleep_seconds + delay > MAX_CUMULATIVE_RETRY_SLEEP_SECONDS
            ):
                return RetryTimingDecision(RetryDisposition.DEFER, delay)
            return RetryTimingDecision(RetryDisposition.RETRY, delay)

        retry_ordinal = self.attempt_count
        base_delay = INITIAL_BACKOFF_SECONDS * (2 ** (retry_ordinal - 1))
        delay = min(
            base_delay + base_delay * _bounded_jitter(self._jitter),
            MAX_SINGLE_RETRY_SLEEP_SECONDS,
        )
        if self.cumulative_sleep_seconds + delay > MAX_CUMULATIVE_RETRY_SLEEP_SECONDS:
            return RetryTimingDecision(RetryDisposition.EXHAUSTED, None)
        return RetryTimingDecision(RetryDisposition.RETRY, delay)

    def record_retry(self, delay_seconds: float) -> None:
        self.attempt_count += 1
        self.cumulative_sleep_seconds += delay_seconds


def _bounded_jitter(jitter: JitterSource) -> float:
    try:
        value = float(jitter())
    except (TypeError, ValueError, OverflowError):
        return 0.0
    if not math.isfinite(value):
        return 0.0
    return min(1.0, max(0.0, value))


class _RateLimitWaitDeferred(Exception):
    def __init__(self, retry_after_seconds: float) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("rate limit wait exceeds the connector blocking ceiling")


@dataclass(slots=True)
class _GroupState:
    documented_limit: int
    tokens: float
    updated_at: float
    observed_limit: int | None = None
    remaining: int | None = None
    reset_seconds: int | None = None
    retry_after_seconds: int | None = None
    last_diagnostics: frozenset[RateHeaderDiagnostic] = frozenset()
    diagnostic_counts: dict[RateHeaderDiagnostic, int] = field(default_factory=dict)
    blocked_until: float = 0.0

    @property
    def effective_limit(self) -> int:
        if self.observed_limit is None:
            return self.documented_limit
        return min(self.documented_limit, self.observed_limit)


@dataclass(slots=True)
class _GroupBucket:
    state: _GroupState
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class _TossRateLimiter:
    def __init__(
        self,
        *,
        monotonic: MonotonicClock | None = None,
        sleeper: AsyncSleeper | None = None,
        jitter: JitterSource | None = None,
    ) -> None:
        self._monotonic = monotonic if monotonic is not None else time.monotonic
        self._sleeper = sleeper if sleeper is not None else asyncio.sleep
        self._jitter = jitter if jitter is not None else _DEFAULT_JITTER.random
        now = self._safe_now()
        self._buckets = {
            group: _GroupBucket(
                _GroupState(
                    documented_limit=documented_limit,
                    tokens=float(documented_limit),
                    updated_at=now,
                )
            )
            for group, documented_limit in DOCUMENTED_RATE_LIMITS.items()
        }

    def new_retry_budget(self) -> _RetryBudget:
        return _RetryBudget(self._jitter)

    async def acquire(self, group: TossRateLimitGroup) -> None:
        bucket = self._bucket(group)
        while True:
            async with bucket.lock:
                now = self._safe_now()
                self._refill(bucket.state, now)
                blocked_for = max(0.0, bucket.state.blocked_until - now)
                if blocked_for > MAX_SINGLE_RETRY_SLEEP_SECONDS:
                    raise _RateLimitWaitDeferred(blocked_for)
                if blocked_for > 0.0:
                    delay = blocked_for
                elif bucket.state.tokens >= 1.0 - TOKEN_EPSILON:
                    bucket.state.tokens = max(0.0, bucket.state.tokens - 1.0)
                    return
                else:
                    delay = max(
                        (1.0 - bucket.state.tokens) / bucket.state.effective_limit,
                        MIN_THROTTLE_SLEEP_SECONDS,
                    )
            await self._sleeper(delay)

    async def observe(
        self,
        group: TossRateLimitGroup,
        headers: Mapping[str, str],
        *,
        status_code: int,
    ) -> RateHeaderTelemetry:
        bucket = self._bucket(group)
        async with bucket.lock:
            now = self._safe_now()
            self._refill(bucket.state, now)
            telemetry = parse_rate_headers(
                headers,
                status_code=status_code,
                current_limit=bucket.state.effective_limit,
            )
            if telemetry.limit is not None:
                bucket.state.observed_limit = telemetry.limit
                bucket.state.tokens = min(bucket.state.tokens, float(bucket.state.effective_limit))
            if telemetry.remaining is not None:
                bucket.state.remaining = telemetry.remaining
                bucket.state.tokens = min(bucket.state.tokens, float(telemetry.remaining))
            if telemetry.reset_seconds is not None:
                bucket.state.reset_seconds = telemetry.reset_seconds
                if telemetry.remaining == 0:
                    bucket.state.blocked_until = max(
                        bucket.state.blocked_until,
                        now + telemetry.reset_seconds,
                    )
            if telemetry.retry_after_seconds is not None:
                bucket.state.retry_after_seconds = telemetry.retry_after_seconds
            bucket.state.last_diagnostics = telemetry.diagnostics
            for diagnostic in telemetry.diagnostics:
                bucket.state.diagnostic_counts[diagnostic] = (
                    bucket.state.diagnostic_counts.get(diagnostic, 0) + 1
                )
            return telemetry

    async def block_for(self, group: TossRateLimitGroup, seconds: float) -> None:
        if not math.isfinite(seconds) or seconds < 0.0:
            raise ValueError("rate limit block must be finite and non-negative")
        bucket = self._bucket(group)
        async with bucket.lock:
            now = self._safe_now()
            bucket.state.blocked_until = max(bucket.state.blocked_until, now + seconds)

    async def sleep_for_retry(self, group: TossRateLimitGroup, seconds: float) -> None:
        if seconds > MAX_SINGLE_RETRY_SLEEP_SECONDS:
            raise ValueError("retry sleep exceeds the connector ceiling")
        await self.block_for(group, seconds)
        await self._sleeper(seconds)

    async def snapshot(self, group: TossRateLimitGroup) -> RateLimitSnapshot:
        bucket = self._bucket(group)
        async with bucket.lock:
            now = self._safe_now()
            self._refill(bucket.state, now)
            return RateLimitSnapshot(
                group=group,
                documented_limit=bucket.state.documented_limit,
                observed_limit=bucket.state.observed_limit,
                effective_limit=bucket.state.effective_limit,
                remaining=bucket.state.remaining,
                reset_seconds=bucket.state.reset_seconds,
                retry_after_seconds=bucket.state.retry_after_seconds,
                last_diagnostics=bucket.state.last_diagnostics,
                diagnostic_counts=tuple(
                    sorted(
                        bucket.state.diagnostic_counts.items(),
                        key=lambda item: item[0].value,
                    )
                ),
                blocked_for_seconds=max(0.0, bucket.state.blocked_until - now),
            )

    def _bucket(self, group: TossRateLimitGroup) -> _GroupBucket:
        if not isinstance(group, TossRateLimitGroup):
            raise ValueError("unknown Toss rate limit group")
        try:
            return self._buckets[group]
        except KeyError:
            raise ValueError("unknown Toss rate limit group") from None

    def _safe_now(self) -> float:
        now = float(self._monotonic())
        if not math.isfinite(now):
            raise RuntimeError("monotonic clock returned a non-finite value")
        return now

    @staticmethod
    def _refill(state: _GroupState, now: float) -> None:
        if now <= state.updated_at:
            return
        elapsed = now - state.updated_at
        state.tokens = min(
            float(state.effective_limit),
            state.tokens + elapsed * state.effective_limit,
        )
        state.updated_at = now
