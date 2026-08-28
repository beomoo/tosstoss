# Phase 2 CP3-C2-B2-C Schema Implementation Gap Codex Report

## 1. Report identity

- Evidence type: `Codex LOCAL documentation/contract self-QA`
- Repository: `beomoo/tosstoss`
- Branch: `feature/phase-02-toss`
- Authoritative starting SHA:
  `f73115ea1182e27259787460307a01b4c3874312`
- Final SHA note: the commit containing this report is identified after
  commit/push; embedding its own SHA here would change that SHA
- Date: `2026-08-28` (`Asia/Seoul`)
- Checkpoint:
  `CP3-C2-B2-C — APPROVED SCHEMA IMPLEMENTATION GAP REMEDIATION — DOCUMENTATION / CONTRACT ONLY`
- Result:
  `BLOCKED — APPROVED SCHEMA CONTRACT IMPLEMENTATION GAP / ADR-016 AWAITING GPT INDEPENDENT REVIEW`

This report does not declare ADR-016 accepted, create or implement migration
`0006`, resume B2-C runtime, or declare CP3-C2-B2-C PASS/CLOSED. All evidence
below is LOCAL Codex evidence, not GitHub CI evidence.

## 2. Approved ADR-015 architecture

GPT independently reviewed authoritative SHA
`f73115ea1182e27259787460307a01b4c3874312` as `PASS WITH CLOSEOUT CONDITION`:

- P0: `0`
- P1: `0`
- P2: `1 — GitHub CI execution evidence absent, NON-BLOCKING`

That review closed SG-01, SG-02, P1-SR-01, P1-SR-02 and P1-SR-03. The user
explicitly accepted ADR-015 on `2026-08-28`. Therefore:

- ADR-015: `ACCEPTED`
- Schema architecture: `APPROVED VIA ADR-015`
- Approved contract:
  `plans/PHASE_02_CP3_C2_B2_C_SCHEMA_REMEDIATION.md`
- Six-table additive Option A: preserved
- Runtime or migration PASS implied by acceptance: `0`

## 3. Implementation-discovered gaps

During the separately authorized `0006` implementation attempt, Codex stopped
with `BLOCKED — APPROVED SCHEMA CONTRACT IMPLEMENTATION GAP`. No file was
changed and no `0006` migration was created. GPT independently confirmed:

### IG-01 — incomplete lifecycle-authorization enum

The approved operation/event matrix required supersession and revocation rows,
but the documented closed enum lacked exact tokens for those rows.

### IG-02 — incomplete exact operation child tuple

The approved parent key
`uq_reviewer_credential_operations_exact_binding` contains eight exact ordered
columns, but the authorization and outcome child proposals omitted
`reviewer_role`, `principal_content_hash`, and `os_owner_sid_hash`. The required
composite FK was therefore not implementable without amending the child
contracts. A weaker subset parent key was not accepted as a workaround.

## 4. Proposed ADR-016 amendment

ADR-016 — Reviewer Operation Exact SQLite Binding Amendment is `PROPOSED`. It
is limited to the following three corrections.

### 4.1 Exact closed `authorization_kind` matrix

Closed enum:

1. `BOOTSTRAP_REGISTRATION`
2. `AUTHORIZED_REGISTRATION`
3. `AUTHORIZED_SUPERSESSION`
4. `AUTHORIZED_REVOCATION`

Exact allowed combinations:

| `operation_type` | `event_type` | `authorization_kind` |
|---|---|---|
| `FIRST_ENROLLMENT` | `REGISTERED` | `BOOTSTRAP_REGISTRATION` |
| `ADD_CREDENTIAL` | `REGISTERED` | `AUTHORIZED_REGISTRATION` |
| `REPLACE_CREDENTIAL` | `REGISTERED` | `AUTHORIZED_REGISTRATION` |
| `REPLACE_CREDENTIAL` | `SUPERSEDED` | `AUTHORIZED_SUPERSESSION` |
| `REVOKE_CREDENTIAL` | `REVOKED` | `AUTHORIZED_REVOCATION` |

Every other combination is rejected. No generic authorization fallback,
free-form token or `payload_json` authority exists.

### 4.2 Exact operation trust binding

Both proposed child tables now include:

- `reviewer_role VARCHAR(32) NOT NULL`
- `principal_content_hash VARCHAR(71) NOT NULL`
- `os_owner_sid_hash VARCHAR(71) NOT NULL`

Each has the exact ordered child FK:

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

to the exact same ordered columns in
`uq_reviewer_credential_operations_exact_binding`. The role is fixed to
`LOCAL_DATA_STEWARD`; both copied hashes require exact
`sha256:<64 lowercase hex>` form. Values are trusted-server-owned copies, not
caller authority. No subset operation UNIQUE/FK was added.

The exact successful-outcome parent tuple also includes operation content hash
and all three trust columns, so operation, outcome and authorization cannot
disagree while preserving `SUCCEEDED`, expected-state and resulting-state
bindings.

### 4.3 Immutable hash-preimage coverage

- `authorization_content_hash` includes `reviewer_role`,
  `principal_content_hash`, and `os_owner_sid_hash` in addition to every
  previously approved semantic relational field.
- `outcome_content_hash` includes the same three columns in addition to every
  previously approved semantic relational field.
- Audit-only timestamps and `payload_json` remain excluded.
- No cryptographic hash cycle or SQLite SHA UDF dependency was introduced.

## 5. Exact changed paths

1. `CHANGELOG.md`
2. `DECISIONS.md`
3. `KNOWN_ISSUES.md`
4. `STATUS.md`
5. `plans/PHASE_02_CP3_C2_B1_RUNTIME_CONTRACT.md`
6. `plans/PHASE_02_CP3_C2_B2_C_SCHEMA_REMEDIATION.md`
7. `plans/PHASE_02_EXECUTION_PLAN.md`
8. `qa/PHASE_02_CP3_C2_B2_C_SCHEMA_IMPLEMENTATION_GAP_CODEX_REPORT.md`

All changed paths are documentation/control-plane files.

## 6. Frozen migration integrity

| Migration | Required Git blob ID | LOCAL result |
|---|---|---|
| `0001_phase_01_foundation.py` | `d00355c2456021e6ffb195e50833adc32c74a4ad` | `MATCH — unchanged` |
| `0002_phase_02_cp3_foundation.py` | `53f40664eca2ea2466cc6154b8579c5db506e0ba` | `MATCH — unchanged` |
| `0003_phase_02_cp3_b_invariants.py` | `47d5a69009949b155211cd68209640136a7cacd9` | `MATCH — unchanged` |
| `0004_phase_02_cp3_c1_security_master.py` | `91b4d96a445be23e7aa55e08b9310dc7334a026d` | `MATCH — unchanged` |
| `0005_phase_02_cp3_c2_b_issuer_authority.py` | `81976b8f70a1f6107526a13acadf23f369b196e3` | `MATCH — unchanged` |

- Migration changed paths: `0`
- Exact requested `0006` path present: `0`
- Any `0006*.py` migration present: `0`
- Migration creation/application in this task: `0 / 0`

## 7. LOCAL documentation QA

| Check | Result |
|---|---|
| Documentation/control-plane-only diff | `PASS — exact 8 declared paths` |
| `services/api/src/**` changed paths | `0 — PASS` |
| Executable `tests/**` changed paths | `0 — PASS` |
| `scripts/**` changed paths | `0 — PASS` |
| Frontend changed paths | `0 — PASS` |
| Dependency changed paths | `0 — PASS` |
| Migration changed paths | `0 — PASS` |
| Exact four-token closed enum documented | `PASS` |
| Exact five allowed authorization combinations documented | `PASS` |
| Both child tables contain all three copied trust columns | `PASS` |
| Both child tuples match the exact eight-column parent key | `PASS` |
| Authorization/outcome hash preimages include all three columns | `PASS` |
| Nullable composite-FK all-null/all-non-null safeguards preserved | `PASS` |
| `0001`–`0005` exact Git blob equality | `PASS` |
| `0006` absent | `PASS` |
| `git diff --check` | `PASS` |
| `git diff --cached --check` | `PASS` |
| Existing secret scan | `PASS` |
| Existing policy scan | `PASS` |
| Status/ADR consistency | `PASS` |
| Remote `main` unchanged at `353159da45cfbe3a7f444bf476ce86fa9aece17c` | `PASS` |

Executable backend/frontend/migration suites were not run because this task is
strictly documentation/control-plane only and changes no executable or schema
file. This is not GitHub CI evidence; GitHub CI evidence remains absent.

## 8. Zero safety counters

- Application/runtime changes = `0`
- `services/api/src/**` changes = `0`
- Executable test changes = `0`
- Script changes = `0`
- Frontend changes = `0`
- Dependency changes = `0`
- Migration changes = `0`
- `0006` creation/application = `0 / 0`
- B2-C runtime implementation = `0`
- Real Windows Hello enrollment/dialog = `0 / 0`
- Real issuer approval execution = `0`
- Persistent canonical Issuer writes = `0`
- Canonical Security writes = `0`
- `ProviderIdentityMapping(VERIFIED)` writes = `0`
- Provider rekeys = `0`
- Live authority requests = `0`
- Live Toss requests = `0`
- Orders/WebSocket/current-price work = `0`

## 9. Final checkpoint state

- ADR-015: `ACCEPTED` (`2026-08-28`)
- ADR-016: `PROPOSED`
- CP3-C2-B2-C schema architecture: `APPROVED VIA ADR-015`
- CP3-C2-B2-C:
  `BLOCKED — APPROVED SCHEMA CONTRACT IMPLEMENTATION GAP / ADR-016 AWAITING GPT INDEPENDENT REVIEW`
- `0006`: `NOT CREATED / NOT IMPLEMENTED`
- B2-C WebAuthn/human-approval runtime: `NOT STARTED / NOT AUTHORIZED`
- CP3-C2-B2-D: `NOT STARTED`
- CP3-C2-C: `NOT STARTED`
- CP3-D: `NOT STARTED`
- Automatic progression: `PROHIBITED`

The next permitted action is GPT independent review of ADR-016 followed by
explicit user acceptance if the review passes. This task does not authorize
`0006` implementation or any B2-C runtime work.
