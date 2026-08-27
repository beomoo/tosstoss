# Phase 2 CP3-C2-B2-B Codex Self-QA Report

## Scope and identity

- Repository: `beomoo/tosstoss`
- Branch: `feature/phase-02-toss`
- Checkpoint: `CP3-C2-B2-B — Production Source Admission, Exact Issuer
  Bridge, Collision/Freshness Evaluation, and Machine Decision Engine`
- Authoritative starting SHA:
  `dd86aeb195222fa94e9bd0ec48a5f1d942825c14`
- Final SHA: this report is committed with the implementation, so the
  authoritative final SHA is reported after commit/push rather than embedded
  recursively in its own content.
- Evidence class: LOCAL Codex self-QA only. This report does not declare GPT
  PASS and is not GitHub CI evidence.

## Exact implementation paths

- `services/api/src/toss_dashboard_api/authority_source_registry.py`
- `services/api/src/toss_dashboard_api/contracts/authority_decision.py`
- `services/api/src/toss_dashboard_api/domain/issuer_authority.py`
- `services/api/src/toss_dashboard_api/repositories/authority.py`
- `tests/backend/test_authority_decision_engine.py`
- `tests/backend/test_authority_repository.py`
- `tests/backend/test_authority_migration.py`
- `scripts/test.ps1`
- `scripts/policy-scan.ps1`
- `STATUS.md`
- `DECISIONS.md`
- `CHANGELOG.md`
- `plans/PHASE_02_EXECUTION_PLAN.md`
- `plans/PHASE_02_CP3_C2_B1_RUNTIME_CONTRACT.md`
- `qa/PHASE_02_CP3_C2_B2_B_CODEX_REPORT.md`

The final staged-path audit must match this list exactly. No route, UI,
connector, fixture, storage model, migration, dependency, credential, network,
or scheduler path is changed.

## Server-owned source-policy registry

All entries are immutable `AuthoritySourcePolicy` values with deterministic
policy IDs/content hashes, exact namespaces/document kinds/scope-role ceilings,
exact adapter/parser versions, exact origin mode and access/license policy. A
production policy insert succeeds only when the full stored contract equals an
entry in the server-owned registry; a caller-provided ID/hash mapping is no
longer accepted.

| registry constant / namespace | admitted documents | scope × role × maximum weight | ingestion |
|---|---|---|---|
| `OPENDART_CORP_CODE_POLICY` / `OPENDART_CORP_CODE` | `CORP_CODE_XML_V1` | `ISSUER_REGULATORY_ID × DART_DISCLOSURE_FILER × DECISIVE` | automated official public |
| `OPENDART_COMPANY_OVERVIEW_POLICY` / `OPENDART_COMPANY_OVERVIEW` | `COMPANY_OVERVIEW_JSON_V1` | `LEGAL_ENTITY_BRIDGE`, `LEGAL_NAME × DART_DISCLOSURE_FILER × SUPPORTING` | automated official public |
| `KR_IROS_JURISDICTION_ONLY_POLICY` / `KR_SUPREME_COURT_IROS` | `VERIFIED_CORPORATE_REGISTRY_EXTRACT_V1` | independently reviewed B2-A compatibility entry: `LEGAL_JURISDICTION × KOREAN_REGISTERED_LEGAL_ENTITY × DECISIVE` | human-assisted verified document |
| `KR_IROS_COMPLETE_POLICY` / `KR_SUPREME_COURT_IROS` | same exact verified document kind | `LEGAL_ENTITY_BRIDGE`, `LEGAL_JURISDICTION`, `LEGAL_NAME × KOREAN_REGISTERED_LEGAL_ENTITY × DECISIVE` | human-assisted verified document |
| `SEC_ACCEPTED_FILING_POLICY` / `SEC_EDGAR_ACCEPTED_FILING` | accepted issuer filing and registrant latest-status JSON contracts | registrant ID/role `DECISIVE`; legal bridge/name `SUPPORTING` for `SEC_REGISTRANT` | automated official public |
| `SEC_LOGIN_PROVENANCE_POLICY` / `SEC_EDGAR_LOGIN_PROVENANCE` | `SEC_SUBMISSION_PROVENANCE_JSON_V1` | `SUBMISSION_PROVENANCE × SEC_LOGIN_CIK/SEC_FILING_AGENT × ZERO` | provenance only |
| `US_STATE_REGISTRY_DE_POLICY` / `US_STATE_REGISTRY_DE` | `VERIFIED_DOMESTIC_ENTITY_RECORD_V1` | `LEGAL_JURISDICTION`, `LEGAL_NAME × US_STATE_REGISTERED_LEGAL_ENTITY × DECISIVE` | human-assisted verified document |

There is no production wildcard namespace or wildcard US state registry.
Unlisted document/scope/role/version/locator combinations receive no positive
authority. Fixture/test/synthetic source mode or ancestor lineage remains
permanently tainted, and format-valid identifiers alone remain non-authority.
The policy scanner permits the OpenDART and SEC public locator roots only as
inert policy data in this exact registry path; host/path/credential bypass
canaries remain rejected. No HTTP transport was added.

## KR and US authority evaluation

### Korea

The positive path requires the same exact eight-digit OpenDART `corp_code`, a
current overview fact carrying exact raw `jurir_no` and provider stock code, a
verified original IROS domestic-corporation jurisdiction fact, a same-document
IROS registration-reference fact matching the overview `jurir_no`, and exact
CP3-C1 provider observation lineage whose symbol matches that admitted bridge.
Name/symbol similarity alone, KRX/listing/provider geography, KRW, language,
`corp_cls`, and stock code as an anchor/jurisdiction/ISIN remain unusable.

### United States

The positive path requires a zero-padded accepted SEC registrant CIK, exact
issuer-registrant role, an accepted issuer filing, exact state-entity and
formation-state bridge fields, a current registrant-status check, an exact
individually admitted domestic formation registry record, and exact non-name
CP3-C1 provider observation lineage. SEC login/agent/accession provenance is
explicit weight-zero provenance and cannot become registrant identity.

Only Delaware is individually admitted in this checkpoint. Other formation
states and foreign/private issuers remain fail-closed `UNRESOLVED` until a
separately reviewed exact state/jurisdiction policy is added; no wildcard or
parser jurisdiction label can substitute.

## Freshness, correction/revocation and collisions

- Historical immutable authority facts are not invalidated merely because
  their retrieval is older than 24 hours.
- `conservative-approval-freshness/0.1.0` applies the 24-hour window only to
  required repository current/latest status facts. Stale or unavailable
  required checks block READY and emit `STALE` when the structural path is
  otherwise complete.
- The engine reconstructs the connected immutable
  `AuthorityEvidenceRelation` graph, rejects fork/merge/cycle ambiguity, and
  verifies the actual current relation-head hash rather than trusting a caller
  application hash.
- Obsolete evidence/applications/bundles/decisions remain immutable and
  queryable. A correction creates a new bundle and same-provider successor
  decision; a revocation/collision safety event produces append-only
  `REVIEW_REQUIRED` where a predecessor exists.
- Collision scanning considers current identifier claims, current positive
  identifier applications even when no claim exists, same-provider competing
  candidates, multiple provider subjects for an identifier, canonical issuer
  conflicts, and CP3-C1 provider active/mapping/collision/current-observation
  state. It preserves all claims and selects no first writer.

## Controlled READY and concurrency

`IssuerAuthorityDecisionEngine.evaluate()` accepts only exact subject,
observation, candidate and evidence IDs plus evaluation time. Strict contracts
reject extra caller fields such as `force`, `override`, `is_ready`,
`bridge_ok`, or `authority_weight`. The engine loads source policies, evidence,
observations, relations, applications, claims and provider state itself.

Evaluation runs in SQLite `BEGIN IMMEDIATE`. Before READY persistence it reloads
provider state, all relation heads, exact source policies and the global
collision scan in the same write transaction. Deterministic competing-writer
tests prove a pre-existing collision/relation writer completes first and the
waiting evaluation observes the new unsafe state. Generic low-level repository
READY insertion remains rejected with
`REVIEW_READY_ENGINE_NOT_IMPLEMENTED`; no caller boolean unlocks READY.

The machine emits only `UNRESOLVED`, `READY_FOR_MANUAL_REVIEW`, `STALE`, or
`REVIEW_REQUIRED`. Human `APPROVED/REJECTED/REVOKED/SUPERSEDED` execution is not
implemented.

## Migration integrity

- Migration changes: `0`
- `0006` created/applied: `0`
- Persistent/runtime application of `0005`: `0`
- `0001` SHA-256:
  `6eba164ef2f8bab42583076805255268e4daba29311e8f6e956f4177c0445762`
- `0002` SHA-256:
  `4b6b716999c5f3f6b52be1e85a53685c14c181fb4991e9ead892080717abaee6`
- `0003` SHA-256:
  `b59e74b5e817b6a5606d9f89f1f57eec3e0ba3616918d117d3cc28af4f5c420b`
- `0004` SHA-256:
  `cd1cbcae309f1e56ba923e6463863749c79a84b4c10499801f5da28b0a3a0f4f`
- `0005` SHA-256:
  `a0c2d77d8db0da59b9fc5058182f367cfdd39ff6b306a03a0e61277d6ff4415b`

The disposable migration gate upgraded blank SQLite through `0005`, downgraded
to base, and re-upgraded through `0005`. Fixture idempotency remained intact.

## LOCAL verification evidence

| command/gate | result |
|---|---|
| B2-B targeted `test_authority_decision_engine.py` | `46 passed in 59.27s` |
| B2-A authority contract/repository/migration suites | `69 passed in 43.28s` |
| backend exact discovery | `659` tests |
| full backend | `659 passed in 301.08s` |
| migration repeat/downgrade/re-upgrade | PASS |
| fixture import idempotency | PASS; second run inserted/updated `0`, unchanged `13` |
| frontend Vitest exact inventory/run | `43`; `43 passed` in 10 files |
| Playwright exact inventory/run | `2`; `2 passed` |
| Ruff/format | PASS; 102 Python files formatted as expected |
| mypy | PASS; 60 source files |
| ESLint | PASS, zero warnings |
| TypeScript/Next route type generation | PASS |
| OpenAPI drift | PASS |
| production build | PASS under offline Node guard |
| process cleanup/preflight self-tests | PASS; external requests `0`, credentials `0` |
| secret scan | PASS; `Validated narrow generated-hash exceptions: 2147` |
| policy scan | PASS; B2-B exact scope |
| `git diff --check` / cached check | PASS |
| full `scripts/test.ps1` | PASS; `All Phase 2 CP3-C2-B2-B implementation checks passed.` |

The final complete wrapper ran against the synchronized staged tree and returned
exit `0`. Earlier pre-stage diagnostics exposed the intentional index/worktree
precondition and generated Ruff/mypy cache artifacts; only those generated
caches were removed. The final cache-clean staged secret and policy scans both
passed. All results in this table remain LOCAL evidence, not GitHub CI.

## Exact zero counters and non-scope

- automatic final promotion = `0`
- canonical Issuer writes = `0`
- canonical Security writes = `0`
- `ProviderIdentityMapping(VERIFIED)` writes = `0`
- provider identity/allocation/history rekeys = `0`
- human approval execution = `0`
- WebAuthn operational verification = `0`
- Windows Hello enrollment runtime = `0`
- issuer-authority link execution = `0`
- link-head operational mutation = `0`
- external authority requests = `0`
- Toss live requests = `0`
- operational credentials used = `0`
- account/order/WebSocket/current-price work = `0`
- migration changes = `0`

## Known limitations and deferred work

- Evidence collection/adapters and the authenticated human-assisted IROS/state
  registry ingestion ceremony are not implemented. B2-B evaluates only exact
  pre-existing immutable ledger records.
- Only one exact US formation-state registry (`DE`) is admitted. Other states
  fail closed until individually specified, implemented and reviewed.
- WebAuthn assertion verification, Windows Hello enrollment, approval/auth
  routes, human disposition, canonical issuer/security promotion, issuer-link
  and link-head workflows remain deferred to separately authorized work.
- No GitHub commit status/workflow result exists for this not-yet-pushed commit.
  LOCAL results above are not GitHub CI evidence.

## Final checkpoint states

- ADR-013: `ACCEPTED`
- ADR-014: `ACCEPTED`
- CP3-C2-B1: `PASS — CONTRACT APPROVED AND CLOSED`
- CP3-C2-B implementation: `IN PROGRESS`
- CP3-C2-B2-A: `PASS — CLOSED`
- CP3-C2-B2-B: `IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW`
- CP3-C2-B2-C: `NOT STARTED`
- CP3-C2-B2-D: `NOT STARTED`
- CP3-C2-C: `NOT STARTED`
- CP3-D: `NOT STARTED`
- Automatic checkpoint progression: `PROHIBITED`

This task stops after the B2-B commit/push. It does not authorize or start a
later checkpoint.
