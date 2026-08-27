# Phase 2 CP3-C2-B2-B Third Remediation — Codex Self-QA Report

## 1. Identity and review boundary

- Repository: `beomoo/tosstoss`
- Branch: `feature/phase-02-toss`
- Starting/reviewed SHA: `8093ee9389d4f7ae716482a87de5eae252e08eff`
- Final SHA: the commit containing this report; returned after the fast-forward
  push because a commit cannot embed its own SHA
- GPT second independent re-review: `CHANGES REQUIRED`
- P0: `0`
- P1: `2` new findings (`P1-08`, `P1-09`)
- P2: `1` — non-blocking GitHub CI execution evidence absent
- P1-01 through P1-07: independently verified `CLOSED` and retained
- Codex outcome: `REMEDIATED — AWAITING GPT INDEPENDENT RE-REVIEW`

This report is LOCAL Codex self-QA evidence. It does not declare GPT PASS and
does not authorize B2-C, B2-D, CP3-C2-C, CP3-D, or automatic progression.

## 2. Exact changed paths

1. `services/api/src/toss_dashboard_api/domain/issuer_authority.py`
2. `tests/backend/test_authority_decision_engine.py`
3. `scripts/test.ps1`
4. `scripts/policy-scan.ps1`
5. `STATUS.md`
6. `DECISIONS.md`
7. `plans/PHASE_02_EXECUTION_PLAN.md`
8. `plans/PHASE_02_CP3_C2_B1_RUNTIME_CONTRACT.md`
9. `CHANGELOG.md`
10. `qa/PHASE_02_CP3_C2_B2_B_REMEDIATION_3_CODEX_REPORT.md`

The script changes only advance the exact backend inventory from `691` to
`702` and re-pin the resulting 77-file control-plane manifest digest. Scanner
rules, offline network guards, secret rules, fixture isolation, and discovery
requirements are unchanged.

## 3. P1-08 — exact legal-entity binding for name history

The engine no longer treats an immutable relation edge as proof that two legal
names describe one entity. For a current decisive registry-name application it
loads every evidence fact from every source document represented in the exact
relation component and derives a field-owner subject key from independently
stored companion facts.

KR subject key:

```text
(KR, KR_SUPREME_COURT_IROS, exact corporate_registration_reference/jurir_no)
```

Every current or historical IROS legal-name document must independently
contain:

- the exact decisive `registry.corporate_registration_reference` bridge;
- the exact decisive verified domestic `registry.legal_entity_status` fact;
- one identical 13-digit corporate-registration reference in both facts; and
- the same exact admitted policy, source namespace, document ID/reference,
  classification, parser/adapter contract, locator root, access/license state,
  production lineage, scope/role weight, and raw/normalized claim contract.

US subject key:

```text
(US, exact US_STATE_REGISTRY_<STATE> namespace,
 exact formation state, exact state_entity_number)
```

Every current or historical state-registry legal-name document must
independently contain the exact decisive active domestic-formation
`registry.legal_entity_status` fact for that same namespace/state/entity. A
name row from another Delaware entity therefore cannot reconcile this
candidate.

The algorithm rejects a component when any member lacks its companion subject
proof, has a different subject key, uses an unapproved admission contract, or
contains a fork/merge/cycle/revocation/non-correction relation. Source
namespace, role, name equality, document order, provider name/symbol, and a
malicious `CORRECTS`/`SUPERSEDES` edge are insufficient by themselves.

Executable coverage includes valid same-subject KR and US history, different
KR `jurir_no`, another Delaware entity number, malicious `CORRECTS` and
`SUPERSEDES` edges, and both relation insertion orders.

## 4. P1-09 — every supporting legal name must reconcile

The former single-global-supporting-name check is replaced by an all-facts
rule:

1. Every structurally current supporting name independently passes exact
   source-policy, document, candidate, observation, relation-head, access/
   license, and permanent-lineage checks.
2. A KR OpenDART name derives its legal-entity subject from the exact same-
   document `company.identity_bridge` and raw `jurir_no`.
3. A US SEC name derives its subject only from a complete exact same-document
   accepted-filing quartet: registrant CIK, issuer-registrant role, stable
   formation-state/entity bridge, and legal name.
4. The supporting subject must equal the decisive field-owner registry subject.
5. Every supporting name must be NFC-exact to the unique current decisive name
   or occur in the same-subject decisive registry's conflict-free immutable
   `CORRECTS`/`SUPERSEDES` history.
6. If one relevant supporting name is unexplained, malformed, or cross-entity,
   `LEGAL_NAME` is `CONFLICT` and READY is blocked.

No case folding, fuzzy matching, punctuation stripping, suffix removal,
whitespace heuristics, transliteration, provider name, or ticker similarity is
used. Explained old/current names across multiple accepted accessions can
coexist because accession remains exact document provenance rather than a
stable issuer-identity conflict key.

Tests cover OLD + NEW accepted filings with same-subject official history in
both insertion orders, OLD + NEW + UNKNOWN, missing official history,
cross-entity history, equivalent multiple OpenDART names, historical filing
age, and the separately current latest-status gate.

## 5. P1-01 through P1-07 non-regression

The complete 89-test B2-B decision-engine suite retains executable proof that:

- P1-01: generic repository production policy/evidence/observation/relation
  admission remains unavailable; only a tests-only white-box snapshot helper
  seeds evaluator state.
- P1-02: the request has no authoritative evaluation timestamp; the engine-owned
  aware UTC clock is read inside the transaction.
- P1-03: all relevant current authority/provider facts are discovered from
  stored state, so omitted conflicts cannot be hidden.
- P1-04: only the exact deterministic canonical issuer subject is a
  non-collision; contradictory canonical identity remains a conflict.
- P1-05: duplicate corp code or registrant CIK invalidates every impacted READY
  leaf in the same `BEGIN IMMEDIATE` writer transaction.
- P1-06: `LEGAL_NAME` remains a mandatory KR/US positive scope; provider
  name/ticker and fuzzy/lossy normalization cannot repair official conflict.
- P1-07: every accepted filing keeps exact same-document CIK/role/bridge/name
  completeness while compatible accessions coexist, incompatible formation/
  entity facts conflict, and former symbols require deterministic authority-
  accepted chronology.

Generic repository READY persistence remains typed fail closed. The controlled
engine path still performs complete discovery, relation-head resolution,
freshness, collisions, decision append, and impacted-leaf invalidation in one
SQLite `BEGIN IMMEDIATE` transaction.

## 6. Migration integrity

Migration changes: `0`. Migration `0006` creation: `0`. Persistent/runtime
application of `0005`: `0`.

| Migration | SHA-256 before and after |
|---|---|
| `0001_phase_01_foundation.py` | `6eba164ef2f8bab42583076805255268e4daba29311e8f6e956f4177c0445762` |
| `0002_phase_02_cp3_foundation.py` | `4b6b716999c5f3f6b52be1e85a53685c14c181fb4991e9ead892080717abaee6` |
| `0003_phase_02_cp3_b_invariants.py` | `b59e74b5e817b6a5606d9f89f1f57eec3e0ba3616918d117d3cc28af4f5c420b` |
| `0004_phase_02_cp3_c1_security_master.py` | `cd1cbcae309f1e56ba923e6463863749c79a84b4c10499801f5da28b0a3a0f4f` |
| `0005_phase_02_cp3_c2_b_issuer_authority.py` | `a0c2d77d8db0da59b9fc5058182f367cfdd39ff6b306a03a0e61277d6ff4415b` |

Disposable migration regression covers blank/current upgrade, downgrade/re-
upgrade, failure cleanup/retry, old-row preservation, collision safety,
append-only triggers, and public Phase 1 revision masking. No persistent
production/runtime database was migrated.

## 7. LOCAL verification evidence

| LOCAL command/gate | Result |
|---|---|
| B2-B targeted decision-engine suite | exactly `89`; `89 passed` |
| B2-A authority contract/repository/migration regression | exactly `69`; `69 passed` |
| backend exact discovery/full pytest | exactly `702`; `702 passed` |
| migration regression (`scripts/migrate.ps1 -Action Test`) | PASS |
| fixture import idempotency | PASS |
| frontend Vitest exact inventory/run | exactly `43`; `43 passed` |
| Playwright E2E exact inventory/run | exactly `2`; `2 passed` |
| Ruff format/check | PASS |
| mypy | PASS |
| ESLint | PASS |
| TypeScript | PASS |
| OpenAPI drift | PASS |
| production build | PASS |
| offline/live preflight self-test | PASS; external requests `0`, credentials `0` |
| `scripts/secret-scan.ps1` | PASS |
| `scripts/policy-scan.ps1` | PASS |
| `git diff --check` | PASS |
| `git diff --cached --check` | PASS |
| full `scripts/test.ps1` | PASS |

All results are LOCAL evidence. No GitHub commit status or workflow execution
evidence exists for this remediation SHA, and none was created to remove the
accepted non-blocking P2.

## 8. Exact zero counters

- automatic final promotion = `0`
- canonical Issuer writes = `0`
- canonical Security writes = `0`
- `ProviderIdentityMapping(VERIFIED)` writes = `0`
- provider identity rekeys = `0`
- human approval execution = `0`
- WebAuthn operational verification = `0`
- Windows Hello enrollment runtime = `0`
- issuer-authority link execution = `0`
- link-head mutation = `0`
- live authority requests = `0`
- Toss live requests = `0`
- credentials used = `0`
- account/order/WebSocket/current-price work = `0`
- migration changes = `0`

## 9. Known limitations and deferred work

- There is still no operational trusted production evidence-ingestion path;
  generic production admission remains unavailable and fail closed.
- Only the reviewed exact KR sources and individually admitted Delaware state
  registry exist in the current source-policy registry; there is no production
  wildcard state policy.
- Operational WebAuthn/authentication/approval, canonical promotion, issuer-
  authority links, security authority, and all live authority collection remain
  later separately gated work.
- GitHub CI execution evidence remains absent and non-blocking for this LOCAL
  remediation handoff.

## 10. Final checkpoint states

- ADR-013: `ACCEPTED`
- ADR-014: `ACCEPTED`
- CP3-C2-B1: `PASS — CONTRACT APPROVED AND CLOSED`
- CP3-C2-B implementation: `IN PROGRESS`
- CP3-C2-B2-A: `PASS — CLOSED`
- CP3-C2-B2-B: `REMEDIATED — AWAITING GPT INDEPENDENT RE-REVIEW`
- CP3-C2-B2-C: `NOT STARTED`
- CP3-C2-B2-D: `NOT STARTED`
- CP3-C2-C: `NOT STARTED`
- CP3-D: `NOT STARTED`
- Automatic checkpoint progression: `PROHIBITED`
