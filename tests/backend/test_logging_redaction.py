import json
import logging

import pytest

from toss_dashboard_api.logging_config import (
    REDACTED,
    UVICORN_ERROR_EVENT,
    JsonFormatter,
    redact,
)

SENSITIVE_SENTINELS = [
    "canary-" + "secret-value",
    "sk-proj-" + "abcdefghijk",
    "ghp_" + "a" * 24,
    "AKIA" + "A" * 16,
    "AIza" + "a" * 24,
    "xoxb-" + "1" * 20,
    "eyJheader" + "." + "eyJpayload" + "." + "signature",
]


def test_recursive_redaction_masks_sensitive_keys_and_values() -> None:
    payload = {
        "Authorization": "Bearer canary-secret-value",
        "nested": {"api_" + "key": "not-for-output"},
        "message": "request used sk-proj-abcdefghijk",
    }
    rendered = json.dumps(redact(payload))
    assert "canary-secret-value" not in rendered
    assert "not-for-output" not in rendered
    assert "sk-proj-abcdefghijk" not in rendered
    assert REDACTED in rendered


def test_json_formatter_is_structured_and_does_not_emit_traceback_text() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="Bearer canary-secret-value",
        args=(),
        exc_info=None,
    )
    record.request_id = "request_fixture"
    parsed = json.loads(formatter.format(record))
    assert parsed["event"] == REDACTED
    assert parsed["request_id"] == "request_fixture"
    assert set(parsed) >= {"timestamp", "level", "logger", "event"}


@pytest.mark.parametrize("sentinel", SENSITIVE_SENTINELS)
def test_json_formatter_redacts_provider_tokens_from_every_allowlisted_field(
    sentinel: str,
) -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg=f"request failed with {sentinel}",
        args=(),
        exc_info=None,
    )
    record.request_id = sentinel
    record.path = f"/{sentinel}"
    rendered = formatter.format(record)
    parsed = json.loads(rendered)
    assert sentinel not in rendered
    assert REDACTED in parsed["event"]
    assert REDACTED in parsed["request_id"]
    assert REDACTED in parsed["path"]


def test_uvicorn_multiline_startup_failure_is_replaced_before_serialization() -> None:
    sentinel = "canary-" + "secret-value"
    private_path = "C:\\private\\fixture\\manifest.json"
    record = logging.LogRecord(
        name="uvicorn.error",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg=(
            f"Traceback (most recent call last):\n  File {private_path}\nRuntimeError: {sentinel}"
        ),
        args=(),
        exc_info=None,
    )
    rendered = JsonFormatter().format(record)
    parsed = json.loads(rendered)
    assert parsed["event"] == UVICORN_ERROR_EVENT
    assert sentinel not in rendered
    assert private_path not in rendered
    assert "Traceback" not in rendered
