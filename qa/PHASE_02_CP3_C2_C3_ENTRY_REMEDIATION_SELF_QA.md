# C3-entry remediation self-QA

## Current accepted review and documentation-only successor — 2026-10-03

**REVIEW ACCEPTANCE DOCUMENTED — INTEGRATION PENDING**. Controlling authority: `TOSSTOSS_C3_ENTRY_REVIEW_ACCEPTANCE_DOCS_ONLY_CODEX_PROMPT.md`, preserved under external evidence root `/home/beomooo/.codex/task-evidence/tosstoss-c3-entry-review-acceptance-20261003T052338Z/authority`. Its exact candidate/verdict/findings are accepted human-provided authority. A separate raw GPT report is not among the local inputs used for this task and is not a prerequisite.

- Reviewed product: `b23feb3f5640582db1ba5e9d4f4523cf78e2b494`; tree `fc273f0aa8ab64156f81ba22d4510ffa74f693a2`.
- Direct parent / previous FAIL: `fba35c8c85e82d2f6549ea9cdc8af270e8e9a7e2`; tree `0f24109aa923830688bb7fe15d4b916b189a1e25`. Its FAIL is unchanged; it was not rerun in the new 63-case verification.
- GPT bounded verdict: **PASS — USER ACCEPTED**. Critical-01 cancellation/partial rebuild/history loss and Major-01 schema/`alembic_version` commit split are **CLOSED for b23feb3...**. Required fixes 0; new Critical/Major/Minor findings 0/0/0.

### Evidence attribution

| Evidence group | Actual existing evidence and limits |
| --- | --- |
| A — Original implementer QA | Windows focused 96, external termination 2, affected 448; standard full backend 1459 / frontend 43 / E2E 2; final policy/secret reported exit 0. Historical implementation receipts, not newly executed here. |
| B — Separate verifier | Fresh native Windows unchanged supplied matrix 60/60, process termination 2/2, independently authored roundtrip 1/1: 63/63. Final three runs exit 0; failures/errors/skips 0. This is separate-verifier execution, not ChatGPT direct execution. |
| C — GPT review | Bounded review of the exact candidate and supplied execution evidence; verdict/finding closure accepted by the user through the controlling authority. GPT did not directly rerun the Windows tests. |

Separate verifier inputs: `TOSSTOSS_b23feb3_INDEPENDENT_WINDOWS_REPORT_KO.md` (SHA-256 `95c1be31c18e290ae4066a9997e8ec9a44863e22c273574b966ec42f17ebc996`) and `TOSSTOSS_b23feb3_INDEPENDENT_WINDOWS_EVIDENCE_20261003.zip` (SHA-256 `a876649703a388d2e82ed13d7dbeab999b938cc85da3d39656ef278743847618`). Read-only CRC/50-entry manifest validation and final test receipts are preserved externally. Supplied provenance records Alembic 1.16.5, SQLAlchemy 2.0.43, 48 Windows dependency pins compared, exact extracted candidate source 382 files, and unchanged source/pins/core dependency bytes in POSTFLIGHT. The existing QA mirror supplied dependencies only; tested product imports came from the extracted candidate. Initial matrix/matrix-02/matrix-03 launcher/path failures (exit 1) are preserved; no product or dependency repair was required.

Closure evidence covers normal/failing upgrade and downgrade, cancellation, real revision UPDATE abort, pre-commit/cleanup/acknowledgment failures, reopen/retry and native process termination within the selected matrix. It does not prove exhaustive fault combinations or remove synthetic-fixture/harness limitations. Full suites were not independently rerun by the separate verifier. Physical power/storage/controller/close failures, concurrent writers, future runtimes/non-SQLite backends, real WebAuthn/physical authenticator/physical OWNER qualifications, M1–M3/shared counters/cascades/readers, live completeness/licensing, NYSE/CGS authority, production/deployment, CP3-D and Trading remain NOT VERIFIED or out of scope.

### Documentation gates and current position

This task changes only STATUS, DECISIONS, KNOWN_ISSUES, CHANGELOG, the Phase 2 execution plan and this self-QA. All other 376 tracked files, including 291 non-Markdown files, retain reviewed bytes/modes. Migrations 0001–0009, Alembic env.py, runtime/contracts/registry, R1/B, tests/harnesses, scanners/acceptance settings and dependency locks are frozen. The C1 contract remains a preserved pre-acceptance snapshot; the current acceptance successors govern review status.

Only diff/allowlist/byte-mode/history/preservation checks, required Windows documentation policy/secret scans and staged review are executed. No 63-case, focused/affected/full QA, migration or new DB execution occurs. Exact commands/exits, final source/mirror/index equality, remote/clean/integration/main proofs and the new docs-only SHA/tree are external in `CLOSEOUT_REPORT.md` and `FINAL_DOCS_IDENTITY.json`. That new SHA is not the GPT-reviewed product SHA. The initial missing-attachment preflight STOP is historical and resolved by `AUTHORITY_RECEIVED.json`; its files remain unchanged. No new large review ZIP is required by authority section 9.

Review documentation: COMPLETE. Integration: PENDING — NOT PERFORMED. ADR-021: **PROPOSED / IMPLEMENTED FOR INDEPENDENT REVIEW** (review PASS accepted; integration/ADR closeout pending). Existing B/C1/ADR-020/0008/C2 closeouts are unchanged; C3 product and CP3-D are NOT STARTED; Phase 2 is IMPLEMENTATION IN PROGRESS. Next: separately authorized exact-candidate integration/ADR closeout. Earlier FAIL/STOP/QA/handoff entries below remain historical.

## Historical C3-entry migration atomicity remediation — 2026-10-03

Previous candidate `fba35c8c85e82d2f6549ea9cdc8af270e8e9a7e2`, tree `0f24109aa923830688bb7fe15d4b916b189a1e25`, received **FAIL — Critical 1 / Major 1 / Minor 0**. It must not be integrated or used for real database migration. Cancellation could lose identifier history; a revision UPDATE failure could split schema and revision commits. Prior passing QA did not cover those paths.

The new controlling remediation authority permits only correction of existing 0009, limited Alembic env.py transaction coordination, failure tests and measured inventory/docs. Alembic owns one transaction through table reconstruction and revision update. Any failed/cancelled/uncertain connection is explicitly discarded; normal completion restores foreign keys before subsequent steps. The existing 36 focused cases and prior 14 C2 counterexamples remain unchanged. New validation covers 60 repository normal/fault cases plus two external OS-termination probes in both directions. The standard runtime subprocess guard remains unchanged; termination probes run separately under the authorized external harness.

ADR-021 remains **PROPOSED / IMPLEMENTED FOR INDEPENDENT REVIEW**. Final gates and committed provenance are recorded in the external review package's `FINAL_IDENTITY.json`, `GATE_RESULTS.json` and `SELF_QA.md`; this document deliberately does not embed its own commit hash. Windows focused **96/96**, external OS-termination **2/2**, and affected regression **448/448** passed, each exit 0 with no skips. Affected coverage includes all prior C2 14 counterexamples, Windows OWNER 8 and frozen R1 core 82. The standard Windows scripts/test.ps1 then ran from the beginning and passed (exit 0): backend **1459**, frontend **43**, E2E **2**, migration roundtrip/re-upgrade, canaries, fixture/API/build checks and standard policy/secret scans. Final documentation scans and commit/push evidence are recorded in the external package. The authorized new commit is identified through FINAL_IDENTITY.json rather than a self-referential literal in this file. The maximum outcome is **CP3-C2-C3-ENTRY REMEDIATED — GPT FINAL INDEPENDENT RE-VERIFICATION REQUIRED**; no acceptance, closeout or C3 product completion is implied.

Migrations 0001–0008, root AGENTS.md, existing identifier/profile/READY semantics, registry/admission, Security anchor/security_id, R1/B and all accepted historical decisions are frozen. Fixtures are synthetic schema evidence, not real WebAuthn. Live authority/API, production DB, deployment, integration/main merge, C3 product work, cascades/cutover, CP3-D and Trading remain outside scope. Earlier STOP/FAIL/QA artifacts and protected CSVs remain preserved.

지금 하는 작업: bounded migration atomicity remediation. 완료 범위: pinned old negatives, bounded correction, Windows focused/affected/full gates. 현재 위치: remediation candidate for independent re-verification. 다음 단계: final scan/committed provenance handoff and GPT re-verification.

## Historical previous-candidate execution report (superseded by independent FAIL)

The following report describes the earlier execution state only. Its NOT CREATED and parent-only Git language is historical; fba35c8 was subsequently committed and independently rejected. It is not the current candidate identity or verdict.

# CP3-C2-C3-ENTRY Remediation — repository self-QA record

Status: CP3-C2-C3-ENTRY REMEDIATED — GPT FINAL INDEPENDENT VERIFICATION REQUIRED.

This repository report preserves the CLI verification record below. Its source snapshot had 380 files and 18 changed/new files. Adding this report produces the final 381-file candidate and 19-file diff; runtime, tests and standard runners remain byte-identical. The report is a documentation addition after successful verification, and grants no later checkpoint authority.

The final document-set policy/secret/diff results and the committed/pushed candidate SHA/tree are recorded in the final ZIP's provenance/CANDIDATE_GIT_VERIFICATION.json and provenance/FINAL_DOCUMENT_GATES.json. Git identity is finalized after those gates, rather than inserted into this report before its own commit. The pre-commit NOT CREATED field in the preserved record is historical at its recorded time.

The added changed file is qa/PHASE_02_CP3_C2_C3_ENTRY_REMEDIATION_SELF_QA.md. The record below lists the other 18 files and their scope. Earlier failed runs remain retained; no assertion, test, scanner threshold or source authority was weakened.

---

# SELF_QA — provisional remediation candidate

**CP3-C2-C3-ENTRY REMEDIATED — GPT FINAL INDEPENDENT VERIFICATION REQUIRED**

ADR-021 remains **PROPOSED / IMPLEMENTED FOR INDEPENDENT REVIEW**. ADR-020 is intact. This is execution evidence, not independent acceptance, checkpoint closeout or C3 product completion.

Base HEAD/origin: `81ef70a76b812c6cf6c4cbbcfc4a1f24b7f7ca86`; tree `5fee605a16785d58ec3a08939997c651acd95ba6`. Candidate commit SHA/tree: **NOT CREATED**. Candidate index remains at baseline. The worktree source manifest identifies the candidate; the separate QA mirror staged tree is only a byte-comparison artifact. Parent alone finalizes staging/commit/push and remote provenance.

| Actual gate | Result | Evidence |
| --- | --- | --- |
| Clean-baseline negative controls | exit 0; both old blockers reproduced | `baseline-negative-02`: four valid KR profiles mismatch old bundle hash, eight link attempts fail FK; US READY has no identifier claim. Separate fresh disposable baseline databases. |
| Final Linux focused | 36 passed, zero skipped, exit 0 | `entry-focused-final-04`; source freeze recorded. |
| Completed Linux affected | **829 passed / 8 failed, exit 1** | `affected-final-03`: seven WINDOWS_REQUIRED failures and one stale HEAD expectation. Preserved as FAIL, not converted to all-pass. |
| Bounded inventory correction | first 17 passed / 1 failed; final **24 passed, exit 0** | `affected-head-expectation-01`, `affected-revision-inventory-02`. Existing public Phase 1 revision assertion retained; only exact HEAD expectations and existing additive-revision inventory corrected. |
| Fresh pinned Windows setup/provenance | exit 0 each | Official portable PowerShell 7.6.6; Python 3.13.15, Node 24.19.0, npm 11.17.0; lock-hashed dependencies, pip check/npm tree pass; imports from dedicated mirror; bytecode disabled. |
| Windows focused | **36 passed, zero skipped, exit 0** | `windows-pathext-focused-01`; new migration/adversarial/profile/link/successor cases. |
| Windows affected | **111 passed, zero skipped, exit 0** | `windows-pathext-affected-01`; OWNER module 8, previous C2 counterexamples 14, contracts/relations/repository/migration and revision/API regression. |
| First Windows full after PATHEXT repair | **1395 passed / 4 failed, exit1** | Launcher-injected application aliases masked negative Settings inputs; preserved in windows-pathext-full-01. |
| Bounded QA environment correction | **14 passed, exit0** | Windows A/B probe proved alias masking; only QA subprocess aliases removed, effective safe defaults verified, unchanged guarded settings-security module passed. |
| Second Windows full after PATHEXT repair | **backend 1399 / frontend 43 / E2E 2 passed; overall exit 1** | Active transcript read lock blocked unchanged secret scanner; preserved in `windows-pathext-full-02`. Dependency layout and external capture corrected without scanner changes. |
| Standard Windows full from beginning | **exit 0: backend 1399, frontend 43, E2E 2** | `windows-pathext-full-03`; unchanged runner, offline/canary guards, format/lint/typecheck, migration repeat/downgrade/re-upgrade, fixture idempotency, API contract, build and scans completed. |
| Final standard policy and secret scans | **exit 0 each** | `windows-pathext-policy-01`, `windows-pathext-secret-01`, after final documentation synchronization. |

Windows focused completed before affected started; affected completed before full started. The same runtime/test bytes were used throughout. All 186 runtime/migration/test/script files still match the final freeze. After QA only six current-state documentation files changed, with their exact QA-time bytes preserved. Final source/mirror/index equality, frozen/primary preservation and diff checks are separately recorded.

The directly observed process PATHEXT was `.CPL` only. Restoring the actual Machine PATHEXT inside the dedicated QA subprocess repaired native command resolution. This environment repair changed no machine/user environment or standard runner/scanner code. Detector thresholds, security assertions, skips/xfails and canaries were not weakened. Before source freeze, the authorized measured inventory updates changed backend count 1363 to1399, control modules99 to101 and their raw-byte digest; standard gate logic was retained. All earlier native/setup/full/scan failures remain preserved; their reports are explicitly historical. No direct/.NET substitute runner was used as QA evidence. The first full run after PATHEXT repair failed four settings-security cases because the ignored launcher injected uppercase application aliases. A direct Windows A/B probe reproduced the masking and proved unsafe inputs are rejected after removing those aliases, while effective LOCAL_ONLY/TRADING_ENABLED/DRY_RUN remain true/false/true. The unchanged guarded settings module passed14/14 before full02 started. Probe01 omitted explicit aliases and failed its diagnostic before-control; probe02 correctly reproduced the original launcher and passed. Both are preserved. No product settings policy or test assertion was changed.

The second standard Windows full run passed backend 1399, frontend 43, E2E 2, migration and build checks, but finished exit 1 because the unchanged secret scanner could not read the active QA transcript. That complete failed attempt is preserved. A subsequent unchanged scanner precheck also rejected a preserved non-UTF-8 setup stderr file; its actual failure is retained, all six legacy launcher diagnostic files were byte-verified into the Linux evidence root, and the next precheck was required to pass. The bounded environment correction captures output only in the Linux evidence root, preserves private mirror evidence by verified byte-for-byte copy, and moves the same official PowerShell bytes and caches under the existing .venv dependency directory and browser assets to the existing .playwright-browsers directory. No scanner exclusions or source assertions changed; the third complete standard full run started from the beginning after the unchanged secret scan precheck.

The new 0009 preserves all historical v0.1 rows, exact application FK, keys/indexes and immutable guards; v0.2 has the exact authorized scope/kind pairs and new SEC writes bind the real existing provenance OWNER application. Upgrade, rollback, v0.1-only downgrade/re-upgrade, and fail-closed v0.2 downgrade are directly tested on Linux and Windows. 0001–0008 remain byte-identical. The shared pure AuthorityProfile constructor is used by C2 and the independently reconstructed repository READY backstop. Supporting evidence remains in bundles. Historical READY rows remain unchanged and normal reevaluation appends direct corrected successors.

KR/US positive fixtures prove exact profile content hash materialization and both link FKs in disposable databases. Authentication/approval rows are explicitly **synthetic schema fixtures, not WebAuthn evidence**. The full adversarial matrix, wrong bindings/hashes/claims, ambiguous owner claims, supporting-claim substitution and historical successor are listed in NEGATIVE_MATRIX.md and actual per-case reports.

Frozen proof covers original migrations, canonical hash/anchor/security_id and AuthorityProfile symbols, source registry/admission, R1/B code, legacy ShareClass and other untouched source. The sole metadata repository edit appends 0009 to the existing internal revision inventory; all its functions/classes remain unchanged. ADR-020 and the full baseline DECISIONS.md prefix remain intact. Primary checkout/index/four diagnostic CSVs and old STOP DECISIONS/ZIP retain their recorded hashes.

Earlier interrupted 28/119-case runs and missing completion records are not final PASS evidence. The first broad format diagnostic found frozen baseline 0006 formatting; that file was not changed and the actual standard format scope passed. All attempts retain actual commands/exits or explicit missing-completion status, with local raw-log hashes. No raw CLI/security logs, databases, credentials or generated authentication payloads are shared.

See NOT_VERIFIED.md for independent review, uncreated candidate/remote identity, actual browser/device ceremony, physical negative-adapter environment limits, C3/M1–M3/counter integration, cascade/reader cutover, live authority/production, deployment, CP3-D and Trading exclusions. See REPRODUCIBILITY.md for package limits.

지금 하는 작업: remediation handoff. 완료 범위: bounded implementation and required execution gates. 현재 위치: independent-review candidate. 다음 단계: parent provenance/commit/push and GPT final independent verification.
