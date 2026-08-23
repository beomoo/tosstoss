from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response

from toss_dashboard_api.config import Settings
from toss_dashboard_api.contracts.responses import ErrorEnvelope
from toss_dashboard_api.main import app, create_app

SENSITIVE_SENTINELS = [
    "canary-" + "secret-value",
    "sk-proj-" + "abcdefghijk",
    "ghp_" + "a" * 24,
    "AKIA" + "A" * 16,
    "AIza" + "a" * 24,
    "xoxb-" + "1" * 20,
    "eyJheader" + "." + "eyJpayload" + "." + "signature",
]


def assert_error_envelope(response: Response, status_code: int, code: str) -> None:
    assert response.status_code == status_code
    payload = response.json()
    parsed = ErrorEnvelope.model_validate(payload)
    assert set(payload) == {"contract_version", "error", "request_id"}
    assert set(payload["error"]) == {"code", "message"}
    assert parsed.contract_version == "0.1.0"
    assert parsed.error.code == code
    assert response.headers["x-request-id"] == parsed.request_id
    rendered = response.text
    assert "traceback" not in rendered.lower()
    assert "detail" not in payload


@pytest.mark.parametrize(
    ("invoke", "status_code", "code"),
    [
        (lambda client: client.get("/does-not-exist"), 404, "NOT_FOUND"),
        (lambda client: client.post("/health"), 405, "METHOD_NOT_ALLOWED"),
        (
            lambda client: client.get("/api/v1/companies/INVALID!/overview"),
            422,
            "VALIDATION_ERROR",
        ),
    ],
)
def test_framework_failures_use_c12_envelope(
    api_client: TestClient,
    invoke: Callable[[TestClient], Response],
    status_code: int,
    code: str,
) -> None:
    assert_error_envelope(invoke(api_client), status_code, code)


def test_invalid_host_is_fail_closed_c12_json(api_client: TestClient) -> None:
    response = api_client.get(
        "/health",
        headers={"host": "attacker.example", "x-request-id": "invalid_host_request"},
    )
    assert_error_envelope(response, 400, "INVALID_HOST")
    assert response.json()["request_id"] != "invalid_host_request"
    assert "attacker.example" not in response.text


@pytest.mark.parametrize(
    "headers",
    [
        {
            "origin": "https://example.invalid",
            "access-control-request-method": "GET",
        },
        {
            "origin": "http://127.0.0.1:3000",
            "access-control-request-method": "DELETE",
        },
    ],
)
def test_invalid_cors_preflight_is_c12_json(
    api_client: TestClient, headers: dict[str, str]
) -> None:
    response = api_client.options("/health", headers=headers)
    assert_error_envelope(response, 400, "INVALID_CORS")
    assert response.headers.get("content-type") == "application/json"


def test_caller_request_id_is_always_replaced(api_client: TestClient) -> None:
    response = api_client.get("/health", headers={"x-request-id": "safe_request_123"})
    assert response.status_code == 200
    assert response.headers["x-request-id"] != "safe_request_123"
    assert len(response.headers["x-request-id"]) == 32


@pytest.mark.parametrize("sensitive_id", SENSITIVE_SENTINELS)
def test_sensitive_request_id_is_never_echoed(api_client: TestClient, sensitive_id: str) -> None:
    response = api_client.get("/does-not-exist", headers={"x-request-id": sensitive_id})
    assert_error_envelope(response, 404, "NOT_FOUND")
    assert response.json()["request_id"] != sensitive_id
    assert sensitive_id not in response.text
    assert sensitive_id not in response.headers["x-request-id"]


class MissingPacketAnalytics:
    def company_overview(self, issuer_id: str):
        return None

    def analysis_packet(self):
        return None


def test_503_response_matches_documented_error_schema(database_context) -> None:
    application = create_app(Settings(), database_context.metadata, MissingPacketAnalytics())
    with TestClient(application) as client:
        response = client.get("/api/v1/sample/analysis-packet")
    assert_error_envelope(response, 503, "SERVICE_UNAVAILABLE")


def test_500_response_matches_documented_error_schema(database_context) -> None:
    application: FastAPI = create_app(
        Settings(), database_context.metadata, database_context.analytics
    )

    @application.get("/_test/unhandled")
    def raise_unhandled() -> None:
        raise RuntimeError("synthetic internal detail")

    with TestClient(application, raise_server_exceptions=False) as client:
        response = client.get("/_test/unhandled")
    assert_error_envelope(response, 500, "INTERNAL_ERROR")
    assert "synthetic internal detail" not in response.text


def test_openapi_documents_only_c12_error_envelopes() -> None:
    schema = app.openapi()
    error_statuses = {"400", "404", "405", "422", "500", "503"}
    for path_item in schema["paths"].values():
        for method, operation in path_item.items():
            if method.upper() != "GET":
                continue
            responses = operation["responses"]
            assert error_statuses <= set(responses)
            for status in error_statuses:
                assert responses[status]["content"]["application/json"]["schema"] == {
                    "$ref": "#/components/schemas/ErrorEnvelope"
                }


def test_contract_version_remains_a_literal_in_openapi() -> None:
    schemas = app.openapi()["components"]["schemas"]
    assert schemas["ErrorEnvelope"]["properties"]["contract_version"]["const"] == "0.1.0"
    strict_contract_schemas = [
        schema for schema in schemas.values() if "contract_version" in schema.get("properties", {})
    ]
    assert strict_contract_schemas
    for schema in strict_contract_schemas:
        assert schema["properties"]["contract_version"]["const"] == "0.1.0"
