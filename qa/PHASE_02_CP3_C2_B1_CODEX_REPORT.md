# Phase 2 CP3-C2-B1 Codex Design Report

CP3-C2-B1:
`PLANNING — AWAITING GPT INDEPENDENT REVIEW`

CP3-C2-B implementation:
`NOT STARTED`

CP3-C2-C:
`NOT STARTED`

CP3-D:
`NOT STARTED`

Automatic checkpoint progression:
`PROHIBITED`

This is a Codex self-report for a design-only checkpoint. It is not an
independent QA verdict, does not accept proposed ADR-014, and does not authorize
runtime or migration implementation.

## Repository and revision

- Repository path: `C:\Users\beomoo\Documents\ChatGPT\tosstoss`
- Repository: `beomoo/tosstoss`
- Branch: `feature/phase-02-toss`
- Authoritative starting SHA:
  `959f78415aade27e57d191db3025c66ea4266999`
- Starting remote branch: same authoritative SHA
- Final SHA: the documentation commit containing this report; reported after
  commit and fast-forward push. A commit cannot contain its own SHA without
  changing that SHA.
- Design date: `2026-08-26` (`Asia/Seoul`)

## Exact changed paths

- `plans/PHASE_02_CP3_C2_B1_RUNTIME_CONTRACT.md`
- `qa/PHASE_02_CP3_C2_B1_CODEX_REPORT.md`
- `STATUS.md`
- `DECISIONS.md`
- `plans/PHASE_02_EXECUTION_PLAN.md`

No application, migration, model, repository, fixture, test, script, policy,
API, frontend, scheduler, connector, dependency, or runtime configuration path
is part of this checkpoint.

## Delivered contract design

The runtime design defines independent versions for:

- `AuthorityEvidence` — immutable field-scoped authority fact with raw hash,
  provenance, authority role, permitted-use state, authority time, and zero-
  authority login/agent role separation;
- `AuthorityBundle` — immutable ordered evidence/provider-lineage snapshot for
  one provider identity and one deterministic issuer candidate;
- `IssuerDecision` — append-only machine state whose maximum positive result is
  `READY_FOR_MANUAL_REVIEW`;
- `IssuerApprovalEvent` — exact-bundle, server-authenticated human approval,
  rejection, revocation, and supersession event with no conflict override; and
- `IssuerAuthorityLink` — append-only provider-to-issuer authority history with
  `security_resolution_state=UNRESOLVED`.

The design adds no values to existing `MappingStatus`. `UNRESOLVED`,
`READY_FOR_MANUAL_REVIEW`, `STALE`, `REVIEW_REQUIRED`, `APPROVED`, `REJECTED`,
`REVOKED`, and `SUPERSEDED` are assigned to new contract-specific state axes.

## Deterministic identity and history

- Canonical serialization is UTF-8/NFC JSON, sorted keys, contract-defined
  member ordering, exact enum/null/time representation, and SHA-256.
- Evidence, bundle, decision, issuer, approval-event, relation, and link ID
  preimages are explicit.
- Retrieval/evaluation/approval/database clocks, run/job/attempt/row IDs,
  insertion or response order, local paths, and authentication sessions are
  excluded from semantic identity.
- Authority-supplied publication/acceptance/as-of/effective facts remain
  semantic when present.
- Corrections, revocations, supersessions, decisions, approval events, and link
  state are append-only. The only mutable proposal is a rebuildable current-head
  CAS projection.

## KR and US boundary review

### Korea

- OpenDART 8-digit `corp_code` is the issuer regulatory anchor in its scope.
- Legal jurisdiction is independently established; KRX market,
  KOSPI/KOSDAQ/KONEX, OpenDART `corp_cls`/`stock_code`, provider market/name, and
  KR currency have zero jurisdiction authority.
- A KRX-listed foreign issuer outside the current KR/US jurisdiction contract is
  `UNRESOLVED / jurisdiction-contract-required`.
- Name-only/symbol-only merge, fake corp code, arbitrary collision winner, and
  fetched-time effective date remain prohibited.

### United States

- Zero-padded `registrant_cik` comes only from authoritative registrant/filer
  metadata in accepted evidence where the candidate is the registrant.
- Accession-prefix/login and filing-agent CIK facts are separate
  `SUBMISSION_PROVENANCE` records with issuer-authority weight zero.
- An accepted issuer filing is required; ticker convenience files and provider
  ticker/name are not issuer authority.
- A foreign private issuer is not coerced to US jurisdiction. Unsupported actual
  jurisdiction remains unresolved even with a valid CIK and accepted filing.

## Concurrency and integrity design

- One decision root and one unique successor edge form a linear decision chain.
- One initial human disposition per exact decision prevents simultaneous
  approve/reject.
- Approval events and issuer links use unique predecessor edges; old rows remain
  queryable.
- Approval executes under a serialized transaction, reloads the exact immutable
  bundle, revalidates current evidence/relation/freshness/collision/provider
  state, verifies server-resolved human authentication, insert-or-verifies the
  canonical issuer, appends event/link, and CAS-updates the head.
- Strong identifier claims are all stored before review. The design intentionally
  does not use a global unique insert as a first-writer winner. More than one
  distinct candidate fingerprint makes every affected candidate unresolved or
  review-required.
- A late contradiction appends a negative safety hold; it does not delete the
  old approval or let a reviewer select an unresolved winner.

## Proposed additive migration

- Proposed revision:
  `0005_phase_02_cp3_c2_b_issuer_authority`
- Proposed down revision:
  `0004_phase_02_cp3_c1_security_master`
- Proposed new-table families: authority evidence/retrieval/relation,
  bundle/evidence/provider-observation membership, identifier claims,
  decisions, authenticated approval events/freshness observations, issuer-only
  link history, and a rebuildable head projection.
- Existing table alteration, backfill, destructive rebuild, fake identifier
  population, provider rekey, or history rewrite: `0`.
- `0005` file created: `0`.
- Migration applied: `0`.

Starting migration SHA-256 baseline:

| Migration | SHA-256 |
|---|---|
| `0001_phase_01_foundation.py` | `6eba164ef2f8bab42583076805255268e4daba29311e8f6e956f4177c0445762` |
| `0002_phase_02_cp3_foundation.py` | `4b6b716999c5f3f6b52be1e85a53685c14c181fb4991e9ead892080717abaee6` |
| `0003_phase_02_cp3_b_invariants.py` | `b59e74b5e817b6a5606d9f89f1f57eec3e0ba3616918d117d3cc28af4f5c420b` |
| `0004_phase_02_cp3_c1_security_master.py` | `cd1cbcae309f1e56ba923e6463863749c79a84b4c10499801f5da28b0a3a0f4f` |

## Scope and security counters

- Automatic canonical promotion: `0`.
- Canonical Issuer rows created: `0`.
- Canonical Security rows created: `0`.
- Existing ProviderIdentityMapping rows created or modified: `0`.
- Existing MappingStatus values changed: `0`.
- Fake/synthetic corp_code or CIK created: `0`.
- Provider identity/allocation-anchor/history rekey: `0`.
- Runtime application change: `0`.
- Migration/test/fixture change: `0`.
- Actual credentials used: `0`.
- Actual Toss/OpenDART/KRX/SEC/exchange/CGS requests: `0`.
- OpenAI API requests: `0`.
- Account/order/WebSocket code or request: `0`.
- LIVE_VERIFIED scope expansion: `0`.
- PR/main merge/tag/release: `0`.

## Documentation safety gates

- `git diff --check`: `PASS`, exit `0`.
- Additional staged-content check `git diff --cached --check`: `PASS`, exit `0`.
- The required command `pwsh -NoProfile -File .\scripts\secret-scan.ps1`
  completed with `PASS` and exit `0`; it reported
  `Validated narrow generated-hash exceptions: 2147`.
- The required command `pwsh -NoProfile -File .\scripts\policy-scan.ps1`
  completed with `PASS` and exit `0`; it reported
  `Phase 2 CP3-C1 scope policy scan passed`.
- Pre-final secret-scan attempt: stopped before scanning because the scanner
  requires index/working-tree parity and the five documentation paths had not
  yet been staged. This was not a secret finding. After staging the exact five
  paths, the scanner completed with exit `0`.
- Known randomized secret-scan self-canary P2 reproduced: `NO` on the completed
  run.
- An intermediate final rerun rejected the earlier colon-separated command/result
  wording on line 170 because it resembled a credential assignment. Only this
  report wording was changed; scanner code, rules, threshold, and scope stayed
  unchanged.
- Scanner, threshold, scope, filter, allowlist, and policy changes: `0`.

These results cover the staged documentation set before this result block was
updated. The report update is restaged and all three required gates are rerun
before commit.

## Independent-review focus

GPT independent review should particularly challenge:

1. whether the provider-to-issuer bridge is strong enough to maintain the exact
   `name-only/symbol-only merge = 0` invariant without beginning security
   approval;
2. whether the separate semantic and audit hashes exclude every retrieval/run/
   DB-order influence while preserving authority-supplied time facts;
3. whether identifier-claim concurrency can ever leave a first writer
   operationally approved after a conflicting claim;
4. whether authenticated-human prerequisites are implementable without trusting
   caller-supplied identity or storing credentials;
5. whether review-required safety holds preserve human approval history without
   being misrepresented as automatic revocation;
6. whether the proposed table/check/index/trigger set is sufficient and minimal;
   and
7. whether any KR foreign-issuer or US foreign-private-issuer path accidentally
   infers jurisdiction from a listing or SEC registration.

## Known limitations and checkpoint result

- Exact runtime local authentication/reauthentication policy remains to be
  independently reviewed and explicitly approved before implementation.
- No official authority connector or live response is implemented or newly
  verified by B1.
- The proposed migration has not been exercised; all migration tests are later
  implementation acceptance requirements.
- Proposed ADR-014 remains `PROPOSED`.
- CP3-C2-B1 remains `PLANNING — AWAITING GPT INDEPENDENT REVIEW`.
- CP3-C2-B implementation, CP3-C2-C, and CP3-D remain `NOT STARTED`.
