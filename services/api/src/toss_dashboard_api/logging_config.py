from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

SENSITIVE_KEY = re.compile(
    r"authorization|cookie|secret|token|api[_-]?key|password|account", re.IGNORECASE
)
SENSITIVE_VALUE = re.compile(
    r"(?i)(bearer\s+\S+|sk-(?:proj-)?[A-Za-z0-9_-]{8,}|canary[-_ ]?secret\S*|"
    r"gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|AIza[A-Za-z0-9_-]{20,}|"
    r"xox[baprs]-[A-Za-z0-9-]{10,}|"
    r"eyJ[A-Za-z0-9_-]{5,}\.eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,})"
)
REDACTED = "[REDACTED]"
UVICORN_ERROR_EVENT = "uvicorn_error"
MULTILINE_EVENT = "multiline_event_suppressed"


def redact(value: Any, key: str | None = None) -> Any:
    if key is not None and SENSITIVE_KEY.search(key):
        return REDACTED
    if isinstance(value, Mapping):
        return {
            str(item_key): redact(item_value, str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, list | tuple):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return SENSITIVE_VALUE.sub(REDACTED, value)
    return value


def safe_log_event(record: logging.LogRecord) -> str:
    """Reduce server exception records to fixed events before JSON serialization."""

    message = record.getMessage()
    if record.name == "uvicorn" or record.name.startswith("uvicorn."):
        if record.levelno >= logging.ERROR or "\n" in message or "\r" in message:
            return UVICORN_ERROR_EVENT
    if "\n" in message or "\r" in message:
        return MULTILINE_EVENT
    redacted = redact(message)
    return redacted if isinstance(redacted, str) else REDACTED


class JsonFormatter(logging.Formatter):
    """Small allowlist JSON formatter with defense-in-depth redaction."""

    _optional_fields = (
        "request_id",
        "job_id",
        "source",
        "stage",
        "record_count",
        "status",
        "latency_ms",
        "error_code",
        "method",
        "path",
        "status_code",
    )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "event": safe_log_event(record),
        }
        for field in self._optional_fields:
            if hasattr(record, field):
                payload[field] = redact(getattr(record, field), field)
        if record.exc_info:
            payload["error_type"] = record.exc_info[0].__name__ if record.exc_info[0] else "Error"
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    for name in tuple(root.manager.loggerDict):
        if name == "toss_dashboard_api" or name.startswith("toss_dashboard_api."):
            logging.getLogger(name).disabled = False
    for name in ("uvicorn", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
        uvicorn_logger.disabled = False
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers.clear()
    access_logger.propagate = False
    access_logger.disabled = True
