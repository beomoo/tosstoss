# Phase 2 CP3-C1 Codex Self-Report

CP3-C1:
`IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW`

CP3-C2:
`NOT STARTED — USER DECISION REQUIRED`

CP3-D:
`NOT STARTED`

Independent QA:
`NOT YET PERFORMED`

This report is a Codex self-report and is not an independent QA result.

## Repository and revision

- Repository: `C:\Users\beomoo\Documents\ChatGPT\tosstoss`
- Branch: `feature/phase-02-toss`
- Starting SHA: `49cc07573570b724d31d00183e40edd9330785cc`
- Final SHA: the normal commit containing this report; reported after commit/push in the final handoff. A commit cannot contain its own SHA without changing that SHA.
- Starting remote: `origin/feature/phase-02-toss` at the same starting SHA
- Prior CP3-B backup stash: preserved and not applied, popped, dropped or modified

## Changed files

### Contracts, domain and repository

- `services/api/src/toss_dashboard_api/contracts/enums.py`
- `services/api/src/toss_dashboard_api/contracts/provider_security_master.py`
- `services/api/src/toss_dashboard_api/domain/security_master.py`
- `services/api/src/toss_dashboard_api/repositories/security_master.py`
- `services/api/src/toss_dashboard_api/repositories/sqlite.py`
- `services/api/src/toss_dashboard_api/storage/models.py`

### Migration and fixtures

- `services/api/alembic/versions/0004_phase_02_cp3_c1_security_master.py`
- `fixtures/phase_02/cp3_c1/stock_discovery_kr.json`
- `fixtures/phase_02/cp3_c1/stock_discovery_us.json`
- `fixtures/phase_02/cp3_c1/stock_detail_kr.json`
- `fixtures/phase_02/cp3_c1/stock_detail_us_partial.json`

### Tests and gates

- `tests/backend/test_security_master_reconciliation.py`
- `tests/backend/test_migrations.py`
- `tests/backend/test_provider_migration.py`
- `tests/backend/test_repositories.py`
- `scripts/test.ps1`
- `scripts/policy-scan.ps1`

### Documentation

- `STATUS.md`
- `CHANGELOG.md`
- `DECISIONS.md`
- `KNOWN_ISSUES.md`
- `plans/PHASE_02_EXECUTION_PLAN.md`
- `qa/PHASE_02_CP3_C1_CODEX_REPORT.md`

## DTO and fixture contracts

- Provider contract version: `toss-security-master/0.1.0`, separate from the Phase 1 public contract and CP3-B source/identity contracts.
- `/api/v1/stocks/all`: strict discovery item/response with exact `symbol`, `name`, `securityType`, `isCommonShare`, nullable `isinCode`; duplicate symbols and unknown/extra fields fail closed.
- `/api/v1/stocks`: strict detail item/response with exact provider listing market/type/status/currency enums, nullable dates and identifiers, canonical Decimal strings, KR-only market detail and duplicate-symbol rejection.
- ISIN is nullable but, when present, must match the 12-character grammar and Luhn checksum. JSON numeric/float Decimal input is rejected.
- Four JSON fixtures contain only synthetic `KRT*`/`UST*` symbols, test names and checksum-valid fabricated ISINs. They contain no credential, token, account data or real-company identifier.

## Normalization and conservative universe

- Provider details normalize to a semantic content hash and deterministic `psmr_<sha256>` record ID. Repeating identical semantics creates one normalized record while each distinct source observation remains auditable.
- Eligible candidate requirements are exact KR/US internal market, supported listing market, `ACTIVE`, `STOCK`, common share, KRW/USD match, valid provider identity and no contradiction/collision/quarantine.
- ETF, ETN, warrant, non-common and unsupported listing markets are not coerced to common equity. Currency/status/delist contradictions quarantine the observation.
- Nullable ISIN/listDate/English name/delist date/leverage use structured missing reasons. Missing ISIN/listDate do not create empty/default identifiers.
- No exchange is inferred. Unknown enum values fail DTO validation before normalized staging.

## Continuity, allocation and enrichment

- Search scope is exact provider and internal market. Evidence is evaluated before allocation: exact active symbol interval, unique valid ISIN history, exact symbol+listDate history, lifecycle state and safe source lineage. Name similarity is never evidence.
- Exactly one non-contradictory candidate reuses its `provider_security_identity_id`; the immutable allocation anchor, ID and first source never change.
- Evidence count zero allocates in the accepted order: `toss-identity-v1|market|ISIN|isin`, then `...|SYMBOL_LIST_DATE|symbol|listDate`, then `...|FIRST_SEEN_RAW|symbol|raw_content_hash`. ID is `tpsi_` plus the full lowercase SHA-256 of the anchor.
- Symbol, ISIN, listDate and market evidence is append-only and source-linked. ISIN/listDate enrichment and symbol change preserve the original identity and old history.
- A provider correction requires an amended source that supersedes the identity's latest source; old/new evidence remains queryable and the candidate is quarantined for review rather than silently published.
- Closed lifecycle plus the same reused ticker but different identifiers allocates a separate identity; same verified historical ISIN can preserve continuity on relisting.

## Collision and lifecycle handling

- Multiple identities selected by evidence, duplicate active ISIN, conflicting identifier changes and share-class/listing-market changes produce no merge, arbitrary winner or new identity.
- Affected identities transition to `UNRESOLVED_COLLISION`; the source observation is `QUARANTINED` and not eligible for mapping.
- Discovery disappearance appends `DISCOVERY_MISSING` only. It does not infer delisting, generate `valid_to`, close a canonical mapping or change an identity state.
- `INACTIVE` and `DELISTED` detail observations preserve prior rows/history and are non-eligible. Contradictory lifecycle details quarantine while preserving normalized evidence and LKG history.
- CP3-C1 emits provider candidate evidence only. It creates no canonical Issuer/Security, corp_code, CIK or VERIFIED mapping.

## Partial detail and deterministic rebuild

- Each detail source stores exact requested, received and missing symbol sets/counts. Complete, partial and empty results are distinct states.
- Valid received rows proceed independently. Every missing symbol requires prior discovery evidence and receives an explicit non-eligible `DETAIL_MISSING`/`QUARANTINED` observation. No synthetic detail object is fabricated.
- Empty detail response is `FAILED_EMPTY_RESPONSE`, never success.
- Replay sorts append-only inputs by `(fetched_at, source_version_id)`. Identity allocation, history IDs, state events and observations exclude clock/run/job/attempt IDs.
- Two clean SQLite databases replaying the same sources in deliberately reversed input order produce byte-identical ordered identity/history/observation/event dumps.

## Migration decision

Exactly one additive migration was necessary. CP3-B tables truthfully model source lineage, immutable identities, identifier history, mapping evidence and latest-pointer foundations, but cannot durably represent:

1. deduplicated Security Master semantic records;
2. source-linked discovery/detail/lifecycle/collision observations;
3. append-only identity-state transition evidence;
4. exact requested/received/missing detail-batch audit.

`0004_phase_02_cp3_c1_security_master` adds one table for each concern with FK/unique/check constraints. Its `down_revision` is exactly `0003_phase_02_cp3_b_invariants`. It performs no backfill or destructive rewrite, cleans only tables created by its failed attempt, and preserves a pre-existing sentinel plus Phase 1/CP3-B rows during a tested mid-DDL failure. `0001`, `0002` and `0003` remain byte-identical; the existing 0003 hash is pinned by regression.

## Tests and false-green review

- New CP3-C1 test module covers C-M01 through C-M09, C-U01 through C-U08 and IR-D through IR-G, plus strict fixtures/ISIN/Decimal, unexpected detail symbols, lifecycle contradiction and cross-market separation.
- Migration regression covers the 0004 exact head/schema, downgrade/re-upgrade and later-table failure cleanup/retry without weakening CP3-B migration tests.
- Backend exact inventory: `540` (increased from `509`; exact equality, not `>=`).
- Frontend exact inventory: `43`.
- E2E exact inventory: `2`.
- Deleted tests: `0`; skip: `0`; xfail: `0`; assertion weakening: `0`; exception swallowing: `0`; unknown-to-known coercion: `0`; empty-result bypass: `0`.
- Secret scanner scope/filter/threshold: unchanged. Policy allowlists and exact control-plane digest were updated only for the added test and new exact inventory.

## Verification results

- Target CP3-C1 + migration regression: `45/45 PASS`.
- Full backend before final staging: `540/540 PASS`.
- Final staged implementation full repository regression: `PASS` via `pwsh -NoProfile -File .\scripts\test.ps1`.
- Backend: exact inventory `540`; `540/540 PASS`.
- Frontend: exact inventory `43`; `43/43 PASS`.
- E2E: exact inventory `2`; `2/2 PASS`.
- Migration: upgrade/repeat/downgrade/base/re-upgrade through `0004` `PASS`.
- Fixture idempotency: first import `inserted=13`; second import `inserted=0`, `updated=0`, `unchanged=13`; `PASS`.
- OpenAPI generated-type drift check: `PASS`.
- Production build: `PASS` twice, including the E2E-owned server build.
- Secret scan: `PASS` with fail-closed ignored-file scope unchanged.
- Policy scan: initial and final `PASS`.
- Full regression exit: `0`.
- Root `.mypy_cache` after run: absent. Root `.ruff_cache` after run: absent.

## Security counts and non-scope

- Actual credential usage: `0`.
- Actual Toss API requests: `0`.
- External provider network requests: `0`.
- OpenAI API requests: `0`.
- Account/holdings/order/conditional-order code or request: `0`.
- `X-Tossinvest-Account`: `0`.
- WebSocket: `0`.
- CP3-C2 canonical promotion: `NOT STARTED — USER DECISION REQUIRED`.
- CP3-D price DTO/normalizer/chunking/snapshot/latest/canonical projection: `NOT STARTED`.
- Frontend, scheduler, live collection, OpenDART, SEC, news and macro changes: `0`.
- LIVE_VERIFIED scope expansion: `0`.
- PR, main merge, tag and release: `0`.

## Known limitations

- `/stocks/all` and complete `/stocks` enum/null/lifecycle semantics remain `[LIVE_UNVERIFIED]`; fixtures are based on official public contract only.
- Provider listing-market to canonical exchange authority remains unapproved, so CP3-C1 does not infer exchange or create canonical Security.
- Canonical promotion authority/evidence remains a CP3-C2 user decision. An eligible CP3-C1 candidate is not a verified canonical mapping.
- Identifier correction/collision recovery needs a future approved review workflow; CP3-C1 deliberately stays quarantined rather than auto-recovering.
- Current Price and provider snapshot/latest publication remain CP3-D scope.
