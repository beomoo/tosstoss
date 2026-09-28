"""Linux startup for the existing Phase 1 Playwright tests."""

import hashlib
import json
import os
import re
import runpy
import stat
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
PYTHON = REPO / ".venv/bin/python"
GUARD = REPO / "scripts/python_runtime_guard.py"


def safe_path(path: Path, root: Path) -> None:
    relative = path.relative_to(root)
    if ".." in relative.parts:
        raise RuntimeError("Parent traversal is not allowed in E2E paths.")
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise RuntimeError("E2E paths must not contain symbolic links.")
        if current.exists():
            info = current.stat()
            if not stat.S_ISDIR(info.st_mode) and (
                not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
            ):
                raise RuntimeError("E2E files must be regular files with one link.")


def main() -> None:
    if sys.platform != "linux" or sys.argv[1:] not in (["backend"], ["frontend"]):
        raise RuntimeError("Expected Linux E2E startup mode: backend or frontend.")
    expected_python = tuple(map(int, (REPO / ".python-version").read_text().split(".")))
    if sys.version_info[:3] != expected_python:
        raise RuntimeError("The E2E Python runtime differs from the pinned version.")

    database = Path(os.environ["PHASE1_E2E_DATABASE_PATH"])
    if (
        database.parent.parent != Path("/tmp")
        or not re.fullmatch(r"tosstoss-gate-a-e2e-[0-9a-f]{32}", database.parent.name)
        or database.name != "playwright-e2e.db"
        or not database.parent.is_dir()
    ):
        raise RuntimeError("E2E requires a fresh disposable /tmp database directory.")
    safe_path(database, Path("/tmp"))

    build_id_path = REPO / "apps/web/.next/BUILD_ID"
    sentinel_path = REPO / "var/phase-01-build-sentinel.txt"
    evidence_path = REPO / "var/phase-01-build-evidence.json"
    for path in (build_id_path, sentinel_path, evidence_path, GUARD):
        safe_path(path, REPO)
        if not path.is_file():
            raise RuntimeError("Current-build E2E evidence is missing.")
    build_id = build_id_path.read_text().strip()
    sentinel = sentinel_path.read_text().strip()
    sentinel_sha256 = hashlib.sha256(sentinel_path.read_bytes()).hexdigest()
    evidence = json.loads(evidence_path.read_text())
    if (
        not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", build_id)
        or not re.fullmatch(r"PHASE1_RUNTIME_[0-9a-f]{32}", sentinel)
        or build_id_path.stat().st_mtime_ns < sentinel_path.stat().st_mtime_ns
        or evidence.get("schema_version") != 1
        or evidence.get("build_id") != build_id
        or evidence.get("sentinel_sha256") != sentinel_sha256
    ):
        raise RuntimeError("E2E evidence does not match the current build and sentinel.")

    env = dict(os.environ)
    env.update(
        LOCAL_ONLY="true",
        TRADING_ENABLED="false",
        DRY_RUN="true",
        OPENAI_API_ENABLED="false",
        ALLOW_ACCOUNT_ENDPOINTS="false",
        PYTHONDONTWRITEBYTECODE="1",
        NEXT_TELEMETRY_DISABLED="1",
        NODE_DISABLE_COMPILE_CACHE="1",
        NPM_CONFIG_OFFLINE="true",
        NEXT_IGNORE_INCORRECT_LOCKFILE="1",
        NEXT_DISABLE_SWC_WASM="1",
        NODE_OPTIONS=f'--require="{REPO / "scripts/node_offline_guard.cjs"}"',
    )
    if sys.argv[1] == "frontend":
        env.update(
            PHASE1_SERVER_ONLY_SENTINEL=sentinel,
            DASHBOARD_API_BASE_URL="http://127.0.0.1:8000",
        )
        runtime = runpy.run_path(str(REPO / "scripts/linux_setup.py"))
        npm_command = runtime["node_command"](REPO)
        env["PATH"] = f"{Path(npm_command[0]).parent}:/usr/bin:/bin"
        os.chdir(REPO / "apps/web")
        os.execve(npm_command[0], [*npm_command, "run", "start"], env)

    for suffix in ("", "-wal", "-shm", "-journal"):
        path = Path(str(database) + suffix)
        safe_path(path, Path("/tmp"))
        if path.exists():
            raise RuntimeError("The disposable E2E database must not exist at startup.")
    database_url = f"sqlite:///{database}"
    fixture_dir = REPO / "fixtures/phase_01"
    env.update(DASHBOARD_DATABASE_URL=database_url, DASHBOARD_FIXTURE_DIR=str(fixture_dir))
    for module, args in (
        ("alembic", ["-x", f"database_url={database_url}", "upgrade", "head"]),
        (
            "toss_dashboard_api.fixtures.importer",
            ["--database-url", database_url, "--fixture-dir", str(fixture_dir)],
        ),
    ):
        subprocess.run(
            [str(PYTHON), "-I", "-B", "-S", str(GUARD), "--module", module, "--", *args],
            cwd=REPO,
            env=env,
            check=True,
        )
        for suffix in ("", "-wal", "-shm", "-journal"):
            safe_path(Path(str(database) + suffix), Path("/tmp"))
    print(
        json.dumps(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": "INFO",
                "logger": "phase1.e2e",
                "event": "e2e_build_coherence",
                "build_id": build_id,
                "sentinel_sha256": sentinel_sha256,
            }
        ),
        flush=True,
    )
    os.chdir(REPO)
    os.execve(
        PYTHON,
        [
            str(PYTHON),
            "-I",
            "-B",
            "-S",
            str(GUARD),
            "--module",
            "uvicorn",
            "--",
            "toss_dashboard_api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--no-access-log",
            "--log-config",
            str(REPO / "services/api/uvicorn_log_config.json"),
        ],
        env,
    )


if __name__ == "__main__":
    main()
