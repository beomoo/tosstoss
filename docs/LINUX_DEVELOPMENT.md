# Linux / WSL development contract

This user-space contract currently covers Ubuntu 26.04, glibc, x86_64, with
the repository on the Linux filesystem. It does not establish fresh-OS
bootstrap, Windows reviewer semantics, R1 acceptance, or cutover approval.
Keep `LOCAL_ONLY=true`, `TRADING_ENABLED=false`, `DRY_RUN=true`,
`OPENAI_API_ENABLED=false`, and `ALLOW_ACCOUNT_ENDPOINTS=false`.

## System prerequisites: separate administrator action

`bash scripts/setup.sh --check-system` is read-only and never invokes sudo.
It checks Ubuntu/architecture, native `/usr/bin/python3 >= 3.12` for bootstrap,
CA certificates, fontconfig, libnspr4, libnss3, libasound2t64 and libasound2-data,
and a nonempty `fc-list :lang=ko`. The project Python is separately provisioned
as exact CPython 3.13.1; bootstrap Python is not the project runtime.

| Requirement | Ubuntu package / check |
| --- | --- |
| HTTPS trust | ca-certificates |
| libnspr4.so, libplc4.so, libplds4.so | libnspr4 |
| libnss3.so, libnssutil3.so, libsmime3.so | libnss3 |
| libasound.so.2 and ALSA data | libasound2t64, libasound2-data |
| Korean font discovery | fontconfig; `fc-list :lang=ko file family` |
| Small Korean sans-serif fallback | fonts-lexi-gulim (or an already usable Korean font) |

Local Ubuntu 26.04 metadata identifies fonts-lexi-gulim 20090423-3build1,
307812 downloaded bytes, 1583 KiB installed, one font family, with all 11172
modern Hangul syllables. The package archive SHA-256 is
`29d5925dc8b9281a7221caa14f31618e4d3ec01408daf58f8cadafa87f447fd8`.
Its actual Korean browser appearance must still be inspected; DOM assertions
and font registration alone are not visual acceptance.

If a prerequisite is missing, an administrator must inspect local package
metadata and simulate an exact version-pinned package transaction first:

```bash
apt-cache policy fonts-lexi-gulim
apt-cache show fonts-lexi-gulim
apt-get --simulate --no-install-recommends --no-remove --no-upgrade \
  install fonts-lexi-gulim=20090423-3build1
```

Only the explicitly missing prerequisites may be installed after confirming
zero removals/downgrades/broad upgrades and an empty `dpkg --audit`. Repeat the
same exact simulation immediately before any privileged installation, and
compare package inventories afterwards. Stop if the version or transaction
differs. `setup.sh` performs no apt mutations or password handling. A stale
package index or unrelated broken package state requires separate system
administration; setup must not repair it silently. Browser installation is
followed by `ldd` checks and an actual offline blank-page Chromium launch.

## User-space setup

From any working directory, run the repository's `scripts/setup.sh` by path.
It derives the source root from its own location:

```bash
bash scripts/setup.sh
source var/linux/activate.sh
```

The generated activation is specific to this source instance. Source it in
each development terminal. It puts the verified native Node prefix first
(system `/usr/bin:/bin` only after it), sets the offline Node guard and safe
application flags, and selects the repository-private Playwright cache.
Always invoke project Python via `.venv/bin/python`, not an ambient Python.

Setup provisions checksum-pinned uv 0.12.13 from its official release as an
interpreter provisioner only. It installs exact CPython 3.13.1 under
`var/linux/python`, creates `.venv`, runs ensurepip, installs
`requirements.lock` using `--require-hashes`, installs this package editable
with `--no-deps --no-build-isolation`, and runs `pip check`. Installed package
versions must exactly equal the lock, apart from the ensurepip bootstrap pip
and this editable project. Both are recorded in `var/linux/runtime.json`.

Node comes from the official Node 24.19.0 Linux x64 archive, verified against
the pinned official SHA-256 before extraction. Its bundled npm must be exactly
11.17.0. Setup runs `npm ci`, `npm ls --all`, and the extraneous dependency
check. It rejects sharp WASM, emnapi runtime and SWC fallback artifacts. It does
not change dependency versions, regenerate locks, use uv dependency resolution,
or introduce another JavaScript package manager.

All runtime archives, interpreters, Node/npm, package caches and Playwright
browsers are under ignored `var/linux/`; `.venv` and `node_modules` are local
to this exact repository. User/global pip, npm and uv configuration is excluded
from setup. An isolated HOME therefore needs no preinstalled user runtime/cache.
The system bootstrap interpreter and documented OS prerequisites remain host
inputs. `runtime.json` records paths, identities, hashes and installed packages.

Setup refuses an existing unowned `.venv`, `node_modules` or `var/linux` before
installing anything. A Windows environment is never reused. Inspect and
explicitly preserve/move unexpected artifacts aside, or use a fresh source
instance. Setup never deletes them. A setup-owned retry must match its source
root, locks and versions; interpreter identity and archive bytes are rechecked.
Failed partial downloads remain available for diagnosis. This provenance check
is for development artifact integrity, not a substitute for R1 human authority.

Playwright remains **1.57.0**. Ubuntu 26.04 is not natively recognized by that
version; the contract explicitly sets
`PLAYWRIGHT_HOST_PLATFORM_OVERRIDE=ubuntu24.04-x64`. This is an empirically
validated compatibility workaround, not an official Ubuntu 26.04 support claim.

Official runtime provenance:
- https://nodejs.org/download/release/v24.19.0/SHASUMS256.txt
- https://github.com/astral-sh/uv/releases/tag/0.12.13

## Local fixture development

The intentional Linux development DB is `var/linux-dev/dashboard.db`.
Never use the preserved `var/dashboard-fixture-b22e919d59cf.db` as a runtime DB.
These commands are run from the repository root after activation:

```bash
mkdir -p var/linux-dev
export DASHBOARD_DATABASE_URL="sqlite:///$PWD/var/linux-dev/dashboard.db"
export DASHBOARD_FIXTURE_DIR="$PWD/fixtures/phase_01"
.venv/bin/python -I -B -S scripts/python_runtime_guard.py --module alembic -- \
  -x "database_url=$DASHBOARD_DATABASE_URL" upgrade head
.venv/bin/python -I -B -S scripts/python_runtime_guard.py \
  --module toss_dashboard_api.fixtures.importer -- \
  --database-url "$DASHBOARD_DATABASE_URL" --fixture-dir "$DASHBOARD_FIXTURE_DIR"
.venv/bin/python -I -B -S scripts/python_runtime_guard.py --module uvicorn -- \
  toss_dashboard_api.main:app --host 127.0.0.1 --port 8000 --no-access-log \
  --log-config services/api/uvicorn_log_config.json
```

In another activated terminal:

```bash
export DASHBOARD_API_BASE_URL=http://127.0.0.1:8000
npm run dev --workspace apps/web
```

Existing npm scripts bind the frontend to 127.0.0.1. Use Ctrl-C to stop the
processes you started. No additional dev.sh is needed. The Python runtime
guard, Node offline guard and WASM prohibition continue to apply. Linux never
maps R1 OWNER SID to UID/GID; the Windows `EqualSid` boundary stays fail-closed.

## Production build and existing E2E

```bash
.venv/bin/python -I -B scripts/build_linux.py
```

This runs the existing native/offline Node preflight and production build,
preserves previous generated output under `var/linux/build-history/`, and
produces the unchanged build-ID/server-only-sentinel evidence required by E2E.
It does not remove previous failures or regenerate expected test results.

With ports 8000/3000 free, use Python's UUID to satisfy the existing exact
disposable-directory contract and run the existing test assertions unchanged:

```bash
export PHASE1_E2E_DATABASE_PATH=$(.venv/bin/python -I -B -c \
  'import pathlib,uuid; p=pathlib.Path("/tmp")/("tosstoss-gate-a-e2e-"+uuid.uuid4().hex); p.mkdir(mode=0o700); print(p/"playwright-e2e.db")')
npm run e2e --workspace apps/web
```

The retained `gate-a` directory prefix is an existing E2E path safety contract,
not a claim about which gate produced the run. The E2E frontend launcher uses
the explicit verified Node executable and its npm CLI, never PATH npm.
Keep diagnostic DB/test artifacts until their preservation disposition is clear.

Focused contract checks: `/usr/bin/python3 -I -B scripts/check_linux_setup.py`.
They are separate from the frozen 1080-test backend inventory. The seven
Windows-only backend cases must be accounted for separately on Linux, never
emulated or silently skipped as successful Windows validation.
