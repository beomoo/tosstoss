import io
import json
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from toss_dashboard_api.config import Settings
from toss_dashboard_api.logging_config import JsonFormatter
from toss_dashboard_api.main import create_app


class FailingAnalytics:
    def company_overview(self, issuer_id: str):
        raise RuntimeError(f"fixture read failed for {issuer_id}: canary-secret-value")

    def analysis_packet(self):
        raise RuntimeError("analysis fixture failed: canary-secret-value")


def error_log_capture() -> tuple[io.StringIO, logging.Handler]:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    return stream, handler


def parsed_error_events(stream: io.StringIO) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in stream.getvalue().splitlines()
        if json.loads(line).get("event") == "request_failed"
    ]


def test_repository_failure_is_safe_and_health_remains_live(database_context) -> None:
    app = create_app(Settings(), database_context.metadata, FailingAnalytics())
    stream, handler = error_log_capture()
    error_logger = logging.getLogger("toss_dashboard_api.errors")
    error_logger.addHandler(handler)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            failed = client.get("/api/v1/companies/issuer_kr_synthetic/overview")
            assert failed.status_code == 503
            payload = failed.json()
            assert set(payload) == {"contract_version", "error", "request_id"}
            assert set(payload["error"]) == {"code", "message"}
            assert payload["error"]["code"] == "SERVICE_UNAVAILABLE"
            assert "canary-secret-value" not in failed.text
            assert client.get("/health").status_code == 200
    finally:
        error_logger.removeHandler(handler)

    events = parsed_error_events(stream)
    assert len(events) == 1
    assert events[0]["error_code"] == "SERVICE_UNAVAILABLE"
    assert events[0]["stage"] == "request"
    assert events[0]["source"] == "application_error_handler"
    assert events[0]["status_code"] == 503
    rendered = stream.getvalue()
    assert "canary-secret-value" not in rendered
    assert "Traceback" not in rendered


class MissingPacketAnalytics:
    def company_overview(self, issuer_id: str):
        return None

    def analysis_packet(self):
        return None


def test_missing_packet_is_safe_503(database_context) -> None:
    app = create_app(Settings(), database_context.metadata, MissingPacketAnalytics())
    with TestClient(app) as client:
        response = client.get("/api/v1/sample/analysis-packet")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"


def test_unhandled_error_is_logged_without_secret_or_traceback(database_context) -> None:
    app: FastAPI = create_app(Settings(), database_context.metadata, database_context.analytics)

    @app.get("/_test/unhandled")
    def raise_unhandled_error() -> None:
        raise RuntimeError("canary-secret-value must never be logged")

    stream, handler = error_log_capture()
    error_logger = logging.getLogger("toss_dashboard_api.errors")
    error_logger.addHandler(handler)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/_test/unhandled")
    finally:
        error_logger.removeHandler(handler)

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "canary-secret-value" not in response.text
    events = parsed_error_events(stream)
    assert len(events) == 1
    assert events[0]["error_code"] == "INTERNAL_ERROR"
    assert events[0]["stage"] == "request"
    assert events[0]["source"] == "unhandled_exception_handler"
    assert events[0]["error_type"] == "RuntimeError"
    rendered = stream.getvalue()
    assert "canary-secret-value" not in rendered
    assert "Traceback" not in rendered
