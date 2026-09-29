# CP3-C2-C additive 0008 implementation self-QA

## Current integration and closeout result — 2026-09-30

Status: **0008 Security Authority Foundation — PASS WITH ISSUES — CLOSED**. This is the additive foundation checkpoint only; it does not close CP3-C2-C or Phase 2.

### Accepted independent review

The exact candidate `0c4702c8bffa58675a5d1b0b9f1b77ca25beb8e4` (tree `64132bf753e680eae9d47252e45859d129d01f7f`) received `PASS WITH ISSUES`: Critical `0`, Major `0`, required code/schema fixes `0`, unauthorized changes `0`, regression found `0`. The user accepted that result. CP3-C2-C1 architecture/design remains `PASS WITH ISSUES — CLOSED`; ADR-020 remains `ACCEPTED`.

### Integration proof

- Integration branch: `feature/phase-02-toss`.
- Merge: `88dcb1e49551069b8e986c35185d9bcced89d4e5`.
- Parent 1: `6c0ed087106d0fdb94615b74a9472df17be08706`.
- Parent 2: `0c4702c8bffa58675a5d1b0b9f1b77ca25beb8e4`.
- Merge tree: `64132bf753e680eae9d47252e45859d129d01f7f`, identical to the reviewed candidate tree.
- At merge time, implementation/schema/test/scanner changes after the candidate were `0`.

### Final Windows QA evidence carried from the reviewed candidate

The Windows standard `scripts/test.ps1` run restarted from the first gate and exited `0`, reaching the final completion marker. Results: backend `1246 passed, 0 failed, 0 skipped, 0 xfail, 0 deselected`; frontend unit `10` test files and `43` tests passed; E2E `2 passed`; Ruff, format (`129` files already formatted), MyPy (`71` source files, no issues), frontend lint/typecheck/build, API contract, migration repeat/downgrade/re-upgrade, fixture idempotency, final secret scan and final policy scan all exited `0`. The earlier backend exit `1` without summary/traceback remains historical; the exact unchanged command passed, followed by the complete successful rerun. This integration closeout did not rerun the full suite.

### Non-blocking review qualifications

- **Issue A — resolved in current docs:** the reviewed candidate's current-state documents still displayed historical `FINAL QA BLOCKED — STOP` after full QA passed. This closeout updates current-state sections and leaves all dated STOP/failure evidence intact.
- **Issue B — review-package completeness:** the final review ZIP duplicated the bounded-remediation request in the slot intended for the original implementation request. Review remained possible because the original request was in the conversation and the accepted C1 contract/repository sources were included. This is not a code/schema defect; the prior ZIP remains preserved.

### Current boundaries

CP3-C2-C2 Machine Security Authority Engine is the next planned checkpoint and is not started; it must be its own implementation task. Under the new root `AGENTS.md`, no additional user approval is needed merely to begin that planned checkpoint. CP3-C2-C3 Human WebAuthn/final mapping and CP3-D remain not started; Phase 2 remains in progress. C2 evaluation, C3 disposition runtime, mixed-counter runtime, B-writer safety cascade, Security-head reader migration, live/current KRX/SEC/primary-exchange contracts and production Security mapping remain **NOT VERIFIED**. No main merge, deployment, production DB write or live authority call occurred.

---

## Historical pre-final remediation and STOP evidence — 2026-09-29

Status: **FINAL QA BLOCKED — STOP**. Maximum successful handoff remains `0008 IMPLEMENTED — GPT FINAL INDEPENDENT VERIFICATION REQUIRED`.

Final Linux/WSL focused 125 and Windows regression 482 passed. Full Windows standard attempt 02 failed: backend 1245 passed / 1 failed, exit 1, 1711.74 seconds. The unchanged existing runtime logging test failed before receiving /health; two targeted diagnostic runs reproduced 1 failed / 1 passed, and the second captured child process exit 3. Root cause of startup termination remains NOT VERIFIED. No timeout/assertion/runtime/scanner change was made. Later full-QA gates, final secret/policy, commit and push were not executed. No independent PASS/CLOSED or next checkpoint is authorized.

Entry verification matched all 369 candidate files to the preserved STOP ZIP, exact base/branch and empty primary index. The original STOP report is preserved separately in the review package. This section supersedes the initial STOP status only within the explicitly authorized remediation; historical evidence below remains unchanged.

### Changes and authority boundary

M1: the Python contract and raw-SQL CHECKs allow only the already accepted B schemes (`https`, `authority-verification`, isolated `fixture`). The concrete locator suffix begins with ASCII alphanumeric and continues with ASCII alphanumeric or `._~/-`, maximum total length 2048. This conservatively excludes wildcard/pattern syntax, HTTP/unknown schemes, credentials, query/fragment, escapes and control characters. Fixture locators require non-production TEST_ONLY/TEST_ISOLATED_ONLY policy with permanent fixture/test taint and ZERO weight. This is representability validation, not new external-source admission. Current source access/license review is still a future C2 requirement; CGS remains blocked and the repository production-admission guard is unchanged.

Minor-01: source_namespace/document_kind share `[A-Z][A-Z0-9_]{0,127}` in all three contracts and matching CHECKs in all three tables. Existing DDL's uppercase set is tightened for first letter and the contract's 128-character bound, not loosened. SQLite's NUL-terminated length/GLOB behavior is addressed with explicit `instr(value,char(0))=0`.

M2: verified unchanged STOP scanner size 249357 and SHA-256 `b312ef430496a6cfa53c383a92173c3bf9d879456cd5e7f7552b26566ae6c6f5`, then updated the exact policy pin from base hash `0823d1d6d834d2dc83204d9c9ee2ecf19d27b8b5e56ab85149141617546ff1f4`. Every scanner difference from base is reproduced by seven fixed inventory literal substitutions on six lines; no other scanner difference exists. The control manifest excludes policy-scan.ps1. Its new digest is independently required by the added test module and test inventory edits, not by the pin update.

### Historical verification before final Windows QA

- New policy matrix first attempt: 57 passed, one raw-SQL NUL locator rejection failed. The failure was preserved. An explicit SQL NUL guard and two token NUL cases were added; no test was weakened.
- Final collection: focused 125 (65 existing + 60 remediation), backend 1246. Frontend 43 and E2E 2 remain required.
- Ruff check passed; official formatting scope: 129 files already formatted.
- Historical first remediation focused run, before the fixture correction: 125 passed in 369.95 seconds, exit 0; failed/skipped/xfail/deselected all 0. Includes all five Security suites and fresh migration lifecycle tests.
- Historical first remediation Windows regression run, before the fixture correction: 482 passed in 1019.37s (0:16:59), exit 0; failed/skipped/xfail/deselected all 0. Covers the original 480 cases plus both metadata repository cases; the historical 479+1 is retained below.
- First remediation full standard attempt: intentionally interrupted during backend progress 28%, before secret scan, after static review identified a dummy credential-URI fixture matching BasicAuthDetector. Initial policy/Ruff/mypy/frontend lint/typecheck/runtime checks had passed. This is an interrupted run, not a completed full QA or scanner/policy failure.
- The fixture now uses an explicit synthetic placeholder; the credential-URI rejection assertion and all 60 cases remain. No scanner/filter/exception changes. This is the second bounded ordinary correction (after the SQLite NUL guard), with all original evidence retained.
- Final Linux/WSL focused rerun after fixture correction: 125 passed in 352.68 seconds, exit 0; failed/skipped/xfail/deselected all 0.
- Final Windows regression rerun after fixture correction: 482 passed in 967.30s (0:16:07), exit 0; failed/skipped/xfail/deselected all 0.
- Final Windows standard full QA attempt 02 from the beginning: exit 1; 1 failed, 1245 passed in 1711.74s (0:28:31). Existing runtime logging test health_response was None; targeted diagnostics reproduced the failure and observed child startup exit 3. Root cause remains NOT VERIFIED.
- Final secret/policy: NOT EXECUTED. Initial policy passed in attempt 02; full execution stopped during backend. Frontend unit/build, API contract, migration/idempotency/E2E and end-of-run scanners were not reached. Focused migration tests passed separately; they do not replace the official full gate.
- Final frozen/scope proofs: 28 frozen files byte-identical to base; 23 authorized candidate paths. Primary index remains empty; HEAD remains approved base; no commit/push. Final report-only edits were not scanner-verified because full QA failed.

The later source/runtime/production limitations from the original report remain unchanged. Initial successful test counts and the 479+1 failure are historical, not substitutes for the required final reruns.

### Final candidate path scope

| Path | Authorized category |
|---|---|
| `CHANGELOG.md` | documentation / QA evidence |
| `DECISIONS.md` | documentation / QA evidence |
| `KNOWN_ISSUES.md` | documentation / QA evidence |
| `STATUS.md` | documentation / QA evidence |
| `plans/PHASE_02_EXECUTION_PLAN.md` | documentation / QA evidence |
| `qa/PHASE_02_CP3_C2_C_0008_SELF_QA.md` | documentation / QA evidence |
| `scripts/policy-scan.ps1` | authorized policy scanner raw pin synchronization; required test/control inventory |
| `scripts/secret-scan.ps1` | authorized exact scanner inventory synchronization |
| `scripts/test.ps1` | planned 0008 tests; exact suite inventory |
| `services/api/alembic/versions/0008_phase_02_cp3_c2_c_security_authority.py` | planned 0008 contract/schema |
| `services/api/src/toss_dashboard_api/contracts/security_authority.py` | planned 0008 contract/schema |
| `services/api/src/toss_dashboard_api/repositories/security_authority.py` | planned 0008 ORM/storage |
| `services/api/src/toss_dashboard_api/repositories/sqlite.py` | authorized revision-mask compatibility update |
| `services/api/src/toss_dashboard_api/storage/security_authority_models.py` | planned 0008 ORM/storage |
| `tests/backend/security_authority_test_support.py` | planned 0008 tests; exact suite inventory |
| `tests/backend/test_migrations.py` | planned 0008 tests; exact suite inventory |
| `tests/backend/test_provider_migration.py` | planned 0008 tests; exact suite inventory |
| `tests/backend/test_repositories.py` | planned 0008 tests; exact suite inventory |
| `tests/backend/test_security_authority_contracts.py` | planned 0008 tests; exact suite inventory |
| `tests/backend/test_security_authority_migration.py` | planned 0008 tests; exact suite inventory |
| `tests/backend/test_security_authority_relations.py` | planned 0008 tests; exact suite inventory |
| `tests/backend/test_security_authority_repository.py` | planned 0008 tests; exact suite inventory |
| `tests/backend/test_security_authority_source_policy.py` | planned 0008 tests; exact suite inventory |


## Preserved initial STOP self-QA

Status: FINAL QA BLOCKED — STOP. This is not independent acceptance or C2/C3 authorization.

## Identity and routing

- Exact base: `6c0ed087106d0fdb94615b74a9472df17be08706`; base tree: `af8a9d1fceb491478c4f0d5dd4a3f7e1c272a01c`.
- Branch: `feature/phase-02-c2c-0008-security-authority`; isolated managed worktree `security-authority-0008/tosstoss`.
- Local CLI execution in WSL; Windows native subprocess QA for the existing supported suite and OWNER cases. Computer Use and nested Codex CLI were not used. No delegation.
- No original checkout branch switch, reset, clean, stash, or replacement of protected evidence. Four original untracked R1 CSVs remain in the original checkout.
- The disposable Windows clone has the candidate source bytes and a matching validation index because the standard scanner checks index/worktree agreement. This is separate from staging the primary implementation candidate, which is gated on final QA success.

## Implemented scope

- Separate closed Security contracts, enums, canonical serialization and hash domains; no widening of frozen B/reviewer types.
- KR issuer plus checksum-validated ISIN anchor; US issuer plus exact SEC registered-class document/row identity. Ticker and display names are absent from canonical identity.
- Static additive 0008: 23 tables, 20 indexes (including two exact parent indexes), 61 triggers. Existing migrations 0001–0007 remain byte-identical to base.
- Composite binding of evidence, applications, bundle membership, claims, decisions, challenge/consumption/authentication, approvals, pairs, profiles, links and heads. Conflicting identifiers and classifications remain representable.
- Immutable historical tables; only the current Security head supports a direct successor/state-hash guarded update. No head deletion or predecessor forks.
- M1: consumption and successful authentication have no approval/link FK dependency. Tests commit them after rolling back subject/profile/event/link work in a SAVEPOINT.
- M2: separate old A and successor B identities, approvals, authentication records and links; full pair binding and deferred pair/event/link references; partial pairs fail and business rollback preserves both terminal authentications.
- M3: shared principal/credential references and COUNTER_SUPPORTED/NO_USABLE_COUNTER consistency; no Security-owned credential cursor and no R1 runtime modification.
- B current-head update/delete protection while an approved dependent Security head exists. Provider-scoped and issuer-wide SQL fixtures check fail-closed behavior and ordered safety transitions.
- Empty C-ledger downgrade removes only 0008 objects; any C history rejects downgrade. Existing nonempty fixture and B/R1 rows survive upgrade and empty-C downgrade; repeated current upgrade and re-upgrade preserve schema/data.
- Low-level immutable repository supports idempotent storage/reading and conflicting claim history. Production admission, READY evaluation, and positive authority/runtime writes are not public repository APIs.
- Existing-source adjustment is the internal additive revision mask only. Existing tests have exact head/table/index inventory updates. QA controls have exact suite/file/cache inventory synchronization only.

## D0 and frozen-source audit

D0 inspected actual 0007 parents and required keys with foreign keys enabled. The additive unique indexes are `uq_0008_issuer_link_binding` on the exact issuer-link tuple and `uq_0008_provider_observation_binding` on observation/provider identity. Both were created successfully on a disposable migrated database; foreign-key check returned no violations. No table rebuild or frozen migration edit was needed.

The evidence package contains D0 parent inventory, entry source inventory and final byte comparisons. Final proof currently covers 28 upstream files, including all seven old migrations, reviewer security/runtime, issuer engine/repository/contracts, and legacy models. The permitted revision-mask addition is classified separately.

The existing B engine conservatively rejects a second provider with the same issuer identifier. The issuer-wide SQL guard test therefore constructs a synthetic full parent graph with all FKs/triggers enabled. It proves schema guard behavior, not real B runtime admission of that scenario. The B engine remains unchanged.

## Verification evidence

- Focused new suites: 65 passed, exit 0, 310.01 seconds; no skipped/xfail/deselected cases.
- Strengthened nonempty migration preservation and M1 rollback plus affected legacy revision suites: 18 passed, exit 0, 84.73 seconds.
- Relevant regression first run: 479 passed, one failed, exit 1, 1611.63 seconds. The only failure was the already-loaded old head revision expectation in test_blank_database_upgrades_to_cp3_head. Its corrected module passed in the 18-case follow-up above. No other regression failure occurred; the subsequent native full run was blocked before the full candidate suite.
- Windows candidate mypy: success, 71 source files. Baseline: 68 source files. Cache metadata 855 to 858: exactly the three new production modules, no removals.
- Official Ruff source/test scope: all checks passed and 128 files already formatted. New migration checked separately: one file already formatted.
- A supplemental broader formatting command included old migrations and reported frozen 0006 as needing formatting. It is outside the standard lint script's format scope; the old file was preserved. This diagnostic is retained and is not represented as a passing check.
- Collection: 1,186 backend tests (1,121 existing plus 65 new); frontend 43 and E2E 2 remain required. Policy control files: 91 to 96; original digest reproduced before calculating the new digest. Scanner metadata/findings/proofs inventory derives from the measured three-module cache addition; detector semantics and exceptions are unchanged.
- Windows repository-standard full QA attempt 1: exit 1, 2026-09-29T04:28:09.8013923Z to 04:28:15.9206973Z. The initial policy gate failed: `The fixed cache-tag provenance scanner raw-byte pin does not match.` No randomized scanner self-canary failed; the unchanged-rerun exception does not apply.
- Read-only diagnosis: the policy pins the complete raw scanner snapshot (249357 bytes; base SHA-256 `0823d1d6d834d2dc83204d9c9ee2ecf19d27b8b5e56ab85149141617546ff1f4`). The six numeric inventory line changes preserve byte length but produce SHA-256 `b312ef430496a6cfa53c383a92173c3bf9d879456cd5e7f7552b26566ae6c6f5`. The separate raw-byte pin was not synchronized before the first final QA attempt. It remains unchanged after failure.
- Per user implementation instruction section 43, any other scanner/policy failure requires `FINAL QA BLOCKED — STOP`. No pin repair, threshold/exception change, rerun, primary candidate staging, commit or push followed the failure. Only read-only diagnosis and STOP handoff documentation/package preparation followed.
- The full native backend/frontend/unit/build/E2E/migration/idempotency/secret-scan/final-policy gates were NOT COMPLETED by this invocation. Earlier focused, affected-regression and standalone type/format results remain narrower evidence. Final handoff documentation was updated after STOP and was not scan-verified.

## Repairs and retained failures

All earlier attempts remain outside the repository in the evidence directories. New-contract principal/credential validation, fixture uniqueness, formatting and type annotations received bounded corrections. The first relevant regression run loaded the old 0007 revision expectation; the expectation was synchronized to 0008 and the affected suites passed separately. No test was removed, skipped, xfailed, deselected or weakened to conceal failure. Existing fixtures/frozen source were not altered for the new relational scenarios.

## Global invariants and production effects

`TRADING_ENABLED=false`, `DRY_RUN=true`, `LOCAL_ONLY=true`. No OpenAI API, paid data API, broker order, production mapping, live source collection, external authority API, public listener, reviewer UI or current-reader migration was introduced. Canonical/approval/link examples are disposable SQL test fixtures only. No production database was migrated.

## NOT VERIFIED and verdict ceiling

C2 machine engine; C3 actual WebAuthn/human disposition; live/production source eligibility; production VERIFIED mapping; R1 mixed issuer/Security counter runtime; B-writer runtime cascade; current-reader consumption of Security heads; physical remote-volume/missing-ACL OWNER scenarios beyond the unchanged suite; and later CP3-D/Phase 2 completion remain unverified or unauthorized. SQL rollback and counter constraints do not prove future runtime transaction/counter integration.

This candidate has not met the final gate and must not be called implemented-complete or PASS. The maximum successful implementation handoff, if separately authorized remediation later passes, is `0008 IMPLEMENTED — GPT FINAL INDEPENDENT VERIFICATION REQUIRED`. No local result closes C2/C3, R1, CP3-C2 or Phase 2. CP3-C2-B and C1 retain their accepted PASS WITH ISSUES — CLOSED qualifications; ADR-020 remains ACCEPTED.
