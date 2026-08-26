# Phase 2 CP3-C2-B2-A Remediation Codex Report

## Scope and review state

- Repository: `beomoo/tosstoss`
- Branch: `feature/phase-02-toss`
- Starting / independently reviewed SHA:
  `05eb70d8dfe488563757107c0697f1a7708018c9`
- Final SHA note: the commit SHA cannot be embedded in the commit that defines
  it; it is reported after commit, fast-forward push, and remote verification.
- Date: `2026-08-27` (`Asia/Seoul`)
- Terminal scope: CP3-C2-B2-A independent-review remediation only
- GPT verdict: `CHANGES REQUIRED`
- P0: `0`
- P1: `3`
- P2: `1`
- Resulting state:
  `REMEDIATED — AWAITING GPT INDEPENDENT RE-REVIEW`
- This is LOCAL Codex self-QA evidence and does not declare GPT `PASS`.

## Exact changed paths

1. `CHANGELOG.md`
2. `DECISIONS.md`
3. `STATUS.md`
4. `plans/PHASE_02_CP3_C2_B1_RUNTIME_CONTRACT.md`
5. `plans/PHASE_02_EXECUTION_PLAN.md`
6. `qa/PHASE_02_CP3_C2_B2_A_REMEDIATION_CODEX_REPORT.md`
7. `scripts/policy-scan.ps1`
8. `scripts/test.ps1`
9. `services/api/alembic/versions/0005_phase_02_cp3_c2_b_issuer_authority.py`
10. `services/api/src/toss_dashboard_api/contracts/__init__.py`
11. `services/api/src/toss_dashboard_api/contracts/authority.py`
12. `services/api/src/toss_dashboard_api/repositories/authority.py`
13. `services/api/src/toss_dashboard_api/storage/models.py`
14. `tests/backend/authority_test_helpers.py`
15. `tests/backend/test_authority_contracts.py`
16. `tests/backend/test_authority_migration.py`
17. `tests/backend/test_authority_repository.py`

No route, connector, scheduler, frontend source, fixture, dependency,
credential, network configuration, pre-0005 migration, or live-request path is
changed.

## P1-01 — decision correction supersession

- Removed the incorrect rule that required a successor decision to keep the
  predecessor's `authority_bundle_id`.
- A successor now verifies the exact new immutable bundle and may change
  `proposed_issuer_id`, while the predecessor and successor must have the same
  `provider_security_identity_id` authority subject.
- Missing/self predecessors and unrelated-provider chain grafts fail closed.
- Existing `uq_issuer_decisions_supersedes` continues to allow only one child
  per predecessor, so competing correction successors cannot first-write a
  fork.
- The executable correction test appends original evidence/bundle/decision A,
  corrected evidence plus a `CORRECTS` relation, bundle/decision B with a new
  issuer candidate, and verifies both chains remain queryable. A competing
  child and unrelated-provider child are rejected without updating or deleting
  old rows.

## P1-02 — B2-A review-ready fail-closed boundary

- `IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW` remains in the approved
  contract, but the B2-A low-level repository rejects every such persistence
  attempt with typed `AuthorityReviewReadyEngineNotImplemented` and exact code
  `REVIEW_READY_ENGINE_NOT_IMPLEMENTED`.
- A structurally decisive regulatory-ID plus legal-jurisdiction bundle is not
  treated as the independently proven provider-to-issuer bridge.
- Tests prove that a name/symbol-only CP3-C1 observation and arbitrary active
  observation membership cannot enable READY persistence.
- B2-B must implement the complete production source-admission, exact CP3-C1
  observation-lineage bridge, collision and positive decision engine, then pass
  separate independent review before this gate may be enabled.

## P1-03 — append-only WebAuthn signature-counter foundation

- The immutable credential column is now nullable
  `registration_sign_count`, not a misleading mutable `sign_count`.
- Exact capability is `SIGN_COUNT_SUPPORTED` or `NO_USABLE_COUNTER`. Supported
  credentials require a non-negative registration count; no-counter
  credentials require null.
- Every append-only `reviewer_authentication_events` row adds matching
  `counter_capability`, nullable `previous_sign_count` and
  `asserted_sign_count`, plus `counter_verified`.
- Supported VERIFIED events require non-negative values and strict
  `asserted_sign_count > previous_sign_count`. Equality and rollback cannot
  verify but remain representable as append-only REJECTED audit facts.
- No-counter VERIFIED events require both counts null and do not fabricate zero
  or advancement.
- Current counter reconstruction begins at the immutable registration value and
  follows the unique linear set of VERIFIED counter-bearing events. A gap or
  fork fails closed. The executable restart test reconstructs `5 → 6 → 7`
  after disposing and reopening the SQLite engine.
- Credential and authentication-event UPDATE/DELETE attempts remain blocked by
  append-only database triggers. No WebAuthn cryptographic or enrollment
  runtime is implemented.

## Migration 0005

- Filename:
  `services/api/alembic/versions/0005_phase_02_cp3_c2_b_issuer_authority.py`
- Revision: `0005_phase_02_cp3_c2_b_issuer_authority`
- Down revision: `0004_phase_02_cp3_c1_security_master`
- Shape: additive only against the pre-0005 schema
- Tables: `21`, unchanged from the approved B2-A family
- Named indexes: `14`
- Immutable table families: `20`
- Append-only UPDATE/DELETE triggers: `40`
- Inline checks: `75` (`68` before remediation)
- Mutable authority table: rebuildable `issuer_authority_link_heads` only
- Identifier-claim issuer winner constraint added: `0`
- Migration `0006` created: `0`
- Persistent production/runtime DB applications: `0`
- Disposable local QA applications/downgrades/re-upgrades only

The exact predecessor migration SHA-256 values remain:

| Migration | SHA-256 |
|---|---|
| `0001_phase_01_foundation.py` | `6eba164ef2f8bab42583076805255268e4daba29311e8f6e956f4177c0445762` |
| `0002_phase_02_cp3_foundation.py` | `4b6b716999c5f3f6b52be1e85a53685c14c181fb4991e9ead892080717abaee6` |
| `0003_phase_02_cp3_b_invariants.py` | `b59e74b5e817b6a5606d9f89f1f57eec3e0ba3616918d117d3cc28af4f5c420b` |
| `0004_phase_02_cp3_c1_security_master.py` | `cd1cbcae309f1e56ba923e6463863749c79a84b4c10499801f5da28b0a3a0f4f` |

Existing migrations `0001`–`0004` changed: `0`.

## LOCAL executable QA

All results below are LOCAL Codex evidence, not GitHub CI evidence.

| Command or gate | Local result |
|---|---|
| Targeted authority contract/repository/migration tests | `69 passed` |
| Migration test inventory | exactly `19`; all passed in targeted/full runs |
| Full backend inventory | exactly `613` collected |
| Full backend pytest | `613 passed` |
| Blank DB upgrade through 0005 | `PASS` |
| Populated 0004 → 0005 and old-row byte comparison | `PASS` |
| Disposable 0005 downgrade/re-upgrade | `PASS` |
| Simulated late DDL failure cleanup/retry | `PASS` |
| Pre-existing authority-object collision | fail-closed `PASS` |
| Append-only ledger and counter UPDATE/DELETE rejection | `PASS` |
| Phase 1 public DB revision masking | `PASS` |
| `scripts/migrate.ps1 -Action Test` | exit `0` |
| Fixture import idempotency | exit `0`; second import unchanged |
| Python Ruff format/check | exit `0` |
| Python mypy | exit `0`; 57 source files |
| Frontend ESLint | exit `0` |
| Frontend TypeScript | exit `0` |
| Frontend Vitest inventory/result | exactly `43`; `43 passed` |
| Playwright E2E inventory/result | exactly `2`; `2 passed` |
| OpenAPI generated-contract drift | exit `0` |
| Production Next.js build | exit `0` |
| Existing policy scan | exit `0`; remediation scope policy passed |
| Existing secret scan | exit `0`; `Secret scan passed` |
| `git diff --check` | exit `0` |
| `git diff --cached --check` | exit `0` |
| Final staged `scripts/test.ps1` | exit `0`; all B2-A remediation checks passed |

The exact backend inventory pin changed only from `598` to `613`. The policy
control manifest remains the same 75-file closed set; only its exact digest and
the B2-A remediation success label changed. No scanner, policy prohibition,
test-discovery boundary, secret threshold, or offline network guard was
weakened.

## Exact zero counters and prohibited work

- Canonical Issuer writes caused by B2-A remediation: `0`
- Canonical Security writes caused by B2-A remediation: `0`
- `ProviderIdentityMapping(VERIFIED)` writes: `0`
- Provider identity/allocation/history rekeys: `0`
- Automatic final promotion: `0`
- Fake/synthetic production authority use: `0`
- First-writer canonical identifier winners: `0`
- Immutable ledger destructive rewrites/deletes: `0`
- WebAuthn operational/cryptographic implementation: `0`
- Windows Hello enrollment runtime: `0`
- Human approval execution: `0`
- Approval/authentication HTTP routes: `0`
- Link-head operational workflow: `0`
- Live/external authority or provider requests: `0`
- Toss live requests: `0`

The standard Phase 1 fixture regression still contains its historical
test-only synthetic canonical rows. No B2-A authority flow creates or promotes
those rows, and fixture lineage remains ineligible for production authority.

## CI evidence status and deferred work

No GitHub commit status or workflow-run result is claimed for the reviewed SHA
or this remediation candidate. No GitHub CI/workflow was created or executed as
part of this task. All commands above ran locally and remain LOCAL evidence.
The supplied P2 remains non-blocking but is not represented as resolved.

- ADR-013: `ACCEPTED` and unchanged
- ADR-014: `ACCEPTED` and unchanged
- CP3-C2-B1: `PASS — CONTRACT APPROVED AND CLOSED`
- CP3-C2-B implementation: `IN PROGRESS`
- CP3-C2-B2-A: `REMEDIATED — AWAITING GPT INDEPENDENT RE-REVIEW`
- CP3-C2-B2-B: `NOT STARTED`
- CP3-C2-B2-C: `NOT STARTED`
- CP3-C2-B2-D: `NOT STARTED`
- CP3-C2-C: `NOT STARTED`
- CP3-D: `NOT STARTED`
- Automatic checkpoint progression: `PROHIBITED`

No later checkpoint starts from this remediation report.
