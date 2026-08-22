from __future__ import annotations

import hashlib
import io
import json
import os
import sys
from pathlib import Path
from typing import Any

from detect_secrets.__version__ import VERSION
from detect_secrets.core import baseline, scan
from detect_secrets.core.secrets_collection import SecretsCollection
from detect_secrets.settings import (
    default_settings,
    get_filters,
    get_plugins,
    get_settings,
)
from detect_secrets.transformers import get_transformed_file
from detect_secrets.util.path import convert_local_os_path

PROHIBITED_FILTERS = (
    "detect_secrets.filters.allowlist.is_line_allowlisted",
    "detect_secrets.filters.common.is_invalid_file",
    "detect_secrets.filters.heuristic.is_lock_file",
    "detect_secrets.filters.heuristic.is_non_text_file",
    "detect_secrets.filters.heuristic.is_swagger_file",
)


class _SnapshotTextIO(io.StringIO):
    """A named in-memory stream compatible with detect-secrets transformers."""

    def __init__(self, content: str, name: str) -> None:
        super().__init__(content, newline=None)
        self.name = name


def _load_request(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("The serial scan request must be a JSON object.")
    return payload


def _require_file_records(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError("files must be a non-empty JSON array.")
    if not all(isinstance(item, dict) for item in value):
        raise ValueError("files must contain only JSON objects.")
    return value


def _validate_file(root: Path, record: dict[str, Any]) -> tuple[str, str]:
    scan_path = record.get("scan_path")
    full_path_value = record.get("full_path")
    expected_size = record.get("size")
    expected_sha256 = record.get("sha256")
    if not isinstance(scan_path, str) or not scan_path:
        raise ValueError("scan_path must be a non-empty string.")
    if not isinstance(full_path_value, str) or not full_path_value:
        raise ValueError("full_path must be a non-empty string.")
    if not isinstance(expected_size, int) or expected_size < 0:
        raise ValueError("size must be a non-negative integer.")
    if (
        not isinstance(expected_sha256, str)
        or len(expected_sha256) != 64
        or any(character not in "0123456789abcdef" for character in expected_sha256)
    ):
        raise ValueError("sha256 must be a lowercase SHA-256 digest.")

    full_path = Path(full_path_value).resolve(strict=True)
    scan_candidate = Path(scan_path)
    resolved_scan_path = (
        scan_candidate.resolve(strict=True)
        if scan_candidate.is_absolute()
        else (root / scan_candidate).resolve(strict=True)
    )
    if full_path != resolved_scan_path or not full_path.is_file():
        raise ValueError(f"A serial scan path identity check failed: {scan_path}")

    content = full_path.read_bytes()
    if len(content) != expected_size:
        raise ValueError(f"A serial scan input changed size: {scan_path}")
    if hashlib.sha256(content).hexdigest() != expected_sha256:
        raise ValueError(f"A serial scan input changed content: {scan_path}")
    text = content.decode("utf-8", errors="strict")
    if "\x00" in text:
        raise ValueError(f"A serial scan input contains NUL bytes: {scan_path}")
    return scan_path, text


def _scan_snapshot(
    secrets: SecretsCollection,
    scan_path: str,
    text: str,
) -> None:
    """Run the pinned detect-secrets file pipeline over an approved text snapshot."""
    try:
        if not get_plugins():
            raise ValueError("The detect-secrets runtime has no active plugins.")
    except FileNotFoundError as error:
        raise ValueError("The detect-secrets plugins could not be loaded.") from error

    converted_scan_path = convert_local_os_path(scan_path)
    scanner_filename = os.path.join(secrets.root, converted_scan_path)
    # These private helpers are stable within the exact 1.5.0 runtime pinned above.
    if scan._is_filtered_out(
        required_filter_parameters=["filename"],
        filename=scanner_filename,
    ):
        return

    has_secret = False
    with _SnapshotTextIO(text, scanner_filename) as snapshot:
        for use_eager_transformers in (False, True):
            if use_eager_transformers:
                if has_secret:
                    break
                snapshot.seek(0)

            lines = get_transformed_file(
                snapshot,
                use_eager_transformers=use_eager_transformers,
            )
            if not lines:
                if use_eager_transformers:
                    break
                lines = snapshot.readlines()

            for secret in scan._process_line_based_plugins(
                lines=list(enumerate(lines, start=1)),
                filename=scanner_filename,
            ):
                has_secret = True
                secrets[converted_scan_path].add(secret)


def main() -> int:
    if len(sys.argv) != 2:
        raise ValueError("Usage: secret_scan_driver.py REQUEST.json")

    request_path = Path(sys.argv[1]).resolve(strict=True)
    request = _load_request(request_path)
    root_value = request.get("root")
    if not isinstance(root_value, str) or not root_value:
        raise ValueError("root must be a non-empty string.")
    root = Path(root_value).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("root must identify a directory.")

    if VERSION != "1.5.0":
        raise ValueError("The detect-secrets runtime is not the approved 1.5.0 release.")
    if sys.flags.isolated != 1:
        raise ValueError("The serial scanner must run in isolated Python mode.")
    if sys.flags.utf8_mode != 1:
        raise ValueError("The serial scanner must run in Python UTF-8 mode.")
    file_records = _require_file_records(request.get("files"))

    completed: list[dict[str, Any]] = []
    with default_settings() as settings:
        settings.disable_filters(*PROHIBITED_FILTERS)
        active_filters = sorted(get_settings().filters)
        prohibited_active = sorted(set(active_filters) & set(PROHIBITED_FILTERS))
        if prohibited_active:
            raise ValueError(f"Prohibited filters remain active: {prohibited_active}")
        filename_filters = sorted(
            filter_function.path
            for filter_function in get_filters()
            if "filename" in filter_function.injectable_variables
        )
        if filename_filters:
            raise ValueError(f"Filename filters remain active: {filename_filters}")

        secrets = SecretsCollection(root=str(root))
        for record in file_records:
            scan_path, text = _validate_file(root, record)
            _scan_snapshot(secrets, scan_path, text)
            completed.append(
                {
                    "scan_path": scan_path,
                    "full_path": record["full_path"],
                    "size": record["size"],
                    "sha256": record["sha256"],
                }
            )

        output = baseline.format_for_output(secrets)
        output["serial_scan"] = {
            "active_filters": active_filters,
            "completed": completed,
        }

    json.dump(output, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
