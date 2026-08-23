from __future__ import annotations

import ast
import asyncio
import hashlib
import inspect
import ssl
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from toss_dashboard_api.config import Settings
from toss_dashboard_api.connectors import toss
from toss_dashboard_api.connectors.toss.models import (
    JSON_MEDIA_TYPE,
    TOKEN_PATH,
    TOSS_ORIGIN,
    TossStaticEndpoint,
)
from toss_dashboard_api.connectors.toss.preflight import (
    APPROVED_CONTRACT_SHA256,
    APPROVED_OPENAPI_VERSION,
    APPROVED_REST_VERSION,
    CANONICAL_OPENAPI_PATH,
    LIVE_SUMMARY_KEYS,
    PREFLIGHT_SYMBOL_MAX_LENGTH,
    _ApprovedContract,
    _build_http_client,
    _run_offline_self_test,
    _run_preflight_for_test,
    _synthetic_contract,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT_SOURCE = (
    PROJECT_ROOT
    / "services"
    / "api"
    / "src"
    / "toss_dashboard_api"
    / "connectors"
    / "toss"
    / "preflight.py"
)
POWERSHELL_SCRIPT = PROJECT_ROOT / "scripts" / "toss-live-preflight.ps1"
RUNNER_SCRIPT = PROJECT_ROOT / "scripts" / "toss_live_preflight_runner.py"

Handler = Callable[[httpx.Request], httpx.Response]


def run(awaitable: Awaitable[Any]) -> Any:
    return asyncio.run(awaitable)


def provider_error(code: str, message: str = "private provider message") -> dict[str, object]:
    return {
        "error": {
            "requestId": "01HXYZABCDEFG123456789",
            "code": code,
            "message": message,
        }
    }


def oauth_token(token: str) -> dict[str, object]:
    return {
        "access_" + "token": token,
        "token_type": "Bearer",
        "expires_in": 120,
    }


def rate_headers(
    *,
    limit: str = "5",
    remaining: str = "4",
    reset: str = "1",
    retry_after: str | None = None,
) -> dict[str, str]:
    headers = {
        "X-RateLimit-Limit": limit,
        "X-RateLimit-Remaining": remaining,
        "X-RateLimit-Reset": reset,
    }
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return headers


class ScenarioProvider:
    def __init__(self) -> None:
        self.contract, self.approved = _synthetic_contract()
        self.contract_status = 200
        self.contract_headers: dict[str, str] = {"content-type": JSON_MEDIA_TYPE}
        self.oauth_status = 200
        self.oauth_payload: object = oauth_token("synthetic-" + "one-shot-token")
        self.oauth_headers: dict[str, str] = {"content-type": JSON_MEDIA_TYPE}
        self.market_status = 200
        self.market_payload: object = {"result": []}
        self.market_headers: dict[str, str] = {
            "content-type": JSON_MEDIA_TYPE,
            **rate_headers(),
        }
        self.requests: list[httpx.Request] = []
        self.counts = {"contract": 0, "oauth": 0, "market": 0}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path == CANONICAL_OPENAPI_PATH:
            self.counts["contract"] += 1
            return httpx.Response(
                self.contract_status,
                content=self.contract,
                headers=self.contract_headers,
            )
        if request.url.path == TOKEN_PATH:
            self.counts["oauth"] += 1
            return httpx.Response(
                self.oauth_status,
                json=self.oauth_payload,
                headers=self.oauth_headers,
            )
        if request.url.path == TossStaticEndpoint.STOCKS.value:
            self.counts["market"] += 1
            return httpx.Response(
                self.market_status,
                json=self.market_payload,
                headers=self.market_headers,
            )
        raise AssertionError("Preflight reached an unapproved endpoint.")


def synthetic_settings() -> Settings:
    credential = "synthetic-" + "preflight-credential"
    return Settings(TOSS_CLIENT_ID=credential, TOSS_CLIENT_SECRET=credential)


def execute(
    provider: ScenarioProvider,
    *,
    settings_factory: Callable[[], Settings] = synthetic_settings,
    symbol: str = "SYNTHETIC-1",
    approved: _ApprovedContract | None = None,
):
    return run(
        _run_preflight_for_test(
            symbol,
            settings_factory=settings_factory,
            approved=approved or provider.approved,
            transport=httpx.MockTransport(provider),
        )
    )


def summary(result: Any) -> dict[str, str]:
    return dict(result.lines)


def test_runtime_approved_contract_is_exact_and_not_auto_updated() -> None:
    assert APPROVED_OPENAPI_VERSION == "3.1.0"
    assert APPROVED_REST_VERSION == "1.2.14"
    assert APPROVED_CONTRACT_SHA256 == (
        "fccf49ab"
        "d11f37f5"
        "57bdd349"
        "138f4a03"
        "c42b829e"
        "bd8b5c14"
        "ab490711"
        "6fb84c7a"
    )
    assert TOSS_ORIGIN == "https://openapi.tossinvest.com"
    assert CANONICAL_OPENAPI_PATH == "/openapi-docs/latest/openapi.json"


def test_preflight_http_client_refuses_redirects_proxy_environment_and_insecure_tls() -> None:
    client = _build_http_client(httpx.MockTransport(lambda _request: httpx.Response(200)))
    try:
        assert client.base_url == httpx.URL(TOSS_ORIGIN)
        assert client.follow_redirects is False
        assert client.trust_env is False
        assert set(inspect.signature(_build_http_client).parameters) == {"transport"}
    finally:
        run(client.aclose())

    live_client = _build_http_client()
    try:
        transport = live_client._transport
        ssl_context = transport._pool._ssl_context
        assert ssl_context.verify_mode == ssl.CERT_REQUIRED
        assert ssl_context.check_hostname is True
    finally:
        run(live_client.aclose())


@pytest.mark.parametrize(
    "symbol",
    [
        "",
        "../unsafe",
        "005930?extra=1",
        "A/B",
        "한글",
        "A" * (PREFLIGHT_SYMBOL_MAX_LENGTH + 1),
    ],
)
def test_invalid_symbol_stops_before_any_transport_or_credential_read(symbol: str) -> None:
    provider = ScenarioProvider()
    settings_reads = 0

    def forbidden_settings() -> Settings:
        nonlocal settings_reads
        settings_reads += 1
        raise AssertionError("Invalid-symbol path read credentials.")

    result = execute(provider, settings_factory=forbidden_settings, symbol=symbol)
    assert summary(result)["ERROR_CATEGORY"] == "BOUNDARY"
    assert provider.counts == {"contract": 0, "oauth": 0, "market": 0}
    assert settings_reads == 0


def test_contract_drift_stops_before_credentials_oauth_and_market() -> None:
    provider = ScenarioProvider()
    provider.contract = (
        b'{"info":{"version":"9.9.9"},"openapi":"9.9.9",'
        b'"servers":[{"url":"https://openapi.tossinvest.com"}]}'
    )
    settings_reads = 0

    def forbidden_settings() -> Settings:
        nonlocal settings_reads
        settings_reads += 1
        raise AssertionError("Drift path read credentials.")

    result = execute(provider, settings_factory=forbidden_settings)
    values = summary(result)
    assert values["PROVIDER_CONTRACT_DRIFT"] == "YES"
    assert values["CONTRACT_SHA_MATCH"] == "NO"
    assert values["OAUTH_REQUEST"] == "NOT_ATTEMPTED"
    assert values["MARKET_REQUEST"] == "NOT_ATTEMPTED"
    assert provider.counts == {"contract": 1, "oauth": 0, "market": 0}
    assert settings_reads == 0


def test_contract_origin_drift_is_fail_closed_even_with_an_approved_synthetic_hash() -> None:
    provider = ScenarioProvider()
    contract = (
        b'{"info":{"version":"1.2.14"},"openapi":"3.1.0",'
        b'"servers":[{"url":"https://outside.invalid"}]}'
    )
    provider.contract = contract
    altered = _ApprovedContract(
        APPROVED_OPENAPI_VERSION,
        APPROVED_REST_VERSION,
        hashlib.sha256(contract).hexdigest(),
        TOSS_ORIGIN,
    )
    result = execute(provider, approved=altered)
    assert summary(result)["CONTRACT_ORIGIN_MATCH"] == "NO"
    assert summary(result)["PROVIDER_CONTRACT_DRIFT"] == "YES"
    assert provider.counts == {"contract": 1, "oauth": 0, "market": 0}


def test_success_is_exactly_one_contract_one_oauth_and_one_stock_get() -> None:
    provider = ScenarioProvider()
    result = execute(provider)
    values = summary(result)
    assert result.passed is True
    assert provider.counts == {"contract": 1, "oauth": 1, "market": 1}
    assert values["PROVIDER_CONTRACT_DRIFT"] == "NO"
    assert values["OAUTH_REQUEST"] == "PASS"
    assert values["MARKET_REQUEST"] == "PASS"
    assert values["MARKET_ENDPOINT"] == TossStaticEndpoint.STOCKS.value


def test_request_boundaries_are_exact_and_account_header_is_absent() -> None:
    provider = ScenarioProvider()
    execute(provider, symbol="SYNTHETIC.1")
    assert [(request.method, request.url.path) for request in provider.requests] == [
        ("GET", CANONICAL_OPENAPI_PATH),
        ("POST", TOKEN_PATH),
        ("GET", TossStaticEndpoint.STOCKS.value),
    ]
    market = provider.requests[-1]
    assert dict(market.url.params) == {"symbols": "SYNTHETIC.1"}
    assert (market.url.scheme, market.url.host, market.url.port) == (
        "https",
        "openapi.tossinvest.com",
        None,
    )
    assert {name.lower() for name in market.headers} == {
        "host",
        "accept",
        "authorization",
        "user-agent",
    }
    prohibited_header = ("X-Tossinvest-" + "Account").lower()
    assert prohibited_header not in market.headers


@pytest.mark.parametrize(
    ("status_code", "payload", "category"),
    [
        (401, {"error": "invalid_client"}, "AUTH"),
        (403, {"error": "access_denied"}, "PERMISSION"),
    ],
)
def test_oauth_401_or_403_is_one_attempt_and_market_is_not_called(
    status_code: int,
    payload: object,
    category: str,
) -> None:
    provider = ScenarioProvider()
    provider.oauth_status = status_code
    provider.oauth_payload = payload
    result = execute(provider)
    values = summary(result)
    assert values["ERROR_CATEGORY"] == category
    assert values["OAUTH_REQUEST"] == "FAIL"
    assert provider.counts == {"contract": 1, "oauth": 1, "market": 0}


def test_oauth_429_has_no_retry() -> None:
    provider = ScenarioProvider()
    provider.oauth_status = 429
    provider.oauth_payload = provider_error("rate-limit-exceeded")
    provider.oauth_headers.update(rate_headers(remaining="0", retry_after="10"))
    result = execute(provider)
    assert summary(result)["ERROR_CATEGORY"] == "RATE_LIMIT"
    assert provider.counts == {"contract": 1, "oauth": 1, "market": 0}


@pytest.mark.parametrize("status_code", [500, 502, 503, 504])
def test_oauth_retryable_production_5xx_is_still_one_shot(status_code: int) -> None:
    provider = ScenarioProvider()
    provider.oauth_status = status_code
    provider.oauth_payload = provider_error("internal-error")
    result = execute(provider)
    assert summary(result)["ERROR_CATEGORY"] == "SERVER"
    assert provider.counts == {"contract": 1, "oauth": 1, "market": 0}


def test_market_401_has_no_token_refresh_or_get_replay() -> None:
    provider = ScenarioProvider()
    provider.market_status = 401
    provider.market_payload = provider_error("expired-token")
    result = execute(provider)
    assert summary(result)["ERROR_CATEGORY"] == "AUTH"
    assert provider.counts == {"contract": 1, "oauth": 1, "market": 1}


def test_market_429_has_no_retry() -> None:
    provider = ScenarioProvider()
    provider.market_status = 429
    provider.market_payload = provider_error("rate-limit-exceeded")
    provider.market_headers.update(rate_headers(remaining="0", retry_after="10"))
    result = execute(provider)
    values = summary(result)
    assert values["ERROR_CATEGORY"] == "RATE_LIMIT"
    assert values["RETRY_AFTER"] == "PRESENT_VALID"
    assert provider.counts == {"contract": 1, "oauth": 1, "market": 1}


@pytest.mark.parametrize("status_code", [500, 502, 503, 504])
def test_market_retryable_production_5xx_is_still_one_shot(status_code: int) -> None:
    provider = ScenarioProvider()
    provider.market_status = status_code
    provider.market_payload = provider_error("maintenance")
    result = execute(provider)
    assert summary(result)["ERROR_CATEGORY"] == "SERVER"
    assert provider.counts == {"contract": 1, "oauth": 1, "market": 1}


@pytest.mark.parametrize("stage", ["contract", "oauth", "market"])
def test_redirect_is_never_followed(stage: str) -> None:
    provider = ScenarioProvider()
    if stage == "contract":
        provider.contract_status = 302
        provider.contract_headers["location"] = "https://outside.invalid/contract"
    elif stage == "oauth":
        provider.oauth_status = 307
        provider.oauth_headers["location"] = "https://outside.invalid/oauth"
    else:
        provider.market_status = 302
        provider.market_headers["location"] = "https://outside.invalid/market"
    result = execute(provider)
    values = summary(result)
    assert values["ERROR_CATEGORY"] == "REDIRECT"
    assert all(request.url.host == "openapi.tossinvest.com" for request in provider.requests)
    assert provider.counts[stage] == 1
    if stage == "contract":
        assert provider.counts == {"contract": 1, "oauth": 0, "market": 0}
    elif stage == "oauth":
        assert provider.counts == {"contract": 1, "oauth": 1, "market": 0}
    else:
        assert provider.counts == {"contract": 1, "oauth": 1, "market": 1}


def test_complete_missing_and_invalid_rate_headers_have_safe_diagnostics() -> None:
    complete = ScenarioProvider()
    complete_values = summary(execute(complete))
    assert complete_values["RATE_HEADERS"] == "PRESENT_VALID"
    assert complete_values["RETRY_AFTER"] == "LIVE_UNVERIFIED"

    missing = ScenarioProvider()
    missing.market_headers = {"content-type": JSON_MEDIA_TYPE}
    missing_values = summary(execute(missing))
    assert missing_values["RATE_HEADERS"] == "MISSING"
    assert missing_values["RATE_LIMIT_HEADER"] == "MISSING"

    invalid = ScenarioProvider()
    invalid.market_headers["X-RateLimit-Remaining"] = "private-invalid-value"
    invalid_values = summary(execute(invalid))
    assert invalid_values["RATE_HEADERS"] == "INVALID"
    assert invalid_values["RATE_REMAINING_HEADER"] == "INVALID"


def test_output_schema_is_fixed_and_never_renders_sensitive_or_raw_provider_values() -> None:
    provider = ScenarioProvider()
    credential = "synthetic-" + "output-credential"
    token = "synthetic-" + "output-token"
    provider.oauth_payload = oauth_token(token)
    provider.market_payload = {"result": [], "private": "actual-price-body-canary"}
    provider.market_headers["X-Private-Header"] = "raw-header-canary"

    def settings_factory() -> Settings:
        return Settings(TOSS_CLIENT_ID=credential, TOSS_CLIENT_SECRET=credential)

    result = execute(provider, settings_factory=settings_factory)
    rendered = result.render()
    assert tuple(key for key, _value in result.lines) == LIVE_SUMMARY_KEYS
    for prohibited in (
        credential,
        token,
        "actual-price-body-canary",
        "raw-header-canary",
        "Authorization",
        "Bearer",
    ):
        assert prohibited not in rendered
    assert not any("=" in value for _key, value in result.lines)


def test_invalid_success_payload_is_discarded_without_rendering() -> None:
    provider = ScenarioProvider()
    provider.market_payload = {"result": "private-body-canary"}
    result = execute(provider)
    assert summary(result)["ERROR_CATEGORY"] == "CONTRACT_INVALID"
    assert "private-body-canary" not in result.render()
    assert provider.counts == {"contract": 1, "oauth": 1, "market": 1}


def test_offline_self_test_uses_mock_transport_and_passes_redaction_and_one_shot() -> None:
    values = run(_run_offline_self_test())
    assert values == {
        "MODE": "SELF_TEST",
        "EXTERNAL_NETWORK_REQUESTS": "0",
        "OUTPUT_SCHEMA": "PASS",
        "REDACTION": "PASS",
        "ONE_SHOT": "PASS",
        "DRIFT_STOP": "PASS",
        "STATUS": "PASS",
    }


def test_powershell_entrypoint_has_only_nonsecret_parameters_and_no_env_file_or_transcript() -> (
    None
):
    source = POWERSHELL_SCRIPT.read_text(encoding="utf-8")
    parameter_prefix = source.split('. (Join-Path $PSScriptRoot "common.ps1")', 1)[0]
    assert all(
        f"${allowed}" in parameter_prefix
        for allowed in ("Live", "ConfirmReadOnly", "SelfTest", "Symbol")
    )
    for prohibited in (
        "ClientId",
        "ClientSecret",
        "Token",
        "Authorization",
        "ApiKey",
        "Secret",
    ):
        assert f"${prohibited}" not in parameter_prefix
    assert ".env" not in source
    assert "Start-Transcript" not in source
    assert "openapi.tossinvest.com" not in source


def test_python_runner_has_only_gate_and_symbol_cli_arguments() -> None:
    tree = ast.parse(RUNNER_SCRIPT.read_text(encoding="utf-8"), filename=str(RUNNER_SCRIPT))
    options = {
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "add_argument"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    }
    assert options == {"--live", "--confirm-read-only", "--self-test", "--symbol"}
    assert "httpx" not in {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }


def test_preflight_is_internal_only_and_exports_no_token_manager_or_raw_token_surface() -> None:
    assert "preflight" not in toss.__all__
    assert "TossTokenManager" not in toss.__all__
    assert "TokenLease" not in toss.__all__
    application_root = PROJECT_ROOT / "services" / "api" / "src" / "toss_dashboard_api"
    importers = []
    for path in application_root.rglob("*.py"):
        if path == PREFLIGHT_SOURCE:
            continue
        if "connectors.toss.preflight" in path.read_text(encoding="utf-8"):
            importers.append(path.relative_to(PROJECT_ROOT).as_posix())
    assert importers == []


def test_preflight_source_contains_only_canonical_docs_oauth_and_stocks_paths() -> None:
    source = PREFLIGHT_SOURCE.read_text(encoding="utf-8")
    assert CANONICAL_OPENAPI_PATH in source
    assert TossStaticEndpoint.STOCKS.name in source
    for prohibited_path in (
        "/api/v1/" + "accounts",
        "/api/v1/" + "holdings",
        "/api/v1/" + "orders",
        "/api/v1/" + "conditional-orders",
    ):
        assert prohibited_path not in source
