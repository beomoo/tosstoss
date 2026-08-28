# Phase 2 CP3-C2-B2-C Schema Remediation Fix Codex Report

## 1. Report identity

- Evidence type: `Codex LOCAL documentation/design self-QA`
- Repository: `beomoo/tosstoss`
- Branch: `feature/phase-02-toss`
- Starting/reviewed SHA: `fd0535fdd022f0171a63a83cb2861e924a92da64`
- Final SHA note: the resulting commit SHA is reported after commit/push;
  embedding it here would change that SHA
- Date: `2026-08-28` (`Asia/Seoul`)
- Checkpoint: `CP3-C2-B2-C SCHEMA CONTRACT REMEDIATION — GPT REVIEW FIX`
- GPT verdict: `CHANGES REQUIRED`
- P0: `0`
- P1: `2` new design findings
- P2: `1 — GitHub CI execution evidence absent, NON-BLOCKING`
- Result:
  `BLOCKED — SCHEMA CONTRACT GAP / SCHEMA REMEDIATION AWAITING GPT INDEPENDENT RE-REVIEW`

This report is Codex LOCAL closeout evidence for the documentation revision. It
does not declare GPT PASS, accept ADR-015, authorize/create/apply migration
`0006`, or resume B2-C runtime implementation.

## 2. Independent review disposition

The review accepted SG-01, SG-02 and additive Option A in principle. The six-
table separation, credential-operation challenge namespace, create/assertion
purpose separation, terminal consumption, issuer/credential-operation
authentication non-substitution, append-only lifecycle/counter history, no
current-counter mutation, no recovery/force/reset, and issuer `SUPERSEDED`
non-blocker conclusion remain unchanged.

### P1-SR-01 — final active credential revocation

Remediated in the proposal, awaiting independent re-review:

- A currently active credential may authenticate its own
  `REVOKE_CREDENTIAL`, including when it is the final active credential.
- The successful result is the exact principal-specific empty active set and
  its deterministic state hash.
- After that transition, issuer approval, add, replace and further revoke all
  fail closed because no active credential can authenticate.
- Historical successful registration permanently prevents first enrollment
  from restarting; recovery/reset remains absent.
- Principal, credential, lifecycle, authentication, authorization and operation
  history remains append-only and queryable.
- Operators needing continued approval capability should add a backup
  credential before intentionally revoking the final one.

### P1-SR-02 — exact credential-state hash contract

Remediated in the proposal, awaiting independent re-review:

- Added exact contract `reviewer-credential-state/0.1.0`.
- Defined `ACTIVE` from the complete, authorized, same-principal, acyclic,
  fork-free credential lifecycle graph with a unique current `REGISTERED` leaf.
- Defined the complete principal/version/SID-bound canonical UTF-8/NFC JSON
  preimage, exact active-member fields, unsigned UTF-8 sort tuple, duplicate
  fail-closed rules, canonical unpadded RFC 4648 base64url credential IDs,
  lifecycle-leaf identity/content hash and SHA-256 rendering.
- Defined the principal-specific empty-state preimage as the same exact object
  with `active_credentials: []`; null, zero hash or magic literals are invalid.
- Excluded audit/request/row/time values and all signature-counter values.
  Counter capability remains included; counter advancement alone does not churn
  ownership/lifecycle state.
- Trusted server code loads all relevant rows and computes/recomputes pre/post
  hashes under the same SQLite `BEGIN IMMEDIATE` writer transaction. SQLite
  enforces relational structure and exact stored-value copying only; no SQLite
  SHA-256 UDF is assumed.
- Defined an exact two-pass completion protocol: project and hash frozen
  server-owned proposed transitions only after allocating their exact event IDs
  and event hashes; compute the candidate state, outcome and authorization
  hashes; insert deferred companion(s) before credential/event rows; reload the
  transaction-visible graph; require a byte-exact post-state match; then insert
  the successful outcome. Any mismatch rolls back.
- Retained six tables and added mandatory deferred exact
  lifecycle-authorization-to-`SUCCEEDED`-outcome binding, including operation,
  principal, outcome hash/result and expected/resulting state hashes. The
  authorization-to-new-credential FK is deferred, and the credential insert
  guard also requires pending exact `REGISTERED`
  authorization, so a registration consumption alone cannot create trusted
  credential state.
- Added relational and trusted-server active-lifecycle revalidation for the
  existing issuer-authentication path, so an immutable but revoked public
  credential cannot authenticate approval after final revoke.

## 3. Exact changed paths

1. `CHANGELOG.md`
2. `DECISIONS.md`
3. `KNOWN_ISSUES.md`
4. `STATUS.md`
5. `plans/PHASE_02_CP3_C2_B1_RUNTIME_CONTRACT.md`
6. `plans/PHASE_02_CP3_C2_B2_C_SCHEMA_REMEDIATION.md`
7. `plans/PHASE_02_EXECUTION_PLAN.md`
8. `qa/PHASE_02_CP3_C2_B2_C_SCHEMA_REMEDIATION_FIX_CODEX_REPORT.md`

## 4. Migration integrity

| Migration | Starting SHA-256 | Result |
|---|---|---|
| `0001_phase_01_foundation.py` | `6eba164ef2f8bab42583076805255268e4daba29311e8f6e956f4177c0445762` | `MATCH — unchanged` |
| `0002_phase_02_cp3_foundation.py` | `4b6b716999c5f3f6b52be1e85a53685c14c181fb4991e9ead892080717abaee6` | `MATCH — unchanged` |
| `0003_phase_02_cp3_b_invariants.py` | `b59e74b5e817b6a5606d9f89f1f57eec3e0ba3616918d117d3cc28af4f5c420b` | `MATCH — unchanged` |
| `0004_phase_02_cp3_c1_security_master.py` | `cd1cbcae309f1e56ba923e6463863749c79a84b4c10499801f5da28b0a3a0f4f` | `MATCH — unchanged` |
| `0005_phase_02_cp3_c2_b_issuer_authority.py` | `a0c2d77d8db0da59b9fc5058182f367cfdd39ff6b306a03a0e61277d6ff4415b` | `MATCH — unchanged` |

- Migration changed paths: `0`
- Existing `0001`–`0005` changed: `0`
- `0006` files present/created/applied: `0 / 0 / 0`
- Frozen `0005` table rebuild/alter: `0`

## 5. LOCAL documentation QA

| Check | Result |
|---|---|
| Documentation/control-plane-only changed paths | `PASS — exact 8 declared paths` |
| `services/api/src/**` changed paths | `0 — PASS` |
| Executable `tests/**` changed paths | `0 — PASS` |
| `scripts/**` changed paths | `0 — PASS` |
| Frontend changed paths | `0 — PASS` |
| Dependency changed paths | `0 — PASS` |
| Migration changed paths | `0 — PASS` |
| `0001`–`0005` SHA-256 equality | `PASS` |
| `0006` absent | `PASS` |
| Remote `main` unchanged at `353159da45cfbe3a7f444bf476ce86fa9aece17c` | `PASS` |
| `git diff --check` | `PASS` |
| `git diff --cached --check` | `PASS` |
| Existing secret scan | `PASS` |
| Existing policy scan | `PASS` |
| Status/ADR consistency | `PASS` |

These are LOCAL Codex checks against the final staged snapshot, not GitHub CI
evidence. No GitHub commit status/workflow result exists for the reviewed SHA;
that evidence gap remains a non-blocking P2.

## 6. Zero counters

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
- Recovery/reset paths = `0`
- Live authority requests = `0`
- Toss live requests = `0`

## 7. Final checkpoint states

- ADR-013: `ACCEPTED`
- ADR-014: `ACCEPTED`
- ADR-015: `PROPOSED`
- CP3-C2-B1: `PASS — CONTRACT APPROVED AND CLOSED`
- CP3-C2-B implementation: `IN PROGRESS`
- CP3-C2-B2-A: `PASS — CLOSED`
- CP3-C2-B2-B: `PASS — CLOSED`
- CP3-C2-B2-C:
  `BLOCKED — SCHEMA CONTRACT GAP / SCHEMA REMEDIATION AWAITING GPT INDEPENDENT RE-REVIEW`
- CP3-C2-B2-D: `NOT STARTED`
- CP3-C2-C: `NOT STARTED`
- CP3-D: `NOT STARTED`
- Automatic checkpoint progression: `PROHIBITED`

The next action is GPT independent re-review of this documentation revision.
ADR-015 acceptance, migration `0006` implementation and B2-C runtime resumption
each require later, separate explicit authorization.
