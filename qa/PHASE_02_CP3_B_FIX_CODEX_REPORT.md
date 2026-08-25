# Phase 2 CP3-B Independent-Review Fix Codex Self Report

CP3-B:
REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW

CP3-C:
NOT STARTED

Independent re-review:
PENDING

This report is a Codex self-report and is not an independent QA result.

## A. Repository and checkpoint

- Repository: `beomoo/tosstoss`
- Local repository: `C:\Users\beomoo\Documents\ChatGPT\tosstoss`
- Branch: `feature/phase-02-toss`
- Starting SHA: `58cc17d80b9b727b516cd45cb906eaa68f813d89`
- Starting origin feature SHA: `58cc17d80b9b727b516cd45cb906eaa68f813d89`
- Remote main SHA: `353159da45cfbe3a7f444bf476ce86fa9aece17c`
- Merge-base: `353159da45cfbe3a7f444bf476ce86fa9aece17c`
- Fix commit SHA: See the Git commit containing this report.
- Checkpoint: CP3-B independent-review P1-01 through P1-05 and P2-01 hardening only.
- Recovery basis: the earlier fix was not found locally or on origin; the pushed CP3-B implementation was preserved and this work is a normal fast-forward follow-up.

## B. Environment

- PowerShell: `7.6.4`
- Python: `3.13.15`
- Node.js: `24.19.0`
- npm: `11.17.0`
- Repository path: ASCII-only, yes.
- Reference PowerShell QA version: `7.6.5`; repository minimum: `7.4.0`; disposition: accepted supported variance.

## C. Changed paths and purpose

The final checkpoint contains 19 changed paths including this report:

1. `services/api/src/toss_dashboard_api/contracts/provider_source.py` — pin exact endpoint-to-dataset/source-locator relations and require CURRENT_PRICE freshness `UNKNOWN` before CP3-D2.
2. `services/api/src/toss_dashboard_api/repositories/provider.py` — enforce repeated-fetch semantics, trace graph, mapping integrity, latest eligibility, and SQL conditional writes.
3. `services/api/src/toss_dashboard_api/repositories/protocols.py` — expose atomic `record_source_version_with_audit()` in `ProviderRepository`.
4. `services/api/src/toss_dashboard_api/storage/provider_raw.py` — replace overwrite-capable rename publication with atomic no-replace publication.
5. `services/api/alembic/versions/0002_phase_02_cp3_foundation.py` — clean up only tables created by a failed 0002 run so a real mid-DDL failure leaves 0001 intact. No schema definition was added or removed; a later 0003 could not make failure inside its predecessor atomic.
6. `tests/backend/test_provider_source_contracts.py` — verify timestamp-present CURRENT_PRICE remains `UNKNOWN` and exact source locators.
7. `tests/backend/test_provider_raw_store.py` — verify competing-target same/different byte behavior, overwrite zero, and temp cleanup.
8. `tests/backend/test_provider_repository.py` — verify later-fetch, trace, relational mapping, latest eligibility, two-session CAS, and first-insert races.
9. `tests/backend/test_provider_migration.py` — exercise a late-table sentinel failure after earlier 0002 DDL and verify cleanup/retry.
10. `scripts/test.ps1` — raise the exact backend inventory gate from 448 to 493; frontend and E2E remain exactly 43 and 2.
11. `scripts/policy-scan.ps1` — update only the pinned control-plane digest for the reviewed final test/control bytes.
12. `plans/PHASE_02_EXECUTION_PLAN.md` — record the hardening scope and re-review gate.
13. `plans/PHASE_02_CP3_A_CONTRACT.md` — align the accepted source/identity contract with the six hardening invariants and acceptance cases.
14. `DECISIONS.md` — append ADR-011/ADR-012 implementation-hardening records without changing their accepted decisions.
15. `KNOWN_ISSUES.md` — update mitigations while preserving live and CP3-C/D limitations.
16. `STATUS.md` — set CP3-B to revised/awaiting re-review and retain CP3-C not started.
17. `CHANGELOG.md` — record the independent-review hardening.
18. `PROGRESS_LOG.md` — preserve the original implementation history and append this follow-up.
19. `qa/PHASE_02_CP3_B_FIX_CODEX_REPORT.md` — persist this self-report.

Changed paths outside the user-authorized checkpoint scope: 0.

## D. Independent-review fixes

### P1-01 — repeated fetch idempotency

- A duplicate raw observation is keyed by canonical request, HTTP status, exact raw hash, provider contract, and immutable request/path semantics.
- Later `fetched_at`, safe request ID, and rate telemetry return the first-seen immutable manifest and do not create or overwrite raw/source rows.
- Content type remains semantic and is not ignored.
- A source version with the same semantics also ignores only later `fetched_at` and a non-authoritative incoming source ID.
- Dataset, parser version, normalized hash, revision status, supersedes link, and provider contract differences fail closed.
- Separate collection attempts and duplicate audit events remain appendable without a duplicate source version.

### P1-02 — exact trace graph

- Exact persistence mapping is `/api/v1/stocks/all → STOCK_DISCOVERY`, `/api/v1/stocks → STOCK_DETAIL`, and `/api/v1/prices → CURRENT_PRICE`.
- `DAILY_FLOW` has no CP3-B-approved path and is not repository-persistable.
- Source insertion validates request existence, raw ownership, provider, path/dataset/locator, raw hash/ref, fetched time, parser, and provider contract.
- Attempt and audit insertion validates provider/dataset/request consistency. Source-linked event types require an existing source; source-free types cannot claim one.
- Atomic source-plus-audit mismatch leaves source and audit counts both zero.
- The atomic method is part of the `ProviderRepository` protocol.

### P1-03 — VERIFIED mapping relational integrity

- VERIFIED requires an existing ACTIVE identity; QUARANTINED, UNRESOLVED_COLLISION, and inactive states are rejected.
- Canonical issuer and security must exist and `SecurityRow.issuer_id` must equal the mapping issuer.
- Evidence must belong to the identity through first source, latest source, or identifier-history source lineage.
- Missing/mismatched canonical rows and unrelated evidence fail without changing existing mapping state.
- Unresolved mapping still cannot carry fake canonical linkage.

### P1-04 — SQL CAS and latest eligibility

- Existing latest-pointer changes use one conditional SQL `UPDATE` with pointer ID and expected state hash in the `WHERE` clause.
- Two independent sessions start from a barrier with the same old hash: exactly one succeeds and the loser receives `ProviderConditionalWriteConflict`.
- First-insert races use `INSERT ... ON CONFLICT DO NOTHING`: identical payloads are idempotent; different payloads produce a typed conflict; one complete row remains.
- Raw database integrity/operational errors are translated to safe repository errors.
- Latest eligibility requires an ACTIVE identity, exact source dataset/observation, matching contracts, and identity lineage.
- CURRENT_PRICE freshness is always `UNKNOWN` before CP3-D2. A timestamp-null CURRENT_PRICE source is valid source history but cannot update latest.

### P1-05 — real mid-migration rollback

- The test upgrades to 0001, imports Phase 1 fixtures, and pre-creates the later `provider_identity_mappings` table as a sentinel.
- 0002 creates several earlier tables before failing at the sentinel.
- The migration removes only tables created by that failed run. Alembic remains at 0001; Phase 1 rows and the sentinel remain unchanged.
- Removing only the intentional sentinel permits retry to head; no partial CP3 schema cleanup is required.
- `0001_phase_01_foundation.py` remains unchanged.

### P2-01 — raw no-replace race hardening

- Publication uses an atomic hard-link create operation that cannot replace an existing target.
- A competing same-byte target deduplicates; a competing different/corrupt target raises `ProviderRawStoreConflict`.
- The competing target survives unchanged, target overwrite count is zero, and temporary files are cleaned.
- A platform/filesystem that cannot perform the no-replace primitive fails closed.

## E. Test design and exact cases

- Repeated fetch: later raw/source timestamps, changed safe telemetry, content-type conflict, normalized/parser/dataset/revision conflict, and distinct duplicate attempt/audit.
- Trace: prices+DAILY_FLOW, stocks/all+CURRENT_PRICE, fetched/parser mismatch, attempt request/dataset/provider mismatch, source-linked event without source, and atomic zero-row rollback.
- Mapping: issuer/security mismatch, missing issuer, missing security, quarantined/collision identity, unrelated evidence, first/latest lineage success, identifier-history lineage success, and existing-state preservation.
- Latest: timestamp+FRESH contract rejection, timestamp+UNKNOWN acceptance, null timestamp source storage/latest rejection, non-active identity, dataset/observation/lineage mismatch, two-session update race, different first-insert race, and same-payload first-insert race.
- Migration: first-table failure is retained and a separate true mid-migration sentinel failure verifies partial-schema cleanup and retry.
- Raw store: publish-time competing same/different targets verify dedupe/conflict, surviving target, no overwrite, and temp cleanup.
- Concurrency method: Python `ThreadPoolExecutor` runs two repositories with independent SQLAlchemy sessions; a `threading.Barrier` releases both writers against the same database state. Sequential calls are not labeled concurrency tests.

## F. Policy and inventory

- Backend inventory before this hardening: exactly 448.
- Backend inventory after this hardening: exactly 493.
- Backend test source files: 32 before / 32 after; no wildcard was added.
- Phase control-plane files: 70 before / 70 after.
- Prior approved control-plane digest: `f486c1d6e7693eeb78fe341c6a28508dbd0ef8b8f2cf7bd82c5e607b7425f604`.
- Final approved control-plane digest: `6da6c2956f1150c1c9cd521db726a04ae5fcc890a8cf83edefca0ddfbb670809`.
- Existing missing-file and lookalike backend-test canaries remain enabled.
- Exact set comparison, exact count/digest, forbidden endpoint/header/network checks, and security canaries were not removed, skipped, or weakened.

## G. Scope not implemented

- CP3-C security-master DTO, normalizer, job, reconciliation service: 0.
- CP3-D price DTO/payload/service/job: 0.
- Frontend or E2E source changes: 0.
- Connector auth/client/rate/preflight changes: 0.
- Public route/OpenAPI changes: 0.
- Fixture changes: 0.
- Dependency/lock/runtime-config changes: 0.
- New migration/schema revision: 0; 0002 schema remains identical and only failure cleanup behavior changed.
- Actual credential use, actual Toss API request, live scheduler/polling: 0.
- Account/order/WebSocket implementation or header surface: 0.

## H. QA commands and results

Preflight:

- `git fetch origin --prune` — exit 0.
- `git fetch origin "+refs/heads/main:refs/remotes/origin/main"` — exit 0.
- Git branch/SHA/merge-base/clean checks — matched the values in section A.

Implementation checks completed before the final staged suite:

- `git diff --check` — exit 0.
- Ruff format/check on changed Python — exit 0.
- Mypy package check — 52 source files, exit 0.
- Provider repository targeted suite — 64 passed, exit 0.
- Provider migration plus general migration targeted suite — 10 passed, exit 0.
- Backend collection — exactly 493, exit 0.
- Policy scan with the final exact count/digest — exit 0.

Final staged full regression:

- Command: `pwsh -NoProfile -File .\scripts\test.ps1`
- Backend exact inventory/result: 493/493 passed.
- Frontend exact inventory/result: 43/43 passed.
- E2E exact inventory/result: 2/2 passed.
- Migration repeat/downgrade/re-upgrade: passed; the backend suite also includes the real mid-migration sentinel rollback test.
- Fixture idempotency: first import inserted 13; second import inserted 0, updated 0, unchanged 13; canonical digest and primary keys preserved.
- OpenAPI generated-type drift check: passed.
- Production build and repeat build: passed twice.
- Initial and final policy scans: passed.
- Secret scan: passed.
- Offline default mode: external network requests 0, credentials used 0, live not requested.
- Toss preflight SelfTest: external network requests 0; gate/schema/redaction/one-shot/drift-stop checks passed.
- Final exit code: 0.

## I. Security confirmation

- Actual credential use: 0.
- Actual Toss API requests: 0.
- Token/auth body/header values stored: 0.
- Account/order endpoint or `X-Tossinvest-Account` changes: 0.
- WebSocket changes: 0.
- External provider requests from the offline suite: 0.
- Secret artifacts: 0; secret scan exit 0.

No client ID, client secret, access token, Authorization header, environment-file content, provider response body, unrestricted raw header, or account identifier is included in this report.

## J. False-green review

- Test deletions: 0.
- Skip additions: 0.
- Xfail additions: 0.
- Inventory reduction: no; 448 → 493.
- Exact inventory gate weakening: 0.
- Expected-file wildcard: 0.
- Control-plane count/digest removal: 0.
- Policy error swallowing or conditional bypass: 0.
- Assertion weakening: 0.
- Expected-exception swallowing: 0.
- Empty fixture/collection bypass: 0.
- Network guard bypass: 0.
- Security-pattern exception additions: 0.

## K. Known limitations and live status

`LIVE_VERIFIED` remains limited to the previously approved CP2 evidence: canonical provider contract drift check, actual OAuth token issuance/credential acceptance/allowed-IP path, actual `GET /api/v1/stocks` outer structure, and successful Limit/Remaining/Reset headers.

`LIVE_UNVERIFIED` remains: `/api/v1/stocks/all`, `/api/v1/prices`, all price timestamp/null/currency/freshness semantics, complete market/security/lifecycle enum semantics, natural 429 `Retry-After`, actual 429/5xx, and production retry timing.

Deferred environment issue: Windows non-ASCII parent-path editable-install portability remains a P2 environment constraint; this repository uses the approved ASCII-only path.

Deferred implementation: CP3-C must implement continuity-first discovery/detail reconciliation. CP3-D must separately implement ProviderPriceSnapshot payload/normalization and any current-price service. This hardening supplies only contract/source/identity/latest-pointer foundations.

## L. Codex self-assessment

Self-assessed P0: 0.

Self-assessed P1: 0; the final staged regression succeeded, but independent re-review remains required.

Self-assessed P2: 0 functional; the pre-existing non-ASCII environment constraint remains deferred.

This is a Codex self-assessment and is not an independent QA result.

## M. Next-step state

CP3-B:
REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW

CP3-C:
NOT STARTED

Automatic checkpoint progression:
PROHIBITED

Main merge:
NOT PERFORMED

PR:
NOT CREATED

Tag/Release:
NOT CREATED
