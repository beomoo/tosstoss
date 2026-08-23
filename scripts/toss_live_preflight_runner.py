from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
API_SOURCE_ROOT = REPO_ROOT / "services" / "api" / "src"
sys.path.insert(0, str(API_SOURCE_ROOT))

from toss_dashboard_api.connectors.toss.preflight import (  # noqa: E402
    LIVE_SUMMARY_KEYS,
    PREFLIGHT_SYMBOL_MAX_LENGTH,
    PREFLIGHT_SYMBOL_PATTERN,
    _run_live_preflight,
    _run_offline_self_test,
)

ACK_ENVIRONMENT_NAME = "TOSS_LIVE_PREFLIGHT_ACK"
EXACT_LIVE_ACK = "READ_ONLY_ONE_SHOT"
SYMBOL_ENVIRONMENT_NAME = "TOSS_PREFLIGHT_SYMBOL"

_SAFE_KEY = re.compile(r"^[A-Z][A-Z0-9_]*$")
_SAFE_VALUE = re.compile(r"^[A-Za-z0-9_./:-]+$")
_SELF_TEST_KEYS = (
    "MODE",
    "EXTERNAL_NETWORK_REQUESTS",
    "GATE_VALIDATION",
    "OUTPUT_SCHEMA",
    "REDACTION",
    "ONE_SHOT",
    "DRIFT_STOP",
    "STATUS",
)
_GATE_KEYS = ("MODE", "STAGE", "ERROR_CATEGORY", "STATUS")
_OFFLINE_KEYS = (
    "MODE",
    "EXTERNAL_NETWORK_REQUESTS",
    "CREDENTIALS_USED",
    "STATUS",
)


class _SafeArgumentError(Exception):
    pass


class _SafeArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        raise _SafeArgumentError


def _parse_arguments(argv: list[str]) -> argparse.Namespace:
    parser = _SafeArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--confirm-read-only", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--symbol")
    return parser.parse_args(argv)


def _resolved_symbol(argument_value: str | None) -> str:
    if argument_value is not None:
        return argument_value
    return os.environ.get(SYMBOL_ENVIRONMENT_NAME, "")


def _gate_error(
    *,
    live: bool,
    confirm_read_only: bool,
    self_test: bool,
    acknowledgment: str | None,
    symbol: str,
) -> str | None:
    if self_test and live:
        return "MODE_CONFLICT"
    if self_test:
        return None
    if not live:
        return "LIVE_NOT_REQUESTED"
    if not confirm_read_only:
        return "READ_ONLY_CONFIRMATION_REQUIRED"
    if acknowledgment != EXACT_LIVE_ACK:
        return "EXACT_ACK_REQUIRED"
    if (
        not 1 <= len(symbol) <= PREFLIGHT_SYMBOL_MAX_LENGTH
        or PREFLIGHT_SYMBOL_PATTERN.fullmatch(symbol) is None
    ):
        return "INVALID_SYMBOL"
    return None


def _summary_is_safe(summary: dict[str, str], expected_keys: tuple[str, ...]) -> bool:
    return (
        tuple(summary) == expected_keys
        and all(_SAFE_KEY.fullmatch(key) is not None for key in summary)
        and all(_SAFE_VALUE.fullmatch(value) is not None for value in summary.values())
    )


def _emit(summary: dict[str, str], expected_keys: tuple[str, ...]) -> bool:
    if not _summary_is_safe(summary, expected_keys):
        return False
    for key, value in summary.items():
        print(f"{key}={value}")
    return True


def _gate_self_test() -> bool:
    cases = (
        (
            dict(
                live=False,
                confirm_read_only=False,
                self_test=False,
                acknowledgment=None,
                symbol="",
            ),
            "LIVE_NOT_REQUESTED",
        ),
        (
            dict(
                live=True,
                confirm_read_only=False,
                self_test=False,
                acknowledgment=EXACT_LIVE_ACK,
                symbol="SYNTHETIC",
            ),
            "READ_ONLY_CONFIRMATION_REQUIRED",
        ),
        (
            dict(
                live=True,
                confirm_read_only=True,
                self_test=False,
                acknowledgment=None,
                symbol="SYNTHETIC",
            ),
            "EXACT_ACK_REQUIRED",
        ),
        (
            dict(
                live=True,
                confirm_read_only=True,
                self_test=False,
                acknowledgment="WRONG_ACK",
                symbol="SYNTHETIC",
            ),
            "EXACT_ACK_REQUIRED",
        ),
        (
            dict(
                live=True,
                confirm_read_only=True,
                self_test=False,
                acknowledgment=EXACT_LIVE_ACK,
                symbol="../unsafe",
            ),
            "INVALID_SYMBOL",
        ),
        (
            dict(
                live=True,
                confirm_read_only=True,
                self_test=False,
                acknowledgment=EXACT_LIVE_ACK,
                symbol="SYNTHETIC-1",
            ),
            None,
        ),
        (
            dict(
                live=True,
                confirm_read_only=True,
                self_test=True,
                acknowledgment=EXACT_LIVE_ACK,
                symbol="SYNTHETIC",
            ),
            "MODE_CONFLICT",
        ),
    )
    return all(_gate_error(**arguments) == expected for arguments, expected in cases)


def _safe_gate_failure(category: str) -> dict[str, str]:
    return {
        "MODE": "LIVE",
        "STAGE": "GATE",
        "ERROR_CATEGORY": category,
        "STATUS": "FAIL",
    }


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = _parse_arguments(sys.argv[1:] if argv is None else argv)
    except _SafeArgumentError:
        summary = _safe_gate_failure("INVALID_ARGUMENTS")
        _emit(summary, _GATE_KEYS)
        return 2

    symbol = _resolved_symbol(arguments.symbol)
    acknowledgment = os.environ.get(ACK_ENVIRONMENT_NAME)
    gate_error = _gate_error(
        live=arguments.live,
        confirm_read_only=arguments.confirm_read_only,
        self_test=arguments.self_test,
        acknowledgment=acknowledgment,
        symbol=symbol,
    )

    if arguments.self_test and not arguments.live:
        try:
            core_summary = asyncio.run(_run_offline_self_test())
            summary = {
                "MODE": core_summary["MODE"],
                "EXTERNAL_NETWORK_REQUESTS": core_summary["EXTERNAL_NETWORK_REQUESTS"],
                "GATE_VALIDATION": "PASS" if _gate_self_test() else "FAIL",
                "OUTPUT_SCHEMA": core_summary["OUTPUT_SCHEMA"],
                "REDACTION": core_summary["REDACTION"],
                "ONE_SHOT": core_summary["ONE_SHOT"],
                "DRIFT_STOP": core_summary["DRIFT_STOP"],
                "STATUS": core_summary["STATUS"],
            }
            if summary["GATE_VALIDATION"] != "PASS":
                summary["STATUS"] = "FAIL"
            if not _emit(summary, _SELF_TEST_KEYS):
                return 1
            return 0 if summary["STATUS"] == "PASS" else 1
        except Exception:
            summary = {
                "MODE": "SELF_TEST",
                "EXTERNAL_NETWORK_REQUESTS": "0",
                "GATE_VALIDATION": "FAIL",
                "OUTPUT_SCHEMA": "FAIL",
                "REDACTION": "FAIL",
                "ONE_SHOT": "FAIL",
                "DRIFT_STOP": "FAIL",
                "STATUS": "FAIL",
            }
            _emit(summary, _SELF_TEST_KEYS)
            return 1

    if gate_error == "LIVE_NOT_REQUESTED":
        summary = {
            "MODE": "OFFLINE",
            "EXTERNAL_NETWORK_REQUESTS": "0",
            "CREDENTIALS_USED": "0",
            "STATUS": "LIVE_NOT_REQUESTED",
        }
        _emit(summary, _OFFLINE_KEYS)
        return 0
    if gate_error is not None:
        summary = _safe_gate_failure(gate_error)
        _emit(summary, _GATE_KEYS)
        return 2

    try:
        result = asyncio.run(_run_live_preflight(symbol))
        summary = dict(result.lines)
        if not _emit(summary, LIVE_SUMMARY_KEYS):
            raise RuntimeError
        return 0 if result.passed else 1
    except Exception:
        summary = _safe_gate_failure("SAFE_WRAPPER_FAILURE")
        _emit(summary, _GATE_KEYS)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
