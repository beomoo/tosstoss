"""Pinned Ubuntu user-space setup; system packages are a separate privilege boundary."""

import argparse
import hashlib
import json
import os
import platform
import re
import shlex
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

PYTHON = "3.13.1"
NODE = "24.19.0"
NPM = "11.17.0"
UV = "0.12.13"  # Interpreter provisioner only; pip/requirements.lock own dependencies.
NODE_ARCHIVE = f"node-v{NODE}-linux-x64.tar.xz"
NODE_SHA256 = "14b342e71204f811bde6153be8e04b62aef63c236fef92b55f9c83154b409647"
UV_ARCHIVE = "uv-x86_64-unknown-linux-gnu.tar.gz"
UV_SHA256 = "745765a3b6e360ad76743599ae5c42e9278c7edf8bbff9fc76d05bf2623a04dd"
SAFE_FLAGS = {
    "LOCAL_ONLY": "true",
    "TRADING_ENABLED": "false",
    "DRY_RUN": "true",
    "OPENAI_API_ENABLED": "false",
    "ALLOW_ACCOUNT_ENDPOINTS": "false",
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def safe_path(path):
    """Reject symlink parents and non-directory/non-regular mutable paths."""
    for item in [*reversed(path.parents), path]:
        require(not item.is_symlink(), f"Refusing symlink path: {item}")
        if item.exists():
            require(
                item.is_dir() or (item.is_file() and item.stat().st_nlink == 1),
                f"Unexpected path type/link count: {item}",
            )


def native_elf(path):
    resolved = path.resolve(strict=True)
    require(not resolved.is_relative_to("/mnt"), f"Native Linux runtime required: {path}")
    with resolved.open("rb") as stream:
        require(stream.read(4) == b"\x7fELF", f"ELF runtime required: {path}")


def run(argv, root, env, capture=False):
    argv = list(map(str, argv))
    print("COMMAND " + shlex.join(argv), flush=True)
    result = subprocess.run(
        argv, cwd=root, env=env, text=True, stdout=subprocess.PIPE if capture else None, check=False
    )
    if capture:
        print(result.stdout, end="", flush=True)
    print(f"EXIT {result.returncode}", flush=True)
    require(result.returncode == 0, f"Command failed (exit {result.returncode})")
    return result.stdout if capture else None


def check_system():
    require(
        sys.platform == "linux" and platform.machine() == "x86_64",
        "Supported contract: Linux x86_64, Ubuntu 26.04 (glibc).",
    )
    require(sys.version_info >= (3, 12), "Bootstrap /usr/bin/python3 >= 3.12 required.")
    native_elf(Path(sys.executable))
    release = dict(
        line.split("=", 1)
        for line in Path("/etc/os-release").read_text().splitlines()
        if "=" in line
    )
    require(
        release.get("ID", "").strip('"') == "ubuntu"
        and release.get("VERSION_ID", "").strip('"') == "26.04",
        "Only Ubuntu 26.04 is currently covered by this Linux setup contract.",
    )
    packages = [
        "ca-certificates",
        "fontconfig",
        "libnspr4",
        "libnss3",
        "libasound2t64",
        "libasound2-data",
    ]
    missing = []
    for package in packages:
        p = subprocess.run(
            ["/usr/bin/dpkg-query", "-W", "-f=${db:Status-Status}", package],
            capture_output=True,
            text=True,
            check=False,
        )
        if p.returncode or p.stdout != "installed":
            missing.append(package)
    require(
        not missing,
        "Missing system prerequisites: "
        + " ".join(missing)
        + ". See docs/LINUX_DEVELOPMENT.md; setup never invokes sudo.",
    )
    fonts = subprocess.check_output(["/usr/bin/fc-list", ":lang=ko", "file", "family"], text=True)
    require(
        bool(fonts.strip()),
        "No Korean font: fc-list :lang=ko is empty. "
        "System prerequisite: fonts-lexi-gulim; see docs/LINUX_DEVELOPMENT.md.",
    )
    print(fonts, end="")
    print("SYSTEM PREREQUISITES PRESENT; Korean browser visual quality is a separate check.")


def download(url, path, expected):
    safe_path(path)
    if not path.exists():
        print(f"DOWNLOAD {url} -> {path}", flush=True)
        # Keep a failed partial download for diagnosis; never reuse it as the archive.
        partial = path.with_suffix(path.suffix + ".partial")
        safe_path(partial)
        require(
            not partial.exists(),
            f"Preserved partial download exists: {partial}. "
            "Inspect and move it aside explicitly before retrying.",
        )
        with urllib.request.urlopen(url, timeout=60) as response, partial.open("xb") as out:
            require(response.url.startswith("https://"), "HTTPS download required")
            while chunk := response.read(1024 * 1024):
                out.write(chunk)
        require(digest(partial) == expected, f"Checksum mismatch; preserved {partial}")
        partial.rename(path)
    require(digest(path) == expected, f"Archive checksum mismatch: {path}")
    print(f"SHA256 {expected} {path}", flush=True)


def unpack(archive, destination, expected_directory):
    target = destination / expected_directory
    safe_path(target)
    if not target.exists():
        with tarfile.open(archive) as tar:
            require(
                all(Path(member.name).parts[0] == expected_directory for member in tar),
                "Unexpected archive root",
            )
            tar.extractall(destination, filter="data")
    # Reuse is tied to archive bytes, not an executable's claimed version.
    with tarfile.open(archive) as tar:
        for member in tar:
            path = destination / member.name
            if member.isfile():
                require(not path.is_symlink() and path.is_file(), f"Runtime file changed: {path}")
                with tar.extractfile(member) as source:
                    require(
                        digest(path) == hashlib.file_digest(source, "sha256").hexdigest(),
                        f"Runtime differs from verified archive: {path}",
                    )
            elif member.issym():
                require(
                    path.is_symlink() and os.readlink(path) == member.linkname,
                    f"Runtime link changed: {path}",
                )
                require(path.resolve().is_relative_to(target), f"Runtime link escaped: {path}")
    return target


def node_command(root):
    """Return exact Node/npm argv, independent of PATH, for daily commands and E2E."""
    prefix = root / "var/linux" / f"node-v{NODE}-linux-x64"
    node = prefix / "bin/node"
    npm = prefix / "lib/node_modules/npm/bin/npm-cli.js"
    marker = root / "var/linux/runtime.json"
    for path in [node, npm, marker]:
        safe_path(path)
    native_elf(node)
    identity = json.loads(marker.read_text())
    require(identity["root"] == str(root), "Runtime belongs to a different source instance")
    require((identity["node"], identity["npm"]) == (NODE, NPM), "Runtime contract drift")
    for path in [node, npm, prefix / "lib/node_modules/npm/package.json"]:
        require(
            digest(path) == identity["runtime_hashes"][str(path.relative_to(root))],
            f"Runtime bytes changed: {path}; rerun verified setup",
        )
    return [str(node), str(npm)]


def setup(root):
    check_system()
    require(os.geteuid() != 0, "Run user-space setup without sudo/root.")
    safe_path(root)
    require(not root.is_relative_to("/mnt"), "Keep the Linux candidate on the Linux filesystem.")
    require((root / ".python-version").read_text().strip() == PYTHON, "Python contract drift")
    require((root / ".node-version").read_text().strip() == NODE, "Node contract drift")
    require(
        json.loads((root / "package.json").read_text())["packageManager"] == f"npm@{NPM}",
        "npm contract drift",
    )
    directory = root / "var/linux"
    venv = root / ".venv"
    modules = root / "node_modules"
    ownership = directory / "setup-state.json"
    for path in [directory, venv, modules, root / "apps/web/node_modules", ownership]:
        safe_path(path)
    locks = {name: digest(root / name) for name in ["requirements.lock", "package-lock.json"]}
    state = {"root": str(root), "python": PYTHON, "node": NODE, "npm": NPM, "locks": locks}
    if ownership.exists():
        require(
            json.loads(ownership.read_text()) == state,
            "Existing setup state differs; preserve it and inspect before changing environments.",
        )
    else:
        for path in [directory, venv, modules, root / "apps/web/node_modules"]:
            require(
                not path.exists(),
                f"Unexpected existing environment: {path}. "
                "Preserve/move it aside explicitly, or use a fresh source instance; "
                "nothing deleted.",
            )
        directory.mkdir(parents=True)
        with ownership.open("x") as out:
            json.dump(state, out, indent=2)
    for name in [
        "runtime.json",
        "activate.sh",
        "npm-userrc",
        "npm-globalrc",
        "python",
        "uv-cache",
        "pip-cache",
        "npm-cache",
        "playwright",
    ]:
        safe_path(directory / name)
    for name in ["npm-userrc", "npm-globalrc"]:
        path = directory / name
        require(not path.exists() or path.read_bytes() == b"", f"Unexpected npm config: {path}")
        path.touch(exist_ok=True)
    env = {
        "HOME": os.environ["HOME"],
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "UV_PYTHON_INSTALL_DIR": str(directory / "python"),
        "UV_CACHE_DIR": str(directory / "uv-cache"),
        "UV_NO_CONFIG": "1",
        "PIP_CONFIG_FILE": "/dev/null",
        "PIP_CACHE_DIR": str(directory / "pip-cache"),
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "NPM_CONFIG_CACHE": str(directory / "npm-cache"),
        "NPM_CONFIG_USERCONFIG": str(directory / "npm-userrc"),
        "NPM_CONFIG_GLOBALCONFIG": str(directory / "npm-globalrc"),
        "PLAYWRIGHT_BROWSERS_PATH": str(directory / "playwright"),
        "PLAYWRIGHT_HOST_PLATFORM_OVERRIDE": "ubuntu24.04-x64",
        "PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD": "1",
        "NEXT_TELEMETRY_DISABLED": "1",
        "NODE_DISABLE_COMPILE_CACHE": "1",
        **SAFE_FLAGS,
    }
    uv_archive = directory / UV_ARCHIVE
    download(
        f"https://github.com/astral-sh/uv/releases/download/{UV}/{UV_ARCHIVE}",
        uv_archive,
        UV_SHA256,
    )
    uv = unpack(uv_archive, directory, "uv-x86_64-unknown-linux-gnu") / "uv"
    native_elf(uv)
    require(
        run([uv, "--version"], root, env, True).split()[1] == UV, "uv provisioner version drift"
    )
    catalog = json.loads(
        run(
            [
                uv,
                "python",
                "list",
                PYTHON,
                "--all-versions",
                "--only-downloads",
                "--show-urls",
                "--output-format",
                "json",
                "--no-config",
            ],
            root,
            env,
            True,
        )
    )
    run([uv, "python", "install", "--no-bin", "--no-config", "--verbose", PYTHON], root, env)
    base = Path(
        run(
            [uv, "python", "find", "--managed-python", "--no-config", PYTHON], root, env, True
        ).strip()
    )
    require(
        base.resolve().is_relative_to(directory / "python"), "Python escaped managed runtime root"
    )
    native_elf(base)
    if not venv.exists():
        run([base, "-I", "-B", "-m", "venv", "--without-pip", venv], root, env)
    python = venv / "bin/python"
    require(not (venv / "Scripts").exists(), "Windows venv cannot be reused")
    native_elf(python)
    info = json.loads(
        run(
            [
                python,
                "-I",
                "-B",
                "-c",
                "import json,sys; print(json.dumps([sys.platform,"
                "'.'.join(map(str,sys.version_info[:3])),sys.prefix,sys._base_executable]))",
            ],
            root,
            env,
            True,
        )
    )
    require(
        info[:3] == ["linux", PYTHON, str(venv)] and Path(info[3]).resolve() == base.resolve(),
        "Existing venv does not belong to the exact Linux development contract; preserve it",
    )
    run([python, "-I", "-B", "-m", "ensurepip", "--upgrade", "--default-pip"], root, env)
    run(
        [python, "-I", "-B", "-m", "pip", "install", "--require-hashes", "-r", "requirements.lock"],
        root,
        env,
    )
    run(
        [
            python,
            "-I",
            "-B",
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--no-build-isolation",
            "-e",
            ".",
        ],
        root,
        env,
    )
    run([python, "-I", "-B", "-m", "pip", "check"], root, env)
    installed = json.loads(
        run([python, "-I", "-B", "-m", "pip", "list", "--format=json"], root, env, True)
    )

    def normalize(value):
        return re.sub(r"[-_.]+", "-", value).lower()

    expected = {
        normalize(name): version
        for name, version in re.findall(
            r"^([\w.-]+)==([^\s;\\]+)", (root / "requirements.lock").read_text(), re.M
        )
    }
    actual = {normalize(item["name"]): item["version"] for item in installed}
    require(
        {k: v for k, v in actual.items() if k not in {"pip", "toss-invest-dashboard"}} == expected,
        "Installed Python packages differ from requirements.lock (including extras)",
    )
    node_archive = directory / NODE_ARCHIVE
    download(
        f"https://nodejs.org/download/release/v{NODE}/{NODE_ARCHIVE}", node_archive, NODE_SHA256
    )
    prefix = unpack(node_archive, directory, f"node-v{NODE}-linux-x64")
    node = prefix / "bin/node"
    npm = prefix / "lib/node_modules/npm/bin/npm-cli.js"
    native_elf(node)
    env["PATH"] = f"{prefix / 'bin'}:/usr/bin:/bin"
    require(
        run(
            [node, "-p", "process.version+':'+process.platform+':'+process.arch"], root, env, True
        ).strip()
        == f"v{NODE}:linux:x64",
        "Exact native Node identity required",
    )
    require(
        run([node, npm, "--version"], root, env, True).strip() == NPM, "Exact npm version required"
    )
    run([node, npm, "ci", "--no-audit", "--no-fund"], root, env)
    run([node, npm, "ls", "--all"], root, env)
    require(
        json.loads(run([node, npm, "query", ":extraneous"], root, env, True)) == [],
        "Extraneous npm dependencies",
    )
    for forbidden in [
        "@img/sharp-wasm32",
        "@emnapi/runtime",
        "next/wasm",
        "next/next-swc-fallback",
    ]:
        require(
            not (modules / forbidden).exists(), f"Forbidden WASM/fallback artifact: {forbidden}"
        )
    require(
        json.loads((modules / "playwright/package.json").read_text())["version"] == "1.57.0",
        "Playwright contract drift",
    )
    env.pop("PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD")
    run([node, modules / "playwright/cli.js", "install", "chromium"], root, env)
    browser = Path(
        run(
            [node, "-e", "console.log(require('playwright').chromium.executablePath())"],
            root,
            env,
            True,
        ).strip()
    )
    require(
        browser.resolve().is_relative_to(directory / "playwright"),
        "Browser escaped managed runtime root",
    )
    for executable in [
        browser,
        *sorted(
            (directory / "playwright").glob("chromium_headless_shell-*/chrome-linux/headless_shell")
        ),
    ]:
        native_elf(executable)
        libraries = run(["/usr/bin/ldd", executable], root, env, True)
        require(
            "not found" not in libraries,
            "Missing browser shared libraries; see system prerequisite contract",
        )
    env["NODE_OPTIONS"] = f'--require="{root / "scripts/node_offline_guard.cjs"}"'
    run(
        [
            node,
            "-e",
            "(async()=>{const b=await require('playwright').chromium.launch({headless:true});"
            "await b.close();console.log('CHROMIUM_LAUNCH_OK')})()"
            ".catch(e=>{console.error(e);process.exit(1)})",
        ],
        root,
        env,
    )
    require(
        all(digest(root / name) == value for name, value in locks.items()), "Dependency lock drift"
    )
    identity = {
        **state,
        "uv": UV,
        "base_python": str(base),
        "python_download_catalog": catalog,
        "python_packages": installed,
        "browser": str(browser),
        "playwright_override": env["PLAYWRIGHT_HOST_PLATFORM_OVERRIDE"],
        "runtime_hashes": {
            str(p.relative_to(root)): digest(p)
            for p in [node, npm, prefix / "lib/node_modules/npm/package.json", uv, base.resolve()]
        },
    }
    (directory / "runtime.json").write_text(json.dumps(identity, indent=2) + "\n")
    activation = {
        **SAFE_FLAGS,
        "PATH": env["PATH"],
        "PLAYWRIGHT_BROWSERS_PATH": env["PLAYWRIGHT_BROWSERS_PATH"],
        "PLAYWRIGHT_HOST_PLATFORM_OVERRIDE": env["PLAYWRIGHT_HOST_PLATFORM_OVERRIDE"],
        "NEXT_TELEMETRY_DISABLED": "1",
        "NODE_DISABLE_COMPILE_CACHE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "NPM_CONFIG_OFFLINE": "true",
        "NEXT_IGNORE_INCORRECT_LOCKFILE": "1",
        "NEXT_DISABLE_SWC_WASM": "1",
        "NPM_CONFIG_CACHE": env["NPM_CONFIG_CACHE"],
        "NPM_CONFIG_USERCONFIG": env["NPM_CONFIG_USERCONFIG"],
        "NPM_CONFIG_GLOBALCONFIG": env["NPM_CONFIG_GLOBALCONFIG"],
        "NODE_OPTIONS": env["NODE_OPTIONS"],
    }
    (directory / "activate.sh").write_text(
        "# Generated by scripts/setup.sh for this exact source location.\n"
        + "\n".join(f"export {key}={shlex.quote(value)}" for key, value in activation.items())
        + "\n"
    )
    node_command(root)
    print(f"SETUP COMPLETE. source {shlex.quote(str(directory / 'activate.sh'))}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-system", action="store_true")
    args = parser.parse_args()
    try:
        if args.check_system:
            check_system()
        else:
            setup(Path(__file__).resolve().parent.parent)
    except (RuntimeError, OSError, ValueError) as error:
        print(f"SETUP STOP: {error}", file=sys.stderr)
        sys.exit(1)
