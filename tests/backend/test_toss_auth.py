from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
import pytest

from toss_dashboard_api.config import Settings
from toss_dashboard_api.connectors.toss.auth import (
    TossCredentialState,
    credential_state,
)
from toss_dashboard_api.connectors.toss.client import TossHttpClient
from toss_dashboard_api.connectors.toss.errors import (
    TossConfigurationError,
    TossContentTypeError,
    TossInvalidClientError,
    TossOAuthPermissionError,
    TossResponseContractError,
    TossTransportError,
)
from toss_dashboard_api.connectors.toss.models import TOKEN_PATH

Handler = Callable[[httpx.Request], Awaitable[httpx.Response] | httpx.Response]


class ManualClock:
    def __init__(self) -> None:
        self.value = 100.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def run(awaitable: Awaitable[Any]) -> Any:
    return asyncio.run(awaitable)


def synthetic_settings(
    *,
    client_id: bool = True,
    client_secret: bool = True,
) -> Settings:
    credential_value = "synthetic-" + "credential-value"
    return Settings(
        toss_client_id=credential_value if client_id else None,
        toss_client_secret=credential_value if client_secret else None,
    )


def token_payload(value: str = "lease-one", expires_in: object = 120) -> dict[str, object]:
    return {
        "access_" + "token": value,
        "token_type": "Bearer",
        "expires_in": expires_in,
    }


def mock_client(
    handler: Handler,
    *,
    settings: Settings | None = None,
    clock: ManualClock | None = None,
) -> TossHttpClient:
    return TossHttpClient._for_test(
        settings or synthetic_settings(),
        httpx.MockTransport(handler),
        monotonic=clock,
    )


def json_response(
    status_code: int,
    payload: object,
    *,
    content_type: str = "application/json; charset=utf-8",
) -> httpx.Response:
    return httpx.Response(
        status_code,
        json=payload,
        headers={"content-type": content_type},
    )


def test_missing_credentials_are_lazy_and_structured() -> None:
    settings = synthetic_settings(client_id=False, client_secret=False)
    assert credential_state(settings) is TossCredentialState.UNAVAILABLE
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise AssertionError("missing credentials must fail before transport")

    async def scenario() -> None:
        async with mock_client(handler, settings=settings) as client:
            with pytest.raises(TossConfigurationError) as captured:
                await client.token_manager.get_token()
            assert captured.value.credential_state == "missing-credentials"

    run(scenario())
    assert calls == 0


@pytest.mark.parametrize(("client_id", "client_secret"), [(True, False), (False, True)])
def test_partial_credentials_fail_closed(client_id: bool, client_secret: bool) -> None:
    settings = synthetic_settings(client_id=client_id, client_secret=client_secret)
    assert credential_state(settings) is TossCredentialState.PARTIAL

    async def scenario() -> None:
        async with mock_client(
            lambda _request: json_response(500, {}), settings=settings
        ) as client:
            with pytest.raises(TossConfigurationError) as captured:
                await client.token_manager.get_token()
            assert captured.value.credential_state == "partial-credentials"

    run(scenario())


def test_valid_token_response_uses_exact_form_contract_without_bearer() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert request.method == "POST"
        assert request.url.path == TOKEN_PATH
        assert request.url.host == "openapi.tossinvest.com"
        assert request.headers["content-type"].startswith("application/x-www-form-urlencoded")
        assert "authorization" not in request.headers
        fields = dict(item.split("=", 1) for item in request.content.decode("ascii").split("&"))
        assert fields["grant_type"] == "client_credentials"
        assert set(fields) == {"grant_type", "client_id", "client_secret"}
        return json_response(200, token_payload())

    async def scenario() -> None:
        async with mock_client(handler) as client:
            lease = await client.token_manager.get_token()
            assert lease.generation == 1
            assert "lease-one" not in repr(lease)

    run(scenario())
    assert calls == 1


def test_malformed_token_json_is_wrapped_without_body() -> None:
    body_canary = "body-" + "fixture"

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=("{" + body_canary).encode(),
            headers={"content-type": "application/json"},
        )

    async def scenario() -> None:
        async with mock_client(handler) as client:
            with pytest.raises(TossResponseContractError) as captured:
                await client.token_manager.get_token()
            assert body_canary not in str(captured.value)
            assert body_canary not in repr(captured.value)

    run(scenario())


@pytest.mark.parametrize(
    "payload",
    [
        {"token_type": "Bearer", "expires_in": 120},
        token_payload() | {"token_type": "bearer"},
        {"access_" + "token": "lease-one", "token_type": "Bearer"},
        token_payload(expires_in=True),
        token_payload(expires_in=0),
        token_payload(expires_in=-1),
        token_payload() | {"refresh_" + "token": "prohibited"},
        token_payload(value=" "),
    ],
)
def test_invalid_token_contracts_fail_closed(payload: dict[str, object]) -> None:
    async def scenario() -> None:
        async with mock_client(lambda _request: json_response(200, payload)) as client:
            with pytest.raises(TossResponseContractError):
                await client.token_manager.get_token()

    run(scenario())


def test_token_and_expiry_are_memory_only_and_safe_in_repr() -> None:
    token_canary = "memory-" + "only"

    async def scenario() -> None:
        async with mock_client(
            lambda _request: json_response(200, token_payload(token_canary))
        ) as client:
            lease = await client.token_manager.get_token()
            rendered = repr(client.token_manager.__dict__)
            assert token_canary not in repr(lease)
            assert token_canary not in rendered
            assert not hasattr(client.token_manager, "database")
            assert not hasattr(client.token_manager, "storage_path")

    run(scenario())


def test_explicit_invalidation_forces_one_new_generation() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return json_response(200, token_payload(f"lease-{calls}"))

    async def scenario() -> None:
        async with mock_client(handler) as client:
            first = await client.token_manager.get_token()
            await client.token_manager.invalidate()
            second = await client.token_manager.get_token()
            assert second is not first
            assert (first.generation, second.generation) == (1, 2)

    run(scenario())
    assert calls == 2


def test_cached_valid_token_is_reused() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return json_response(200, token_payload())

    async def scenario() -> None:
        async with mock_client(handler) as client:
            first = await client.token_manager.get_token()
            second = await client.token_manager.get_token()
            assert second is first

    run(scenario())
    assert calls == 1


def test_one_hundred_concurrent_get_token_calls_are_single_flight() -> None:
    calls = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        return json_response(200, token_payload())

    async def scenario() -> None:
        async with mock_client(handler) as client:
            leases = await asyncio.gather(*(client.token_manager.get_token() for _ in range(100)))
            assert len({id(lease) for lease in leases}) == 1
            assert {lease.generation for lease in leases} == {1}

    run(scenario())
    assert calls == 1


def test_issuance_failure_releases_the_single_flight_lock() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return json_response(200, {"invalid": "shape"})
        return json_response(200, token_payload())

    async def scenario() -> None:
        async with mock_client(handler) as client:
            with pytest.raises(TossResponseContractError):
                await client.token_manager.get_token()
            lease = await client.token_manager.get_token()
            assert lease.generation == 1

    run(scenario())
    assert calls == 2


def test_cancelled_issuance_does_not_deadlock_the_next_caller() -> None:
    calls = 0
    started = asyncio.Event()
    never_release = asyncio.Event()

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            started.set()
            await never_release.wait()
        return json_response(200, token_payload())

    async def scenario() -> None:
        async with mock_client(handler) as client:
            task = asyncio.create_task(client.token_manager.get_token())
            await started.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            lease = await asyncio.wait_for(client.token_manager.get_token(), timeout=1)
            assert lease.generation == 1

    run(scenario())
    assert calls == 2


def test_monotonic_expiry_reissues_without_wall_clock_dependency() -> None:
    calls = 0
    clock = ManualClock()

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return json_response(200, token_payload(f"lease-{calls}", expires_in=10))

    async def scenario() -> None:
        async with mock_client(handler, clock=clock) as client:
            first = await client.token_manager.get_token()
            clock.advance(8.99)
            assert await client.token_manager.get_token() is first
            clock.advance(0.01)
            second = await client.token_manager.get_token()
            assert second.generation == 2

    run(scenario())
    assert calls == 2


def test_short_expiry_margin_is_bounded_and_not_immediately_expired() -> None:
    calls = 0
    clock = ManualClock()

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return json_response(200, token_payload(f"lease-{calls}", expires_in=1))

    async def scenario() -> None:
        async with mock_client(handler, clock=clock) as client:
            first = await client.token_manager.get_token()
            assert await client.token_manager.get_token() is first
            clock.advance(0.89)
            assert await client.token_manager.get_token() is first
            clock.advance(0.01)
            assert (await client.token_manager.get_token()).generation == 2

    run(scenario())
    assert calls == 2


def test_generation_aware_invalidation_ignores_a_stale_generation() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return json_response(200, token_payload(f"lease-{calls}"))

    async def scenario() -> None:
        async with mock_client(handler) as client:
            first = await client.token_manager.get_token()
            assert await client.token_manager.invalidate_if_current(first.generation) is True
            second = await client.token_manager.get_token()
            assert await client.token_manager.invalidate_if_current(first.generation) is False
            assert await client.token_manager.get_token() is second

    run(scenario())
    assert calls == 2


def test_invalid_client_and_permission_failures_are_distinct() -> None:
    async def invalid_client_scenario() -> None:
        async with mock_client(
            lambda _request: json_response(
                401,
                {"error": "invalid_client", "error_description": "not retained"},
            )
        ) as client:
            with pytest.raises(TossInvalidClientError):
                await client.token_manager.get_token()

    async def permission_scenario() -> None:
        async with mock_client(
            lambda _request: json_response(
                403,
                {"error": "access_denied", "error_description": "not retained"},
            )
        ) as client:
            with pytest.raises(TossOAuthPermissionError):
                await client.token_manager.get_token()

    run(invalid_client_scenario())
    run(permission_scenario())


def test_oauth_transport_failure_is_safely_wrapped() -> None:
    credential_canary = "credential-" + "fixture"
    settings = Settings(
        toss_client_id=credential_canary,
        toss_client_secret=credential_canary,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("raw failure must not escape", request=request)

    async def scenario() -> None:
        async with mock_client(handler, settings=settings) as client:
            with pytest.raises(TossTransportError) as captured:
                await client.token_manager.get_token()
            assert credential_canary not in str(captured.value)
            assert credential_canary not in repr(captured.value)
            assert "raw failure" not in str(captured.value)

    run(scenario())


def test_oauth_rejects_non_json_content_type() -> None:
    async def scenario() -> None:
        async with mock_client(
            lambda _request: httpx.Response(
                200,
                text="not json",
                headers={"content-type": "text/plain"},
            )
        ) as client:
            with pytest.raises(TossContentTypeError):
                await client.token_manager.get_token()

    run(scenario())
