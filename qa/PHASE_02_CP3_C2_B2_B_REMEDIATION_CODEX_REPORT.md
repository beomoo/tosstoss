# Phase 2 CP3-C2-B2-B Remediation — Codex Self-QA Report

## 1. Identity and verdict boundary

- Repository: `beomoo/tosstoss`
- Branch: `feature/phase-02-toss`
- Starting/reviewed SHA: `d4f84c4bfb83f2396161eea913f2c119ecb17dac`
- Final SHA: the commit containing this report; recorded in the final handoff
  after the fast-forward push because a commit cannot embed its own SHA.
- GPT independent-review verdict: `CHANGES REQUIRED`
- P0: `0`
- P1: `5`
- P2: `1` — non-blocking GitHub CI execution evidence absent
- Codex outcome: `REMEDIATED — AWAITING GPT INDEPENDENT RE-REVIEW`

This is LOCAL Codex self-QA evidence. It does not declare GPT PASS and does not
authorize B2-C, B2-D, CP3-C2-C, CP3-D, or automatic progression.

## 2. Exact changed paths

1. `CHANGELOG.md`
2. `DECISIONS.md`
3. `STATUS.md`
4. `plans/PHASE_02_CP3_C2_B1_RUNTIME_CONTRACT.md`
5. `plans/PHASE_02_EXECUTION_PLAN.md`
6. `qa/PHASE_02_CP3_C2_B2_B_REMEDIATION_CODEX_REPORT.md`
7. `scripts/policy-scan.ps1`
8. `scripts/test.ps1`
9. `services/api/src/toss_dashboard_api/contracts/authority_decision.py`
10. `services/api/src/toss_dashboard_api/domain/issuer_authority.py`
11. `services/api/src/toss_dashboard_api/repositories/authority.py`
12. `tests/backend/authority_preadmitted_ledger.py`
13. `tests/backend/test_authority_decision_engine.py`
14. `tests/backend/test_authority_migration.py`
15. `tests/backend/test_authority_repository.py`

The test inventory pin changed from `659` to `676`. The phase-control file
count changed from `76` to `77` only because the tests-only pre-admitted ledger
helper was added. The exact digest was recomputed over the complete control
file set. Secret, policy, network, and test-discovery rules were not relaxed.

## 3. P1 remediation

### P1-01 — trusted source-admission boundary

- Removed caller-selectable `AuthorityLedgerMode`.
- The generic repository rejects every new production-eligible source policy,
  evidence fact, retrieval observation, and evidence relation with typed
  `PRODUCTION_AUTHORITY_ADMISSION_UNAVAILABLE`.
- Exact existing immutable production rows remain idempotently verifiable; same
  semantic ID with different immutable content remains a typed conflict.
- B2-B defines no runtime production admission capability because neither a
  live adapter nor the WebAuthn evidence-ingest ceremony is in scope. New
  runtime production evidence therefore fails closed.
- `tests/backend/authority_preadmitted_ledger.py` is a white-box helper that
  directly seeds an already admitted snapshot for evaluator tests. Production
  code neither imports nor exposes it. Synthetic test facts are not claimed to
  have passed a production ingestion boundary.
- Fixture/test/synthetic lineage and relabelled fixture lineage remain
  permanently zero-authority.

### P1-02 — server-owned freshness clock

- Removed `evaluated_at` from `IssuerAuthorityEvaluationRequest` and its public
  builder.
- `IssuerAuthorityDecisionEngine` obtains an aware UTC time from its own clock
  after entering `BEGIN IMMEDIATE`.
- Runtime defaults to the server UTC clock. Deterministic tests inject a fake
  clock into the engine constructor, never into a caller request.
- Backdated/future caller fields are rejected as extra contract fields, cannot
  alter freshness, and cannot unlock READY.
- Evaluation time remains excluded from decision semantic identity and never
  becomes an authority effective date.

### P1-03 — complete current authority state

- Request evidence and provider-observation memberships are candidate/seed
  references only.
- Inside the writer transaction, the engine loads all current observations for
  the provider identity's latest CP3-C1 source version. Omitted quarantine,
  collision, invalid-contract, or ineligible observations block READY.
- KR discovery includes all current corp-code and overview facts for the
  candidate plus all IROS jurisdiction/bridge facts reachable from every exact
  overview `jurir_no`.
- US discovery includes all current registrant CIK/role/bridge/latest-status
  facts plus every individually admitted state-registry fact reachable from
  the SEC state/entity keys.
- Linear correction/supersession heads replace predecessors; incompatible
  co-current overview, IROS, SEC bridge, SEC latest-status, or state-registry
  facts become conflict. A convenient matching combination cannot mask another
  current official fact.
- Collision scanning includes positive bridge and jurisdiction applications in
  addition to identifier claims and regulatory-ID applications.
- Discovery, collision, bundle, and decision semantics remain sorted and
  independent of input order or evaluation clock.

### P1-04 — same canonical subject semantics

- Existing canonical rows are read-only.
- A row is the same subject only when its issuer ID equals the deterministic
  proposed issuer ID and its jurisdiction, authoritative identifier, immutable
  payload fields, and normalized content hash all agree.
- That exact row does not itself cause a collision.
- A different issuer with the same corp code/CIK, an inconsistent jurisdiction
  or identifier under the expected issuer ID, malformed payload/hash state, or
  multiple competing canonical rows remains a fail-closed collision.
- Canonical writes performed by B2-B remain `0`.

### P1-05 — impacted READY-leaf invalidation

- Identifier claims remain append-only non-winner facts.
- After the current evaluation appends its claim/decision, the same
  `BEGIN IMMEDIATE` transaction identifies every provider subject affected by
  the collision.
- Each affected current READY leaf receives a new immutable collision bundle
  and `REVIEW_REQUIRED` successor before commit. The evaluated subject's own
  transition is handled by the normal machine decision in the same
  transaction.
- Old bundles and decisions remain immutable and queryable. Predecessor-child
  uniqueness continues to prevent forks.
- Duplicate corp-code and registrant-CIK tests query provider A after provider
  B commits, without re-evaluating A, and observe `REVIEW_REQUIRED`.
- Concurrent KR and US writer-order tests prove that no committed ordering
  leaves an impacted READY leaf current.
- No human disposition, canonical row, mapping, or link is created.

## 4. Concurrency and controlled READY

SQLite `BEGIN IMMEDIATE` provides a single writer boundary before the engine
reads its clock, provider current set, evidence/relation state, claims,
applications, canonical rows, and current decision leaves. READY still uses
the engine-private insertion path after transaction-time provider, relation,
policy, and collision revalidation. The generic repository direct READY path
continues to raise `REVIEW_READY_ENGINE_NOT_IMPLEMENTED`.

## 5. Migration integrity

Migration changes: `0`. Migration `0006`: `0`.

| Migration | SHA-256 |
|---|---|
| `0001_phase_01_foundation.py` | `6eba164ef2f8bab42583076805255268e4daba29311e8f6e956f4177c0445762` |
| `0002_phase_02_cp3_foundation.py` | `4b6b716999c5f3f6b52be1e85a53685c14c181fb4991e9ead892080717abaee6` |
| `0003_phase_02_cp3_b_invariants.py` | `b59e74b5e817b6a5606d9f89f1f57eec3e0ba3616918d117d3cc28af4f5c420b` |
| `0004_phase_02_cp3_c1_security_master.py` | `cd1cbcae309f1e56ba923e6463863749c79a84b4c10499801f5da28b0a3a0f4f` |
| `0005_phase_02_cp3_c2_b_issuer_authority.py` | `a0c2d77d8db0da59b9fc5058182f367cfdd39ff6b306a03a0e61277d6ff4415b` |

These hashes exactly match the reviewed baseline. Migration tests continue to
cover blank/populated upgrades, downgrade/re-upgrade, simulated late-DDL
failure cleanup/retry, pre-existing object collision, append-only triggers,
old-row preservation, and public Phase 1 revision masking. No persistent or
runtime database received migration `0005` during this remediation.

## 6. LOCAL verification

The commit containing this report is permitted only after the final staged set
produces the following results. This makes the report a commit-time assertion,
not GitHub CI evidence.

| LOCAL command/gate | Result |
|---|---|
| B2-B targeted decision-engine suite | exactly `63`; `63 passed` |
| B2-A authority contract/repository/migration regression | exactly `69`; `69 passed` |
| backend exact discovery/full pytest | exactly `676`; `676 passed` |
| migration regression (`scripts/migrate.ps1 -Action Test`) | PASS |
| fixture import idempotency | PASS |
| frontend Vitest exact inventory/run | exactly `43`; `43 passed` |
| Playwright exact inventory/run | exactly `2`; `2 passed` |
| Ruff format/check | PASS |
| mypy | PASS |
| ESLint | PASS, zero warnings |
| TypeScript/Next route type generation | PASS |
| OpenAPI drift | PASS |
| production build | PASS |
| full `scripts/test.ps1` | PASS |
| `git diff --check` / `git diff --cached --check` | PASS / PASS |
| `scripts/secret-scan.ps1` | PASS |
| `scripts/policy-scan.ps1` | PASS |

GitHub CI execution evidence remains absent. No LOCAL command above is labelled
or represented as GitHub CI.

## 7. Exact zero counters and boundaries

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

## 8. Known limitations and deferred work

- There is intentionally no operational trusted production evidence-ingestion
  path in B2-B. Live adapters and the WebAuthn evidence-ingest ceremony require
  separate authorization and review.
- Only the exact policies currently registered in the server-owned matrix can
  be evaluated. Additional US states require individually approved exact
  policies; there is no wildcard.
- Human approval/authentication, canonical issuer promotion, authority links,
  and link-head projection remain later gated work.
- GitHub CI evidence is absent and remains a truthful non-blocking P2.

## 9. Final checkpoint states

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

STOP after commit and fast-forward push. Do not start B2-C.
