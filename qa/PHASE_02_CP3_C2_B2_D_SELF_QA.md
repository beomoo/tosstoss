# CP3-C2-B2-D self QA — 2026-09-28

Status: **IMPLEMENTED — GPT FINAL INDEPENDENT VERIFICATION REQUIRED**. This is a self-QA result, not an independent PASS/CLOSED decision. The initial blocked candidate and its no-commit/no-push state are retained below as historical evidence; the bounded remediation result appears at the end.

## Authority and checkout

- Exact base: `48d4201281db2fabdb58f09ba6860bd184e722c8` (`origin/feature/phase-02-toss` at entry).
- Candidate: `feature/phase-02-b2d-issuer-disposition` in the managed Linux worktree. The original checkout and its untracked R1 evidence were left untouched.
- D0 read-only audit found the required challenge, consumption, authentication, approval, observation, link, and head relations in frozen `0005`; `0006` and `0007` retain them. B2-B has reusable locked evaluation rules. The B1 challenge-to-consumption-to-authentication relationship needs same-transaction server checks, which this service provides.
- The full user implementation instruction is supplied separately with the GPT review package. This work does not authorize the next checkpoint or a main/integration merge.

## Changed files and implementation

| File | Purpose |
| --- | --- |
| `services/api/src/toss_dashboard_api/reviewer/issuer_disposition.py` | Local, unrouted, owner-checked service; R1 WebAuthn verification and counter ledger reuse; challenge issuance/terminal consumption; APPROVED, REJECTED, REVOKED, paired SUPERSEDED; canonical Issuer insert-or-verify; event/observation/link/head history; post-approval REVIEW_REQUIRED. |
| `services/api/src/toss_dashboard_api/domain/issuer_authority.py` | Exposes the same B2-B rules through `evaluate_locked` on the caller's session and SQLite writer transaction. |
| `tests/backend/test_issuer_disposition.py` | Real disposable SQLite relational, WebAuthn, race, idempotency, negative binding, and rollback tests. |
| `scripts/policy-scan.ps1` | Registers the new backend test in the exact approved file set and recalculates its strict source digest. No scan pattern, threshold, or exception was relaxed. |
| `STATUS.md`, `CHANGELOG.md`, `KNOWN_ISSUES.md`, this report, `qa/CP3_C2_B2_D_MIGRATION_BLOB_PROOF.txt`, `qa/CP3_C2_B2_D_FROZEN_SOURCE_PROOF.txt`, `qa/CP3_C2_B2_D_SCANNER_COUNT_PROOF.txt`, `qa/CP3_C2_B2_D_SAMPLE.json`, `qa/CP3_C2_B2_D_GPT_REVIEW_REQUEST.md` | Candidate status, blocker, immutable source evidence, actual disposable fixture output, and independent review instructions. |

The service creates no Security row, VERIFIED ProviderIdentityMapping, provider rekey, frontend route, trading path, scheduler, or live API call. It neither creates nor changes migrations. The existing R1 cryptographic verifier, credential policy, OWNER/SID implementation, and counter reconstruction remain unchanged.

## Historical first-candidate verification results (superseded by bounded remediation)

| Check | Result | Scope |
| --- | --- | --- |
| B2-D focused, final source | **30 passed**, exit `0` | `tests/backend/test_issuer_disposition.py`; no skip/xfail/deselect. |
| B2-B/R1/migration focused regression, exploratory pre-final | **440 passed**, exit `0` | Eight named backend test files; source/test edits followed this run, so it is not final-state full regression evidence. |
| Backend Ruff check / format check / mypy | exit `0` each | All backend source and tests for Ruff; 68 source files for mypy. |
| Frontend lint / typecheck / unit test / build | exit `0` each | 10 unit test files, 43 tests passed; no frontend source change. |
| Linux exact `setup.sh` / `build_linux.py` | exit `0` each | Isolated candidate environment and production build evidence. |
| Linux fixture E2E | exit `0` | Fresh disposable `/tmp` DB; 2 Playwright tests listed. Initial attempts failed before tests because the worktree lacked `.venv` and a required DB path; setup and a fresh path resolved those environment prerequisites. |
| Windows-local QA mirror policy scan | exit `0` on its scanned snapshot | Exact candidate source hashes copied to a short-path QA clone; approved new test path and manifest digest updated without weakening rules. Later report/test edits and STOP mean this is not a final-tree policy-scan claim. This is not R1 Windows security QA. |
| Windows-local QA mirror build / fixture E2E / lint / typecheck | exit `0` each | Required scanner artifact producers; the Windows QA mirror is not the authoritative implementation worktree. |
| Standard secret scan | **exit `1` — BLOCKED** | The frozen generated-artifact exception proof expects 854 pinned mypy metadata files. B2-D's new production Python module yields 855; the scanner rejects the changed population before a final source scan result. No scanner exception was changed. A separate authorization decision is required for an exact bounded control update. |
| Full backend `pytest -q` on Linux | **1102 passed, 7 failed**, exit `1` | All 7 failures are the frozen `test_reviewer_windows_owner.py` tests calling Win32 `_Win32()` under Linux and receiving `WINDOWS_REQUIRED`. No B2-D test failed. The production source matched the final source; later test-only additions were verified in the separate final B2-D focused run. A pre-final run was interrupted after 120 passed (exit `2`) when source/tests changed. |
| Migration immutability | **7/7 exact Git blobs match base; `0008` absent** | See `CP3_C2_B2_D_MIGRATION_BLOB_PROOF.txt`. Ten frozen R1/contract/model source blobs also match exact base. |

No failing test was skipped, marked xfail, weakened, or removed. Counts in this table are direct command results; a command that did not reach test execution is reported as such.

## Relational and safety evidence

- An exact READY leaf with valid, fresh WebAuthn produces one VERIFIED issuer authentication, approval event with observation membership, canonical Issuer, APPROVED link, and UNRESOLVED head. KR DART corp code and US SEC registrant CIK cases pass.
- REJECTED appends only the disposition event. REVOKED preserves the prior event/link and Issuer, appends successors, and moves the head by guarded CAS. SUPERSEDED requires distinct old/new challenges, consumptions, and authentications and commits the old SUPERSEDED plus successor APPROVED chain atomically.
- Wrong disposition, invalid signature/origin, absent UV/UP, unknown credential, expiration, altered challenge bindings, single-auth supersession, stale authority, and conflicting canonical issuer fail closed in the focused tests. A real SQLite APPROVED versus REJECTED race yields one initial disposition.
- A signed assertion with an incorrect RP ID hash fails at the B2-D entry point. The approval test checks the exact observation IDs, content hashes, and contiguous membership ordinals linked to its approval event.
- Late authority loss preserves the historical approval and appends a REVIEW_REQUIRED machine decision and safety link/head. B2-B evaluation occurs on the same SQLAlchemy session and SQLite `BEGIN IMMEDIATE` transaction as disposition execution.
- Tests assert Security count and VERIFIED mapping count do not increase and compare the provider identity row column by column before/after approval. No name-only or symbol-only merge is implemented; issuer promotion uses the exact B2-B anchor and decisive legal-name evidence.

## Security, limits, and remaining risk

- `LOCAL_ONLY=true`, `TRADING_ENABLED=false`, and `DRY_RUN=true` remain the operating boundary. No OpenAI API, paid API, or live provider request was used.
- Bounded Windows-native B2-D→R1 OWNER check: **REQUIRED BUT NOT VERIFIED** because the new B2-D entry point newly traverses the frozen R1 owner boundary. Computer Use initialization returned `Mcp error: -32602: sandboxCwd is not a local file URI: file:///home/beomooo/projects/tosstoss`. **COMPUTER USE UNAVAILABLE — STOP.** No shell/model fallback was used for the Windows R1 check. Windows scanner/build/E2E mirror results do not prove this boundary.
- Production credentials, production DB behavior, live DART/SEC collection, UI integration, public deployment, and independent GPT review: **NOT VERIFIED**.
- The standard secret scan is blocked by its fixed generated-artifact metadata population. The Linux full suite exits `1` on Windows-only OWNER tests, and the required bounded Windows-native B2-D→R1 check is unavailable in this WSL-local Codex App context. Commit/push and an implementation-complete handoff are blocked; no test was deselected or weakened.
- The initial npm-installed worktree dependency directories were preserved at `/tmp/tosstoss-b2d-pre-setup-20260928` before running the exact `setup.sh`. The Windows-local QA copy is a separate short-path clone; nine changed-file SHA-256 identities matched for an intermediate policy scan. The source code remained stable afterward, while tests/reports changed; no final-tree Windows policy-scan claim is made after STOP.
- The review ZIP will carry the current candidate and safe evidence. Its bounded local review cannot substitute for a full checkout, exact final commit, or a wider R1/public/trading approval.

## Bounded remediation after independent review FAIL (2026-09-28)

The earlier STOP record above is historical evidence. Independent GPT review found Critical 0, Major 2. The user authorized M1/M2 correction, missing concurrency and late-conflict QA, strict generated-artifact inventory synchronization after proof, and Windows-native bounded OWNER verification. The ceiling remains `IMPLEMENTED — GPT FINAL INDEPENDENT VERIFICATION REQUIRED` only after all final gates pass; this report does not declare PASS/CLOSED.

- M1: issuer raw challenge is now exactly `secrets.token_bytes(32)`. Durable digest is `canonical.digest(raw)` and binding is `canonical.row_hash` over frozen `ISSUER_CHALLENGE_FIELDS`, including challenge ID/version/digest and all disposition/authority fields. GV-09 original expected digest and binding values remain unchanged. The direct production `_new_challenge` deterministic test proves 32 requested CSPRNG bytes, returned raw options, durable digest/binding, absence of raw bytes from durable payload, and independent binding changes for disposition, decision, bundle, provider, predecessor and successor.
- M2: B2-B freshness/latest and B2-D approval membership use one `latest_authority_observation` helper. Approval writes only the selected current observation for each bundle evidence. The immutable approval event audit hash covers event/authentication IDs, authenticated/recorded data, and the canonical ordered observation ID/content-hash/ordinal/membership-hash rows. A historical O1/current O2 test includes O2 and excludes O1; a later failed O3 invalidates the bound authorization. Injecting historical membership into a disposable DB causes `APPROVAL_EVENT_AUDIT_CONFLICT` on use.
- Race QA: real disposable SQLite connections/threads cover APPROVED versus REJECTED, two duplicate APPROVED attempts, two head successors, REVOKED versus safety successor, SUPERSEDED pair versus REVOKED head mutation, and three reused successful authentication-event binding attempts. Persisted assertions check one winner, linear link leaf/head, no mixed pair, and no cross-bound event. Existing duplicate challenge completion and SUPERSEDED rollback tests remain.
- Late conflict: B2-B now exposes its already-computed affected-provider IDs without policy changes. B2-D `evaluate_and_revalidate_affected` evaluates and projects all affected current approved links under one caller-owned writer transaction. The two-provider fixture preserves both old approvals/links and issuers while both heads move to REVIEW_REQUIRED links backed by REVIEW_REQUIRED machine decisions.
- Strict scanner proof: Windows-native pinned Python 3.13 mypy produced 854 base and 855 candidate metadata paths. The only added path is the authorized B2-D module. Fixed scanner values are exactly 855 metadata, 1710 mypy proof keys and 1705 mypy findings; detector and exception semantics are unchanged. The fixed count rejects 854 and 856. The prior mismatch remains recorded in `qa/CP3_C2_B2_D_SCANNER_COUNT_PROOF.txt`.
- Windows OWNER: exact candidate source bytes were copied to a Windows-local short-path QA clone before `-B` Python execution. The disposable DB probe traverses B2-D issue/complete through frozen `_Win32` directory OWNER/TOKEN_USER `EqualSid`; the direct existing OWNER test also passes. Result: 2 passed, 0 failed, exit 0. No production DB, security source change or Computer Use fallback.
- Frozen proof: all migration blobs 0001–0007 match base `48d4201281db2fabdb58f09ba6860bd184e722c8`; 0008 is absent. Frozen reviewer `webauthn_core.py`, `ledger.py`, `runtime.py`, `windows_owner.py`, `canonical.py`, `schema.py` match base byte for byte.

Focused B2-D suite: 41 passed, 0 failed/skipped/xfail/deselected, exit 0. Relevant B2-B/R1/migration regression: 544 passed, 0 failed, exit 0. Windows standard full QA and final-tree scanner/policy results are recorded in the final handoff once complete. Production DB writes, live authority/Toss requests, deployments and merges: 0. Independent final GPT verification and wider R1/public/trading approval remain NOT VERIFIED.

## Final Windows-native standard QA after remediation

The Windows-local QA mirror was copied from the implementation worktree after the final source/test/control edits. All 17 changed/new candidate paths had matching SHA-256 bytes before the standard run, and the mirror index equaled its worktree. It was a disposable short-path clone, not a production checkout or DB. The authoritative implementation worktree stayed uncommitted during these tests.

| Gate | Command/scope | Passed | Failed | Skipped | Xfail | Deselected | Exit |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| B2-D focused | `.venv/bin/python -m pytest tests/backend/test_issuer_disposition.py -q --disable-warnings --maxfail=1` | 41 | 0 | 0 | 0 | 0 | 0 |
| Relevant B2-B/R1/migration regression | Exact 12-file command below | 544 | 0 | 0 | 0 | 0 | 0 |
| Bounded Windows B2-D→R1 OWNER plus direct R1 test | Exact `-B` command below | 2 | 0 | 0 | 0 | 0 | 0 |
| Standard Windows-native full backend | `scripts/test.ps1`, collected inventory exactly 1121 | 1121 | 0 | 0 | 0 | 0 | 0 |
| Standard frontend unit | `scripts/test.ps1`, 10 files, inventory exactly 43 | 43 | 0 | 0 | 0 | 0 | 0 |
| Standard Chromium fixture E2E | `scripts/test.ps1`, inventory exactly 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| Standard migration repeat/downgrade/re-upgrade | `scripts/test.ps1` | PASS | 0 | 0 | 0 | 0 | 0 |
| Standard fixture import idempotency | `scripts/test.ps1`, first 13 inserted, second 13 unchanged and 0 updated | PASS | 0 | 0 | 0 | 0 | 0 |
| Backend Ruff/format/mypy; frontend lint/typecheck/build; API contract | `scripts/test.ps1` | PASS | 0 | 0 | 0 | 0 | 0 |
| Full secret scan | `scripts/test.ps1`, actual repository verdict after generated-artifact canaries | PASS | 0 | 0 | 0 | 0 | 0 |
| Final policy scan in standard harness | `scripts/test.ps1`, after E2E and secret scan | PASS | 0 | 0 | 0 | 0 | 0 |

The standard full backend result was `1121 passed in 1443.38s (0:24:03)`; Windows-native `scripts/test.ps1` exited `0`. Its final secret scanner reported metadata 855, P=2408, D=2403, E=2403, applied=2403, five unregistered proof-only keys, and `Secret scan passed`. Its final policy scanner reported four positive and 35 negative fixed cache-tag provenance canaries, one approved source span, network authority 0, and `Phase 2 CP3-C2-B2-C schema implementation scope policy scan passed`. The policy script's historical name is retained; this is the actual final run on the B2-D candidate, not an intermediate preflight.

The full standard Windows-native command was:

```bash
pwsh.exe -NoProfile -Command '$env:Path="C:\Program Files\Git\cmd;C:\Program Files\nodejs;"+$env:Path; $env:PATHEXT=".COM;.EXE;.BAT;.CMD;.VBS;.VBE;.JS;.JSE;.WSF;.WSH;.MSC"; Set-Location "C:\Users\beomoo\b2d-qa-20260928"; & .\scripts\test.ps1'
```

The regression command was:

```bash
.venv/bin/python -m pytest -q tests/backend/test_authority_contracts.py tests/backend/test_authority_repository.py tests/backend/test_authority_decision_engine.py tests/backend/test_reviewer_webauthn_core.py tests/backend/test_reviewer_runtime.py tests/backend/test_reviewer_runtime_time.py tests/backend/test_reviewer_time_profile.py tests/backend/test_reviewer_operation_migration.py tests/backend/test_counter_capability_migration.py tests/backend/test_authority_migration.py tests/backend/test_migrations.py tests/backend/test_provider_migration.py
```

The bounded Windows OWNER command, run from `C:\Users\beomoo\b2d-qa-20260928`, was:

```powershell
.venv\Scripts\python.exe -B -m pytest tests/backend/test_reviewer_windows_owner.py::test_real_windows_owner_token_user_and_canonical_sid_hash qa/CP3_C2_B2_D_WINDOWS_OWNER_PROBE.py::test_b2d_entry_uses_real_win32_owner_and_token_user -q --disable-warnings --maxfail=1
```

The disposable B2-D probe calls the unchanged Win32 OWNER implementation, obtains filesystem OWNER SID and process TOKEN_USER SID, and uses the accepted `EqualSid` mechanism. It asserts no bytecode was generated. The seven Windows-only tests were not silently deselected from standard backend QA.

## Final safety and interpretation

- Direct tests and persisted disposable rows prove no unauthenticated disposition, no cross-bound successful authentication reuse, no one-authentication SUPERSEDED, one winner per applicable race, no head fork, no mixed partial SUPERSEDED rows and one valid current leaf/head. Security count and VERIFIED mapping count stay unchanged; the provider identity row is compared before/after. The service has no automatic issuer approval, synthetic issuer authority, name-only merge, symbol-only merge or provider rekey path.
- Every successful disposition business write remains inside one `BEGIN IMMEDIATE`; `evaluate_locked` receives the caller's session and never commits or rolls back independently. Public B2-B `evaluate()` remains compatible.
- Migration 0001–0007 Git blobs and frozen R1 `webauthn_core.py`, `ledger.py`, `runtime.py`, `windows_owner.py`, `canonical.py`, `schema.py` match base exactly; 0008 is absent. The changed-path audit is limited to the original B2-D service/B2-B session reuse/tests/docs, GPT-required remediation and strict QA-control inventory synchronization. No migration, frontend reviewer, scheduler, trading, public API, provider ingestion or frozen security file changed.
- Production DB writes, live authority requests, live Toss requests, deployments and merges: 0. No OpenAI API or paid API was called. Production/live integration, full physical remote/missing-ACL R1 cases, external independent final verification, public/trading authorization and next checkpoint remain **NOT VERIFIED**.
- The earlier Linux `1102 passed, 7 failed` result is historical platform evidence only; all seven failures were frozen Win32 OWNER tests returning `WINDOWS_REQUIRED`. The Windows-native `1121 passed` standard run supplies the platform-complete backend result for this candidate.

The final review package provides the complete base and candidate source snapshots, exact diff, approvals, safe QA result summary, fixed-proof files, and a copy-ready request. It excludes credentials, production data, raw security logs and installed dependencies. Running the tests independently or checking the pushed remote ref requires the candidate commit SHA and checkout recorded in its manifest.
