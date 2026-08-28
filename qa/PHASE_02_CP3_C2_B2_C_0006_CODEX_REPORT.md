# Phase 2 CP3-C2-B2-C 0006 Codex Report

## 1. Report identity and result boundary

- Evidence type: `Codex LOCAL implementation self-QA`
- Repository: `beomoo/tosstoss`
- Branch: `feature/phase-02-toss`
- Authoritative starting SHA:
  `4104973d84307b80a236d9b737b2d29339b27153`
- Final SHA note: the commit containing this report is identified in the final
  handoff after commit/push; embedding that commit's SHA here would change it
- Date: `2026-08-28` (`Asia/Seoul`)
- Checkpoint: `CP3-C2-B2-C — 0006 Reviewer Credential-Operation Ledger Schema Implementation`
- Schema result: `IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW`
- B2-C WebAuthn/human-approval runtime: `NOT STARTED / NOT AUTHORIZED`

This report does not declare migration `0006` or CP3-C2-B2-C PASS/CLOSED. All
test results below are LOCAL evidence, not GitHub CI execution evidence.

## 2. Decision state and authorized scope

- ADR-015 — WebAuthn Enrollment and Credential-Operation Ledger Amendment:
  `ACCEPTED` on `2026-08-28`
- ADR-016 — Reviewer Operation Exact SQLite Binding Amendment: `ACCEPTED` on
  `2026-08-28`
- ADR-016 review basis: GPT independent review of SHA
  `4104973d84307b80a236d9b737b2d29339b27153` returned `PASS WITH CLOSEOUT
  CONDITION`, P0 `0`, P1 `0`, P2 `1` non-blocking; IG-01 and IG-02 were closed,
  and the user explicitly accepted the decision
- Governing schema contract:
  `plans/PHASE_02_CP3_C2_B2_C_SCHEMA_REMEDIATION.md`
- Strategy: additive only; existing-table rebuilds `0`; synthetic backfill `0`
- Production application change: one revision-compatibility allowlist entry in
  `repositories/sqlite.py`; WebAuthn/runtime behavior added there `0`

## 3. Exact changed paths

1. `CHANGELOG.md`
2. `DECISIONS.md`
3. `KNOWN_ISSUES.md`
4. `STATUS.md`
5. `plans/PHASE_02_CP3_C2_B1_RUNTIME_CONTRACT.md`
6. `plans/PHASE_02_CP3_C2_B2_C_SCHEMA_REMEDIATION.md`
7. `plans/PHASE_02_EXECUTION_PLAN.md`
8. `qa/PHASE_02_CP3_C2_B2_C_0006_CODEX_REPORT.md`
9. `scripts/policy-scan.ps1`
10. `scripts/secret-scan.ps1`
11. `scripts/test.ps1`
12. `services/api/alembic/versions/0006_phase_02_cp3_c2_b2_c_reviewer_operations.py`
13. `services/api/src/toss_dashboard_api/repositories/sqlite.py`
14. `tests/backend/test_authority_migration.py`
15. `tests/backend/test_migrations.py`
16. `tests/backend/test_provider_migration.py`
17. `tests/backend/test_repositories.py`
18. `tests/backend/test_reviewer_operation_migration.py`

Application-source changes outside the one revision-compatibility entry: `0`.
Frontend, dependency, fixture and runtime-route changes: `0`.

## 4. Revision and six-table inventory

- Revision: `0006_phase_02_cp3_c2_b2_c_reviewer_operations`
- Down revision: `0005_phase_02_cp3_c2_b_issuer_authority`
- New tables: `6`
- Named additive indexes: `23`
- New triggers: `23` (`12` append-only plus `11` insert/counter guards)

Exact tables:

1. `reviewer_credential_operations`
2. `reviewer_credential_operation_challenges`
3. `reviewer_credential_operation_challenge_consumptions`
4. `reviewer_credential_operation_authentication_events`
5. `reviewer_webauthn_credential_event_authorizations`
6. `reviewer_credential_operation_outcomes`

## 5. Exact named index inventory

Existing-0005 additive indexes:

1. `uq_reviewer_principals_active_local_steward`
2. `uq_reviewer_principals_exact_owner_binding`
3. `uq_reviewer_credentials_exact_target`
4. `uq_reviewer_credentials_exact_content`
5. `uq_reviewer_credentials_exact_registration`
6. `uq_reviewer_credential_events_exact_authorization`
7. `uq_reviewer_credential_events_root`
8. `ix_reviewer_authentication_counter_chain`

New-ledger indexes:

9. `uq_reviewer_credential_operations_exact_binding`
10. `uq_reviewer_credential_operations_exact_subject`
11. `uq_reviewer_credential_operations_root`
12. `uq_reviewer_credential_operations_successor`
13. `uq_reviewer_credential_operation_challenges_exact_operation_step`
14. `uq_reviewer_credential_operation_challenges_exact_binding`
15. `uq_reviewer_credential_operation_challenge_step`
16. `ix_reviewer_credential_operation_challenge_expiry`
17. `uq_reviewer_credential_operation_consumptions_exact_terminal`
18. `uq_reviewer_credential_operation_consumptions_exact_registration`
19. `uq_reviewer_credential_operation_authentication_exact_result`
20. `uq_reviewer_credential_operation_outcomes_exact_terminal`
21. `uq_reviewer_credential_operation_outcomes_exact_success`
22. `uq_reviewer_credential_event_authorization_step`
23. `ix_reviewer_credential_operation_counter_chain`

No weaker subset UNIQUE operation identity was added.

## 6. Exact trigger inventory

Append-only triggers (`UPDATE` and `DELETE` for each new table):

1. `trg_reviewer_credential_operations_append_only_update`
2. `trg_reviewer_credential_operations_append_only_delete`
3. `trg_reviewer_credential_operation_challenges_append_only_update`
4. `trg_reviewer_credential_operation_challenges_append_only_delete`
5. `trg_reviewer_credential_operation_challenge_consumptions_append_only_update`
6. `trg_reviewer_credential_operation_challenge_consumptions_append_only_delete`
7. `trg_reviewer_credential_operation_authentication_events_append_only_update`
8. `trg_reviewer_credential_operation_authentication_events_append_only_delete`
9. `trg_reviewer_webauthn_credential_event_authorizations_append_only_update`
10. `trg_reviewer_webauthn_credential_event_authorizations_append_only_delete`
11. `trg_reviewer_credential_operation_outcomes_append_only_update`
12. `trg_reviewer_credential_operation_outcomes_append_only_delete`

Insert/counter guards:

13. `trg_reviewer_credential_operations_insert_guard`
14. `trg_reviewer_credential_operation_challenges_insert_guard`
15. `trg_reviewer_credential_operation_consumptions_insert_guard`
16. `trg_reviewer_webauthn_credentials_requires_registration_proof`
17. `trg_reviewer_webauthn_credential_events_requires_authorization`
18. `trg_reviewer_webauthn_credential_events_chain_guard`
19. `trg_reviewer_credential_operation_authentication_active_guard`
20. `trg_reviewer_credential_operation_outcomes_insert_guard`
21. `trg_reviewer_authentication_events_credential_active_guard`
22. `trg_reviewer_authentication_events_counter_union_guard`
23. `trg_reviewer_credential_operation_authentication_counter_union_guard`

The five guards on existing reviewer tables require registration proof,
lifecycle authorization and exact lifecycle chaining, reject issuer auth by a
non-active credential, and serialize the issuer/operation authentication
counter union. Existing append-only triggers were not weakened.

## 7. ADR-016 implementation evidence

### Closed authorization enum and matrix

The `authorization_kind` CHECK permits exactly:

- `BOOTSTRAP_REGISTRATION`
- `AUTHORIZED_REGISTRATION`
- `AUTHORIZED_SUPERSESSION`
- `AUTHORIZED_REVOCATION`

The authorization insert guard permits exactly the five approved
operation/event/kind rows. A parameterized negative test enumerates and rejects
all other combinations. No generic lifecycle token, free-form token or
`payload_json` authority exists.

### Exact operation and successful-outcome bindings

Both authorization and outcome rows include non-null `reviewer_role`,
`principal_content_hash`, and `os_owner_sid_hash`, with role fixed to
`LOCAL_DATA_STEWARD` and both hashes checked as exact lowercase
`sha256:<64 hex>` values.

Both child tables use the exact ordered eight-column deferred FK to
`uq_reviewer_credential_operations_exact_binding`:

```text
reviewer_credential_operation_id,
operation_content_hash,
reviewer_principal_id,
reviewer_role,
principal_content_hash,
os_owner_sid_hash,
operation_type,
expected_credential_state_hash
```

Authorization uses the exact ordered eleven-column successful-outcome FK,
including outcome ID/hash, operation ID/hash, the complete principal trust
tuple, `SUCCEEDED`, expected state and resulting state. A mismatch in any trust
column is rejected relationally.

### Content-hash preimages

Trusted-server test vectors cover `reviewer_role`, `principal_content_hash` and
`os_owner_sid_hash` in both `authorization_content_hash` and
`outcome_content_hash`; mutating each field changes the corresponding hash.
Audit timestamps and `payload_json` remain excluded. SQLite performs no
aggregate credential-state hashing and declares/calls no `sha256()` SQL
function.

## 8. SG/P1 relational enforcement evidence

- SG-01: exact active local steward, unique FIRST_ENROLLMENT root, 32-byte
  registration challenge, bounded expiry, unique consumption, exact successful
  registration/public credential/lifecycle/outcome proof, and permanent
  first-enrollment closure after any historical successful registration
- SG-02: credential-operation challenges, consumptions and authentication
  events are separate from issuer approval challenges/authentication; neither FK
  graph can substitute for the other
- P1-SR-01: authenticated final-active-credential revoke is accepted, appends
  exact REVOKED/AUTHORIZED_REVOCATION history and leaves an exact empty active
  set; later issuer/add/replace/revoke attempts fail closed and bootstrap does
  not reopen
- P1-SR-02: aggregate `reviewer-credential-state/0.1.0` hashes remain trusted
  server values copied relationally; counter values are excluded and no SQLite
  SHA dependency exists
- P1-SR-03: terminal consumptions bind exactly one deferred outcome; the only
  continuation is successful ADD/REPLACE AUTHORIZATION_ASSERTION with one
  VERIFIED operation-auth event and one bounded REGISTRATION_CREATE challenge
- REPLACE success requires the same-operation REGISTERED plus SUPERSEDED pair
  and exact `AUTHORIZED_REGISTRATION` plus `AUTHORIZED_SUPERSESSION` companions
- REVOKE success requires the exact target REVOKED plus
  `AUTHORIZED_REVOCATION` companion
- Failed registration preserves the immutable VERIFIED counter event, writes no
  lifecycle transition, terminalizes with unchanged state and supplies the
  successor operation's exact predecessor state

## 9. Signature-counter union evidence

The two append-only histories are reconstructed together:

- existing `reviewer_authentication_events`
- new `reviewer_credential_operation_authentication_events`

For `SIGN_COUNT_SUPPORTED`, tests cover registration-count root, strict
increase, exact prior/asserted adjacency, equality rejection, rollback
rejection, gap rejection, fork rejection, and one-winner issuer-auth versus
operation-auth race behavior. For `NO_USABLE_COUNTER`, previous and asserted
counts remain exact `NULL/NULL`; zero is never fabricated. No mutable current
counter column was introduced.

## 10. Upgrade, failure and downgrade evidence

- Blank database upgrade `0001 -> 0006`: `PASS`
- Populated non-reviewer `0005 -> 0006`: `PASS`; authority evidence, bundle and
  decision data preserved
- Unexpected reviewer/authentication lineage: `FAIL CLOSED`; no synthetic
  backfill
- Conflicting 0006 object name: `FAIL CLOSED`
- Deliberately injected late DDL failure: `PASS`; only attempt-owned 0006
  objects rolled back/removed, Alembic remains at `0005`, predecessor data is
  unchanged, and retry succeeds
- Empty disposable downgrade and re-upgrade: `PASS`
- Non-empty ledger downgrade: `FAIL CLOSED`; no audit history deletion
- Valid transaction `PRAGMA foreign_keys=ON` and
  `PRAGMA foreign_key_check`: `PASS / clean`
- Malformed nullable reference groups: `REJECTED`

## 11. Frozen migration integrity

| Migration | Required and observed Git blob ID | Result |
|---|---|---|
| `0001_phase_01_foundation.py` | `d00355c2456021e6ffb195e50833adc32c74a4ad` | `MATCH` |
| `0002_phase_02_cp3_foundation.py` | `53f40664eca2ea2466cc6154b8579c5db506e0ba` | `MATCH` |
| `0003_phase_02_cp3_b_invariants.py` | `47d5a69009949b155211cd68209640136a7cacd9` | `MATCH` |
| `0004_phase_02_cp3_c1_security_master.py` | `91b4d96a445be23e7aa55e08b9310dc7334a026d` | `MATCH` |
| `0005_phase_02_cp3_c2_b_issuer_authority.py` | `81976b8f70a1f6107526a13acadf23f369b196e3` | `MATCH` |

Frozen migration edits/rebuilds: `0`.

## 12. LOCAL test evidence

| Command/scope | Result |
|---|---|
| `test_reviewer_operation_migration.py` inventory | `83 collected` |
| Isolated 0006 schema tests | `83 passed` |
| All migration tests | `118 passed in 176.72s` |
| B2-A/B2-B authority regression | `158 passed in 222.45s` |
| Full backend suite | `785 passed in 641.65s` |
| Backend Ruff format/check | `104 files formatted; all checks passed` |
| Backend mypy | `Success: no issues found in 60 source files` |
| Frontend ESLint | `PASS — 0 warnings` |
| Frontend TypeScript typecheck | `PASS` |
| Frontend Vitest | `43 passed in 10 files` |
| OpenAPI generated-type drift check | `PASS` |
| Production build | `PASS — two consecutive builds` |
| Playwright E2E | `2 passed` |
| Migration repeat/downgrade/re-upgrade | `PASS` |
| Fixture import idempotency | `PASS — second import inserted 0 / updated 0 / unchanged 13` |
| Toss safe preflight | `OFFLINE; external requests 0; credentials 0` |
| Toss self-test | `PASS; external requests 0` |
| `scripts/test.ps1` final staged run | `PASS — exit 0` |
| Secret scan on final staged set | `PASS` |
| Policy scan on final staged set | `PASS` |
| `git diff --check` / `git diff --cached --check` | `PASS / PASS` |

The final staged full harness completed every gate and exited `0`. Earlier
diagnostic passes correctly rejected generated local cache artifacts and an
unstaged index; both were removed/resolved before the final run and were not
secret findings. The final secret scanner narrowly recognizes the five frozen
predecessor Git blob IDs in the migration and integrity test only after
recomputing and matching each approved blob.

## 13. Automated QA safety counters

- Real Windows Hello enrollment: `0`
- Windows Hello dialogs: `0`
- Actual user SID persisted as a fixture: `0`
- Real human issuer approvals: `0`
- Persistent canonical Issuer writes: `0`
- Canonical Security writes: `0`
- `ProviderIdentityMapping(VERIFIED)` writes: `0`
- Provider rekeys: `0`
- Live authority requests: `0`
- Live Toss requests: `0`
- Orders/WebSocket/current-price work: `0`
- B2-C WebAuthn/human-approval runtime implementation: `0`
- GitHub CI execution evidence: `ABSENT — NON-BLOCKING P2`

## 14. Final checkpoint state

- ADR-015: `ACCEPTED` (`2026-08-28`)
- ADR-016: `ACCEPTED` (`2026-08-28`)
- `0006`: `IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW`
- CP3-C2-B2-C runtime: `NOT STARTED / NOT AUTHORIZED`
- CP3-C2-B2-D: `NOT STARTED`
- CP3-C2-C: `NOT STARTED`
- CP3-D: `NOT STARTED`
- Automatic progression: `PROHIBITED`

The next permitted action is GPT independent review of the `0006`
implementation. No later checkpoint or runtime work began.
