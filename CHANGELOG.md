# Changelog

## Current C3-entry exact integration and ADR-021 closeout — 2026-10-03

- Integrated exact accepted docs successor `63352a32fde3df1d75b56c7e3c2d7861b080e666` by non-fast-forward merge `8234a4ff7080174a25dce3132b13f7f3a05063d0`, parents `81ef70a76b812c6cf6c4cbbcfc4a1f24b7f7ca86` and `63352a32fde3df1d75b56c7e3c2d7861b080e666`. Merge/successor tree `3e5c2e5e4199c01e273d2741c47fa461129197d2`; diff 0.
- Preserved reviewed product identity `b23feb3f5640582db1ba5e9d4f4523cf78e2b494` / tree `fc273f0aa8ab64156f81ba22d4510ffa74f693a2`, user-accepted bounded PASS and Critical-01/Major-01 closure. The previous fba35c8 FAIL is unchanged.
- Recorded **CP3-C2-C3-ENTRY: PASS — CLOSED; ADR-021: ACCEPTED** solely for bounded migration/profile/identifier compatibility. Post-merge changes are the six authorized documents only; product/test/scanner/dependency diff 0. Existing QA attribution and all NOT VERIFIED qualifications remain.
- **C3 Human WebAuthn / Final Security Mapping: NEXT PLANNED CHECKPOINT — NOT STARTED**; CP3-D NOT STARTED; Phase 2 IMPLEMENTATION IN PROGRESS. No full/targeted QA rerun, migration execution, main update, deployment, live/production action or later implementation occurred. Final closeout SHA/tree and light-gate receipts are external in `FINAL_INTEGRATION_IDENTITY.json` and `CLOSEOUT_REPORT.md`.

## Historical C3-entry review acceptance documentation — 2026-10-03

- Recorded user acceptance of GPT **PASS — bounded C3-entry migration remediation** for product `b23feb3f5640582db1ba5e9d4f4523cf78e2b494`, tree `fc273f0aa8ab64156f81ba22d4510ffa74f693a2`. Critical-01 and Major-01 are closed for that candidate; required fixes 0, new Critical/Major/Minor findings 0/0/0.
- Separated original implementer QA (96/2/448; full backend 1459/frontend 43/E2E 2), the separate verifier's fresh native Windows 60+2+1 cases, and GPT evidence review. No product tests or migrations were rerun in this docs-only task. Earlier FAIL/STOP/setup/QA evidence remains preserved.
- Updated only the six authorized current-state documents; product, migrations, tests, scanners, pins and the C1 contract are unchanged. The new docs-only commit is identified separately by external `FINAL_DOCS_IDENTITY.json`.
- **REVIEW ACCEPTANCE DOCUMENTED — INTEGRATION PENDING**. ADR-021 stays **PROPOSED / IMPLEMENTED FOR INDEPENDENT REVIEW** (review PASS accepted; integration/ADR closeout pending). Integration/main updates were not performed; C3 product and CP3-D are NOT STARTED. Existing closeouts and qualifications remain.

## Historical C3-entry migration correction — 2026-10-03

Previous candidate fba35c8c85e82d2f6549ea9cdc8af270e8e9a7e2 (tree 0f24109aa923830688bb7fe15d4b916b189a1e25) received **FAIL — Critical 1 / Major 1 / Minor 0** for cancellation history loss and split schema/revision commits. That candidate is preserved and must not be integrated or used for real DB migration. The current bounded correction changes only 0009, narrow Alembic env.py transaction coordination, failure tests and measured inventory/current docs. Historical 0001–0008 and the existing identifier/profile/source authority/READY/R1/B contracts remain frozen.

Windows focused **96/96**, external OS-termination **2/2**, and affected regression **448/448** passed, each exit 0 with no skips. Affected coverage includes all prior C2 14 counterexamples, Windows OWNER 8 and frozen R1 core 82. The standard Windows scripts/test.ps1 then ran from the beginning and passed (exit 0): backend **1459**, frontend **43**, E2E **2**, migration roundtrip/re-upgrade, canaries, fixture/API/build checks and standard policy/secret scans. Final documentation scans and commit/push evidence are recorded in the external package. The authorized new commit is identified through FINAL_IDENTITY.json rather than a self-referential literal in this file.

ADR-021 stays **PROPOSED / IMPLEMENTED FOR INDEPENDENT REVIEW**. The ceiling is **CP3-C2-C3-ENTRY REMEDIATED — GPT FINAL INDEPENDENT RE-VERIFICATION REQUIRED**. No acceptance, closeout, C3 product work or integration is claimed. See qa/PHASE_02_CP3_C2_C3_ENTRY_REMEDIATION_SELF_QA.md and the external SELF_QA/FINAL_IDENTITY reports. Previous NOT CREATED and parent-only commit statements below describe historical execution state; the new explicit authority permits the new commit/push after gates.

## Historical previous C3-entry report

The following entry is historical; later accepted C1/0008/C2 records remain unchanged.


### Historical C3-entry execution record — 2026-10-01 (fba35c8; independently FAIL)

Implemented the bounded 0009 identifier-provenance/profile-hash correction against baseline `81ef70a76b812c6cf6c4cbbcfc4a1f24b7f7ca86`. Only new 0009 evolves the identifier contract; 0001–0008 remain byte-identical. Historical v0.1 rows and decisions remain immutable. Exact profile construction is shared by C2 and the independently reconstructed repository READY backstop; US v0.2 identifiers bind the existing SEC provenance OWNER application. Supporting bundle evidence and append-only successor lineage are retained. Source authority, Security anchor/security_id, R1/B semantics and legacy ShareClass remain unchanged.

Windows focused: **36 passed**, affected: **111 passed**, each exit 0 and zero skips. The affected suite includes the Windows OWNER module (8 tests, including native directory OWNER/TOKEN_USER verification) and the previous 14 C2 counterexamples. The unchanged standard `scripts/test.ps1` then ran from the beginning and completed with exit 0: backend 1399, frontend 43, E2E 2, migration QA, fixture idempotency, API-contract/build checks and standard secret/policy scans. Source/mirror/index equality and runtime/test byte freezes are recorded.

Earlier Linux evidence remains 829 passed / 8 failed (seven WINDOWS_REQUIRED cases and one stale HEAD expectation); it is not relabelled all-pass. The bounded HEAD/additive-revision inventory correction passed its final 24-case rerun. Earlier Windows setup/full/scan failures remain preserved. The directly observed `.CPL`-only process PATHEXT was repaired by restoring the actual Machine PATHEXT in the dedicated QA subprocess only, with Windows-local cwd; this environment repair changed no machine/user environment, runner, detector, assertion or canary. The candidate retains only the separately authorized measured test/migration inventory updates. The first full run after PATHEXT repair retained 1395 passed / 4 failed because the ignored launcher application aliases masked negative Settings inputs. A direct Windows A/B probe established the cause; removing only those QA subprocess aliases retained effective safe defaults, and the unchanged guarded settings suite passed14/14 before the subsequent full run. The second standard Windows full run passed backend 1399, frontend 43, E2E 2, migration and build checks, but finished exit 1 because the unchanged secret scanner could not read the active QA transcript. That complete failed attempt is preserved. The bounded environment correction captures output only in the Linux evidence root, preserves private mirror evidence by verified byte-for-byte copy, and moves the same official PowerShell bytes and caches under the existing .venv dependency directory and browser assets to the existing .playwright-browsers directory. No scanner exclusions or source assertions changed; the third complete standard full run started from the beginning after the unchanged secret scan precheck.

**CP3-C2-C3-ENTRY REMEDIATED — GPT FINAL INDEPENDENT VERIFICATION REQUIRED**. ADR-021 remains **PROPOSED / IMPLEMENTED FOR INDEPENDENT REVIEW**. Candidate commit SHA/tree are **NOT CREATED**; the parent owns final staging/commit/push after validating the source-manifest package. No acceptance, closeout or C3 completion is claimed.

## 2026-10-01 — exact CP3-C2-C2 integration and closeout

- Reviewed candidate `e5aad022f8140523fad00b293c4bc9f4dfca86ff`, tree `c529c740607f1b89a3624407180a0099e00bb01a`: GPT **PASS**, Critical/Major/Minor `0/0/0`, required code/schema fixes `0`, unauthorized changes `0`. The user accepted this exact verdict in the C2 integration/closeout request.
- Exact integration merge `eb6088f90c55c8d15b8ea1c206f2b7f7b0349799` on `feature/phase-02-toss` has parent 1 `120194fe6631db51c115776a49c55d3a25d93e7e` and parent 2 `e5aad022f8140523fad00b293c4bc9f4dfca86ff`. Its tree is `c529c740607f1b89a3624407180a0099e00bb01a`, identical to the reviewed candidate before documentation changes.
- Closed C2 as **PASS — CLOSED**, preserving C1/0008 **PASS WITH ISSUES — CLOSED** and accepted ADR-020. Updated current-state sections in the six authorized closeout documents; historical failures and qualifications are retained.
- Accepted C2 behavior: machine Security authority evaluation, server-owned source admission, application-backed scope proof, freshness and relation heads, durable negative evidence, KR type/kind reconciliation, global active-listing collision handling, and append-only machine decision chains. Maximum positive state remains `READY_FOR_MANUAL_REVIEW`; machine writes do not grant human approval or final Security mapping.
- Windows full QA is Codex execution evidence, not a suite independently rerun by GPT. No entire Windows C2 suite is rerun for this documentation-only closeout. Reviewed runtime, migrations, tests, scanners and source-registry semantics remain unchanged. C3 is the next planned checkpoint, not started; CP3-D is not started; Phase 2 remains in progress. No main merge, deployment, production write or live authority call.

## 2026-10-01 — CP3-C2-C2 final periodic-cover bounded remediation candidate

- Address the sole Major remaining in independent review of `00e01d87`: deterministic same-CIK + class/ticker relevance, complete supplied-field class/ticker/exchange cross-check, and C2-owned READY persistence backstop. Support authority and existing normalization/current-head rules remain unchanged.
- Add 21 regression cases for positive/unrelated/null controls, every reported contradiction, malformed internal READY, correction/history/replay and missing positive-owner authority; retain all previous R1–R5 tests.
- No migration, source admission/licensing, R1/B/global-enum change, C3, live request or production write. Actual exact-tree QA and final identity belong to the fresh review package; independent acceptance and integration remain pending.

## 2026-09-30 — CP3-C2-C2 consolidated remediation candidate

- Bind READY scopes to exact admitted applications and add independent repository guards for membership, hash, source currentness, class and canonical binding.
- Preserve effective accepted Form 25 evidence across retrieval failures; reconcile relevant periodic-cover contradictions without promoting support to listing ownership.
- Scan active venue/ticker collisions across providers, preserve same-Security and nonoverlapping-reuse controls, and append affected safety successors atomically.
- Reconcile KR security type with stock kind and append persisted negative successors on issuer/provider/evidence prerequisite loss.
- Add the combined 14-case differential matrix and supplementary positive, negative, persistence, replay and restoration tests. Synchronize only measured test/control inventory. Final QA/commit evidence is supplied by the external remediation review package; no independent PASS/CLOSED or integration is declared here.

## 2026-09-30 — CP3-C2-C2 synchronized full QA passed

- The synchronized candidate passed the complete Windows standard `scripts/test.ps1` run from the beginning in attempt 09 (exit 0): backend 1,294 passed, frontend 43 passed, E2E 2 passed, and every static, API-contract, migration, fixture-idempotency, secret, and policy gate passed. Exact counts and exits are in `qa/PHASE_02_CP3_C2_C2_SELF_QA.md`.
- All 376 candidate files matched the Windows QA mirror byte-for-byte. Migrations 0001–0008, R1 WebAuthn/counter/OWNER code, B2-D issuer disposition, and global legacy mapping enums remain unchanged.
- C2 remains capped at `READY_FOR_MANUAL_REVIEW`. GPT final independent verification is required before any C3 work.


## 2026-09-30 — CP3-C2-C2 machine engine and Windows QA

- Implemented the server-owned C2 evaluation path for admitted normalized KR and US evidence, including immutable applications/claims/bundles/decisions, current-head reconstruction, freshness, contradiction, collision, replay, and transaction checks. NYSE and CGS remain non-admitted; the KRX adapter remains disabled.
- Windows standard QA attempt 06 passed from the beginning: backend 1,294 passed, frontend 43 passed, E2E 2 passed, and all static, contract, migration, fixture-idempotency, secret, and policy gates passed. See `qa/PHASE_02_CP3_C2_C2_SELF_QA.md`.
- No migration, C3, canonical Security, legacy `VERIFIED` mapping, production write, or live-source behavior was added. Final exact-tree QA, commit/push, and independent verification remain required.


## 2026-09-30 — CP3-C2-C2 source-authority review and implementation start

- Recorded the user-approved exact source-admission matrix and source-specific freshness bounds under accepted ADR-020 in `plans/PHASE_02_CP3_C2_C2_SOURCE_AUTHORITY_REVIEW.md`.
- Started C2 machine-engine implementation from `120194fe6631db51c115776a49c55d3a25d93e7e` on the isolated implementation branch. No live source calls, C3 behavior, canonical Security writes, or legacy mapping writes are authorized.

## 2026-09-30 — exact 0008 integration and closeout

- Integrated reviewed candidate `0c4702c8bffa58675a5d1b0b9f1b77ca25beb8e4` into `feature/phase-02-toss` as explicit merge `88dcb1e49551069b8e986c35185d9bcced89d4e5`, parents `6c0ed087106d0fdb94615b74a9472df17be08706` and `0c4702c8bffa58675a5d1b0b9f1b77ca25beb8e4`, tree `64132bf753e680eae9d47252e45859d129d01f7f` equal to the reviewed candidate tree.
- Accepted independent final result `PASS WITH ISSUES` (Critical 0, Major 0, required code/schema fixes 0, unauthorized changes 0, regression found 0). CP3-C2-C1 architecture/design and ADR-020 remain accepted; the additive 0008 Security Authority Foundation is `PASS WITH ISSUES — CLOSED`.
- Recorded the two non-blocking review qualifications: stale current-state QA wording in candidate documentation (corrected here while preserving historical STOP evidence), and duplicated bounded-remediation authorization in the final review ZIP (package-completeness limitation, not an implementation defect).
- Updated current-state documentation and replaced root `AGENTS.md` with the user-provided operating rules. No reviewed implementation, migration, scanner or test semantics changed. CP3-C2-C2 is the next planned checkpoint but is not started in this closeout; C3 and CP3-D remain not started; Phase 2 remains in progress.

## 2026-09-29 — bounded 0008 independent-review remediation

- M1: shared contract/DDL locator scheme and concrete-token boundary; production fixture/wildcard/HTTP rejection and permanent isolated fixture requirements.
- Minor-01: source/document token parity, 1–128 uppercase ASCII token; M2: synchronize the measured exact scanner raw-byte pin without scanner semantics changes.
- Added 60 remediation cases and required suite/control inventory updates. Status: **FINAL QA BLOCKED — STOP**. Historical STOP and failed attempts are retained.

Final Linux/WSL focused 125 and Windows regression 482 passed. Full Windows standard attempt 02 failed: backend 1245 passed / 1 failed, exit 1, 1711.74 seconds. The unchanged existing runtime logging test failed before receiving /health; two targeted diagnostic runs reproduced 1 failed / 1 passed, and the second captured child process exit 3. Root cause of startup termination remains NOT VERIFIED. No timeout/assertion/runtime/scanner change was made. Later full-QA gates, final secret/policy, commit and push were not executed. No independent PASS/CLOSED or next checkpoint is authorized.

## 2026-09-29 — additive 0008 Security authority foundation candidate

- Implemented separate 23-object contracts/schema/models and immutable storage, M1 terminal-auth persistence, exact M2 pairs, M3 counter fields without R1 runtime changes, append-only history and issuer/head guards.
- Added 65 focused cases; synchronized required old head/table/index assertions and measured QA inventories (backend 1186, control files 96, mypy metadata 858).
- Status: **FINAL QA BLOCKED — STOP**. No C2/C3 runtime, production authority admission or current-reader cutover. Details and limitations: `qa/PHASE_02_CP3_C2_C_0008_SELF_QA.md`.

## 2026-09-29 — CP3-C2-C1 architecture integration and closeout

- Merged exact reviewed C1 design candidate `6270547c91e861f2615c92cb027d5d5cf86ce937` into `feature/phase-02-toss` as `ea17105be49c063662d70d286637d90407f36087`; merge tree equals candidate tree. The user accepted independent re-review **PASS WITH ISSUES** (Critical 0, Major 0; prior M1/M2/M3 closed) and accepted ADR-020. CP3-C2-C1 is **PASS WITH ISSUES — CLOSED**.
- Preserved the non-blocking evidence-package limitation: the reviewer received the previous ZIP, but inspected the remediated GitHub source and independently reproduced essential M1/M2/M3 mechanisms. The updated 31-check ZIP was not itself independently rerun.
- `0008` remains designed only, and C2/C3 remain unauthorized. This closeout changes documentation only; runtime and migration verification remain future gates.

## 2026-09-29 — CP3-C2-C1 bounded design remediation

- Recorded the independent GPT verdict on C1 candidate `289266f1a230637d545ed0eef8f6fd73a933bbde`: **FAIL — DESIGN REMEDIATION REQUIRED**, three Major findings.
- Corrected the Security contract and proposed ADR-020 for terminal authentication across business rollback, exact old/successor two-auth supersession constraints, and Security authentication participation in the single R1 credential counter graph.
- Extended the disposable SQLite feasibility probe to 31 passing checks. The result is **REMEDIATED — GPT INDEPENDENT RE-REVIEW REQUIRED**; no migration or runtime code was changed.

# 2026-09-29 — CP3-C2-C1 Security authority design handoff

- Added a versioned, Security-specific authority contract and proposed ADR-020 for an additive 0008 schema, KR KRX ISIN and US SEC registered-class anchors, issuer-head prerequisite, collision/cascade behavior, two-authorization supersession, and a v2 current mapping head.
- Recorded the design checkpoint in `STATUS.md` and `plans/PHASE_02_EXECUTION_PLAN.md`. C1 is `DESIGNED — GPT INDEPENDENT REVIEW REQUIRED`; ADR-020 remains `PROPOSED`. No runtime or migration was implemented, and C2/C3 remain unauthorized.


## Unreleased — CP3-C2-B2-D and CP3-C2-B user closeout — 2026-09-29

- The user accepted independent GPT final review of B2-D candidate `3216043a531372a1ff04002b76f522d38ed03568`: `PASS WITH ISSUES`, Critical `0`, Major `0`, M1/M2 `CLOSED`, unauthorized changes `0`, required code fixes `0`, required B2-D QA reruns `0`. CP3-C2-B2-D is `PASS WITH ISSUES — CLOSED`.
- Integrated that exact candidate into `feature/phase-02-toss` with explicit merge `1eedc36e571d408c3fe33e726521907224efb971`: parents `48d4201281db2fabdb58f09ba6860bd184e722c8` and `3216043a531372a1ff04002b76f522d38ed03568`; merge tree `d02154c54c971ffc26e6ea153f18c58f63ba58df` equals the reviewed candidate tree.
- With B1, B2-A, B2-B, B2-C/0006/0007, R1 backend core and B2-D accepted, the user authorized overall CP3-C2-B implementation `PASS WITH ISSUES — CLOSED`. The qualification retains B2-D randomized scanner self-canary reproducibility, absent separately named exact-duplicate REJECTED/REVOKED regressions, and R1 physical remote-volume/missing-ACL negative cases covered only by controlled simulation.
- Closeout changes only current-state documentation. CP3-C2-C Canonical Security Authority / Final Mapping and CP3-D remain `NOT STARTED`; Phase 2 remains `IMPLEMENTATION IN PROGRESS`. No main merge, tag, release, deployment or automatic checkpoint progression follows.

## Unreleased — CP3-C2-B2-D bounded remediation — 2026-09-28

- Corrected the issuer challenge to exactly 32 OS-CSPRNG bytes, `canonical.digest(raw_challenge)` and the unchanged ADR-017 issuer challenge canonical field set; direct production-path GV-09 regression uses the accepted digest and binding values.
- Reused B2-B's latest observation selector for approval membership; the immutable approval audit now binds exact ordered observation references. Added historical/current observation, post-authorization change and tamper regressions.
- Added real separate-connection SQLite race/idempotency tests and a narrow production-callable path that revalidates every collision-affected approved provider under one writer transaction, projecting both heads to REVIEW_REQUIRED in the two-provider fixture.
- Proved the strict mypy artifact delta is exactly one authorized B2-D source module; synchronized only fixed scanner population counts, the standard backend test inventory and the policy source/test digest.
- Final focused `41 passed`, relevant regression `544 passed`, Windows-native full standard QA backend `1121 passed`, frontend `43 passed`, E2E `2 passed`; migration, fixture idempotency, build, API contract, lint/typecheck, secret and policy gates exit `0`. Bounded B2-D→R1 Win32 OWNER/TOKEN_USER `EqualSid` probe plus direct R1 integration test: `2 passed`.
- Frozen 0001–0007 migrations and R1 security core remain byte-identical; 0008 absent. Status ceiling: `IMPLEMENTED — GPT FINAL INDEPENDENT VERIFICATION REQUIRED`. The preceding B2-D failed candidate entry remains historical; no PASS/CLOSED or next checkpoint claim.

## Unreleased — CP3-C2-B2-D issuer disposition candidate — 2026-09-28

- Added the local unrouted issuer disposition service over the accepted R1 WebAuthn verifier and frozen 0005–0007 ledger: challenge issuance/consumption, authenticated APPROVED/REJECTED/REVOKED/SUPERSEDED, canonical Issuer insert-or-verify, append-only event/link history, and guarded head transitions.
- Exposed B2-B evaluation under a caller-owned writer transaction without changing its rules. Added post-approval REVIEW_REQUIRED projection and focused relational/concurrency tests.
- Final B2-D focused QA passed 30 tests. Full Linux backend QA exited `1` with 7 frozen Win32 OWNER tests returning `WINDOWS_REQUIRED`; Computer Use could not initialize in this WSL-local App context; the standard secret scan exited `1` on its 854-versus-855 generated-artifact count. No commit/push or PASS/CLOSED claim followed. See `qa/PHASE_02_CP3_C2_B2_D_SELF_QA.md`.

## Unreleased — B2-C R1 closeout — 2026-09-28

- Persisted the independently verified R1/WSL working candidate and recorded user closeout of B2-C R1 backend core as `PASS — CLOSED`.
- R1 Windows Final QA: `PASS WITH ISSUES`; Critical `0`, Major `0`, required code fixes `0`, required QA reruns `0`.
- Non-blocking P2: remote-volume and missing-ACL Windows negative cases used controlled simulations; physical remote and missing-ACL devices were not validated.
- CP3-C2-B remains `IN PROGRESS`; B2-D, CP3-C2-C and CP3-D remain `NOT STARTED`; Phase 2 remains `IMPLEMENTATION IN PROGRESS`. Earlier STOP and failed-QA entries remain historical evidence.

## Unreleased — CSV257 exact exception focused verified; full QA entry — 2026-09-09

- Proved all 259 original source byte hashes before changes; preserved exact
  historical CSVs. Added a fixed-version CSV-only Hex finding proof/matcher,
  detached registration and self-canaries in the existing secret scanner.
- Final CSV focused exit 0: 8 positive/100 negative groups, two unchanged-driver
  outside-scope canaries, actual P=259/D=E=257 and two proof-only keys absent.
  Same final scanner's generated regression exit 0: unchanged 79 negatives,
  31-file batch and P=2406/D=E=2401 with five proof-only keys absent.
- Preserved all development failures and earlier positive byte snapshots;
  corrected only new CSV exact-string/identity and generic-dispatch integration.
  Updated only the exact policy control digest (85 files) and current docs.
  Full QA entry requires exact index/preservation/cleanup gates; full result and
  final scans are not yet claimed. No commit/push; R1 is not accepted or closed.
- OBS-04 local PASS, historical failures, frozen migrations, runtime/dependencies,
  four untracked CSVs and KI-017/KI-018 remain preserved. General DB/process
  failure replay and historical canary cause remain NOT VERIFIED.

## Unreleased — SCAN02-01/02 focused verified; CSV preflight unverified — 2026-09-08

- Added generated-only empty-byte hashing without changing the shared helper.
  Registered only actual proof-matching findings through an atomic map update.
  Final focused command exit 0: existing 41 plus empty 17 and registration 21
  negative checks; 31-file detector batch; 854 metadata, two tags and 704 TS
  sources proved. P=2406, D=E=2401, applied=2401, proof-only unregistered=5.
- Preserved development exit 1 on a Windows reserved test name and non-final
  exit 0 separately from the final source run. No detector/runtime change.
- CSV-only observer exited 1 and failed to retain a verified result; NV-CSV is
  blocking. No CSV rewrite/exception/retry, policy sync, staging, full QA, final
  scans, commit or push. R1 remains `NOT VERIFIED — FINAL QA BLOCKED`.

## Unreleased — R1 scanner acceptance addendum and STOP — 2026-09-07

- User accepted revised F.3/F.4 strict rejection, proof/exception zero and input
  preservation without requiring adverse-order candidate retention. Added the
  separate favorable-order witness; detector/filter/scope settings are unchanged.
- One focused run passed 41 synthetic negative checks and a 31-file detector
  batch, then exited 1 on empty-byte argument binding in production source proof
  (`R1-SCAN-02`). No complete focused/population PASS, policy synchronization,
  full QA, staging, commit or push. R1 remains `NOT VERIFIED — FINAL QA BLOCKED`.
- Preserved prior STOP executions/witness, original 27 staged files and four
  untracked diagnostic CSVs. Only scanner self-canaries and current documentation
  changed; zero-byte hashing correction is proposed, not implemented. See latest
  R1 report. The following dated entries are historical, not current instructions.

## Unreleased — Phase 2 CP3-C2-B2-C R1 WebAuthn Backend Core — 2026-09-05

- Latest authorization: the user accepted the diagnosis as `PASS WITH ISSUES`,
  not R1 acceptance. R1 remains `NOT VERIFIED — FINAL QA BLOCKED`. Narrow,
  independently regenerated per-finding secret exceptions and fail-closed
  self-canaries were authorized. Their focused verification stopped at
  `R1-SCAN-01`: two `-GeneratedArtifactSelfTest` runs exited 1 because an F3
  synthetic hex candidate was filtered by the unchanged detector when placed
  after `version_id`, despite strict unknown-field rejection. No field-order,
  assertion or detector/filter weakening was applied. Full QA, full secret scan,
  policy scan, commit and push were not run; exact policy digest update remains
  gated on focused PASS. Separate requirement/detection design approval is needed.
  The new diagnostic population alone is `PROVEN_NOT_SECRET=2401`; historical
  2401 identities remain `NOT VERIFIED` (2392 recovered metadata + 9 missing).
  Four diagnostic CSVs remain local evidence, excluded from the R1 commit.
  Prior failures below remain historical; the canary's past cause is unverified,
  its behavior stays unchanged, and general DB/process-crash replay safety and
  real browser/device ceremony remain `NOT VERIFIED`.
- Partially implemented separately authorized, unrouted backend core for canonicalization,
  real WebAuthn verification, Windows OWNER/TOKEN_USER binding, immutable
  credential lifecycle and frozen 0006/0007 transaction/counter reconstruction.
- Added focused offline tests with ephemeral real ES256/RS256 keys; synchronized
  exact approved dependency and test/source policy inventories.
- Synchronized current 0007 status to PASS — CLOSED (user closeout 2026-09-05).
  R1 was stopped at the frozen SQLite timestamp precision gap (R1-TIME-01).
  The subsequent conditional user authorization resumes R1-only integer
  millisecond server-time generation, raw-time expiry and explicit historical
  SQL-conflict handling. Fresh focused 213, regression 277, full backend 1064,
  frontend 43 and E2E 2 passed. Final secret scan is blocked by generated Ruff
  binary cache inputs; targeted cleanup was rejected before execution. No
  scanner weakening or alternate deletion path was added. Full QA closeout is
  incomplete; the older interrupted run remains historical, not full QA PASS.
  Full QA was deliberately interrupted; implementation completion and independent
  review are not claimed. No commit/push was performed at this STOP.
- Preserved frozen 0001–0007, no 0008, no operational DB writes, no routes/frontend,
  no issuer promotion and no public/trading implementation. See
  `qa/PHASE_02_CP3_C2_B2_C_R1_WEBAUTHN_CORE_CODEX_REPORT.md`.
- Subsequent approved R1-REPLAY-01 remediation adds immutable unfinished-path
  time-profile admission before crypto; preserves completed historical records.
  Exact red/green reproductions, new-process persistence, focused 229 and specified
  regression 277 passed. Exact two-file Ruff cache cleanup succeeded with source
  hashes unchanged. The next secret scan exited 1 on a disposable SQLite journal;
  STOP without other cleanup, policy/full-QA execution, commit or push. Prior
  failed/interrupted runs above remain historical; no R1 closeout is claimed.
- Approved stale-resource resumption validated and disposed of three complete
  test directories through unchanged standard cleanup. Actual 1080/43/2 passed,
  but the first full run exited 1 on unstaged-document/index mismatch. All nine
  document changes were then staged with exact raw blob equality; the next full
  run exited 1 at the process-cleanup canary manifest timeout. No code/scanner
  change, further cleanup, commit/push or R1 acceptance follows this new STOP.
- Subsequent post-document standalone policy scan exited 0; secret scan exited 1
  with 2401 unadjudicated potential-secret findings, including displayed mypy
  metadata and Next.js cache paths. No additional deletion, exception or retry;
  the final reporting-only STOP update is not a successful scanned commit snapshot.

## Unreleased — Phase 2 CP3-C2-B2-C 0007 Counter-Capability Migration — 2026-08-31

- Implemented the separately authorized exact additive
  `0007_phase_02_cp3_c2_b2_c_counter_capability_bootstrap` migration while
  preserving frozen migrations `0001`–`0006` byte-identically.
- Added the three ADR-018 append-only counter-capability tables, the exact 23
  index inventory, 15 new insert/append-only guards, and version-replaced
  exactly the two frozen counter-union triggers with exact `0006` restoration
  on downgrade.
- Added 66 dedicated migration tests covering exact schema/FK/index/trigger,
  late-upgrade cleanup, exact identity, clean upgrade/downgrade/re-upgrade,
  FIRST/ADD/REPLACE nine-terminal
  branches, expiry/issuance ordering, failure-result verification matrices,
  append-only enforcement, distinct child/overall safe-code projection,
  projection negatives, and counter-union continuation/replay behavior. The
  integrated backend inventory is now exactly 851 tests.
- Production application change is limited to one additive database-revision
  compatibility allowlist entry. WebAuthn ceremony/runtime, services, routes,
  UI, human approval execution, and new dependencies remain `0`; persistent
  `var/dashboard.db` migration application remains `0`.
- Final staged implementation-snapshot LOCAL QA passed through the standard
  `scripts/test.ps1` harness: backend `851 passed in 971.60s`, frontend `43`
  passed, E2E `2` passed, disposable migration round-trip/repeat PASS, fixture
  import `13` inserted then `13` unchanged, production build, lint/format,
  typecheck, secret scan, and policy scan PASS. Focused evidence also includes
  dedicated `66`, reviewer-migration `83`, authority-migration `19`, and generic
  migration `2` passing tests. A final evidence-only documentation update was
  followed by diff, policy, secret, integrity, artifact, and remote-ref rechecks.
- Current status is `IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW`; this entry
  does not declare `PASS` or `CLOSED`. B2-C R1 remains `NOT STARTED / REQUIRES
  SEPARATE AUTHORIZATION`; Public Read-only Deployment and Automated Trading
  remain `FUTURE / NOT AUTHORIZED / NOT STARTED`.
- Lower dated entries preserve their historical checkpoint state; their former
  current-state statements about an uncreated `0007` are superseded only by
  this latest implementation record.

## Unreleased — ADR-019 USER-ACCEPTANCE CLOSEOUT — 2026-08-31

- Recorded explicit user acceptance of ADR-019, `Vendor-Neutral WebAuthn Human
  Authority Boundary`, with proposal date `2026-08-29` and decision date
  `2026-08-31`.
- Preserved historical B1 wording `Windows Hello-backed platform credential
  only`; ADR-019 amends only strict authenticator-vendor provenance, leaving
  every unaffected B1/ADR-017/ADR-018 control unchanged.
- Kept ADR-015/ADR-016/ADR-017/ADR-018 accepted, `0006 PASS — CLOSED`, future
  `0007 NOT CREATED / NOT AUTHORIZED`, and R1 `NOT STARTED / REQUIRES SEPARATE
  AUTHORIZATION`.
- Kept Public Read-only Deployment and Automated Trading
  `FUTURE / NOT AUTHORIZED / NOT STARTED`, current `LOCAL_ONLY=true`,
  `TRADING_ENABLED=false`, `DRY_RUN=true`, and automatic progression
  `PROHIBITED`.
- Retained two non-blocking review issues: future Public deployment source
  redistribution/publication eligibility review and absent GitHub CI execution
  evidence.
- Application, runtime, migration, test, dependency, fixture, frontend, network
  exposure and trading changes are all `0`.

## Unreleased — ADR-019 Human Authority and Master Trust Boundaries — 2026-08-29

- Revised ADR-019 to `Vendor-Neutral WebAuthn Human Authority Boundary` and
  kept it `PROPOSED — AWAITING GPT REVIEW / USER ACCEPTANCE` with decision date
  `NONE`.
- Preserved the historical accepted B1 phrase `Windows Hello-backed platform
  credential only`; proposed amendment scope removes only Microsoft Windows
  Hello vendor/product provenance as an authorization condition.
- Kept fresh registered-credential WebAuthn signature, exact RP/origin/type,
  UP/UV, 32-byte five-minute one-time challenge, exact allow-list and
  credential binding, counter fail-closed rules, append-only authentication/
  approval audit, first enrollment, no recovery and app-data OWNER SID/process
  `TOKEN_USER` equality controls unchanged.
- Distinguished the current local Windows-first read-only implementation from
  two separately authorized future checkpoints: anonymous Public Read-only
  Deployment and Automated Trading.
- Frozen the future public trust boundary as internal processing -> public-safe
  projection/read model -> public read-only API/UI -> any Internet viewer. The
  public domain receives no mutation, owner/admin, secret, internal-storage or
  trading authority, and no hosting/network product is selected.
- Recorded future AI/Codex as an untrusted order-intent producer behind a
  deterministic risk policy engine and separate trade executor. No trading
  implementation, risk engine, broker call, credential or deployment was
  added.
- Current `LOCAL_ONLY=true`, `TRADING_ENABLED=false` and `DRY_RUN=true` remain
  mandatory. Public Read-only Deployment and Automated Trading are both
  `FUTURE / NOT AUTHORIZED / NOT STARTED`.
- Migrations `0001`–`0006` remain byte-identical; `0007` remains
  `NOT CREATED / NOT AUTHORIZED`; R1 remains `BLOCKED / NOT STARTED — ADR-019
  DECISION REQUIRED`; later checkpoints and automatic progression remain
  prohibited.
- Application, runtime, migration, test, dependency, fixture, frontend,
  network-exposure and trading changes are all `0`.

## Unreleased — ADR-017/ADR-018 USER-ACCEPTANCE CLOSEOUT — 2026-08-29

- Independent review authority remains from authoritative SHA
  `dbf913d5654b3a1095d359ac34e1edcde2f63c1e`.
- `CHANGES REQUIRED` closeout findings are now closed by user decision:
  `ADR-017` and `ADR-018` are both `ACCEPTED`.
- Explicit user decision: `ADR-017` and `ADR-018` accepted on
  `2026-08-29`; `ADR-019` remains `PROPOSED — ON HOLD / AWAITING SEPARATE
  USER DECISION`.
- All findings through `RG-01`–`RG-11` and `FR-01`–`FR-03` are now contractually
  closed as design artifacts.
- `ADR-017` acceptance freeze includes canonical principal/credential preimages,
  CTAP2-canonical COSE mapping, exact challenge derivations, user-handle model,
  registration proof contract, and accepted golden vectors.
- `ADR-018` acceptance freeze includes all-operation continuation bootstrap
  (`FIRST_ENROLLMENT` / `ADD_CREDENTIAL` / `REPLACE_CREDENTIAL`),
  exact one-time continuation contracts, exact user-handle slot formulas,
  app-data OWNER SID equality requirement, and exact immediate-trigger-safe
  insertion ordering.
- `ADR-019` trust-boundary blocker remains: platform+UV+resident+attestation=none
  proves a user-verifying Windows platform credential and not strict Windows Hello
  provenance.
- Migrations `0001`–`0006` remain byte-identical; `0006` remains
  `PASS — CLOSED`; `0007` remains `NOT CREATED / NOT AUTHORIZED`.
- Committed application, migration, test, dependency, fixture, frontend, and
  runtime changes remain `0`.
- `R1` remains `NOT STARTED / BLOCKED` due `ADR-019`, later checkpoints remain
  `NOT STARTED`, and automatic progression remains `PROHIBITED`.

## Unreleased — ADR-017/ADR-018 Full R1 Implementability Remediation — 2026-08-29

- Recorded the full-design independent verdict at authoritative SHA
  `c34d8ca5a25bbea8c4ff410b7d62dc451f357528`: `CHANGES REQUIRED`, P0 `0`,
  P1 `3`, P2 `2`. Neither ADR was accepted.
- Extended Option C to every credential-producing operation: first enrollment,
  add, and replace. Add/replace preserve the already-committed authorizing
  assertion and counter edge; replace success atomically registers the new
  credential and supersedes the old target, while failure leaves ownership
  unchanged and creates an exact frozen terminal predecessor outcome.
- Defined the exact 32-byte per-operation WebAuthn credential-slot handle,
  display-only user entity constants, non-empty assertion allow lists, optional
  returned-user-handle validation, and restart reconstruction without a new
  persisted handle column.
- Defined Windows owner identity as UTF-8 hashing of exact canonical
  `ConvertSidToStringSidW` output from the validated current-process
  `TOKEN_USER`; all API failures and non-Windows production fail closed.
- Fixed exact registration request and proof derivation for platform attachment,
  required discoverability/UV, attestation none, `credProps`, and restricted
  CTAP2-canonical ES256/RS256 public material.
- Added an implementation-ready proposed future
  `0007_phase_02_cp3_c2_b2_c_counter_capability_bootstrap` design with three
  exact append-only tables, all keys/FKs/checks/indexes/hash preimages/guards,
  frozen projection transactions, replay/restart rules, and a complete frozen-
  trigger replacement audit. `0007` remains `NOT CREATED / NOT AUTHORIZED`.
- Preserved migrations `0001`–`0006` byte-identically and kept `0006 PASS —
  CLOSED`. Application, migration, test, dependency, fixture, and frontend
  changes are `0`; no real Windows Hello or issuer approval ran.
- `ADR-017` is `ACCEPTED` (`2026-08-29`); `ADR-018` is `ACCEPTED`
  (`2026-08-29`). `ADR-019` is `PROPOSED — ON HOLD / AWAITING SEPARATE USER
  DECISION`. R1 remains `NOT STARTED / BLOCKED` pending `ADR-019`, and automatic
  progression remains prohibited.

## Unreleased — ADR-017 Counter-Capability Remediation — 2026-08-28

### Documentation/control-plane proposal

- Recorded independent review of authoritative SHA
  `c76fe7616db65c53ffc5a81d3e3c0cb390c0fa3b`: `CHANGES REQUIRED`, P0 `0`, P1
  `1`, P2 `2`. ADR-017 remains `PROPOSED — CHANGES REQUIRED / RG-06 OPEN`.
- Audited counter bootstrap Options A/B/C. Rejected permanent zero-to-no-counter
  policy because it loses supported-counter clone-detection history; rejected
  blanket zero-registration incompatibility because it is unacceptably brittle
  for a Windows Hello-only product; selected, but did not accept, a fresh
  one-time post-registration assertion.
- Proposed, but did not accept or implement, ADR-018 — WebAuthn Counter
  Capability Bootstrap Amendment. Verified `0 -> positive` selects
  `SIGN_COUNT_SUPPORTED`; verified `0 -> 0` selects the repository
  `NO_USABLE_COUNTER` evidence mode. No browser/AAGUID/attachment/username/
  backup/payload/caller/vendor-metadata signal is authority.
- Audited frozen `0005`/`0006` as insufficient for that continuation: first
  enrollment cannot carry an assertion, registration consumption cannot wait
  for classification, and the existing counter union would omit the bootstrap
  edge. A minimum three-table pre-admission challenge/consumption/finalization
  ledger and cross-ledger guards are proposed for a necessary future `0007`.
  `0007` is `NOT CREATED / NOT AUTHORIZED`; `0006` remains `PASS — CLOSED`.
- Corrected ADR-017 to the WebAuthn-required CTAP2 canonical CBOR encoding form,
  retaining RFC 8949 only as the underlying CBOR reference. Independent CTAP2
  re-encoding kept both frozen ES256/RS256 hex, base64url and fingerprints byte-
  identical; all ten existing vectors remain unchanged where unaffected.
- Added counter-decision vectors and the schema sufficiency audit in
  `qa/PHASE_02_CP3_C2_B2_C_ADR_017_COUNTER_CAPABILITY_REMEDIATION_CODEX_REPORT.md`.
  Application, migration, test, dependency, frontend, real Windows Hello and
  issuer-approval runtime changes are all `0`.
- ADR-015/ADR-016 remain `ACCEPTED`; R1 remains `NOT STARTED / BLOCKED`; B2-D,
  CP3-C2-C and CP3-D remain `NOT STARTED`; automatic progression remains
  `PROHIBITED`.

## Unreleased — Phase 2 CP3-C2-B2-C Runtime Canonicalization Gap — 2026-08-28

### Documentation/control-plane proposal

- Recorded the R1 pre-implementation fail-closed stop at authoritative SHA
  `391fa38808033640081565ca9649bbba3501f071`: RG-01 through RG-05 leave
  principal, credential, COSE, challenge and authentication persisted bytes
  underdetermined. R1 application/runtime changed files remain `0`.
- Proposed, but did not accept, ADR-017 — WebAuthn Runtime Canonicalization and
  Hash Preimage Amendment. It defines exact NFC compact JSON, recursively
  unsigned-UTF-8-sorted keys, null/Boolean/timestamp semantics and
  `sha256:<64-lowerhex>` storage.
- Fixed the exact principal and public-credential preimages; CTAP2 canonical
  CBOR COSE_Key encoding (RFC 8949 underlying reference); `-7 -> ES256` and
  `-257 -> RS256`; canonical unpadded
  base64url TEXT; raw credential/public-key fingerprints; closed transports;
  and no-counter `null` semantics.
- Fixed both challenge digests as SHA-256 of exactly 32 raw OS-CSPRNG bytes and
  proposed exact operation/issuer challenge bindings plus exact operation/
  issuer authentication preimages. The dependency DAG has no cryptographic
  cycle; existing event/operation/consumption/authorization/outcome/state hash
  contracts are unchanged.
- Added ten exact docs-only golden vectors. Two calculator runs were byte-
  identical; isolated Python 3.13 feasibility checks with `webauthn==3.0.0`
  and `cbor2==6.1.4` decoded and materialized both approved COSE key types.
  Repository dependency installation/change and actual Windows Hello use are
  `0` for this task.
- ADR-015 and ADR-016 remain `ACCEPTED`; `0006` remains `PASS — CLOSED`;
  ADR-017 remains `PROPOSED` with decision date `NONE`. R1 is `NOT STARTED /
  BLOCKED — APPROVED RUNTIME CONTRACT GAP`; `0007` is forbidden; later
  checkpoints remain `NOT STARTED`; automatic progression is `PROHIBITED`.

## Unreleased — Phase 2 CP3-C2-B2-C 0006 Closeout — 2026-08-28

### Documentation/control-plane closeout

- Recorded GPT independent review of implementation SHA
  `1be18a622006a6b6a46e251350e2d861d596823d`: `PASS WITH CLOSEOUT CONDITION`,
  P0 `0`, P1 `0`, P2 `1 — GitHub CI execution evidence absent, NON-BLOCKING`.
- Recorded the user's explicit `2026-08-28` closeout approval. The additive
  `0006` schema implementation is now `PASS — CLOSED`; SG-01, SG-02,
  P1-SR-01, P1-SR-02, P1-SR-03, IG-01 and IG-02 remain `CLOSED`.
- This closeout changes documentation/control-plane files only. Migrations
  `0001`–`0006` remain byte-identical to the reviewed SHA; runtime, test,
  script, frontend, fixture and dependency changes are `0`.
- CP3-C2-B implementation remains `IN PROGRESS`. B2-C Windows Hello/WebAuthn,
  reviewer authentication and human approval runtime remain `NOT STARTED / NOT
  AUTHORIZED`; B2-D, CP3-C2-C and CP3-D remain `NOT STARTED`, and automatic
  progression remains `PROHIBITED`.
- GitHub CI execution evidence remains absent as an approved non-blocking P2;
  LOCAL closeout checks are not GitHub CI evidence.

## Unreleased — Phase 2 CP3-C2-B2-C 0006 Implementation — 2026-08-28

### ADR-016 acceptance and additive schema implementation

- Recorded GPT independent review of SHA
  `4104973d84307b80a236d9b737b2d29339b27153`: `PASS WITH CLOSEOUT CONDITION`,
  P0 `0`, P1 `0`, P2 `1` non-blocking, with IG-01 and IG-02 closed.
- Recorded the user's explicit acceptance of ADR-016 on `2026-08-28` and the
  separate authorization for the approved additive `0006` schema only.
- Added additive revision
  `0006_phase_02_cp3_c2_b2_c_reviewer_operations` with the approved six-table
  credential-operation ledger, 23 named indexes, 12 new-table append-only
  triggers, and 11 insert/counter guards. Migrations `0001`–`0005` remain
  byte-identical and no existing table was rebuilt.
- Implemented ADR-016's exact four-token/five-row authorization matrix, copied
  trust columns, exact eight-column operation FKs, exact eleven-column
  successful-outcome binding, terminal outcome/continuation graphs, active
  lifecycle guards, and issuer/operation counter union without a SQLite SHA
  dependency.
- Added isolated migration/schema coverage and minimal additive public-revision
  compatibility. The 0006 implementation is `IMPLEMENTED — AWAITING GPT
  INDEPENDENT REVIEW`; it is not declared PASS/CLOSED.
- Final LOCAL QA passed targeted `83`, all-migration `118`, authority-regression
  `158`, backend `785`, frontend `43`, E2E `2`, repeat/downgrade/re-upgrade,
  fixture idempotency, Ruff, mypy, ESLint, TypeScript, OpenAPI, two production
  builds, secret scan and policy scan. Final staged `scripts/test.ps1` exited
  `0`; this is not GitHub CI evidence.
- WebAuthn/human-approval runtime and later checkpoints remain unauthorized or
  not started; automatic progression remains prohibited.

## Unreleased — Phase 2 CP3-C2-B2-C Exact SQLite Binding Amendment — 2026-08-28

### Documentation/control-plane amendment

- Recorded GPT independent review of SHA
  `f73115ea1182e27259787460307a01b4c3874312`: `PASS WITH CLOSEOUT CONDITION`,
  P0 `0`, P1 `0`, P2 `1` non-blocking, followed by explicit user acceptance of
  ADR-015 on `2026-08-28`. ADR-015 is now `ACCEPTED`; the six-table schema
  architecture is approved without declaring migration or runtime PASS.
- Recorded the later fail-closed implementation stop with no changed files and
  no `0006`. GPT independently confirmed IG-01, the incomplete
  `authorization_kind` enum/matrix, and IG-02, the unimplementable exact
  operation child FK caused by three missing copied trust columns.
- Proposed, but did not accept, ADR-016 — Reviewer Operation Exact SQLite
  Binding Amendment. The exact closed enum is
  `BOOTSTRAP_REGISTRATION|AUTHORIZED_REGISTRATION|AUTHORIZED_SUPERSESSION|
  AUTHORIZED_REVOCATION`, with only the five documented operation/event/token
  combinations allowed.
- Added `reviewer_role`, `principal_content_hash`, and `os_owner_sid_hash` to
  the proposed authorization and outcome child schemas, bound both to the exact
  ordered eight-column operation parent key, and included all three columns in
  both immutable content-hash preimages. No subset operation identity, generic
  authorization fallback, payload authority, or SQLite SHA UDF was introduced.
- CP3-C2-B2-C is `BLOCKED — APPROVED SCHEMA CONTRACT IMPLEMENTATION GAP /
  ADR-016 AWAITING GPT INDEPENDENT REVIEW`. `0006` remains not created/not
  implemented; B2-C runtime and all later checkpoints remain `NOT STARTED`, and
  automatic progression remains `PROHIBITED`.
- This change is documentation/control-plane only. Application, test, script,
  frontend, dependency and migration changes are `0`; migrations `0001`–`0005`
  remain byte-identical. LOCAL checks are not GitHub CI evidence, which remains
  absent/non-blocking.

## Unreleased — Phase 2 CP3-C2-B2-C Operation Terminalization Fix — 2026-08-28

### Documentation proposal revision

- Recorded GPT independent re-review of SHA
  `e016fc59973e5c81181e7cf20c1ebe3d7aada043`: `CHANGES REQUIRED`, P0 `0`,
  P1 `1`, P2 `1` non-blocking. P1-SR-01 and P1-SR-02 are independently
  verified `CLOSED`; P1-SR-03 remains subject to re-review after this revision.
- Required every failed, expired, or otherwise operation-terminal challenge
  consumption to commit exactly one mapped operation outcome before returning a
  terminal result. Failed outcomes append no lifecycle transition and preserve
  the exact expected credential-state hash.
- Added mutual deferred exact bindings between terminal consumption and outcome,
  plus a closed `EXPIRED`/`REJECTED`/`FAILED_CLOSED` mapping. Attributable
  rejected audits remain optional safe facts; no synthetic authentication or
  credential is created for unattributable failures.
- Bound each operation to its initial challenge in one issuance transaction.
  The sole nonterminal case—successful ADD/REPLACE authorization—must atomically
  commit its verified counter event and exactly one five-minute registration
  challenge, preventing orphan operations and reusable authorization sessions.
- Preserved authenticated final-credential revoke/empty-state semantics and the
  exact trusted-server `reviewer-credential-state/0.1.0` SHA boundary.
- ADR-015 remains `PROPOSED`; `0006` creation/application and B2-C runtime remain
  `0`. CP3-C2-B2-C remains blocked awaiting GPT independent re-review; later
  checkpoints remain `NOT STARTED`, and automatic progression is `PROHIBITED`.
- This revision changes documentation/control-plane files only. LOCAL checks
  are not GitHub CI evidence; GitHub CI execution evidence remains absent and
  non-blocking.

## Unreleased — Phase 2 CP3-C2-B2-C Schema Remediation Review Fix — 2026-08-28

### Documentation proposal revision

- Recorded GPT independent review of SHA
  `fd0535fdd022f0171a63a83cb2861e924a92da64`: `CHANGES REQUIRED`, P0 `0`,
  P1 `2`, P2 `1` non-blocking. SG-01/SG-02 and additive Option A were accepted
  in principle; P1-SR-01 and P1-SR-02 await independent re-review.
- Corrected final-active-credential lifecycle semantics. A valid authenticated
  `REVOKE_CREDENTIAL` may revoke the final active credential and commits the
  exact empty active set. Approval/add/replace/further revoke then fail closed,
  first enrollment cannot restart, and recovery/reset remains absent.
- Defined exact `reviewer-credential-state/0.1.0` canonical JSON and SHA-256
  semantics, including active membership, sort/duplicate rules, principal-
  specific empty state, audit exclusions, and explicit exclusion of signature-
  counter values.
- Assigned aggregate state-hash computation/revalidation to trusted server code
  under the same SQLite `BEGIN IMMEDIATE` transaction. SQLite enforces the
  relational graph and exact stored-value bindings only; no undeclared SQLite
  SHA-256 function is assumed.
- Retained six additive tables and strengthened the lifecycle authorization
  companion with a mandatory deferred FK to the exact successful operation
  outcome/pre-state/post-state tuple. A credential/lifecycle event cannot commit
  without its successful CAS result.
- ADR-015 remains `PROPOSED`. CP3-C2-B2-C remains `BLOCKED — SCHEMA CONTRACT
  GAP / SCHEMA REMEDIATION AWAITING GPT INDEPENDENT RE-REVIEW`; B2-D,
  CP3-C2-C and CP3-D remain `NOT STARTED`; automatic progression remains
  `PROHIBITED`.
- Runtime, test, script, frontend, dependency and migration changes remain `0`.
  Migrations `0001`–`0005` are unchanged; `0006` creation/application, real
  enrollment/approval/canonical writes and live authority/Toss requests remain
  `0`. LOCAL checks are not GitHub CI evidence.

## Unreleased — Phase 2 CP3-C2-B2-C Schema Contract Remediation — 2026-08-28

### Documentation proposal

- Recorded the implementation-entry result
  `BLOCKED — SCHEMA CONTRACT GAP` for CP3-C2-B2-C. P0 is 0; SG-01 and SG-02
  are the two confirmed schema blockers. GitHub CI execution evidence remains
  absent/non-blocking.
- Proposed ADR-015,
  `WebAuthn Enrollment and Credential-Operation Ledger Amendment`, and left it
  `PROPOSED` pending GPT independent review and explicit user acceptance.
- Added
  `plans/PHASE_02_CP3_C2_B2_C_SCHEMA_REMEDIATION.md`. The selected future
  `0006` strategy is additive option A: six append-only credential-operation
  tables plus exact additive indexes and insert guards, with no `0005` table
  rebuild.
- The proposal separates first-enrollment/create challenges and credential-
  management/get assertions from issuer-approval challenges. It designs unique
  terminal consumption, exact principal/SID/credential binding, mandatory
  lifecycle-event authorization, union append-only counter reconstruction,
  operation-chain concurrency and no-recovery fail-closed behavior.
- Corrected the earlier feasibility note: issuer `SUPERSEDED` is not a current
  schema blocker. Existing `0005` can represent separately authenticated old
  `SUPERSEDED` and successor `APPROVED` link versions atomically with a guarded
  final head CAS.
- Runtime, test, script, frontend, dependency, and migration changes are `0`.
  Migrations `0001`–`0005` remain byte-identical, `0006` creation/application is
  `0`, and no real Windows Hello enrollment, approval, canonical/link write, or
  live authority/Toss request occurred.
- CP3-C2-B2-C remains
  `BLOCKED — SCHEMA CONTRACT GAP / SCHEMA REMEDIATION AWAITING GPT INDEPENDENT
  REVIEW`. B2-D, CP3-C2-C and CP3-D remain `NOT STARTED`; automatic progression
  remains `PROHIBITED`.

## Unreleased — Phase 2 CP3-C2-B2-B Issuer Authority Decision Engine — 2026-08-27

### Documentation closeout

- GPT independently reviewed SHA
  `d81148636c237ac8ab6b85e930d3926fae19c855` and returned `PASS WITH
  CLOSEOUT CONDITION`, P0 0 / P1 0 / P2 1 non-blocking. P1-01 through P1-09
  are `CLOSED`.
- CP3-C2-B2-B is `PASS — CLOSED`; CP3-C2-B implementation remains `IN
  PROGRESS`. B2-C/B2-D, CP3-C2-C and CP3-D remain `NOT STARTED`, and automatic
  progression remains `PROHIBITED`.
- This closeout changes documentation/QA only. Runtime, contract, repository,
  domain, test, fixture, script, dependency, frontend and migration changes are
  `0`; migrations `0001`–`0005` remain byte-identical and `0006` remains `0`.
- Production authority admission and generic READY remain fail closed. Machine
  maximum positive state remains `READY_FOR_MANUAL_REVIEW`; operational human
  approval/WebAuthn, canonical Issuer/Security writes, VERIFIED mapping,
  provider rekey, issuer-link execution and live authority/Toss requests remain
  `0`.
- GitHub CI execution evidence remains absent and is retained as a non-blocking
  P2. LOCAL Codex checks are not represented as GitHub CI evidence. This
  closeout does not authorize B2-C.

### Third independent-review remediation

- Second independently reviewed SHA
  `8093ee9389d4f7ae716482a87de5eae252e08eff` received `CHANGES REQUIRED`,
  P0 0 / P1 2 new / P2 1. P1-01 through P1-07 remain independently verified
  `CLOSED`; P2 remains the non-blocking absence of GitHub CI execution evidence.
- Bound every decisive KR IROS legal-name history member to the same exact
  official `corporate_registration_reference`/`jurir_no`, and every US state-
  registry member to the same exact namespace, formation state, and state
  entity number. These bindings come from independently stored same-document
  registry subject facts; a correction/supersession edge alone cannot bridge
  different legal entities.
- Reconciled every relevant supporting OpenDART/accepted SEC legal name rather
  than requiring one global supporting-name value. Multiple exact current and
  officially explained former names may coexist, while one unknown or cross-
  entity name blocks READY. No fuzzy, case, punctuation, suffix, whitespace,
  provider-name, or ticker reconciliation was added.
- Retained same-document SEC CIK/role/bridge/name completeness, compatible
  accession semantics, authority-accepted former-symbol chronology, historical-
  filing/freshness separation, complete current-state discovery, generic
  production admission/READY rejection, and transaction-wide impacted-READY
  invalidation.

### Second independent-review remediation

- Re-reviewed SHA `722a5036d7d05ad6b8de0314ff6ac5ee8dafacc2`
  received `CHANGES REQUIRED`, P0 0 / P1 2 new / P2 1. P1-01 through P1-05
  remain independently verified `CLOSED`; P2 remains the non-blocking absence
  of GitHub CI execution evidence.
- Added required KR OpenDART/IROS and US accepted SEC/exact-state-registry
  `LEGAL_NAME` evaluation. Official names must be NFC-exact or reconciled by a
  conflict-free immutable field-owner correction/supersession history. Provider
  name/ticker, fuzzy matching, and lossy normalization cannot repair a conflict.
- Separated accepted-filing accession provenance from stable SEC issuer/entity
  bridge semantics. Compatible historical filings can coexist across different
  accessions only when every filing independently has exact same-document CIK,
  issuer role, bridge, and legal-name facts. Formation-state/entity conflicts
  still fail closed; former symbols require deterministic authority acceptance
  chronology, and historical filing age remains separate from latest-status
  freshness.

### Independent-review remediation

- Reviewed SHA `d4f84c4bfb83f2396161eea913f2c119ecb17dac` received
  `CHANGES REQUIRED`, P0 0 / P1 5 / P2 1. P2 remains the non-blocking absence
  of GitHub CI execution evidence.
- Generic repository admission of every new production policy, evidence fact,
  retrieval observation, and correction/revocation relation now fails closed.
  Offline evaluator tests use a tests-only white-box pre-admitted snapshot;
  production code cannot import it and no operational trusted ingestion path is
  claimed.
- Freshness now uses an engine-owned aware UTC clock read inside the writer
  transaction. Caller request timestamps cannot backdate or force READY.
- The engine discovers all relevant current provider observations and KR/US
  authority state instead of trusting caller-selected memberships. Omitted
  co-current official conflicts and unsafe provider observations block READY.
- Exact deterministic canonical issuer rows are recognized as the same subject;
  different or inconsistent rows remain collisions. Duplicate corp-code/CIK
  transactions append `REVIEW_REQUIRED` successors for every impacted READY
  leaf before commit.

### Added

- Added an immutable server-owned exact authority-source registry for OpenDART
  corp-code/company-overview, verified Korean IROS records, SEC accepted issuer
  filing/latest-status metadata, weight-zero SEC login/agent provenance, and
  the individually admitted Delaware formation registry. There is no wildcard
  production namespace or caller-controlled authority escalation.
- Added strict versioned B2-B evaluation/bridge contracts and an offline
  `IssuerAuthorityDecisionEngine` that loads immutable ledger state itself.
- Added exact KR OpenDART `corp_code` + raw `jurir_no` + verified domestic IROS
  + non-name CP3-C1 provider bridge evaluation, and exact US registrant CIK/
  accepted filing + domestic state record + non-name provider bridge
  evaluation. Listing market, exchange, currency, language, name, and ticker
  remain zero jurisdiction/issuer authority by themselves.
- Added current correction/revocation-head reconstruction, conservative
  repository latest-status freshness, deterministic identifier/application/
  canonical/provider collision scanning, and append-only machine transitions.
- Added controlled READY persistence under SQLite `BEGIN IMMEDIATE` with
  transaction-time revalidation. Arbitrary generic repository READY remains
  typed fail closed.

### Verification and boundaries

- B2-B targeted coverage is now 89 offline tests; retained 69/69 B2-A authority
  tests and executable non-regression proof for P1-01 through P1-07. Exact full
  inventory is backend 702, frontend 43, E2E 2.
- Migrations `0001`–`0005` are unchanged; `0006` creation and persistent/runtime
  application of `0005` are 0.
- Automatic promotion, canonical Issuer/Security writes, VERIFIED mapping,
  provider rekey, human approval, WebAuthn operation, link-head mutation, live
  authority/provider requests, and credential use remain 0.
- CP3-C2-B implementation remains `IN PROGRESS`; B2-B is `REMEDIATED —
  AWAITING GPT INDEPENDENT RE-REVIEW`. B2-C/B2-D, CP3-C2-C and CP3-D remain
  `NOT STARTED`; automatic progression remains `PROHIBITED`.
- All reported checks are LOCAL Codex evidence. GitHub CI evidence is absent
  unless independently produced after push; this entry does not declare GPT
  PASS.

## Unreleased — Phase 2 CP3-C2-B2-A Documentation Closeout — 2026-08-27

### Independent re-review

- Remediated SHA `57e9bbbf2a1fd117b8e31c7288f2f08475c7e4ae`
  received `PASS WITH CLOSEOUT CONDITION`, P0 0 / P1 0 / P2 1.
- P1-01 cross-bundle same-provider correction supersession, P1-02 premature
  `READY_FOR_MANUAL_REVIEW` persistence, and P1-03 append-only WebAuthn
  signature-counter storage are all `CLOSED`.
- P2-01, absence of GitHub CI execution evidence, remains non-blocking. Local
  Codex safety gates are not represented as GitHub CI evidence.

### Closeout boundary

- CP3-C2-B2-A is `PASS — CLOSED`; CP3-C2-B implementation remains `IN
  PROGRESS`.
- CP3-C2-B2-B is `NOT STARTED — REQUIRES SEPARATE USER START APPROVAL`.
  B2-C/B2-D, CP3-C2-C and CP3-D remain `NOT STARTED`; automatic progression is
  `PROHIBITED`.
- Documentation-only closeout changes no runtime, test, script or migration.
  `0001`–`0004` remain unchanged, `0005` remains the current additive B2-A
  migration with persistent/runtime application `0`, and `0006` remains `0`.
- Operational WebAuthn/approval, canonical Issuer/Security writes, VERIFIED
  mapping, provider rekey, link-head workflow and live authority/provider
  requests remain `0`.

## Unreleased — Phase 2 CP3-C2-B2-A Independent-Review Remediation — 2026-08-27

### Fixed

- corrected evidence may now produce a new immutable bundle and a successor
  decision for the same provider authority subject, including a corrected issuer
  candidate. The existing unique predecessor-child index rejects a competing
  successor, and repository validation rejects unrelated-provider chain grafts.
- B2-A now rejects every low-level `READY_FOR_MANUAL_REVIEW` decision insert
  with typed `REVIEW_READY_ENGINE_NOT_IMPLEMENTED`; exact observation membership
  is not treated as the independently proven provider-to-issuer bridge that the
  separately gated B2-B engine must implement and pass independent review.
- immutable credential state now stores `registration_sign_count`, while each
  append-only authentication audit stores exact counter capability plus nullable
  prior/asserted counts. Supported VERIFIED counters must strictly advance;
  equality/rollback cannot verify, and no-counter authenticators retain null
  counts without fake advancement.

### Compatibility and boundary

- additive revision/down-revision remain
  `0005_phase_02_cp3_c2_b_issuer_authority` /
  `0004_phase_02_cp3_c1_security_master`; the same approved 21 tables, 14 named
  indexes, and 40 append-only triggers remain. Inline checks are hardened from
  68 to 75.
- migrations `0001`–`0004`, existing provider/canonical rows, MappingStatus,
  identifier-claim non-winner semantics and immutable ledger history remain
  unchanged.
- operational WebAuthn verification, approval execution, canonical Issuer or
  Security writes, VERIFIED mapping, provider rekey, link-head workflow and live
  authority/provider requests remain `0`.

### Status

- Reviewed SHA `05eb70d8dfe488563757107c0697f1a7708018c9` received `CHANGES
  REQUIRED`, P0 0 / P1 3 / P2 1. CP3-C2-B2-A is now
  `REMEDIATED — AWAITING GPT INDEPENDENT RE-REVIEW`; it is not self-declared
  PASS.
- CP3-C2-B implementation remains `IN PROGRESS`. B2-B/B2-C/B2-D, CP3-C2-C and
  CP3-D remain `NOT STARTED`; automatic progression remains `PROHIBITED`.

## Unreleased — Phase 2 CP3-C2-B2-A Authority Ledger Foundation — 2026-08-27

### Added

- approved ADR-013/ADR-014에 맞춘 versioned `AuthoritySourcePolicy`, raw
  `AuthorityEvidence`, retrieval observation/relation, candidate-specific
  `AuthorityEvidenceApplication`, exact application-member `AuthorityBundle`,
  identifier claim과 machine-only `IssuerDecision` contract를 추가했다.
- canonical UTF-8/NFC JSON과 SHA-256 semantic IDs는 retrieval/evaluation/record
  time, DB/run/request ID, clock와 member input order를 제외한다.
- additive `0005_phase_02_cp3_c2_b_issuer_authority`에 approved 21-table
  authority/authentication/approval/link family, 68 inline CHECK, 14 named
  index와 40 append-only UPDATE/DELETE trigger를 추가했다.
- deterministic immutable row를 same-ID/same-content이면 idempotent success,
  same-ID/different-content이면 typed conflict로 처리하는 low-level SQLite
  ledger repository를 추가했다.

### Safety and compatibility

- source-policy exact scope/role/weight matrix와 server-owned production policy
  registry boundary를 두고 unlisted scope, fixture/test namespace, copied or
  relabelled tainted lineage와 historical synthetic corp_code/CIK를 production
  bundle에서 fail closed한다.
- corp_code/CIK claim lookup은 non-unique로 유지해 contradictory claims를 모두
  보존하고 insertion-order winner나 canonical issuer를 만들지 않는다.
- `0001`~`0004` SHA-256과 기존 provider/issuer/security/source/history row를
  보존하며 기존 `MappingStatus = VERIFIED | UNRESOLVED`와 Phase 1 public
  database revision contract를 변경하지 않는다.
- reviewer/WebAuthn/challenge/approval/link table은 later-phase schema
  foundation뿐이다. WebAuthn verification, human approval execution, canonical
  Issuer/Security write, VERIFIED mapping, provider rekey와 live authority
  request는 모두 0이다.

### QA and status

- Initial B2-A targeted offline tests `54`, full backend inventory `598`, frontend
  inventory `43`, E2E inventory `2`를 고정했다. Final staged full regression과
  migration/fixture/build/secret/policy 결과는
  `qa/PHASE_02_CP3_C2_B2_A_CODEX_REPORT.md`에 기록한다.
- `scripts/test.ps1`의 exact backend inventory와
  `scripts/policy-scan.ps1`의 exact test allowlist/control-manifest count/digest만
  새 authorized files에 맞춰 갱신했다. scanner 조건이나 network guard는
  완화하지 않았다.
- At reviewed SHA `05eb70d8dfe488563757107c0697f1a7708018c9`, B2-A의
  historical state는 `IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW`였다. 이
  상태는 위 remediation record로 대체됐다. CP3-C2-B implementation은
  `IN PROGRESS`; B2-B/B2-C/B2-D, CP3-C2-C와 CP3-D는 `NOT STARTED`, automatic
  progression은 `PROHIBITED`다.

## Unreleased — Phase 2 CP3-C1 Independent-Review P1 Remediation — 2026-08-26

### Fixed

- current identifier를 source chronology와 identifier history의 의미 상태로 해석한다. closed history는 current에서 제외하고, symbol-change observation은 provider가 제공하지 않은 변경일을 만들지 않은 채 새 open symbol을 current로 만든다. 둘 이상의 상충 current 값은 history ID/hash 순서로 winner를 고르지 않고 collision quarantine으로 fail closed한다.
- 한 STOCK_DETAIL source의 전체 response를 publish 전에 분석해 duplicate non-null ISIN을 검출한다. 모든 affected observation을 처음부터 `QUARANTINED`/`UNRESOLVED_COLLISION`으로 기록하며 기존 identity는 source-consistent하게 함께 격리하고 신규 충돌 후보에는 identity를 할당하지 않는다.
- C-M04/IR-F의 두 affected observation 검증을 강화하고 three-step rename, current lookup, discovery/detail missing, ambiguous current, new-candidate duplicate ISIN, response-order independence 회귀를 추가했다.

### QA and Scope

- GPT independent review 결과 `CHANGES REQUIRED`, P0 0/P1 2를 전사한 QA record와 Codex fix self-report를 분리해 추가했다.
- Backend exact inventory는 `540 → 544`; frontend `43`, E2E `2`를 유지한다. migration은 0이며 `0001`~`0004`는 byte-identical이다.
- actual credential, actual Toss API request, external provider network와 canonical auto-promotion은 각각 0이다.
- 상태는 CP3-B `PASS — CLOSED`, CP3-C1 `REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW`, CP3-C2 `NOT STARTED — USER DECISION REQUIRED`, CP3-D `NOT STARTED`; automatic progression은 `PROHIBITED`다.

## Unreleased — Phase 2 CP3-C1 Security Master Staging & Reconciliation — 2026-08-26

### Added

- `/api/v1/stocks/all`과 `/api/v1/stocks` 응답을 위한 `toss-security-master/0.1.0` strict DTO, checksum-valid nullable ISIN, canonical Decimal 문자열과 비식별 KR/US offline fixture를 추가했다.
- 같은 provider/market의 active symbol, unique ISIN, symbol+listDate, lifecycle/source lineage를 anchor 할당보다 먼저 평가하는 continuity-first reconciliation을 구현했다. 이름은 증거로 사용하지 않는다.
- valid ISIN → symbol+listDate → symbol+first-seen raw hash 우선순위의 immutable provider identity, append-only symbol/ISIN/listDate/market history, enrichment no-rekey와 symbol-change continuity를 구현했다.
- 다중·모순 evidence, duplicate ISIN, identifier/share-class/listing-market change를 auto merge/new identity/arbitrary winner 없이 `UNRESOLVED_COLLISION`/`QUARANTINED`로 fail closed한다.
- discovery disappearance의 `DISCOVERY_MISSING`-only 처리, inactive/delisted observation, exact partial/empty detail batch audit와 `(fetched_at, source_version_id)` clean-DB deterministic replay를 구현했다.
- semantic normalized record, source-linked staging/lifecycle observation, identity-state event와 detail-batch result를 위한 additive `0004_phase_02_cp3_c1_security_master` 네 table을 추가했다.

### QA and Scope

- C-M01~C-M09, C-U01~C-U08와 IR-D~IR-G를 포함한 offline 회귀를 추가하고 backend exact inventory를 509에서 540으로 올렸다. frontend 43와 E2E 2 exact gate는 유지한다.
- 기존 `0001`, `0002`, `0003` bytes와 Phase 1 public API/OpenAPI/fixture를 보존하고 0004 mid-DDL cleanup/retry를 검증한다.
- actual credential, actual Toss request와 external provider network는 각각 0이다. canonical Issuer/Security promotion, price/CP3-D, live collection, frontend와 scheduler는 구현하지 않았다.
- 상태는 CP3-B `PASS — CLOSED`, CP3-C1 `IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW`, CP3-C2 `NOT STARTED — USER DECISION REQUIRED`, CP3-D `NOT STARTED`이며 automatic progression은 `PROHIBITED`다.

## Unreleased — Phase 2 CP3-B Controlled Rollback + Minimal P1 Reapply — 2026-08-26

### Fixed

- canonical request별 source history를 하나의 ORIGINAL root와 하나의 current leaf를 갖는 linear chain으로 검증한다. 후속 version은 exact leaf만 supersede할 수 있고 second root, non-leaf supersession, fork, cycle과 cross-request link를 fail closed한다.
- additive `0003_phase_02_cp3_b_invariants`에 ORIGINAL root, non-null supersedes child와 open-ended VERIFIED mapping을 위한 SQLite partial unique index를 추가한다. migration은 invalid pre-existing history/overlap을 rewrite 없이 거부하고 `0001`/`0002`를 수정하지 않는다.
- VERIFIED mapping의 nullable validity boundary를 unbounded interval로, 양 끝을 inclusive로 해석해 같은 provider identity의 bounded/open-ended overlap을 repository에서 차단한다. 기존 mapping을 자동 종료·변경하지 않는다.
- source revision과 current VERIFIED promotion의 independent-session race에서 exactly one writer만 성공하고 loser는 raw SQLite exception 대신 safe typed conflict를 받는다.

### QA and Scope

- backend exact inventory gate를 493에서 509로 올렸다. source chain/root/fork/order/preservation, mapping overlap/history/concurrent promotion과 0003 upgrade/downgrade/re-upgrade/invalid-data tests를 추가했다.
- frontend 43, E2E 2 exact gate와 policy missing/lookalike canary, exact control-plane count 70 및 digest enforcement를 유지한다.
- CP2와 approved CP3-A contract, `0001`, `0002`, connector/runtime, frontend, public API/OpenAPI와 dependency는 변경하지 않았다.
- actual credential 사용과 actual Toss API request는 0이며 CP3-C는 `NOT STARTED`다.
- `a33cf6e0ff74bf7db1a373061f90785a92709696` 기준으로 기존 작업을 stash에 보존한 뒤 P1 직접 관련 변경만 선택 재구성했다.
- `scripts/secret-scan.ps1`과 `scripts/secret_scan_driver.py`는 baseline 그대로이며 audit transport ZIP은 repository에 포함하지 않는다.
- CP3-B 상태는 `IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW`; automatic progression은 `PROHIBITED`다.

## Unreleased — Phase 2 CP3-B Independent-Review Hardening — 2026-08-25

### Fixed

- same request/status/raw hash/provider contract의 later fetch에서 `fetched_at`·safe telemetry 차이를 semantic duplicate로 처리하고 first-seen raw/source manifest를 보존한다. dataset/parser/normalized hash/revision/supersedes 차이는 conflict다.
- `/stocks/all → STOCK_DISCOVERY`, `/stocks → STOCK_DETAIL`, `/prices → CURRENT_PRICE` exact mapping과 request→raw→source→attempt/audit graph를 repository에서 강제한다. `DAILY_FLOW` persistence는 승인 endpoint가 없어 금지한다.
- VERIFIED mapping은 ACTIVE identity, 실제 issuer/security 관계와 identity first/latest 또는 identifier-history source evidence를 요구한다.
- provider latest update를 DB-level one-statement conditional SQL update로 변경하고 two-session winner 1/typed loser conflict, first-insert race와 complete-row 보존을 검증한다.
- CURRENT_PRICE freshness는 CP3-D2 전 항상 `UNKNOWN`이며 timestamp-null source는 보존 가능하지만 latest pointer에는 사용할 수 없다.
- `0002` 후반 DDL sentinel failure 시 earlier CP3 tables를 제거하고 0001 revision/Phase 1 rows/pre-existing sentinel을 보존한다.
- raw final publish를 overwrite 가능한 rename에서 atomic no-replace로 변경해 competing same bytes는 dedupe, different bytes는 conflict로 처리한다.

### QA and Status

- backend exact inventory gate를 448에서 493으로 올리고 later-fetch/trace/mapping/two-session CAS/mid-migration/no-replace negative tests를 추가했다.
- test file exact allowlist, control-plane count 70과 digest gate, missing/lookalike canary와 모든 보안 gate를 유지했다.
- actual credential 사용과 actual Toss API request는 0이며 LIVE_VERIFIED 범위는 확대하지 않았다.
- CP3-B: `REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW`; CP3-C: `NOT STARTED`; automatic progression: `PROHIBITED`.
- final staged full regression의 exact 결과와 exit code는 `qa/PHASE_02_CP3_B_FIX_CODEX_REPORT.md`에 기록한다.

## Unreleased — Phase 2 CP3-B Provider Source Trace Foundation — 2026-08-25

### Added

- 독립 `toss-source/0.1.0` provider source contract와 `toss-identity/0.1.0` identity foundation contract
- deterministic secret-free canonical request, allowlisted raw manifest metadata와 exact-byte SHA-256 contract
- injected base directory, hash-addressed opaque ref, reparse/symlink/hard-link 방어, flush/fsync와 atomic rename을 사용하는 append-only raw store
- canonical request/raw/source revision/attempt/audit/identity/history/mapping/latest pointer용 additive 9-table `0002_phase_02_cp3_foundation`
- insert-or-verify conflict detection, source+audit atomic transaction, append-only identity metadata와 compare-and-set latest pointer SQLite repository
- contract/canonical request/raw store/revision/repository/migration/security 회귀 tests; backend exact inventory 357 → 448

### Compatibility and Security

- Phase 1 global `ContractVersion = Literal["0.1.0"]`, SourceRecord/Issuer/Security, fixture row/ID/hash/payload, public API/OpenAPI와 `0001` bytes 보존
- auth endpoint body, credential/token/header/account metadata, absolute raw path와 unrestricted response header 저장 surface 0
- actual credential 사용과 actual Toss API request 0; standard suite는 offline 경계를 유지
- account/order/WebSocket, connector auth/client/rate/preflight, frontend, config, dependency와 live script 변경 0

### Scope and Status

- endpoint DTO/normalizer, collection job, Security Master continuity reconciliation와 Current Price/ProviderPriceSnapshot 구현은 포함하지 않음
- ADR-010/011/012는 `ACCEPTED`, CP3-A는 `PASS — CONTRACT APPROVED AND CLOSED`
- CP3-B는 `IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW`; `PASS`, `APPROVED`, `COMPLETE`가 아님
- CP3-C는 `NOT STARTED`, automatic checkpoint progression은 `PROHIBITED`
- `/stocks/all`, `/prices`, provider enum/null/lifecycle, price timestamp-null/currency/freshness와 actual 429/5xx timing은 계속 `[LIVE_UNVERIFIED]`

### QA

- target contract/raw/repository/migration regression 100개 PASS, 전체 backend inventory 448개로 증가
- final staged full regression의 exact 결과와 exit code는 동일 commit의 `qa/PHASE_02_CP3_B_CODEX_REPORT.md`에 기록

## Unreleased — Phase 2 CP3-A Approval and Final Closeout — 2026-08-25

### Approved

- 사용자 명시적 결정으로 ADR-011 `date-only Toss 관측을 versioned source contract로 분리`를 `ACCEPTED`로 전환
- 사용자 명시적 결정으로 revised ADR-012 `Toss provider security identity와 canonical issuer/security mapping 분리`를 `ACCEPTED`로 전환
- GPT independent re-review `PASS WITH CLOSEOUT CONDITION`, P0 0/P1 0과 P1-01/P1-02 `CLOSED` 결과를 `qa/PHASE_02_CP3_A_INDEPENDENT_QA.md`에 별도 보존
- CP3-A planning/contract를 `PASS — CONTRACT APPROVED AND CLOSED`로 closeout; CP3-B는 `NOT STARTED`, automatic progression은 `PROHIBITED`

### QA Closeout

- P2 `final post-report-edit regression evidence gap`은 두 QA 보고서를 포함한 final 9-file staged documentation set을 먼저 완성·stage한 뒤 전체 `scripts/test.ps1`을 실행해 해소
- final staged set 기준 exit 0: backend inventory 357 및 357/357, frontend inventory 43 및 43/43, E2E inventory 2 및 2/2 PASS
- migration repeat/downgrade/re-upgrade, fixture second import `inserted=0`/`updated=0`/`unchanged=13`, OpenAPI, production build 2회, secret scan, initial/final policy scan PASS
- actual Toss credential usage 0, actual Toss API requests 0, offline default/SelfTest external request 0

### Scope and Limitations

- application/test/fixture/migration/dependency/runtime config/API route/connector/CP3-B implementation 변경 0
- test 삭제, skip/xfail, inventory 감소, assertion 완화, exception/scanner/network guard 우회 0
- `/stocks/all`, `/prices`, complete enum/null/lifecycle, price timestamp-null/currency/freshness, natural 429와 actual 429/5xx production timing은 계속 `[LIVE_UNVERIFIED]`
- PR/main merge/tag/release 0

## Unreleased — Phase 2 CP3-A Independent Review Fix — 2026-08-25

### Changed

- independent review `CHANGES REQUIRED`의 P1-01을 반영해 valid provider identity 기준 `ProviderPriceSnapshot`/latest storage와 verified-only canonical current-price view를 분리했다. nullable `security_id` linkage 때문에 Phase 2 provider-scoped 목표가 Phase 3 OpenDART/Phase 4 SEC regulatory mapping에 순환 의존하지 않는다.
- P1-02를 반영해 신규 anchor allocation 전에 active identity/history continuity를 검색하고, 단일 후보 재사용, identifier enrichment, collision quarantine, evidence 0일 때만 최초 anchor 선택, 후속 rekey 금지와 deterministic replay 규칙을 추가했다.
- provider price without canonical mapping, verified mapping promotion, fake regulatory ID prevention, ISIN/listDate enrichment, enrichment collision과 deterministic rebuild를 P0 문서 acceptance로 추가했다.
- ADR-011은 `PROPOSED — INDEPENDENT REVIEW P1-NOT-BLOCKING / AWAITING USER APPROVAL`, ADR-012는 `PROPOSED — REVISED AFTER INDEPENDENT REVIEW / AWAITING RE-REVIEW`로 유지했다. Codex가 어느 ADR도 새로 승인하지 않았다.
- 상태를 `CP3-A REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW / CP3-B NOT STARTED`로 갱신하고 자동 checkpoint 진행을 금지했다.

### Security and Scope

- documentation/contract-only 보완이며 application/test/fixture/migration/dependency/runtime config/API route/connector 변경 0
- actual credential 사용 0, actual Toss API 호출 0, account/order/WebSocket 변경 0
- CP3-B implementation, PR/main merge/tag/release 0

### Review

- independent review result: P0 0 / P1 2 / CP3-B not authorized
- 이 보완은 두 P1의 재검토를 요청하며 CP3-A 승인 또는 다음 checkpoint 승인을 선언하지 않는다.
- staged eight-file documentation set의 첫 full `scripts/test.ps1`은 exit 0이었다: backend 357/357, frontend 43/43, E2E 2/2, migration repeat/downgrade/re-upgrade, fixture second import `inserted=0`/`updated=0`/`unchanged=13`, OpenAPI, production build 2회, secret scan과 initial/final policy scan PASS.

## Unreleased — Phase 2 CP3-A Contract Checkpoint — 2026-08-24

### Added

- `plans/PHASE_02_CP3_A_CONTRACT.md`에 Security Master와 Current Price의 endpoint 역할, KR/US universe, provider staging identity, lifecycle, PriceSnapshot, source trace, hash/idempotency/revision, additive migration과 CP3-B/C/D acceptance 계약 추가
- ADR-012 `Toss provider security identity와 canonical issuer/security mapping 분리`를 `PROPOSED — AWAITING INDEPENDENT REVIEW`로 추가

### Changed

- Phase 2 실행계획을 현재 `CP1 PASS / CP2 COMPLETE / CP3-A IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW / CP3-B NOT STARTED` 상태로 정합화하면서 CP1 당시 조사 baseline과 현재 live verification matrix를 분리
- ADR-011을 `/prices timestamp=null`까지 표현하는 nullable observed time/date와 structured missing reason 계약으로 수정하되 `PROPOSED — REVISED FOR CP3-A / AWAITING INDEPENDENT REVIEW` 유지
- actual OAuth/stocks/success rate header만 `[LIVE_VERIFIED]`, `/stocks/all`, `/prices`, natural 429/5xx와 CP3 semantics/freshness는 `[LIVE_UNVERIFIED]`로 유지
- issuer identity, timestamp-null source semantics와 기존 source-record natural-key/revision 충돌을 Known Issues에 추가·갱신

### Security

- CP3-A는 문서·계약 checkpoint로 application/test/fixture/migration/dependency/runtime config/API route/connector 변경 0
- actual credential 조회·사용 0, actual Toss API 호출 0, account/order/WebSocket 변경 0, secret artifact 0
- CP3-B/C/D application implementation, PR/main merge/tag/release를 수행하지 않음

### QA

- current environment: PowerShell 7.6.4(최소 7.4.0 이상, previous final QA reference 7.6.5와의 accepted variance), Python 3.13.15, Node 24.19.0, npm 11.17.0, ASCII-only path
- 최종 staged documentation 기준 `scripts/test.ps1` exit code 0: backend 357/357, frontend 43/43, E2E 2/2, migration repeat/downgrade/re-upgrade, fixture 2차 import `inserted=0`/`updated=0`/`unchanged=13`, OpenAPI check, production build 2회, secret scan, initial/final policy scan PASS
- Toss preflight default와 SelfTest는 각각 external network requests 0이었고 default credential usage도 0
- 실패 이력 1: 첫 full run은 pre-existing orphaned workspace dev listeners가 3000/8000을 점유해 E2E 시작에서 exit 1이었다. 동일 repository command line을 확인한 exact process tree만 종료하고 포트 availability를 검증했다.
- 실패 이력 2: 두 번째 full run은 E2E 2/2 뒤 unstaged documentation 때문에 secret scan의 index/working-tree equality gate에서 exit 1이었다. scanner 예외를 추가하지 않고 허용 문서 7개만 stage한 뒤 전체 suite를 처음부터 재실행했다.

### Limitations

- CP3-A는 `PASS`, `APPROVED` 또는 `COMPLETE`가 아니다. ADR-011/ADR-012와 exact provider enum/identity/migration 결정은 GPT independent review와 사용자 승인을 기다린다.
- CP3-B는 `NOT STARTED`이며 자동으로 진행하지 않는다.

## Unreleased — Phase 2 CP2 Final Closeout — 2026-08-24

### Changed

- CP2-A~D final integrated QA를 완료하고 상태를 `CP2 COMPLETE / Phase 2 IMPLEMENTATION IN PROGRESS / CP3 NOT STARTED`로 갱신
- ADR-010을 `ACCEPTED`로 전환하고 exact REST allowlist, memory-only token, bounded retry, offline/live 분리 결정을 확정
- actual live 검증과 미검증 범위를 분리해 OAuth·stocks·성공 rate header만 `[LIVE_VERIFIED]`로 재분류
- Windows non-ASCII repository parent path의 setuptools editable build 실패를 `P2 DEFERRED / ENVIRONMENT CONSTRAINT`로 기록

### QA

- CP2-D2 사용자 독립 one-shot: provider drift `NO`, OpenAPI `3.1.0`, provider `1.2.14`, actual OAuth와 `GET /api/v1/stocks` PASS, allowed-IP 실행 경로와 Limit/Remaining/Reset header 유효성 PASS
- natural 429를 유도하지 않아 `Retry-After`는 `[LIVE_UNVERIFIED]` 유지; actual 429/5xx, production retry timing과 다른 market endpoint도 미검증 유지
- Vitest UTF-8 byte-safe exact 43 inventory 구현 commit `411749e171a717b3060973cb7b127fb94f592bab`
- ASCII-only 사용자 QA 환경 PowerShell 7.6.5, Python 3.13.15, Node 24.19.0, npm 11.17.0에서 backend 357/357, frontend 43/43, E2E 2/2, migration, fixture idempotency, OpenAPI, production build, secret scan, initial/final policy scan과 exit 0 확인

### Security

- closeout에서 live API를 재호출하거나 credential을 재사용·요청하지 않았고, actual credential 값·token·body·raw header 값을 문서·Git·QA evidence에 기록하지 않음
- P0 0, P1 0, unresolved functional P2 0; Windows path portability P2 1건은 workaround와 함께 명시적으로 이월

### Limitations

- CP2 완료는 Phase 2 완료가 아니다. CP3 이후 security master/current price, normalization, storage, freshness와 나머지 endpoint 구현은 시작하지 않았다.

## Unreleased — Phase 2 CP2-D1 — 2026-08-23

### Added

- `scripts/toss-live-preflight.ps1`의 safe default, offline `-SelfTest`, `-Live` + `-ConfirmReadOnly` + exact ACK three-way gate
- exact canonical OpenAPI runtime drift gate와 environment-only credential contract를 실행하는 internal Python runner/helper
- canonical OpenAPI GET 최대 1회, OAuth POST 최대 1회, `GET /api/v1/stocks` 최대 1회의 one-shot request budget
- OAuth/market 401·403·429·5xx, redirect, drift, safe output/redaction과 request count를 검증하는 MockTransport backend 테스트 36개

### Changed

- backend inventory를 321개에서 357개로 확대하고 standard `scripts/test.ps1`에 default와 offline SelfTest만 포함
- Toss connector source allowlist를 internal-only `preflight.py` exact filename까지 확대하고 control-plane manifest digest를 고정
- production retry/401 refresh 정책은 그대로 유지하면서 live preflight 전용 경로만 retry·refresh·replay 0회로 분리

### Security

- credential은 D2에서만 기존 server-only `TOSS_CLIENT_ID`/`TOSS_CLIENT_SECRET` environment에서 읽고 CLI credential/token parameter와 `.env` loading을 제공하지 않음
- exact HTTPS origin·OpenAPI path·stocks endpoint만 허용하고 redirect 거부, TLS verification, `trust_env=False`, account/order/account header 금지를 유지
- PowerShell wrapper는 child stdout을 fixed key allowlist로 다시 필터링하고 provider body/message, raw header map, Authorization, credential, token, traceback과 private path를 출력·저장하지 않음
- D1 작업과 standard test에서 실제 credential 사용 0, OAuth POST 0, market GET 0; live evidence·DB·fixture·frontend·migration 변경 없음

### QA

- provider contract drift `NO`: OpenAPI `3.1.0`, REST API `1.2.14`, canonical SHA-256 `fccf49abd11f37f557bdd349138f4a03c42b829ebd8b5c14ab4907116fb84c7a`, exact origin 일치
- CP2-D1 baseline SHA `7437d8a30a6f2081431efee815ce96da85700f9b`, final validated implementation SHA `7840eee70ea3d4d8be9057904501ba277e68c99a`
- default `EXTERNAL_NETWORK_REQUESTS=0`, SelfTest `EXTERNAL_NETWORK_REQUESTS=0` 및 gate/schema/redaction/one-shot/drift-stop PASS
- Node.js 24.19.0에서 최종 `scripts/test.ps1` exit code 0: backend 357/357, frontend 43/43, E2E 2/2, migration, fixture idempotency, OpenAPI, build 2회, secret scan, CP2-D1 policy scan PASS
- D1 시작 전 승인된 anonymous canonical OpenAPI 문서 GET 1회만 수행했고 실제 credential, OAuth와 market business request는 수행하지 않음

### Limitations

- 실제 token issuance, 허용 IP, stocks response, rate-limit headers, provider timing, natural 429 `Retry-After`, edge/IP behavior는 계속 `[LIVE_UNVERIFIED]`다.
- CP2-D2는 `NOT STARTED`이며 CP2, CP2-D 또는 Phase 2 완료로 간주하지 않는다.

## Unreleased — Phase 2 CP2-C — 2026-08-23

### Added

- 12개 callable method/path를 7개 runtime group에 exact 매핑하는 `rate_limit.py`
- client×group shared async token bucket과 documented/observed/effective limit 분리
- 네 rate header만 읽는 strict integer parser와 memory-only missing/invalid/inconsistent diagnostic
- 총 3회 시도, 단일·누적 30초 상한, 1→2→4초 backoff와 bounded additive jitter timing primitive
- bounded 429 및 exact `500/502/503/504` retry, safe exhaustion/deferred typed error
- fake monotonic/sleeper/jitter와 `httpx.MockTransport` 기반 CP2-C backend 테스트 65개
- 429 Reset acquire wait와 backoff의 통합 누적 ceiling을 검증하는 deterministic backend 회귀 4개

### Changed

- OAuth `/oauth2/token`을 shared `AUTH` limiter와 같은 bounded retry policy에 연결
- market GET의 401 generation-aware refresh/replay는 1회를 유지하면서 rate retry budget을 분리
- Toss connector source allowlist를 exact 7개 Python 파일로 고정하고 backend inventory를 252개에서 317개로 확대
- 독립 검토 P2 수정으로 429 이후 재시도의 limiter acquire wait를 같은 operation `_RetryBudget`에 포함하고 backend inventory를 321개로 확대
- missing/invalid `Retry-After`에서 유효한 Reset이 잔여 single/cumulative budget을 넘으면 대기를 자르지 않고 즉시 safe deferred error로 종료

### Security

- public token manager/lease/raw bearer surface 없이 token을 connector-private memory에 유지
- response header 전체를 저장하지 않고 `X-RateLimit-Limit`, `Remaining`, `Reset`, `Retry-After`만 숫자로 관찰
- provider body/message, Authorization, Cookie, Set-Cookie, credential과 uncontrolled URL을 rate state/error에 보존하지 않음
- 400/401 규칙 외 auth error/403/404/422/501/contract/transport/boundary error는 retry하지 않음
- actual credential, actual Toss request, account/order surface와 CP2-D live script를 추가하지 않음

### QA

- provider contract drift `NO`: OpenAPI `3.1.0`, REST API `1.2.14`, canonical SHA-256 `fccf49abd11f37f557bdd349138f4a03c42b829ebd8b5c14ab4907116fb84c7a`
- implementation commit `e0017a1891b8f7048c5dc97565224749cf287989`
- P2 cumulative-wait hardening implementation commit `fe65076021f2cc9b3c8d533c3e844b9b9699d5b9`
- Node.js 24.19.0, npm 11.17.0에서 최종 `scripts/test.ps1` exit code 0
- backend 321/321, frontend 43/43, E2E 2/2, migration, fixture idempotency, OpenAPI, build 2회, secret scan, CP2-C policy scan PASS
- standard test outbound network 0; retry constants와 무관하게 connector target 144개가 약 1초에 완료

### Limitations

- 실제 OAuth/token, 허용 IP, runtime rate header·Retry-After, provider response/error와 timing은 계속 `[LIVE_UNVERIFIED]`다.
- CP2-D live preflight는 `NOT STARTED`이며 `scripts/toss-live-preflight.ps1`을 만들지 않았다.
- CP2-C PASS는 CP2 또는 Phase 2 완료를 의미하지 않는다.

## Phase 2 CP2-B — 2026-08-23

### Added

- strict OAuth token/error 모델과 backend application-owned single token manager
- memory-only token lease, monotonic expiry, bounded safety margin, explicit·generation-aware invalidation
- exact Toss origin과 enum 기반 11개 market GET path만 노출하는 `httpx.AsyncClient` transport
- streaming response ceiling(OAuth 64 KiB, market JSON 32 MiB), content-type/JSON/redirect 안전 검사
- CP2-B auth·boundary·integration·concurrency 테스트 75개

### Changed

- Toss connector source allowlist를 CP2-B의 exact 6개 Python 파일로 발전
- backend inventory를 176개에서 251개로 확대하고 통합 gate 기대값을 갱신
- ADR-010은 `PROPOSED`를 유지하면서 CP2-A/CP2-B 구현 진행 메모를 추가

### Security

- `trust_env=False`, `follow_redirects=False`, TLS verification 고정과 connect/read/write/pool timeout을 적용
- 외부 arbitrary URL/method/header API 없이 POST는 내부 `/oauth2/token` 하나로 제한
- symbol traversal/scheme injection과 raw query string, unknown query key/value를 fail closed
- market GET Authorization을 transport 내부에서만 구성하고 token POST·query·Cookie에 전달하지 않음
- 401 `expired-token`/`invalid-token`만 generation-aware invalidate 후 최대 한 번 재발급·replay
- provider body/message, credential, token을 exception/log/raw/DB/QA evidence에 저장하지 않음

### QA

- provider contract drift `NO`: REST API `1.2.14`, canonical SHA-256 `fccf49abd11f37f557bdd349138f4a03c42b829ebd8b5c14ab4907116fb84c7a`
- implementation commit `6a823edc6b3e02cf1c06778f26045f7c535066ed`
- Node.js 24.19.0, npm 11.17.0에서 최종 `scripts/test.ps1` exit code 0
- backend 251/251, frontend 43/43, E2E 2/2, migration, fixture idempotency, OpenAPI, build 2회, secret scan, CP2-B policy scan PASS
- standard test outbound network 0; 모든 Toss connector test는 합성 credential과 `httpx.MockTransport` 사용

### Limitations

- 실제 credential, token endpoint, market endpoint는 호출하지 않아 live OAuth·허용 IP·response/rate header는 계속 `[LIVE_UNVERIFIED]`다.
- CP2-C rate limiter·429/5xx retry와 CP2-D live preflight는 시작하지 않았다.

## Phase 2 CP2-A — 2026-08-23

### Added

- 실제 transport 없이 `services/api/src/toss_dashboard_api/connectors/toss` 전용 namespace scaffold
- optional server-only `TOSS_CLIENT_ID`, `TOSS_CLIENT_SECRET` secret-aware 설정과 빈 `.env.example` 항목
- exact Toss origin·12개 callable endpoint/rate metadata·connector 경로 정책 데이터
- HTTP import, frontend direct Toss, 계좌·주문 endpoint, account header, generic connector와 공개 credential 환경변수 negative canary

### Changed

- `httpx==0.28.1`을 exact runtime dependency로 승격하고 source/runtime 위치·version·lock hash 검증을 강화
- backend test inventory를 172개에서 176개로 확대
- CP2의 범위를 바꾸지 않고 CP2-A부터 CP2-D까지의 실행 순서를 계획에 명시

### Security

- `httpx` import 허용 가능 위치를 Toss backend connector namespace 하나로 제한
- `Authorization`, Bearer, client ID/secret, access token, cookie, set-cookie redaction 보강
- Toss/client secret assignment와 Authorization Bearer 합성 카나리를 secret scan에서 거부
- `.env`, `.env.local`, `.env.*.local`과 동등한 ignore 규칙을 검증하고 실제 credential·`.env` 파일을 추가하지 않음
- 계좌·보유·주문·구매가능금액·매도가능수량·수수료·조건주문 surface와 `X-Tossinvest-Account`를 runtime에서 계속 금지

### QA

- provider contract drift `NO`: REST API `1.2.14`, canonical SHA-256 `fccf49abd11f37f557bdd349138f4a03c42b829ebd8b5c14ab4907116fb84c7a`
- Node.js 24.19.0, npm 11.17.0에서 통합 `scripts/test.ps1` exit code 0
- backend 176/176, frontend 43/43, E2E 2/2, migration, fixture idempotency, OpenAPI drift, build 2회, secret scan, policy scan PASS
- validated implementation commit: `e1bca561998d745bb357dc8c92f835926886e770`

### Limitations

- CP2-A는 CP2 전체 완료가 아니다. OAuth/token manager, HTTP request, rate limit/retry, live preflight는 CP2-B 이후 범위이며 시작하지 않았다.
- `requirements.in`과 `requirements.lock`은 baseline부터 `httpx==0.28.1`과 승인 hash를 포함해 파일 내용 변경이 필요하지 않았다.

## 0.1.0 — 2026-08-22

### Added

- FastAPI/Pydantic 기반 Phase 1 로컬 fixture API와 안전한 오류 envelope
- SQLite metadata migration, 읽기 전용 fixture repository와 멱등 import audit
- 합성 KR/US issuer·security, 가격·수급·재무·기관 보유·공시 diff·가치평가·데이터 품질·analysis packet fixture
- Next.js/TypeScript Company 및 Data Quality 읽기 전용 화면과 loading/empty/error/not-found 상태
- OpenAPI snapshot과 `openapi-typescript` 생성 타입 drift 검사
- Windows PowerShell setup/dev/build/test/migrate/import/E2E/secret/policy 스크립트
- localhost·외부 네트워크·프로세스 소유권·브라우저 transport·테스트 inventory fail-closed gate
- Phase 1 샘플 API JSON, 실행 로그와 Playwright 화면 증거

### Changed

- ADR-005부터 ADR-008까지 Phase 1 계약·식별자·저장 경계·로컬 fail-closed 결정을 `ACCEPTED`로 기록
- Windows Node.js 지원 하한을 24.16.0으로 올리고 `.node-version`을 24.19.0으로 고정하는 ADR-009를 `PROPOSED`로 추가
- 모든 주요 PowerShell 진입점이 정확한 Node/npm 실행 파일과 상속 `NODE_OPTIONS`를 작업 전에 검증하도록 강화
- 최종 테스트 inventory를 backend 172개, frontend 43개, E2E 2개로 확대·고정
- 프로젝트 상태를 Phase 1 완료·독립 QA PASS로 갱신

### Fixed

- Node.js 24.15.0의 Windows TCP 네이티브 충돌을 지원 버전 사전검사로 회피
- E2E frontend 기동을 검증된 정확한 `npm.cmd` 경로로 고정
- Node engine 변경 뒤 이전 값에 남아 있던 비밀정보 스캐너의 `package-lock.json` 승인 digest를 현재 추적 잠금 파일과 동기화

### Security

- FastAPI와 Next.js를 127.0.0.1 전용으로 제한하고 정확한 host/CORS allowlist 적용
- 실제 키·계좌·주문·OpenAI·외부 데이터 connector를 구현하지 않음
- source, 브라우저 bundle, QA artifact와 로그를 비밀정보 검사 범위에 포함
- destructive migration downgrade를 명시적 disposable DB 경로와 확인 플래그로 제한
- Python/Node의 non-loopback 연결과 브라우저의 비허용 요청을 테스트에서 차단·수집

### QA

- 구현 기준 commit: `f358fa3f0d1af44d0348bc5ba5c48be7866d7b21`
- 최종 독립 검증 commit: `57b2a63ead06d03191d8094e1689b8d2ab3d7764`
- PR #1을 merge commit `b1829a7375704271a21267e1fcf62808147be593`으로 `main`에 병합
- Phase 1 release baseline annotated tag: `v0.1.0`
- Node.js 24.19.0, npm 11.17.0에서 setup 2회와 개발 서버 smoke 통과
- backend pytest 172개, frontend Vitest 43개(10 files), Playwright 2개 통과
- Ruff/ESLint, mypy 40 files, TypeScript, process cleanup canary 20회 통과
- migration 왕복, fixture 멱등성, OpenAPI drift, Next build, secret scan, policy scan 통과
- 최종 통합 실행은 secret scan 직전까지 기존 로그를 회수하고, stale lock digest 수정 후 실패한 보안·정책 게이트만 별도로 재검증해 중복 실행을 피함

### Limitations

- 모든 회사·시장·공시·기관 데이터는 합성 fixture이며 실제 투자 데이터가 아님
- 실제 Toss/OpenDART/SEC/news/macro 연결, 계좌, 주문, 자동매매, OpenAI API는 비범위
- ADR-009는 계속 `PROPOSED`이며, Phase 2 전용 상세 실행계획은 아직 작성되지 않음

## 0.1.0-docs — 2026-08-16

### Added

- 전체 단계별 구현계획
- 제품 요구사항
- 아키텍처와 데이터 계약
- SEC 13F·DART 지분공시 기반 기관 포지션 사양
- 가치평가, 공시 문장 비교, 매크로 영향 사양
- 자산제곱 후속 인터페이스
- 보안·운영 원칙
- Phase별 승인 기준
- Codex `/plan`, `/goal`, 독립 리뷰 프롬프트
- QA 템플릿

### Security

- 실제 주문 기능 비범위
- OpenAI API 비사용
- 시크릿 서버 전용
- 로컬 읽기 전용 우선
