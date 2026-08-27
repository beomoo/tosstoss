# Phase 2 CP3-C2-B2-B Second Remediation — Codex Self-QA Report

## 1. Identity and review boundary

- Repository: `beomoo/tosstoss`
- Branch: `feature/phase-02-toss`
- Starting/reviewed SHA: `722a5036d7d05ad6b8de0314ff6ac5ee8dafacc2`
- Final SHA: the commit containing this report; returned after the fast-forward
  push because a commit cannot embed its own SHA
- GPT independent re-review: `CHANGES REQUIRED`
- P0: `0`
- P1: `2` new findings (`P1-06`, `P1-07`)
- P2: `1` — non-blocking GitHub CI execution evidence absent
- P1-01 through P1-05: independently verified `CLOSED` and retained
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
10. `qa/PHASE_02_CP3_C2_B2_B_REMEDIATION_2_CODEX_REPORT.md`

The two script changes only advance the exact backend test inventory from
`676` to `691` and re-pin the corresponding 77-file phase-control digest. No
scanner, offline guard, secret rule, policy rule, or test-discovery boundary is
weakened.

## 3. P1-06 — legal-name reconciliation

The engine matrix now recognizes exactly these versioned fact kinds:

| Jurisdiction | Supporting fact | Decisive field-owner fact |
|---|---|---|
| KR | `KR_OPENDART_LEGAL_NAME` from `OPENDART_COMPANY_OVERVIEW` / `COMPANY_OVERVIEW_JSON_V1` / `company.corp_name` | `KR_IROS_LEGAL_NAME` from `KR_SUPREME_COURT_IROS` / verified registry extract / `registry.legal_name` |
| US | `US_SEC_LEGAL_NAME` from `SEC_EDGAR_ACCEPTED_FILING` / accepted issuer filing / `filing.legal_name` | `US_STATE_LEGAL_NAME` from the exact individually admitted state registry / verified domestic record / `registry.legal_name` |

Positive KR and US bundles now require `AuthorityScope.LEGAL_NAME` in addition
to the previously required regulatory ID, bridge, jurisdiction, and applicable
registrant-role scopes.

The reconciliation algorithm is deliberately narrow:

1. Both the supporting and decisive facts must independently pass exact stored
   source-policy, document-kind, scope, role, parser/adapter, provenance,
   observation, relation-head, access/license, and freshness checks.
2. KR OpenDART name and bridge facts must belong to the same exact source
   document; IROS name, bridge, and jurisdiction facts must belong to the same
   verified registry document. US SEC CIK, role, bridge, and name must belong to
   the same accepted filing; state name and jurisdiction must belong to the
   same state-registry document.
3. Comparison performs NFC normalization only. It does not case-fold, strip
   punctuation or legal suffixes, collapse whitespace, transliterate, or use
   fuzzy matching.
4. A difference is accepted only when the decisive field-owner name fact is
   the unique current head of a conflict-free linear immutable component made
   solely of same-source/same-role `LEGAL_NAME` facts connected exclusively by
   `CORRECTS` or `SUPERSEDES`, and that official history contains the exact
   supporting name.
5. Multiple unexplained co-current names, a fork/merge/cycle, a revocation, an
   unrelated-scope relation graft, missing name evidence, or an unusable/stale
   required current name fails closed.

Provider names and tickers are never read by this algorithm. Name agreement
alone still cannot establish issuer identity, jurisdiction, or the non-name
provider bridge.

## 4. P1-07 — compatible historical SEC filings

The engine now separates two meanings that were previously conflated:

- exact accession/source-document identity remains immutable filing
  provenance and is still validated inside every CIK/role/bridge/name fact;
- stable issuer/entity compatibility is evaluated from exact registrant CIK,
  formation state, and state entity number, not from accession.

For every relevant accepted filing, the engine requires a complete exact
same-document quartet: registrant CIK, issuer-registrant role, legal-entity
bridge, and legal name. A convenient fact from one filing cannot complete a
different filing's quartet.

Multiple accepted filings with different accessions do not conflict solely
because their document IDs differ when the stable issuer/entity facts agree.
They still conflict when formation states or state entity numbers disagree, a
filing fact set is incomplete, legal names are not officially reconciled, or
the provider bridge history is ambiguous.

Different historical provider symbols are not treated as issuer-identity
contradictions by themselves. They are usable only when every bridge supplies
an authority acceptance timestamp and the unique latest accepted bridge symbol
matches the current exact CP3-C1 provider observation. Missing timestamps,
equal latest timestamps with competing symbols, or a latest symbol that does
not match current provider lineage fails closed. Authority acceptance time is
semantic filing history; it is not supplied by the caller or derived from
retrieval/evaluation time.

Accepted filings remain immutable historical facts regardless of age. Only the
separate current/latest registrant-status and state-registry checks use the
repository 24-hour conservative freshness policy.

## 5. Previously closed P1-01 through P1-05

The complete 78-test decision-engine suite retains executable proof that:

- P1-01: the generic repository cannot admit a new production policy,
  evidence, observation, or relation; only a tests-only white-box helper seeds
  an explicitly pre-admitted snapshot for evaluator tests. Synthetic test data
  is not claimed to cross a production admission boundary.
- P1-02: evaluation requests cannot contain `evaluated_at`; the engine reads an
  aware UTC clock after `BEGIN IMMEDIATE`, with constructor injection only for
  deterministic tests.
- P1-03: omitted current authority facts and provider observations are
  discovered from stored state and contradictory co-current facts block READY.
- P1-04: only the exact deterministic canonical issuer subject is a
  non-collision; different or internally inconsistent canonical rows remain
  conflicts and B2-B performs no canonical write.
- P1-05: duplicate corp code or registrant CIK transactions append
  `REVIEW_REQUIRED` successors to every impacted READY leaf before commit,
  under deterministic writer-order concurrency tests.

Generic repository READY persistence remains typed fail-closed. The controlled
engine path continues to use one SQLite `BEGIN IMMEDIATE` writer transaction
for discovery, collision/head evaluation, revalidation, decision append, and
impacted-leaf invalidation.

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

Disposable migration regression continues to cover blank upgrade, populated
`0004` upgrade, downgrade/re-upgrade, failure cleanup/retry, collision safety,
append-only triggers, old-row preservation, and public Phase 1 revision
masking. No persistent production/runtime database was migrated.

## 7. LOCAL verification evidence

| LOCAL command/gate | Result |
|---|---|
| B2-B targeted decision-engine suite | exactly `78`; `78 passed` |
| B2-A authority contract/repository/migration regression | exactly `69`; `69 passed` |
| backend exact discovery/full pytest | exactly `691`; `691 passed` |
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

- There is still no operational trusted production evidence-ingestion path.
  Generic production admission therefore remains unavailable and fail-closed.
- The exact source registry currently admits only its reviewed KR sources and
  the individually named Delaware state registry; no wildcard state policy
  exists.
- Human authentication/approval, canonical promotion, issuer-authority links,
  security authority, and all live collection remain later separately gated
  work.
- GitHub CI execution evidence remains absent and non-blocking for this local
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
