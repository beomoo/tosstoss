# CP3-C2-C3-M3 Shared Counter Union — final review candidate self-QA

Status: IMPLEMENTATION AND REQUIRED QA COMPLETE.
**CP3-C2-C3-M3 SHARED COUNTER UNION CORRECTED — GPT FINAL INDEPENDENT VERIFICATION REQUIRED**. This review candidate asserts no acceptance, integration or closeout. Exact candidate SHA/tree and remote status are delivered in the external `COORDINATOR_CANDIDATE_IDENTITY.json` and `COORDINATOR_FINALIZATION_REPORT.md` under the evidence root; they are not embedded in their own commit content.
Full **C3 Human WebAuthn / Final Security Mapping is NOT IMPLEMENTED**.

## Authority and execution identity

- Authority SHA256: `21d1cafdf1341f31028d9b01aac5b9a08951b86628516ad2de797cafa172699b`.
- Base and QA-time precommit HEAD: `24586cf9f2ee10a7e40045e1acd569344f03c2d6`; base tree `7f598a84b8841a6efb578e3310123e91e910695a`.
- Branch: `codex/phase-02-c3-m3-shared-counter-union`, dedicated worktree only.
- WSL authoritative, Windows subprocess interop only. No subagents, Computer Use, nested Windows Codex, application API, production DB or live authority calls.
- LOCAL_ONLY=true, TRADING_ENABLED=false, DRY_RUN=true. Standard QA subprocesses use the repository's guarded environment and verified safe defaults; inherited application flags are cleared only there so negative settings tests remain effective.
- Evidence root: `/home/beomooo/.codex/task-evidence/tosstoss-c3-m3-shared-counter-union-20261003T112551Z`. Every gate has a timestamped complete safe log and command/exit/time JSON under `execution/`. Earlier failed attempts remain failures.
- Windows mirror: `C:\Users\beomoo\c3-m3-union-qa-20261003T112551Z`; 386 source files matched the candidate. Only this task's mirror/index was synchronized. The authoritative staged index was empty and semantically unchanged at precommit QA time. Final commit/remote identity and clean-index observations are recorded externally.
- Linux Python 3.13.1 and Windows Python 3.13.15: all 48 lockfile pins verified; no existing dependencies or versions changed. Linux import receipt resolves all 73 product/test modules to this worktree.

## Design and preservation

One forward migration, `0010_phase_02_cp3_c3_shared_counter_union.py`, verifies the exact predecessor revision, all 305 reviewer/Security schema objects and exact guard SQL. It admits and validates complete existing history before dropping a trigger. It extends every issuer input in the frozen 0007 issuer/lifecycle/bootstrap guards with the same Security UNION ALL projection and creates the symmetric Security guard from the same frozen generator. No MAX-only interpretation, +1 rule, parallel counter or fake issuer event is introduced. Existing `SIGN_COUNT_SUPPORTED` and null `NO_USABLE_COUNTER` semantics remain.

The reader adds every persisted Security authentication row without SQL filtering. AuthenticationEvent, ApprovalChallenge and ChallengeConsumption contracts, hashes, scalar/payload projections, exact binding tuple, policy, principal/OWNER/credential and single-use references must validate. The original graph algorithm then validates the union. Contradictory Security history fails closed. R1 `_counter` is AST-identical after removing only the additive Security input; `_credentials` is unchanged, including revoked/replaced history.

0010 uses native BEGIN IMMEDIATE only when SQLite has not yet started a transaction. It never commits or rolls back locally; Alembic retains revision UPDATE and outer transaction ownership. Numeric Security history refuses downgrade unchanged; safe history restores exact predecessor SQL. Reopen receipts cover both directions, four fault points, RuntimeError and KeyboardInterrupt, and actual SQLite revision UPDATE ABORT. No physical power-loss guarantee is claimed.

Required migration derivatives preserve existing behavior: add only the 0010 recognition line in `services/api/src/toss_dashboard_api/repositories/sqlite.py` to the established internal-additive-revision list so the public Phase 1 revision remains 0001; this is a required derivative, not reader cutover; update three actual-head expectations; align two old fixture setups with their stated 0009 and 5→6 contracts. Old assertions are retained. Scanner changes are only measured test-file inventory/count/digest and backend count. No scanner logic, exclusions, acceptance threshold or test semantics changed.

367 existing paths remain byte-identical, including 0001–0009, env.py, root AGENTS.md and frozen crypto/contracts. R1 graph meaning, Security anchor/profile/identifier contracts, source weights and C2 READY meaning are preserved. Frozen/scope receipts separately prove these boundaries, scanner inventory-only changes and preservation of other worktrees/old evidence.

## Executed gates

| Gate | Final observation |
|---|---|
| Old structural reproduction | Reproduced old reader=6 and truthful 7→8 DB rejection. Exit 0 means negative reproduction completed, NOT product PASS. Old import failure and harness-injected predecessor remain historical negative evidence. |
| New counter/migration Windows focus | 83 passed, 0 failures/errors/skips. Actual 5→6→7→8 uses shared reader naturally; cross-domain/negative/admission/race/lifecycle/bootstrap/null/single-use matrix included. |
| Migration reopen receipts | 25 recorded receipts: roundtrip 1, downgrade 2, corrupt history 4, four-point/two-direction/two-exception faults 16, actual revision ABORT 2. |
| Affected Linux regression | Initial 708 cases: 706 passed, 2 failed. Both fixture causes repaired; complete affected modules rerun: 4 passed and 26 passed. Issuer regression: 41 passed. Earlier failures retained. |
| Additive revision compatibility | Windows 22 passed, including unchanged API and Uvicorn tests. Linux returned 20 passed / 2 guard-environment failures because no checkout-local Linux venv; recorded guard diagnosis, no guard/test bypass. |
| Standard full Windows repository QA | **EXIT 0**; backend **1542 passed**, frontend **43 passed**, E2E **2 passed**. Format/lint/type, offline runtime guards, 20-iteration process cleanup canary, live preflight OFFLINE + SELF_TEST, exact inventory, migration repeat/downgrade/reupgrade, fixture idempotency, OpenAPI check, production build, secret and policy scanners completed. |
| Frozen and preservation proof | At precommit QA time: dedicated branch only, HEAD at exact base, staged set empty. Other worktrees, old evidence and protected data/mirrors are preserved. Candidate-stage preservation and final docs scanner receipts are recorded in the external finalization report. |

Standard full QA receipt: `20261003T142021694873Z_windows-standard-full-attempt-06.json`; log: `20261003T142021694873Z_windows-standard-full-attempt-06.log`; duration 3299.89 seconds. Full gate inventory with actual commands, exits, timestamps, logs and all failed attempts is `GATE_RESULTS.json` / `IMPLEMENTATION_READY_FOR_COORDINATOR.md` in the evidence root. `DESIGN_AND_MATRIX.md` maps authority sections 17–26/30 to named tests. `REPAIRS.md` explains every bounded repair and superseded run. The four-test health fixture experiment was reverted and is not final-source evidence.

## Remaining limits and next step

NOT VERIFIED / NOT IMPLEMENTED: physical authenticator, real user ceremony, physical production OWNER/TOKEN_USER qualification, full C3 M1, M2 SUPERSEDED, human dispositions, canonical Security promotion, B issuer cascade, C2 post-approval cascade, Security current-reader cutover, production mapping, live/current KRX/SEC or exchange completeness/licensing, NYSE production authority, CGS, CP3-D, deployment and Trading. Synthetic Security fixtures do not establish physical authenticator or production OWNER claims. Windows tests establish only their actual disposable/test scope.

Future M1 uses one BEGIN IMMEDIATE outer transaction: Domain A outside Domain B SAVEPOINT; on business failure roll back only B, outer COMMIT, then typed failure. The former independent pre-business Domain A COMMIT instruction is withdrawn. No M1 flow is implemented here.

Maximum ceiling: **CP3-C2-C3-M3 SHARED COUNTER UNION CORRECTED — GPT FINAL INDEPENDENT VERIFICATION REQUIRED**. This is implementer self-QA, not independent acceptance. Coordinator-authorized candidate finalization follows the completed source review. The external final identity/report records the exact bounded commit and branch push result. GPT independent verification is next; exact integration and fresh updated C3 authority each require separate authorization. No ZIP is created in this session.

- Current work: final review candidate and independent-verification handoff after completed implementation and required QA.
- Completed scope: 0010, additive Security reader admission, necessary revision compatibility, required tests/full Windows QA and evidence.
- Overall position: Phase 2 CP3-C2-C3-M3 structural correction; full C3 remains NOT IMPLEMENTED.
- Next: GPT independent verification, followed only by separately authorized exact integration and fresh updated C3 authority.

The unchanged standard full-QA receipt is `execution/20261003T142021694873Z_windows-standard-full-attempt-06.json` (aggregate exit 0). Candidate finalization changes only these six completion documents after the passing runtime/test/script input. The external `COORDINATOR_DOCS_ONLY_DELTA.patch`, source-equality proof and `COORDINATOR_FINAL_GATE_RESULTS.json` record the exact delta and unchanged final-candidate-docs policy/secret scanner reruns. Original `GATE_RESULTS.json`, the ready report, prior diff and manifest remain preserved precommit snapshots; no earlier failed run is relabeled.
