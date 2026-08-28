# Phase 2 CP3-C2-B2-C Schema Remediation Terminalization Codex Report

## 1. Scope and provenance

- Repository: `beomoo/tosstoss`
- Branch: `feature/phase-02-toss`
- Starting/reviewed SHA: `e016fc59973e5c81181e7cf20c1ebe3d7aada043`
- Final SHA: recorded after this immutable report is committed
- Date: `2026-08-28` (`Asia/Seoul`)
- Task: documentation/control-plane-only P1-SR-03 remediation
- GPT verdict on starting SHA: `CHANGES REQUIRED`
- Findings: P0 `0`, P1 `1`, P2 `1` non-blocking
- P1-SR-01: independently verified `CLOSED`
- P1-SR-02: independently verified `CLOSED`
- P1-SR-03: remediated in this proposal; not self-declared closed
- GitHub CI execution evidence: absent; all commands below are LOCAL Codex
  evidence only

This report neither accepts ADR-015 nor authorizes migration `0006` or B2-C
runtime implementation.

## 2. Exact changed paths

- `CHANGELOG.md`
- `DECISIONS.md`
- `KNOWN_ISSUES.md`
- `STATUS.md`
- `plans/PHASE_02_CP3_C2_B1_RUNTIME_CONTRACT.md`
- `plans/PHASE_02_CP3_C2_B2_C_SCHEMA_REMEDIATION.md`
- `plans/PHASE_02_EXECUTION_PLAN.md`
- `qa/PHASE_02_CP3_C2_B2_C_SCHEMA_REMEDIATION_TERMINALIZATION_CODEX_REPORT.md`

Application/runtime, test, fixture, script, frontend, dependency and migration
changed paths are all `0`.

## 3. P1-SR-03 remediation

The proposed future `0006` contract now classifies every challenge consumption
as exactly one of:

- operation-terminal: every failure and every successful final step, mutually
  deferred-bound to exactly one operation outcome in the same transaction; or
- continuation-bearing: only a successful ADD/REPLACE existing-credential
  assertion, atomically bound to its immutable `VERIFIED` counter event and
  exactly one subsequent five-minute registration challenge.

The closed terminal mapping is:

- `EXPIRED -> EXPIRED`;
- invalid signature, missing UP/UV, or invalid registration -> `REJECTED`;
- binding, origin/RP, counter, replay, or other closed failure ->
  `FAILED_CLOSED`; and
- a successful final operation step -> `SUCCEEDED`.

For every failure, the writer inserts the terminal consumption, optionally
inserts a safe rejected authentication audit when the attempt is attributable,
recomputes the full credential state, proves lifecycle writes are zero, appends
the unique outcome with resulting state equal to expected state, commits, and
only then returns the typed failure. Circular deferred exact FKs between the
consumption and outcome make either half uncommittable alone.

Operation issuance now preallocates and commits the operation and its initial
challenge together through a deferred exact FK. A verified ADD/REPLACE
assertion cannot become a reusable authorization session: its consumption,
counter event and one continuation challenge commit atomically. If later
registration fails, the valid counter event remains append-only, credential
ownership state remains unchanged, and the failed outcome permits a fresh
successor operation to reconstruct that advanced counter history.

The future design explicitly treats a consumed terminal challenge without an
outcome, or an operation without its initial challenge/outcome/exact
continuation graph, as ledger corruption. It must not silently create a
successor.

## 4. Closed-finding preservation

- P1-SR-01 remains unchanged: an authenticated final active credential revoke
  succeeds and produces the exact principal-specific empty state. Approval,
  add, replace and further revoke then fail closed; first enrollment does not
  restart; recovery/reset remains absent.
- P1-SR-02 remains unchanged: `reviewer-credential-state/0.1.0` has an exact
  canonical preimage; counters are excluded from ownership-state identity; the
  trusted server computes SHA-256 inside `BEGIN IMMEDIATE`; SQLite enforces
  relational invariants without an undeclared SHA UDF; lifecycle transitions
  remain bound to successful CAS outcomes.
- Option A remains additive, the six proposed ledger tables remain separated
  from issuer-approval authentication, and `SUPERSEDED` remains a non-blocker.

## 5. Migration integrity and zero counters

Starting-SHA and working-tree Git blob IDs are identical:

| Migration | Git blob ID | SHA-256 |
|---|---|---|
| `0001_phase_01_foundation.py` | `d00355c2456021e6ffb195e50833adc32c74a4ad` | `6eba164ef2f8bab42583076805255268e4daba29311e8f6e956f4177c0445762` |
| `0002_phase_02_cp3_foundation.py` | `53f40664eca2ea2466cc6154b8579c5db506e0ba` | `4b6b716999c5f3f6b52be1e85a53685c14c181fb4991e9ead892080717abaee6` |
| `0003_phase_02_cp3_b_invariants.py` | `47d5a69009949b155211cd68209640136a7cacd9` | `b59e74b5e817b6a5606d9f89f1f57eec3e0ba3616918d117d3cc28af4f5c420b` |
| `0004_phase_02_cp3_c1_security_master.py` | `91b4d96a445be23e7aa55e08b9310dc7334a026d` | `cd1cbcae309f1e56ba923e6463863749c79a84b4c10499801f5da28b0a3a0f4f` |
| `0005_phase_02_cp3_c2_b_issuer_authority.py` | `81976b8f70a1f6107526a13acadf23f369b196e3` | `a0c2d77d8db0da59b9fc5058182f367cfdd39ff6b306a03a0e61277d6ff4415b` |

- Migration changes: `0`
- Migration `0006` created/applied: `0 / 0`
- B2-C runtime implementation: `0`
- Real Windows Hello enrollment: `0`
- Approval execution: `0`
- Canonical Issuer/Security writes: `0 / 0`
- `ProviderIdentityMapping(VERIFIED)` writes: `0`
- Provider rekeys: `0`
- Credential/recovery/reset execution: `0`
- Live authority/Toss requests: `0 / 0`

## 6. LOCAL documentation QA

| LOCAL command/check | Result |
|---|---|
| `git diff --check` | PASS |
| `git diff --cached --check` | PASS |
| staged/working path allowlist | PASS — exactly 8 documentation/control-plane paths |
| `services/api/src/**`, `tests/**`, `scripts/**`, frontend, dependency and migration changed paths | PASS — 0 |
| starting-SHA versus working-tree Git blobs for `0001`–`0005` | PASS — exact 5/5 |
| migration `0006` inventory | PASS — 0 files |
| ADR/status consistency | PASS — ADR-015 PROPOSED; B2-C blocked; later checkpoints not started; progression prohibited |
| `pwsh -NoProfile -File .\scripts\secret-scan.ps1` | PASS — final isolated run; scanner unchanged |
| `pwsh -NoProfile -File .\scripts\policy-scan.ps1` | PASS — scanner unchanged |
| `git ls-remote --heads origin refs/heads/main refs/heads/feature/phase-02-toss` before commit | PASS — feature at starting SHA; main at `353159da45cfbe3a7f444bf476ce86fa9aece17c` |

The final remote-feature equality, unchanged remote-main SHA and clean worktree
are verified after commit/push and reported in the completion response. These
results are LOCAL Codex evidence, not GitHub CI evidence.

## 7. Final state

- ADR-013: `ACCEPTED`
- ADR-014: `ACCEPTED`
- ADR-015: `PROPOSED`
- CP3-C2-B implementation: `IN PROGRESS`
- CP3-C2-B2-A: `PASS — CLOSED`
- CP3-C2-B2-B: `PASS — CLOSED`
- CP3-C2-B2-C:
  `BLOCKED — SCHEMA CONTRACT GAP / SCHEMA REMEDIATION AWAITING GPT INDEPENDENT RE-REVIEW`
- CP3-C2-B2-D: `NOT STARTED`
- CP3-C2-C: `NOT STARTED`
- CP3-D: `NOT STARTED`
- Automatic progression: `PROHIBITED`

ADR-015 acceptance, migration implementation and B2-C runtime resumption each
require their separately authorized future steps. This checkpoint stops after
the documentation commit and push.
