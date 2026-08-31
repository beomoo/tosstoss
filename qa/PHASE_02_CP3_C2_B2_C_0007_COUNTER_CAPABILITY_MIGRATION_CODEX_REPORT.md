# Phase 2 CP3-C2-B2-C — 0007 Counter-Capability Migration Codex Report

## 1. Verdict and authority boundary

- Authoritative starting SHA:
  `de0429a81feb0711376ad054550ceb3141d6ea6a`
- Work branch: `feature/phase-02-b2c-counter-bootstrap`
- User authority: exact `0007` schema implementation and offline migration
  tests only
- Current result: `IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW`
- This report does **not** declare `PASS`, `CLOSED`, or GPT approval.
- R1 WebAuthn/human-approval runtime remains
  `NOT STARTED / REQUIRES SEPARATE AUTHORIZATION`.
- Public Read-only Deployment and Automated Trading remain
  `FUTURE / NOT AUTHORIZED / NOT STARTED`.
- Automatic progression remains `PROHIBITED`.

## 2. Migration identity and strategy

- Path:
  `services/api/alembic/versions/0007_phase_02_cp3_c2_b2_c_counter_capability_bootstrap.py`
- `revision`:
  `0007_phase_02_cp3_c2_b2_c_counter_capability_bootstrap`
- `down_revision`:
  `0006_phase_02_cp3_c2_b2_c_reviewer_operations`
- Strategy: additive tables, indexes, and guards, except the accepted same-name
  version replacement of exactly two frozen counter-union triggers
- Existing table rebuilds: `0`
- Existing migration edits: `0`
- Existing row rewrites: `0`
- Persistent `var/dashboard.db` applications: `0`

Upgrade verifies the frozen predecessor blobs and required exact `0006` object
surface before mutation. A failed upgrade restores the two legacy counter-union
triggers before removing only newly created objects. Downgrade refuses non-empty
new tables, restores the exact `0006` definitions of both replaced triggers,
drops only `0007` objects, and leaves frozen tables and rows untouched.

## 3. Frozen migration evidence

| migration | required and observed Git blob |
|---|---|
| `0001_phase_01_foundation.py` | `d00355c2456021e6ffb195e50833adc32c74a4ad` |
| `0002_phase_02_cp3_foundation.py` | `53f40664eca2ea2466cc6154b8579c5db506e0ba` |
| `0003_phase_02_cp3_b_invariants.py` | `47d5a69009949b155211cd68209640136a7cacd9` |
| `0004_phase_02_cp3_c1_security_master.py` | `91b4d96a445be23e7aa55e08b9310dc7334a026d` |
| `0005_phase_02_cp3_c2_b_issuer_authority.py` | `81976b8f70a1f6107526a13acadf23f369b196e3` |
| `0006_phase_02_cp3_c2_b2_c_reviewer_operations.py` | `f10e7f5bc21e232fc68b38144f5b8fb124f31698` |

The migration and its tests independently verify these exact blobs. Final
pre-commit verification is recorded in section 10.

## 4. Exact schema inventory

### Tables

Exactly three append-only tables are created:

1. `reviewer_webauthn_counter_capability_registrations` — 49 columns
2. `reviewer_webauthn_counter_capability_challenges` — 32 columns
3. `reviewer_webauthn_counter_capability_assertions` — 55 columns

Every accepted column, type, nullability group, CHECK, primary/UNIQUE key,
ordered composite FK, exact-copy projection, content hash, and binding field is
covered by the dedicated schema tests. There is no fourth state table, mutable
current-state table, or JSON authority substitute.

### Indexes

The exhaustive 23-index inventory is:

1. `uq_0007_reviewer_credential_operation_outcomes_bootstrap_projection`
2. `uq_0007_credential_event_authorization_projection`
3. `uq_0007_cc_registration_content`
4. `uq_0007_cc_registration_parent`
5. `uq_0007_cc_registration_child`
6. `uq_0007_cc_registration_credential`
7. `uq_0007_cc_registration_credential_fingerprint`
8. `uq_0007_cc_registration_public_key_fingerprint`
9. `uq_0007_cc_registration_exact_copy`
10. `uq_0007_cc_registration_assertion_copy`
11. `ix_counter_capability_registrations_operation`
12. `uq_0007_cc_challenge_digest`
13. `uq_0007_cc_challenge_binding`
14. `uq_0007_cc_challenge_registration`
15. `uq_0007_cc_challenge_exact_child`
16. `uq_0007_cc_challenge_exact_copy`
17. `ix_counter_capability_challenges_expiry`
18. `uq_0007_cc_assertion_content`
19. `uq_0007_cc_assertion_challenge`
20. `uq_0007_cc_assertion_registration`
21. `uq_0007_cc_assertion_consumption_projection`
22. `uq_0007_cc_assertion_outcome_projection`
23. `ix_counter_capability_assertions_operation`

Dedicated tests compare exact ordered index columns, not only index names.

### New triggers

The 15 new triggers are:

- Append-only denial, two per new table:
  - `trg_reviewer_webauthn_counter_capability_registrations_append_only_update`
  - `trg_reviewer_webauthn_counter_capability_registrations_append_only_delete`
  - `trg_reviewer_webauthn_counter_capability_challenges_append_only_update`
  - `trg_reviewer_webauthn_counter_capability_challenges_append_only_delete`
  - `trg_reviewer_webauthn_counter_capability_assertions_append_only_update`
  - `trg_reviewer_webauthn_counter_capability_assertions_append_only_delete`
- Insert/projection/counter guards:
  - `trg_0007_counter_capability_registrations_insert_guard`
  - `trg_0007_counter_capability_challenges_insert_guard`
  - `trg_0007_counter_capability_assertions_insert_guard`
  - `trg_0007_operation_consumptions_bootstrap_projection_guard`
  - `trg_0007_operation_outcomes_bootstrap_projection_guard`
  - `trg_0007_credentials_counter_bootstrap_guard`
  - `trg_0007_credential_event_authorizations_counter_bootstrap_guard`
  - `trg_0007_credential_events_counter_bootstrap_guard`
  - `trg_0007_counter_capability_assertions_counter_union_guard`

Exactly two frozen counter-union definitions are version-replaced under their
existing names:

1. `trg_reviewer_authentication_events_counter_union_guard`
2. `trg_reviewer_credential_operation_authentication_counter_union_guard`

The upgrade definitions preserve the prior issuer/operation counter protections
and admit only the accepted supported bootstrap edge. Downgrade recreates the
exact normalized SQL emitted by frozen `0006`; dedicated tests compare both
definitions byte-for-byte after normalization.

## 5. Dedicated 66-test matrix

`tests/backend/test_counter_capability_migration.py` covers:

- clean `0001 -> 0007`, `0007 -> 0006`, and `0006 -> 0007`;
- late-upgrade injected failure cleanup back to exact `0006` objects/triggers;
- exact migration identity, single `0007` head, and frozen `0001`–`0006` blobs;
- exact three-table column/type/nullability/default/PK inventory;
- exact 23-index names, uniqueness, and ordered columns;
- exact FK child and ordered parent-column targets;
- exact 15-new-trigger inventory and two replaced-trigger definitions;
- downgrade restoration of exact `0006` counter-union SQL;
- FIRST/ADD/REPLACE pending creation, single-use and collision behavior;
- rejection of duplicate pending, expired/consumed/terminal parent, and child
  expiry later than parent;
- the nine terminal transactions and accepted insertion order;
- selected invalid orderings that must fail immediately/fail closed;
- FIRST/ADD lifecycle cardinality and REPLACE exact registration/supersession
  authorization/event cardinality;
- three expiry projections with unchanged credential state and zero lifecycle
  writes;
- wrong principal, operation hash, SID hash, credential/fingerprint, public-key
  fingerprint, parent challenge, purpose, outcome ID/hash, and resulting state;
- fake success/credential, invalid supersession projection, failed-assertion
  writes, duplicate consumption/outcome, replay and counter fork;
- exact cause-bearing failure-result verification facts, assertion consumption
  not before child issuance, and distinct child/overall safe-code roles;
- UPDATE and DELETE rejection on each new table;
- supported bootstrap continuation into the later counter union, unique
  bootstrap edge, distinct fork/duplicate rejection, no fabricated registration
  zero for `NO_USABLE_COUNTER`, and
  the unaffected positive-registration direct path;
- unrelated active-credential exact preservation and pending-stage lifecycle
  event count preservation;
- non-empty downgrade refusal; and
- `PRAGMA foreign_key_check == []` after every committed representative flow.

## 6. Nine representative terminal results

| operation | classification/result | committed projection | FK rows |
|---|---|---|---:|
| FIRST | `0 -> positive` | supported edge; one credential, registration authorization/event, successful outcome | 0 |
| FIRST | `0 -> 0` | no-usable-counter; `registration_sign_count=NULL`; one credential, registration authorization/event, successful outcome | 0 |
| FIRST | failure | failed assertion/consumption/outcome; unchanged state; zero credential/event/authorization | 0 |
| ADD | `0 -> positive` | supported edge; prior authorizer history preserved; one new credential and registration authorization/event | 0 |
| ADD | `0 -> 0` | no-usable-counter; prior authorizer history preserved; one new credential and registration authorization/event | 0 |
| ADD | failure | prior authorizer history preserved; unchanged state; zero new credential/event/authorization | 0 |
| REPLACE | `0 -> positive` | supported edge; new registration authorization/event plus exact old supersession authorization/event | 0 |
| REPLACE | `0 -> 0` | no-usable-counter; new registration authorization/event plus exact old supersession authorization/event | 0 |
| REPLACE | failure | old target remains active; unchanged state; zero new credential/event/authorization | 0 |

All nine transactions use the accepted assertion-first/outcome-last ordering.
FIRST and ADD have six ordered writes on success; REPLACE has eight. Failure
and expiry use assertion, frozen consumption, then frozen outcome only.

Explicit FIRST, ADD, and REPLACE expiry cases produced `EXPIRED` frozen
projections, equal expected/resulting state hashes, zero credential/lifecycle
writes, and zero foreign-key-check rows. Child expiry beyond the parent and
success at/after either expiry are rejected.

## 7. Changed files

Implementation and tests:

- `services/api/alembic/versions/0007_phase_02_cp3_c2_b2_c_counter_capability_bootstrap.py`
- `tests/backend/test_counter_capability_migration.py`
- `tests/backend/test_migrations.py`
- `tests/backend/test_provider_migration.py`
- `tests/backend/test_repositories.py`
- `services/api/src/toss_dashboard_api/repositories/sqlite.py` — one additive
  internal revision-compatibility allowlist entry only
- `scripts/test.ps1`
- `scripts/policy-scan.ps1`
- `scripts/secret-scan.ps1`

Current-status and evidence documentation:

- `STATUS.md`
- `CHANGELOG.md`
- `KNOWN_ISSUES.md`
- `plans/PHASE_02_EXECUTION_PLAN.md`
- `plans/PHASE_02_CP3_C2_B1_RUNTIME_CONTRACT.md`
- `plans/PHASE_02_CP3_C2_B2_C_SCHEMA_REMEDIATION.md`
- `plans/PHASE_02_CP3_C2_B2_C_ADR_018_COUNTER_CAPABILITY_SCHEMA_PROPOSAL.md`
- `qa/PHASE_02_CP3_C2_B2_C_0007_COUNTER_CAPABILITY_MIGRATION_CODEX_REPORT.md`

No dependency, package manifest, fixture, frontend, route, service, WebAuthn,
SID/filesystem adapter, public deployment, or trading file changed. No sample
JSON or UI screenshot was generated because this is a schema-only checkpoint.

## 8. Scope and security accounting

- WebAuthn application/runtime behavior: `0`
- WebAuthn service/route/UI additions: `0`
- SID/filesystem-owner runtime adapters: `0`
- Issuer approval/canonical/link execution: `0`
- Dependency changes: `0`
- Persistent DB applications: `0`
- Production credential/reviewer rows: `0`
- External authority/provider calls: `0`
- OpenAI API calls: `0`
- Account/order/trading implementation: `0`
- Public network exposure: `0`

The single repository application-file line is only the established additive
revision-compatibility declaration required so the unchanged read-only runtime
accepts a database already migrated to the new additive head. It introduces no
ceremony, write path, route, or business behavior.

`LOCAL_ONLY=true`, `TRADING_ENABLED=false`, and `DRY_RUN=true` remain unchanged.

## 9. QA execution evidence

| check | result |
|---|---|
| dedicated `test_counter_capability_migration.py` | `66 passed in 167.85s` |
| existing `test_reviewer_operation_migration.py` | `83 passed in 229.62s` |
| existing `test_authority_migration.py` | `19 passed in 57.11s` |
| existing `test_migrations.py` | `2 passed in 27.67s` |
| first full backend diagnostic | `4 failed, 837 passed in 953.03s`; all four identified the missing additive head compatibility entry |
| focused rerun after one-line compatibility fix | `4 passed in 11.86s` |
| final full backend suite | `851 passed in 971.60s (0:16:11)` |
| migration disposable upgrade/repeat/downgrade/re-upgrade | `PASS` |
| fixture import/re-import idempotency | `PASS` — 13 inserted, then 13 unchanged |
| frontend tests | `43 passed` in 10 files |
| lint/format | `PASS`; 105 files formatted-check, Ruff, ESLint; explicit migration/test Ruff check also passed |
| backend/frontend typecheck | `PASS`; mypy 60 source files, guarded Node/Next type generation and `tsc` |
| frontend production build | `PASS` |
| E2E | `2 passed in 16.7s` |
| policy scan | `PASS` |
| secret scan | `PASS`; pre-harness staged scan validated 2167 narrow generated-hash exceptions, and the standard post-build scan validated 2169 |
| `git diff --check` / cached check | `PASS` after this evidence-only documentation update |
| standard `scripts/test.ps1` | `PASS`; `All Phase 2 CP3-C2-B2-C schema implementation checks passed.` |

The standard harness completed on the fully staged implementation snapshot
before this evidence-only result update. After recording the results, the diff,
policy, secret, frozen-blob, dependency, migration-inventory, generated-artifact,
and remote-ref guards were rerun on the final staged tree. No implementation or
test change followed the successful standard harness.

The first full-backend failure was not hidden or weakened. The existing runtime
tests correctly rejected unknown head `0007`; the same one-line compatibility
pattern previously used for additive revisions was extended, and all four
failing cases passed before scheduling the full final rerun.

The first typecheck attempt exposed a missing compiled file inside the existing
local `mypy==1.17.1` environment. Reinstalling the exact already-locked package
version from the cached wheel repaired the local QA environment. No requirement,
lock, package manifest, or dependency version changed.

## 10. Final pre-commit checklist

- [x] final full 851-test backend run passes
- [x] standard staged-snapshot `scripts/test.ps1` passes
- [x] `git diff --check` and `git diff --cached --check` pass
- [x] policy and secret scans pass on the staged snapshot
- [x] exactly one `0007` migration exists
- [x] frozen `0001`–`0006` blobs match section 3
- [x] dependency manifests and locks have zero diff
- [x] no persistent DB, `.next`, cache, bytecode, or temporary DB is tracked;
      disposable generated outputs were removed before commit
- [x] remote `feature/phase-02-toss` and `main` remain at authorized SHAs

## 11. Known limitations and independent evidence status

- GitHub CI workflow/check-run evidence is `ABSENT / NOT INDEPENDENTLY VERIFIED`.
  LOCAL QA is not represented as GitHub CI; KI-018 remains open/non-blocking.
- Future public redistribution/publication eligibility is not resolved; KI-017
  remains open/non-blocking and Public Read-only Deployment remains future.
- No real WebAuthn/passkey/Windows Hello ceremony ran. This task does not test or
  authorize R1 runtime behavior.
- No migration was applied to the persistent authority database. Operational
  rollout, backup, and restore remain outside this implementation-only task.
- The migration implementation and tests require independent GPT review before
  any user-authorized closeout. Current status must remain
  `IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW`.
