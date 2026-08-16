import json
import logging

from toss_dashboard_api.logging_config import REDACTED, JsonFormatter, redact


def test_recursive_redaction_masks_sensitive_keys_and_values() -> None:
    payload = {
        "Authorization": "Bearer canary-secret-value",
        "nested": {"api_key": "not-for-output"},  # pragma: allowlist secret
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
