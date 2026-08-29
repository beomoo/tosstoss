# Phase 2 CP3-C2-B2-C — ADR-017 / ADR-018 USER-ACCEPTANCE CLOSEOUT CODEX REPORT

## 1. Scope and authority

- repository: `beomoo/tosstoss`
- branch: `feature/phase-02-toss`
- authoritative starting SHA: `dbf913d5654b3a1095d359ac34e1edcde2f63c1e`
- independent-repository context: documentation/control-plane only
- independent verdict carried forward: `PASS WITH CLOSEOUT CONDITION` at
  `dbf913d5654b3a1095d359ac34e1edcde2f63c1e`
- independent finding counts carried forward:
  `P0: 0 / unresolved P1: 0 / P2: 1`
- requested closeout outcome: user acceptance for **ADR-017 + ADR-018**, no implementation or migration execution.
- provenance chain:
  - authoritative base `09ced6c0d0000f911075154c97a0e1cf54656f86` (previously
    `CHANGES REQUIRED`, `P0 0 / P1 3 / P2 1`)
  - remediation + FR completion + this acceptance-closeout review at
    `dbf913d5654b3a1095d359ac34e1edcde2f63c1e`
    (`PASS WITH CLOSEOUT CONDITION`, `P0 0 / unresolved P1 0 / P2 1`)
  - explicit user acceptance on `2026-08-29`

## 2. Control-plane decision closure

- ADR-017: `ACCEPTED` (`2026-08-29`)
- ADR-018: `ACCEPTED` (`2026-08-29`)
- ADR-019: `PROPOSED — ON HOLD / AWAITING SEPARATE USER DECISION`
- `0006`: `PASS — CLOSED`
- `0007`: `NOT CREATED / NOT AUTHORIZED`
- R1: `NOT STARTED / BLOCKED`
- B2-D: `NOT STARTED`
- CP3-C2-C: `NOT STARTED`
- CP3-D: `NOT STARTED`
- automatic progression: `PROHIBITED`

Only user acceptance changed ADR-017 and ADR-018 status; runtime/workflow remains unchanged and blocked on ADR-019.

## 3. ADR-017/ADR-018 resolution summary

### ADR-017 (runtime canonicalization and hash preimages)

- `RG-01`~`RG-07` plus required follow-on closure from prior review are accepted as contract controls.
- `CTAP2 canonical` terminology is retained for COSE map/byte-form validation; RFC-8949 remains cited only as underlying reference.
- Exact raw-byte vectors for ES256/RS256 are unchanged and preserved.
- Principal/credential/content hashes and all 10 previously accepted vectors remain valid.

### ADR-018 (counter-capability bootstrap)

- `0 -> positive` / `0 -> 0` semantics for FIRST_ENROLLMENT, ADD_CREDENTIAL, and REPLACE_CREDENTIAL finalized.
- Zero-registration bootstrap applies to all new credential creation operations.
- The future `0007` projection design is accepted as control-plane design only and still **not created**.

## 4. ADR-019 trust-boundary state

- Current contract only proves `platform + UV + resident + attestation=none`.
- It does **not** prove strict Windows Hello provenance.
- ADR-019 remains proposed on-hold and unresolved.

## 5. Artifact and status consistency checks

- `plans/PHASE_02_CP3_C2_B2_C_SCHEMA_REMEDIATION.md`:
  - ADR-017 and ADR-018 now marked accepted; ADR-019 on hold.
  - Runtime implementation state set to `0 / NOT STARTED / BLOCKED — ADR-019 DECISION REQUIRED`.
- `plans/PHASE_02_CP3_C2_B2_C_ADR_018_COUNTER_CAPABILITY_SCHEMA_PROPOSAL.md`:
  - ADR-017 and ADR-018 accepted; `0007` unchanged and not created.
- `plans/PHASE_02_CP3_C2_B1_RUNTIME_CONTRACT.md`:
  - ADR-017/018 accepted; ADR-019 on hold; R1 not started and blocked.
- `plans/PHASE_02_EXECUTION_PLAN.md` and `KNOWN_ISSUES.md` updated to reflect ADR-019-only block.
- `DECISIONS.md`, `STATUS.md`, and `CHANGELOG.md` updated to reflect the same decision state.

## 6. Frozen migration integrity

The following Alembic migrations remain frozen and unchanged:

| migration | required blob |
|---|---|
| `0001` | `d00355c2456021e6ffb195e50833adc32c74a4ad` |
| `0002` | `53f40664eca2ea2466cc6154b8579c5db506e0ba` |
| `0003` | `47d5a69009949b155211cd68209640136a7cacd9` |
| `0004` | `91b4d96a445be23e7aa55e08b9310dc7334a026d` |
| `0005` | `81976b8f70a1f6107526a13acadf23f369b196e3` |
| `0006` | `f10e7f5bc21e232fc68b38144f5b8fb124f31698` |

No migration file was edited in this task.

## 7. Change surface summary

- application: `0`
- migration: `0` (no new file under implementation)
- test: `0`
- dependency/lockfile: `0`
- frontend: `0`
- fixture/script: `0`
- real Windows Hello: `0`
- issuer approval runtime: `0`

## 8. Local/documentation checks

| check | result |
|---|---|
| `git diff --check` | PASS |
| `git diff --cached --check` | PASS |
| exact docs-only path allowlist | PASS |
| frozen `0001`–`0006` blob verification | PASS |
| secret scan on changed docs | NOT VERIFIED |
| policy scan (no non-doc runtime/surface edits) | PASS |
| `ADR/status/plan consistency` (cross-doc checks in this task) | PASS |
| ADR-019 blocker evidence preserved | PASS |
| automatic progression prohibition reflected | PASS |

## 8.1 CI evidence

- GitHub CI execution was not run in this docs-only control-plane closeout; evidence is local-only.
- This is unchanged from prior R1-doc-only gates.

Note: section 8.2 records the required disposable-tree scanner attempt and exact output.

## 8.2 Native scanner proof (disposable-tree)

- Working tree: detached clean worktree at authoritative SHA
  `eb61fadc4f6886b7649193579f9b96e444d112a7`
- Command: `pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/secret-scan.ps1`
- Result: `Exit code 1`
- Failure reason:
  `Required current-build evidence is missing: <repo>\\apps\\web\\.next\\BUILD_ID`
- Status: `SECRET SCAN — NOT VERIFIED`

## 9. Exact changed paths

- `DECISIONS.md`
- `STATUS.md`
- `qa/PHASE_02_CP3_C2_B2_C_ADR_017_018_ACCEPTANCE_CLOSEOUT_CODEX_REPORT.md`

## 10. Finalization

- `ADR-017` and `ADR-018` are user-accepted as control-plane contracts.
- `ADR-019` remains proposed/on-hold and is not self-accepted.
- `R1` remains `BLOCKED / NOT STARTED` until ADR-019 is resolved and separately accepted.
- `0007` is preserved as not created and not authorized.
- CP3-C2-C / CP3-D / B2-D remain `NOT STARTED`, automatic progression remains prohibited.
- No runtime code, migration, test, dependency, fixture, frontend, or issuer-approval execution was performed.
