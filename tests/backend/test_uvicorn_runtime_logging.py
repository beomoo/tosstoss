from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from tests.backend.conftest import FIXTURE_DIR, PROJECT_ROOT, DatabaseContext

LOG_CONFIG = PROJECT_ROOT / "services" / "api" / "uvicorn_log_config.json"


def _runtime_environment(database_url: str, fixture_dir: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "ALLOW_ACCOUNT_ENDPOINTS": "false",
            "APP_ENV": "test",
            "DASHBOARD_API_HOST": "127.0.0.1",
            "DASHBOARD_DATABASE_URL": database_url,
            "DASHBOARD_FIXTURE_DIR": str(fixture_dir),
            "DRY_RUN": "true",
            "LOCAL_ONLY": "true",
            "OPENAI_API_ENABLED": "false",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUNBUFFERED": "1",
            "TRADING_ENABLED": "false",
        }
    )
    return environment


def _uvicorn_command(application: str, port: int) -> list[str]:
    return [
        sys.executable,
        "-m",
        "uvicorn",
        application,
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--no-access-log",
        "--log-config",
        str(LOG_CONFIG),
    ]


def _parse_json_lines(output: str) -> list[dict[str, Any]]:
    lines = [line for line in output.splitlines() if line.strip()]
    assert lines, "uvicorn emitted no structured runtime logs"
    parsed: list[dict[str, Any]] = []
    for line in lines:
        item = json.loads(line)
        assert isinstance(item, dict)
        parsed.append(item)
    return parsed


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _stop_server(process: subprocess.Popen[str]) -> str:
    if process.poll() is None:
        process.terminate()
    try:
        output, _ = process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        output, _ = process.communicate(timeout=5)
    return output


def test_unhandled_runtime_failure_emits_only_redacted_json_logs(
    database_context: DatabaseContext,
) -> None:
    sentinel = "canary-" + "secret-value"
    port = _free_loopback_port()
    environment = _runtime_environment(database_context.url, FIXTURE_DIR)
    environment["UVICORN_TEST_EXCEPTION"] = sentinel
    process = subprocess.Popen(
        _uvicorn_command("tests.backend.uvicorn_canary_app:app", port),
        cwd=PROJECT_ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = ""
    try:
        deadline = time.monotonic() + 12
        health_response: httpx.Response | None = None
        while time.monotonic() < deadline:
            if process.poll() is not None:
                break
            try:
                health_response = httpx.get(f"http://127.0.0.1:{port}/health", timeout=0.25)
            except httpx.TransportError:
                time.sleep(0.05)
                continue
            if health_response.status_code == 200:
                break
        assert health_response is not None and health_response.status_code == 200
        response = httpx.get(
            f"http://127.0.0.1:{port}/_test/unhandled/{sentinel}",
            headers={"x-request-id": sentinel},
            timeout=2,
        )
        assert response.status_code == 500
        assert response.json()["error"]["code"] == "INTERNAL_ERROR"
        assert sentinel not in response.text
        assert sentinel not in response.headers["x-request-id"]
    finally:
        output = _stop_server(process)

    logs = _parse_json_lines(output)
    assert sentinel not in output
    assert "Traceback" not in output
    assert any(item.get("event") == "request_failed" for item in logs)
    assert any(item.get("event") == "uvicorn_error" for item in logs)


def test_startup_failure_traceback_and_paths_are_suppressed(
    database_context: DatabaseContext, workspace_tmp_path: Path
) -> None:
    sentinel = "ghp_" + "a" * 24
    fixture_copy = workspace_tmp_path / "startup-failure-fixture"
    shutil.copytree(FIXTURE_DIR, fixture_copy)
    manifest_path = fixture_copy / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][sentinel] = "sha256:" + "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        _uvicorn_command("toss_dashboard_api.main:app", _free_loopback_port()),
        cwd=PROJECT_ROOT,
        env=_runtime_environment(database_context.url, fixture_copy),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
        check=False,
    )
    output = result.stdout + result.stderr
    logs = _parse_json_lines(output)
    assert result.returncode != 0
    assert sentinel not in output
    assert "Traceback" not in output
    assert str(PROJECT_ROOT) not in output
    assert str(workspace_tmp_path) not in output
    assert any(item.get("event") == "uvicorn_error" for item in logs)
