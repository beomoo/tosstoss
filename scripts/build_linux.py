"""Offline Linux production build with the existing E2E build-evidence contract."""

import hashlib
import json
import os
import re
import runpy
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
SETUP = runpy.run_path(str(ROOT / "scripts/linux_setup.py"))


def main():
    require = SETUP["require"]
    safe_path = SETUP["safe_path"]
    run = SETUP["run"]
    npm = SETUP["node_command"](ROOT)
    web = ROOT / "apps/web"
    build = web / ".next"
    runtime = ROOT / "var"
    sentinel = runtime / "phase-01-build-sentinel.txt"
    evidence = runtime / "phase-01-build-evidence.json"
    for path in [build, sentinel, evidence, web / "next-env.d.ts", web / "tsconfig.json"]:
        safe_path(path)
    require(
        not any(name.startswith("NEXT_PUBLIC_") for name in os.environ),
        "NEXT_PUBLIC environment variables are prohibited",
    )
    for folder in [ROOT, web]:
        for path in folder.glob(".env*"):
            safe_path(path)
            require(
                not re.search(r"(?m)^\ufeff?\s*(?:export\s+)?NEXT_PUBLIC_", path.read_text()),
                f"Public build configuration is prohibited: {path.name}",
            )
    archive = (
        runtime
        / "linux/build-history"
        / (datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex)
    )
    safe_path(archive)
    archive.mkdir(parents=True)
    for path in [build, sentinel, evidence]:
        if path.exists():
            path.rename(archive / path.name)
    sentinel.write_text("PHASE1_RUNTIME_" + uuid4().hex)
    inputs = [
        ROOT / name
        for name in [
            "package.json",
            "package-lock.json",
            "requirements.lock",
            "apps/web/package.json",
            "apps/web/next.config.ts",
            "apps/web/tsconfig.json",
        ]
    ]
    before = {str(p): SETUP["digest"](p) for p in inputs}
    env = dict(os.environ, **SETUP["SAFE_FLAGS"])
    env.update(
        PATH=f"{Path(npm[0]).parent}:/usr/bin:/bin",
        NEXT_TELEMETRY_DISABLED="1",
        NODE_DISABLE_COMPILE_CACHE="1",
        NPM_CONFIG_OFFLINE="true",
        NEXT_IGNORE_INCORRECT_LOCKFILE="1",
        NEXT_DISABLE_SWC_WASM="1",
        NODE_OPTIONS=f'--require="{ROOT / "scripts/node_offline_guard.cjs"}"',
        PHASE1_SERVER_ONLY_SENTINEL=sentinel.read_text(),
    )
    run([npm[0], ROOT / "scripts/node_runtime_preflight.cjs"], ROOT, env)
    run([*npm, "run", "build", "--workspace", "apps/web"], ROOT, env)
    require(all(SETUP["digest"](Path(p)) == sha for p, sha in before.items()), "Build input drift")
    for name in ["@img/sharp-wasm32", "@emnapi/runtime", "next/wasm", "next/next-swc-fallback"]:
        require(not (ROOT / "node_modules" / name).exists(), f"Forbidden WASM fallback: {name}")
    for name in ["cache", "dev"]:
        path = build / name
        safe_path(path)
        if path.exists():
            path.rename(archive / ("generated-" + name))
    build_id = build / "BUILD_ID"
    for name in ["static", "server"]:
        path = build / name
        safe_path(path)
        require(path.is_dir(), f"Missing build directory: {path}")
        files = list(path.rglob("*"))
        require(any(p.is_file() for p in files), f"Empty build directory: {path}")
        for item in files:
            safe_path(item)
            if item.is_file():
                require(
                    item.stat().st_mtime_ns >= sentinel.stat().st_mtime_ns,
                    f"Stale build file: {item}",
                )
    safe_path(build_id)
    require(re.fullmatch(r"[A-Za-z0-9_-]{8,128}", build_id.read_text().strip()), "Invalid BUILD_ID")
    require(build_id.stat().st_mtime_ns >= sentinel.stat().st_mtime_ns, "Stale BUILD_ID")
    record = {
        "schema_version": 1,
        "build_id": build_id.read_text().strip(),
        "sentinel_sha256": hashlib.sha256(sentinel.read_bytes()).hexdigest(),
        "sentinel_written_at_utc": datetime.fromtimestamp(
            sentinel.stat().st_mtime, UTC
        ).isoformat(),
        "build_id_written_at_utc": datetime.fromtimestamp(
            build_id.stat().st_mtime, UTC
        ).isoformat(),
        "completed_at_utc": datetime.now(UTC).isoformat(),
    }
    evidence.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record))


if __name__ == "__main__":
    main()
