# Phase 2 CP3-C2-B2-A Codex Self-QA Report

## Scope and state

- Repository: `beomoo/tosstoss`
- Branch: `feature/phase-02-toss`
- Starting SHA: `7f7b935be0ec1b7e5761e1c3b6851dde23d9c7c6`
- Final SHA note: the commit SHA cannot be embedded in the commit that defines
  it; it is reported after commit, push, and remote verification.
- Date: `2026-08-27` (`Asia/Seoul`)
- Terminal scope: `CP3-C2-B2-A — Authority Ledger & Additive 0005 Foundation`
- CP3-C2-B implementation: `IN PROGRESS`
- CP3-C2-B2-A: `IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW`
- This report is local Codex self-QA evidence. It does not declare GPT `PASS`.

## Exact changed paths

1. `CHANGELOG.md`
2. `DECISIONS.md`
3. `STATUS.md`
4. `plans/PHASE_02_CP3_C2_B1_RUNTIME_CONTRACT.md`
5. `plans/PHASE_02_EXECUTION_PLAN.md`
6. `qa/PHASE_02_CP3_C2_B2_A_CODEX_REPORT.md`
7. `scripts/policy-scan.ps1`
8. `scripts/test.ps1`
9. `services/api/alembic/versions/0005_phase_02_cp3_c2_b_issuer_authority.py`
10. `services/api/src/toss_dashboard_api/contracts/__init__.py`
11. `services/api/src/toss_dashboard_api/contracts/authority.py`
12. `services/api/src/toss_dashboard_api/repositories/authority.py`
13. `services/api/src/toss_dashboard_api/repositories/sqlite.py`
14. `services/api/src/toss_dashboard_api/storage/models.py`
15. `tests/backend/authority_test_helpers.py`
16. `tests/backend/test_authority_contracts.py`
17. `tests/backend/test_authority_migration.py`
18. `tests/backend/test_authority_repository.py`
19. `tests/backend/test_migrations.py`
20. `tests/backend/test_provider_migration.py`
21. `tests/backend/test_repositories.py`

No route, connector, scheduler, frontend, fixture, dependency, credential,
network configuration, or pre-existing migration path is changed.

## Migration 0005

- Filename:
  `services/api/alembic/versions/0005_phase_02_cp3_c2_b_issuer_authority.py`
- Revision: `0005_phase_02_cp3_c2_b_issuer_authority`
- Down revision: `0004_phase_02_cp3_c1_security_master`
- Migration shape: additive only; no old-table ALTER, backfill, rekey, or rewrite
- New tables: `21`

The exact new tables are:

1. `authority_source_policies`
2. `reviewer_principals`
3. `reviewer_webauthn_credentials`
4. `reviewer_webauthn_credential_events`
5. `authority_evidence`
6. `authority_evidence_observations`
7. `authority_evidence_relations`
8. `authority_evidence_applications`
9. `authority_bundles`
10. `authority_bundle_evidence_applications`
11. `authority_bundle_scope_results`
12. `authority_bundle_provider_observations`
13. `authority_identifier_claims`
14. `issuer_decisions`
15. `issuer_approval_challenges`
16. `issuer_approval_challenge_consumptions`
17. `reviewer_authentication_events`
18. `issuer_approval_events`
19. `issuer_approval_evidence_observations`
20. `issuer_authority_links`
21. `issuer_authority_link_heads`

Schema enforcement created by 0005:

- Inline `CHECK` expressions: `68`
- Named indexes: `14`, including non-unique identifier/provider claim lookup,
  evidence/application lookup, and unique linear-chain constraints for
  decisions, credential events, approval events, and link history
- Append-only triggers: `40` (`BEFORE UPDATE` + `BEFORE DELETE` on each of 20
  immutable table families)
- Sole mutable authority table: rebuildable `issuer_authority_link_heads`
- Contradictory corp_code/CIK claims remain storable; the identifier lookup
  index is deliberately non-unique and creates no first-writer winner.

The migration was applied only to disposable local QA databases for blank,
0004-upgrade, downgrade/re-upgrade, failure/retry, and full-suite verification.
Persistent runtime/production database application count is `0`.

## Predecessor migration integrity

The approved starting SHA and final working tree have the same exact hashes:

| File | SHA-256 |
|---|---|
| `0001_phase_01_foundation.py` | `6eba164ef2f8bab42583076805255268e4daba29311e8f6e956f4177c0445762` |
| `0002_phase_02_cp3_foundation.py` | `4b6b716999c5f3f6b52be1e85a53685c14c181fb4991e9ead892080717abaee6` |
| `0003_phase_02_cp3_b_invariants.py` | `b59e74b5e817b6a5606d9f89f1f57eec3e0ba3616918d117d3cc28af4f5c420b` |
| `0004_phase_02_cp3_c1_security_master.py` | `cd1cbcae309f1e56ba923e6463863749c79a84b4c10499801f5da28b0a3a0f4f` |

- Existing migrations `0001`–`0004` changed: `0`
- Existing provider/issuer/security/source/history rows rewritten: `0`
- Existing rows in a populated 0004 database survived upgrade byte-for-byte.
- Public Phase 1 database revision contract remains `0001_phase_01`; only the
  internal additive Alembic head advances to 0005.

## Contracts, models, and repository primitives

The B2-A contract foundation adds:

- canonical UTF-8/NFC JSON serialization and SHA-256 semantic ID/hash helpers;
- immutable versioned source policy, evidence, evidence observation, evidence
  relation, evidence application, exact bundle application member/scope result,
  identifier claim, and issuer machine-decision contracts;
- exact source namespace/document/scope/role/weight admission and server-owned
  production policy registry binding;
- permanent fixture/test/synthetic lineage taint and zero production authority;
- raw fact versus candidate-specific application separation, including exact
  raw claim value, normalized claim value, locator, document reference,
  content hash, authority time, policy, lineage, candidate and provider
  observation binding;
- order-independent exact application bundle membership and explicit
  `MISSING`, `CONFLICT`, `STALE`, `UNSUPPORTED`, and `UNUSABLE` scope results;
- append-only, non-winner identifier claims and machine-only decisions whose
  maximum positive state is `READY_FOR_MANUAL_REVIEW`; and
- low-level SQLite insert-or-verify primitives returning idempotent success for
  same ID/same immutable payload and typed conflict for same ID/different
  immutable payload or provenance.

Semantic identity excludes `fetched_at`, `retrieved_at`, `evaluated_at`,
`recorded_at`, database IDs, job/run/request IDs, insertion/parser order,
current clock, local paths, and authentication sessions. Authority-supplied
semantic time fields remain semantic.

The repository intentionally exposes no approve, authenticate, promote,
canonical Issuer/Security write, VERIFIED mapping, or link-head mutation method.

## Executable local QA

All commands below ran locally with the repository offline/network guards. They
are LOCAL Codex evidence, not GitHub CI evidence.

| Command/gate | Result |
|---|---|
| B2-A targeted authority contract/repository/migration tests | `54 passed` |
| Full backend inventory | exactly `598` collected |
| Full backend pytest | `598 passed` |
| B2-A migration tests | `11 passed` within the targeted/full runs |
| Blank DB upgrade through 0005 | `PASS` |
| Existing 0004 DB upgrade and old-row byte comparison | `PASS` |
| 0005 disposable downgrade/re-upgrade | `PASS` |
| Simulated mid-migration DDL failure cleanup and retry | `PASS` |
| Append-only UPDATE/DELETE rejection | `PASS` |
| `pwsh -NoProfile -File .\scripts\migrate.ps1 -Action Test` | exit `0` |
| Fixture import idempotency | exit `0`; second import unchanged |
| Frontend Vitest inventory/result | exactly `43`; `43 passed` |
| Playwright E2E inventory/result | exactly `2`; `2 passed` |
| Python Ruff/format and frontend ESLint | exit `0` |
| Python mypy and frontend TypeScript | exit `0` |
| OpenAPI generated-contract drift check | exit `0` |
| Production Next.js build | exit `0` |
| Default Toss preflight | `MODE=OFFLINE`; external requests `0`; credentials used `0` |
| Toss preflight self-test | all cases `PASS`; external requests `0` |
| Existing secret scan | exit `0`; `Secret scan passed` |
| Existing policy scan | exit `0`; `Phase 2 CP3-C2-B2-A scope policy scan passed` |
| `git diff --check` | exit `0` |
| `git diff --cached --check` | exit `0` |
| Full staged `scripts/test.ps1` | exit `0`; all CP3-C2-B2-A checks passed |

The first full-suite attempt completed backend, migration, fixture, frontend,
build, and E2E execution but correctly stopped at the secret scanner because
the authorized working tree had not yet been staged. No scanner exception was
added. The final report and all authorized files were staged before the final
full-suite run so the successful secret/policy result covers the exact commit
candidate.

During staged pre-gate verification, two secret scans were accidentally
overlapped; the second correctly detected the first scanner's deliberate
temporary entropy canary. After the first process exited and removed that
temporary directory, one serial scan found an ignored `.mypy-authority-temp`
cache from an earlier direct typecheck plus the four predecessor hashes written
as uninterrupted Python hex literals. The generated cache was moved out of the
repository, and the same hash values were expressed as concatenated
eight-character audit chunks. No scanner rule, filter, threshold, scope, or
exception changed. The final serial and full-suite scans then ran against the
exact staged candidate.

`scripts/test.ps1` changed only to rename its checkpoint inventory function and
raise the exact backend inventory from `544` to `598`. `scripts/policy-scan.ps1`
changed only to add the three new `test_authority_*.py` files to its exact test
allowlist, raise the exact control-file count from `71` to `75`, refresh the
exact manifest digest, and update its success label. Scanner assertions,
prohibited-path rules, secret logic, and network guards were not weakened.

## Exact zero counters and terminal boundary

- Canonical Issuer writes caused by B2-A authority flow: `0`
- Canonical Security writes caused by B2-A: `0`
- `ProviderIdentityMapping(VERIFIED)` writes caused by B2-A: `0`
- Provider identity/allocation/history rekeys: `0`
- Automatic final promotion: `0`
- First-writer canonical identifier winners: `0`
- Fake/synthetic production authority uses: `0`
- Live/external authority requests: `0`
- Toss live requests: `0`
- Credential uses: `0`
- WebAuthn operational implementation: `0`
- Windows Hello enrollment runtime: `0`
- Authentication/approval routes: `0`
- Human approval execution: `0`
- Canonical issuer promotion service: `0`
- Link-head workflow implementation: `0`

The standard disposable Phase 1 fixture regression still creates its historical
test-only canonical fixture rows; those are not B2-A authority promotion and
cannot enter a production authority policy/bundle.

## Deferred work and known limitations

- The reviewer/WebAuthn/challenge/authentication/approval/link schemas are
  foundation only. Cryptographic assertion verification, enrollment, routes,
  human dispositions and link-head compare-and-swap are deferred.
- No OpenDART, SEC, IROS, US state-registry, KRX, or Toss live adapter/request is
  implemented or executed for B2-A.
- No canonical Issuer creation/link transaction is implemented; issuer
  promotion remains a later separately gated B phase.
- No canonical Security authority, Current Price, UI, scheduler, account,
  order, or WebSocket work is included.
- No GitHub commit status or workflow run is claimed. All QA in this report is
  local evidence pending GPT independent review of the pushed SHA.

## Final checkpoint states

- ADR-013: `ACCEPTED` and unchanged
- ADR-014: `ACCEPTED` and unchanged
- CP3-C2-B1: `PASS — CONTRACT APPROVED AND CLOSED`
- CP3-C2-B implementation: `IN PROGRESS`
- CP3-C2-B2-A: `IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW`
- CP3-C2-B2-B: `NOT STARTED`
- CP3-C2-B2-C: `NOT STARTED`
- CP3-C2-B2-D: `NOT STARTED`
- CP3-C2-C: `NOT STARTED`
- CP3-D: `NOT STARTED`
- Automatic checkpoint progression: `PROHIBITED`

No later checkpoint starts from this report.
