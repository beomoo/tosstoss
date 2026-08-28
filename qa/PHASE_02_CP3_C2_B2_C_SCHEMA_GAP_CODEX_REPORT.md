# Phase 2 CP3-C2-B2-C Schema Gap Codex Report

## 1. Report identity

- Evidence type: `Codex LOCAL documentation/design self-QA`
- Repository: `beomoo/tosstoss`
- Branch: `feature/phase-02-toss`
- Starting SHA: `60f2805d2390c91a026b3381877006be9000dedb`
- Final SHA note: the resulting commit SHA is reported after commit/push;
  embedding it here would change that SHA
- Date: `2026-08-28` (`Asia/Seoul`)
- Checkpoint:
  `CP3-C2-B2-C — SCHEMA CONTRACT REMEDIATION — DOCUMENTATION ONLY`
- Result:
  `BLOCKED — SCHEMA CONTRACT GAP / SCHEMA REMEDIATION AWAITING GPT INDEPENDENT REVIEW`
- P0: `0`
- Confirmed schema blockers: `2`
- P2: `GitHub CI execution evidence absent — NON-BLOCKING`

This report is Codex self-QA evidence. It does not declare GPT PASS, accept
ADR-015, authorize migration `0006`, or resume B2-C runtime implementation.

## 2. Independent verification incorporated

### SG-01 — first enrollment bootstrap

Confirmed. Frozen `0005` cannot durably represent a server-created,
Windows-owner-SID-bound first-enrollment bootstrap, `webauthn.create` challenge,
finite expiry and one terminal success/failure consumption before a credential
exists.

### SG-02 — credential-management reauthentication

Confirmed. `reviewer_authentication_events` is correctly bound to an issuer
approval challenge, decision, bundle and issuer disposition. It cannot
relationally represent `ADD_CREDENTIAL`/`REPLACE_CREDENTIAL` authorization or
their signature-counter advancement without falsifying issuer audit meaning.

### Corrected non-blocker

Issuer `SUPERSEDED` is not treated as a schema blocker. Existing `0005` can
represent separately authenticated old `SUPERSEDED` and successor `APPROVED`
events/link versions in one `BEGIN IMMEDIATE` transaction followed by guarded
head CAS.

## 3. Proposed remediation

- ADR: `ADR-015 — WebAuthn Enrollment and Credential-Operation Ledger
  Amendment`
- ADR state: `PROPOSED`
- Detailed plan:
  `plans/PHASE_02_CP3_C2_B2_C_SCHEMA_REMEDIATION.md`
- Selected approach: `A — additive new tables plus additive indexes/triggers`
- Existing `0005` table rebuild/alter: `0`

The exact future migration proposal is:

- Filename:
  `services/api/alembic/versions/0006_phase_02_cp3_c2_b2_c_reviewer_operations.py`
- Revision: `0006_phase_02_cp3_c2_b2_c_reviewer_operations`
- Down revision: `0005_phase_02_cp3_c2_b_issuer_authority`
- File created in this task: `0`
- Migration applied in this task: `0`

Six proposed append-only tables:

1. `reviewer_credential_operations`
2. `reviewer_credential_operation_challenges`
3. `reviewer_credential_operation_challenge_consumptions`
4. `reviewer_credential_operation_authentication_events`
5. `reviewer_webauthn_credential_event_authorizations`
6. `reviewer_credential_operation_outcomes`

The proposal specifies every relational column, FK, CHECK, UNIQUE/index and
trigger invariant, including:

- one active server-owned local steward and exact hashed Windows SID binding;
- one linear operation chain and exact current active-credential-state hash;
- distinct `REGISTRATION_CREATE` and `AUTHORIZATION_ASSERTION` purposes;
- fresh 32-byte OS-CSPRNG challenge digest/binding and at-most-five-minute
  expiry;
- exactly one terminal consumption, including failed attempts;
- exact same-principal active authorizing credential;
- mandatory cryptographic authorization companion for every future
  `REGISTERED|REVOKED|SUPERSEDED` event;
- no issuer-approval/credential-operation authentication substitution;
- counter reconstruction from immutable registration count plus both
  append-only authentication ledgers;
- no mutable current counter, unauthenticated recovery, force or override; and
- no password, PIN, biometric, private key, raw nonce, bearer/cookie or private
  authenticator material.

A second DDL-level review against frozen `0005` also made every SQLite
composite-FK parent tuple explicit. Nullable target fields are verified with
null-safe guards rather than placed in a composite FK (which SQLite would skip
when any child column is null), and lifecycle/registration/operation references
carry exact immutable content hashes plus checked purpose/result constants.

## 4. Exact changed paths

1. `CHANGELOG.md`
2. `DECISIONS.md`
3. `KNOWN_ISSUES.md`
4. `STATUS.md`
5. `plans/PHASE_02_CP3_C2_B1_RUNTIME_CONTRACT.md`
6. `plans/PHASE_02_CP3_C2_B2_C_SCHEMA_REMEDIATION.md`
7. `plans/PHASE_02_EXECUTION_PLAN.md`
8. `qa/PHASE_02_CP3_C2_B2_C_SCHEMA_GAP_CODEX_REPORT.md`

## 5. Migration integrity

| Migration | Starting SHA-256 | Result |
|---|---|---|
| `0001_phase_01_foundation.py` | `6eba164ef2f8bab42583076805255268e4daba29311e8f6e956f4177c0445762` | `MATCH — unchanged` |
| `0002_phase_02_cp3_foundation.py` | `4b6b716999c5f3f6b52be1e85a53685c14c181fb4991e9ead892080717abaee6` | `MATCH — unchanged` |
| `0003_phase_02_cp3_b_invariants.py` | `b59e74b5e817b6a5606d9f89f1f57eec3e0ba3616918d117d3cc28af4f5c420b` | `MATCH — unchanged` |
| `0004_phase_02_cp3_c1_security_master.py` | `cd1cbcae309f1e56ba923e6463863749c79a84b4c10499801f5da28b0a3a0f4f` | `MATCH — unchanged` |
| `0005_phase_02_cp3_c2_b_issuer_authority.py` | `a0c2d77d8db0da59b9fc5058182f367cfdd39ff6b306a03a0e61277d6ff4415b` | `MATCH — unchanged` |

- Migration changed paths: `0`
- `0006` files present: `0`
- Persistent/runtime `0005` application: `0`

## 6. LOCAL documentation QA

| Check | Result |
|---|---|
| Documentation/control-plane-only changed paths | `PASS — exact 8 declared paths` |
| `services/api/src/**` changed paths | `0 — PASS` |
| `tests/**` changed paths | `0 — PASS` |
| `scripts/**` changed paths | `0 — PASS` |
| Frontend changed paths | `0 — PASS` |
| Dependency changed paths | `0 — PASS` |
| Migration changed paths | `0 — PASS` |
| `0001`–`0005` SHA-256 equality | `PASS` |
| `0006` absent | `PASS` |
| Remote `main` remains `353159da45cfbe3a7f444bf476ce86fa9aece17c` | `PASS` |
| `git diff --check` | `PASS` |
| `git diff --cached --check` | `PASS` |
| Existing secret scan | `PASS` |
| Existing policy scan | `PASS` |
| Status/ADR consistency | `PASS` |

These are LOCAL Codex checks against the final staged snapshot, not GitHub CI
evidence. The pre-staging secret-scan invocation correctly refused to scan an
index/worktree mismatch; the final staged-snapshot invocation passed.

## 7. Zero counters

- Application/runtime changes = `0`
- `services/api/src/**` changes = `0`
- Executable test changes = `0`
- Script changes = `0`
- Frontend changes = `0`
- Dependency changes = `0`
- Migration changes = `0`
- `0006` creation/application = `0`
- Real Windows Hello enrollment = `0`
- Credential/private-secret persistence = `0`
- Human issuer approval execution = `0`
- Canonical Issuer writes = `0`
- Canonical Security writes = `0`
- `ProviderIdentityMapping(VERIFIED)` writes = `0`
- Provider identity rekeys = `0`
- Issuer-authority link/head writes = `0`
- Live authority requests = `0`
- Toss live requests = `0`

## 8. Final checkpoint states

- ADR-013: `ACCEPTED`
- ADR-014: `ACCEPTED`
- ADR-015: `PROPOSED`
- CP3-C2-B1: `PASS — CONTRACT APPROVED AND CLOSED`
- CP3-C2-B implementation: `IN PROGRESS`
- CP3-C2-B2-A: `PASS — CLOSED`
- CP3-C2-B2-B: `PASS — CLOSED`
- CP3-C2-B2-C:
  `BLOCKED — SCHEMA CONTRACT GAP / SCHEMA REMEDIATION AWAITING GPT INDEPENDENT REVIEW`
- CP3-C2-B2-D: `NOT STARTED`
- CP3-C2-C: `NOT STARTED`
- CP3-D: `NOT STARTED`
- Automatic checkpoint progression: `PROHIBITED`

The next action is GPT independent review of this documentation proposal.
Migration implementation and B2-C runtime resumption require later, separate
explicit authorization.
