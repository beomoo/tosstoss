# Phase 2 CP3-A Independent Review Fix — Codex Self Report

Checkpoint Status:
CP3-A REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW

CP3-B:
NOT STARTED

Independent re-review:
PENDING

This report is a Codex self-report and is not an independent QA result.

## 1. Report identity

| item | value |
|---|---|
| repository | `beomoo/tosstoss` |
| local repository | `C:\Users\beomoo\Documents\ChatGPT\tosstoss` |
| branch | `feature/phase-02-toss` |
| checkpoint | `Phase 2 CP3-A Independent Review Fix — P1-01/P1-02 documentation/contract only` |
| starting SHA | `386a0b2fe7bd18ed4b662eb2695ff85cc2a08cd3` |
| CP3-A implementation SHA | `3e09ba4163625a193f953379ebc868f560501568` |
| CP3-A report follow-up SHA | `386a0b2fe7bd18ed4b662eb2695ff85cc2a08cd3` |
| implementation-fix SHA | See the Git commit containing this report. |
| starting origin feature SHA | `386a0b2fe7bd18ed4b662eb2695ff85cc2a08cd3` |
| remote main SHA | `353159da45cfbe3a7f444bf476ce86fa9aece17c` |
| merge-base | `353159da45cfbe3a7f444bf476ce86fa9aece17c` |

Preflight found a clean working tree, the required branch, matching local/origin feature SHAs, and the expected remote-main ancestry. No branch switch or local main creation was performed.

## 2. Environment

| item | result | disposition |
|---|---|---|
| PowerShell | `7.6.4` | repository minimum `7.4.0`; accepted variance from previous final QA reference `7.6.5` |
| Python | `3.13.15` | expected |
| Node.js | `24.19.0` | expected and within supported range |
| npm | `11.17.0` | expected |
| repository path | ASCII-only | accepted |

No environment installation or version change was performed.

## 3. Independent-review findings addressed

The first independent review result was `CHANGES REQUIRED`, with P0 0 and P1 2. CP3-B was not authorized.

### P1-01 — provider identity and Current Price separation

- `ProviderPriceSnapshot` is keyed by required immutable `provider_security_identity_id`; `security_id` and canonical mapping state are nullable linkage.
- A valid, non-collision, non-quarantine provider identity may own provider-scoped price snapshots and latest state while canonical mapping remains `UNRESOLVED`.
- A canonical current-price view is created or exposed only through a verified `security_id` linkage.
- Unresolved provider prices cannot be represented as canonical company prices, used for issuer/company analysis, joined automatically to OpenDART/SEC/13F, or exposed as verified canonical Security data.
- A later approved mapping adds linkage only. Provider identity, source, price IDs, hashes, revisions, and history are not rekeyed.
- This removes the Phase 2 provider-scoped Security Master + Current Price dependency on Phase 3 corp_code and Phase 4 CIK availability without weakening regulatory-ID safeguards.

### P1-02 — immutable provider identity reconciliation

- Every observation searches active identity and append-only provider identifier history for continuity before applying a new-allocation anchor priority.
- Exactly one deterministic, non-contradictory candidate reuses the immutable provider identity. New ISIN/listDate/symbol evidence is appended as enrichment/revision history.
- Multiple candidates or a conflict with another active identity cause `UNRESOLVED_COLLISION`/`QUARANTINE`; automatic merge, arbitrary winner selection, and new identity allocation are all prohibited.
- Only zero continuity evidence permits first allocation using unique valid ISIN, then symbol+listDate, then symbol+first-seen raw evidence.
- Stronger identifiers discovered later never migrate the anchor or rekey the ID. An approved canonical mapping also leaves the provider ID unchanged.
- Deterministic rebuild replays ordered raw/source history and must reproduce the same provider identity, immutable anchor, and identifier history.

## 4. Changed files and purpose

| file | purpose |
|---|---|
| `plans/PHASE_02_CP3_A_CONTRACT.md` | provider/canonical price split, continuity-first reconciliation, migration/hash/latest consistency, and seven P0 acceptance cases |
| `plans/PHASE_02_EXECUTION_PLAN.md` | Phase 2 provider-scoped completion path, checkpoint state, storage and CP3-D1 plan consistency |
| `DECISIONS.md` | ADR-011 review disposition and revised ADR-012 proposal |
| `KNOWN_ISSUES.md` | circular dependency and identifier-enrichment reconciliation risks/current conservative defaults |
| `STATUS.md` | first review result, two fixes, GPT re-review pending, CP3-B not started |
| `CHANGELOG.md` | documentation-only independent-review fix history and scope |
| `PROGRESS_LOG.md` | preflight, P1 resolution, ADR and stop-point record |
| `qa/PHASE_02_CP3_A_FIX_CODEX_REPORT.md` | this Codex self-report |

Allowed-scope files outside this set changed: `0`.

## 5. Contract and acceptance changes

- `/stocks/all` remains KR/US discovery only and `LIVE_UNVERIFIED`; disappearance alone is not delisting.
- `/stocks` remains maximum-200-symbol detail enrichment. Only the actual call structure and successful outer response are `LIVE_VERIFIED`; enum/null/lifecycle semantics are not promoted.
- `/prices` remains `LIVE_UNVERIFIED`. Its eligible input is a validated provider identity, not a mandatory canonical security mapping.
- KR/US, ACTIVE, common-share, explicitly supported stock type, expected currency, collision-free conservative universe rules remain fail closed.
- Toss symbol remains provider-scoped and is never stored as corp_code/CIK. Name-only or ISIN-only issuer merge, synthetic regulatory IDs, and false `VERIFIED` mapping remain prohibited.
- `ProviderPriceSnapshot` preserves Decimal-string, currency, nullable provider timestamp, source version, raw/normalized hashes, availability/freshness/revision and provider contract version.
- Timestamp null remains `DEGRADED`/`UNKNOWN`, does not copy `fetched_at`, and does not update user-facing latest. Missing/null price is never replaced by zero.
- Provider price normalized hashes exclude later canonical linkage/mapping events so promotion cannot rewrite provider history. Mapping evidence has its own record/hash.
- Additive migration remains proposed only: provider identity/history/mapping, source/raw/audit, provider-identity latest pointer, no `0001` rewrite, fake backfill, destructive rebuild, or SQLite price history.
- CP3-B/C/D split remains gated. The actual test code for seven new P0 acceptance cases was not implemented in this checkpoint.

The added documented acceptance cases cover provider price without canonical mapping, verified mapping promotion, fake regulatory-ID prevention, ISIN enrichment, listDate enrichment, enrichment collision, and deterministic rebuild after enrichment. Each requires positive row/ID/history evidence and explicit zero-count assertions for forbidden canonical publish, merge, rekey, or new identity behavior.

## 6. ADR status

| ADR | status |
|---|---|
| ADR-010 | `ACCEPTED` — unchanged |
| ADR-011 | `PROPOSED — INDEPENDENT REVIEW P1-NOT-BLOCKING / AWAITING USER APPROVAL` |
| ADR-012 | `PROPOSED — REVISED AFTER INDEPENDENT REVIEW / AWAITING RE-REVIEW` |

ADR-011 and ADR-012 are not accepted by Codex. Exact provider enums, exchange mapping, provider/canonical schema details, freshness thresholds, and approval authority remain subject to the required review and user decision.

## 7. Not implemented

| scope | changes or usage |
|---|---:|
| application source | 0 |
| test code | 0 |
| fixtures | 0 |
| migration files | 0 |
| dependencies/lockfiles | 0 |
| runtime config/routes/connectors | 0 |
| scheduler/live polling/UI | 0 |
| actual Toss credential use | 0 |
| actual Toss API calls | 0 |
| account/order/WebSocket | 0 |
| CP3-B implementation | 0 |

## 8. QA commands and results

The following results are from the first completed full regression on the staged eight-file checkpoint set. After replacing the pending fields in this report, the entire suite must be rerun on the final document set; commit is prohibited unless that final run also exits `0` with the same exact inventories.

| command/gate | result | exit code |
|---|---|---:|
| `git diff --check` | PASS | `0` |
| `git diff --name-only` | PASS; seven tracked modified paths at that point, with the new report separately visible as untracked in `git status --short` | `0` |
| `git diff --cached --check` | PASS after staging all eight allowed files | `0` |
| `git diff --cached --name-only` | exactly eight allowed files | `0` |
| `pwsh -NoProfile -File .\scripts\test.ps1` | PASS | `0` |
| backend inventory/result | exactly `357`; `357 passed` | `0` |
| frontend inventory/result | exactly `43`; `43 passed` | `0` |
| E2E inventory/result | exactly `2`; `2 passed` | `0` |
| migration | repeat / downgrade / re-upgrade PASS | `0` |
| fixture idempotency | second import `inserted=0`, `updated=0`, `unchanged=13` | `0` |
| OpenAPI | generated-contract check PASS | `0` |
| production build | two complete Next.js builds PASS | `0` |
| secret scan | PASS | `0` |
| initial/final policy scan | both PASS | `0` |

Offline Toss preflight evidence remained `EXTERNAL_NETWORK_REQUESTS=0`, `CREDENTIALS_USED=0`; SelfTest also reported `EXTERNAL_NETWORK_REQUESTS=0` and PASS for gate/schema/redaction/one-shot/drift-stop checks.

## 9. Security confirmation

- Actual credential use: `0`
- Actual Toss API calls: `0`
- Token/auth body/credential value persisted: `0`
- Account/holding/order endpoint or header changes: `0`
- `X-Tossinvest-Account`: `0`
- WebSocket changes: `0`
- Secret artifacts: `0`

Only safe summary evidence is recorded. No credential value, access token, authorization header, environment-file content, actual API response body, unrestricted raw header, or account identifier is included.

## 10. False-green review

| check | result |
|---|---|
| deleted tests | 0 |
| added skip | 0 |
| added xfail | 0 |
| inventory reduction | no; exact backend/frontend/E2E inventories remained `357/43/2` |
| assertion weakening | 0 |
| expected exception swallow | 0 |
| empty fixture/collection bypass | 0 |
| network guard bypass | 0 |

The checkpoint changes documentation only. Test, fixture, script, and policy source files were not changed.

## 11. Known limitations

### LIVE_VERIFIED

- canonical provider contract origin/hash match, OpenAPI `3.1.0`, provider REST `1.2.14`, and no drift at the prior approved live checkpoint
- actual OAuth issuance and credential acceptance at the prior approved live checkpoint
- allowed-IP execution path
- actual `GET /api/v1/stocks` call structure and successful outer response
- successful response Limit/Remaining/Reset rate headers

### LIVE_UNVERIFIED

- `/api/v1/stocks/all`
- `/api/v1/prices`
- complete market/securityType/null/identifier/lifecycle semantics
- price/currency/timestamp-null/freshness semantics
- natural 429 `Retry-After`, actual 429/5xx behavior, and production retry timing

The Windows non-ASCII editable-install issue remains a deferred environment P2; this checkpoint used the ASCII-only repository path. Provider enum spellings, exchange mapping, canonical mapping/promotion authority, freshness thresholds, and the revised ADR-012 schema remain unresolved until review. A future live checkpoint remains separately gated and requires explicit user authorization.

## 12. Codex self-assessment

Self-assessed P0: `0`

Self-assessed P1: `0` after the documentation fix and completed full offline regression; independent re-review remains pending

Self-assessed P2: `1` deferred environment constraint for Windows non-ASCII editable install; this run used the accepted ASCII-only path

This is a Codex self-assessment and is not an independent QA result.

## 13. Next-step state

CP3-A:
REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW

CP3-B:
NOT STARTED

Automatic checkpoint progression:
PROHIBITED

Main merge:
NOT PERFORMED

PR:
NOT CREATED

Tag/Release:
NOT CREATED
