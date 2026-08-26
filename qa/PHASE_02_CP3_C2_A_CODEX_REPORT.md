# Phase 2 CP3-C2-A Codex Planning Report

CP3-C2-A:
`PLANNING COMPLETE — AWAITING GPT INDEPENDENT REVIEW`

CP3-C1:
`PASS — CLOSED`

CP3-C2 implementation:
`NOT STARTED`

CP3-D:
`NOT STARTED`

Automatic checkpoint progression:
`PROHIBITED`

This report is a Codex self-report. It is not an independent QA result and does
not approve the proposed contract or authorize CP3-C2 implementation.

## Repository and scope

- Repository: `C:\Users\beomoo\Documents\ChatGPT\tosstoss`
- Branch: `feature/phase-02-toss`
- Starting SHA: `42cfee25418251f998e6f79981352390d9bf2540`
- Final SHA: the normal documentation commit containing this report; reported
  after commit and fast-forward push. A commit cannot contain its own SHA
  without changing that SHA.
- Research/retrieval date: `2026-08-26` (`Asia/Seoul`)
- Application/domain/repository/storage changes: `0`
- Migration changes: `0`
- Fixture/test/script/policy changes: `0`
- API/frontend/scheduler/connector changes: `0`
- Actual credentials used: `0`
- Actual Toss API requests: `0`
- External provider requests made by repository code: `0`
- Order/account/WebSocket scope: `0`
- Preserved stash: not applied, popped, dropped, or modified.

## Exact planned changed paths

- `plans/PHASE_02_CP3_C2_PROMOTION_AUTHORITY.md`
- `qa/PHASE_02_CP3_C2_A_CODEX_REPORT.md`
- `STATUS.md`
- `DECISIONS.md`
- `plans/PHASE_02_EXECUTION_PLAN.md`

No production implementation path is part of this checkpoint.

## Research performed

Current public authority material was re-checked on the retrieval date. The
contract records the exact URL, field, field-specific authority scope,
limitations, access/licensing boundary, and conflict behavior for each source.

Korea research covered:

- FSS OpenDART corporation code and company overview;
- Supreme Court Internet Registry legal-entity authority/access limits;
- KRX Standard Code System, market-specific issue-basic services, listing and
  delisting data, and KIND;
- KSD/SEIBro supporting evidence; and
- Toss and unofficial-source discovery-only boundaries.

United States research covered:

- SEC CIK uniqueness/scope and EDGAR accepted submissions;
- SEC's explicit accuracy/scope limitation for company ticker files;
- Form 8-A, periodic filing cover rows, and Form 25;
- Nasdaq and NYSE primary-listing evidence;
- FINRA OTC scope;
- CGS CUSIP/ISIN numbering authority and license requirements;
- GLEIF/state-registry supporting boundaries; and
- Toss/OpenFIGI/commercial discovery-only boundaries.

Only public documentation was inspected. No credentialed authority or provider
API was called.

## Contract conclusion

Automatic final canonical promotion proposed:
`NO`

Automation may collect, normalize, revision-check, collision-scan, and assemble
an immutable evidence bundle. Its terminal positive state is only
`READY_FOR_MANUAL_REVIEW`. A current canonical issuer/security and
`ProviderIdentityMapping(VERIFIED)` require an explicit authenticated human
data-steward approval. Manual approval cannot override contradictory official
evidence.

### KR issuer authority

OpenDART `corp_code` is the strong disclosure-registry issuer identifier. The
company overview and, when available through a permitted workflow, court
registry/LEI evidence support legal identity. Toss name/symbol and KRX short
code cannot create or replace corp_code.

### KR security authority

KRX is the field-owning authority for the Korean standard security code/ISIN,
market, share/stock kind, and listing lifecycle. Final provider linkage requires
an approved OpenDART issuer, an unambiguous OpenDART stock-code→KRX issue bridge,
an exact provider ISIN→KRX ISIN match, current/historical listing evidence, no
collision, and manual approval.

### US issuer authority

SEC CIK is the strong SEC-filer identifier, but CIK scope must be confirmed by
an accepted issuer filing showing that the candidate is the registrant rather
than a filing agent, fund, or individual. Ticker/name and SEC's ticker
convenience files are not issuer authority.

### US security authority

An accepted SEC class-registration anchor and the field-owning primary
exchange's class/ticker/listing evidence must agree. A licensed CGS CUSIP/ISIN
may be used only under a separately approved compliant access path. Without
licensed CGS data, the proposal permits a separately reviewed immutable SEC
registered-class anchor, never a ticker anchor. All final decisions remain
manual.

## Fail-closed and no-rekey review

The proposed contract explicitly requires:

- default `UNRESOLVED`;
- canonical writes `0` under missing, stale, contradictory, unavailable,
  unlicensed, or ambiguous evidence;
- duplicate-identifier affected candidates all quarantined with no winner;
- fake corp_code/CIK `0`;
- name-only and symbol-only merge `0`;
- provider identity, allocation anchor, raw/source history, identifier history,
  normalized record, and observation rekey/rewrite `0`;
- `fetched_at` never used as an authority effective date; and
- append-only correction/revocation/history.

## Current schema findings

The existing schema requires issuer and security together for a `VERIFIED`
provider mapping and cannot represent issuer-approved/security-unresolved,
multi-state approval/revocation, a cross-authority evidence bundle, or an
approver identity. The current `ShareClass.COMMON` and KR/US-only jurisdiction
also cannot safely represent all required US/KR cases. Existing Phase 1
synthetic identifiers remain regression fixtures only and are prohibited as
new promotion evidence.

These are later implementation design requirements, not changes in CP3-C2-A.
No `0005` or other migration was created. Any versioned contract/additive
migration requires a separate authorized implementation checkpoint.

## Split recommendation

Recommendation:
`CP3-C2-B issuer authority/mapping` followed by
`CP3-C2-C security authority/final mapping`.

The split keeps issuer approval truthful when the security is unresolved and
isolates the higher-risk instrument, share-class, listing, ticker-reuse, and
CUSIP/ISIN licensing decisions. CP3-C2-B does not set
`ProviderIdentityMapping` to `VERIFIED`; CP3-C2-C may do so only after separate
approval and the complete authority bundle.

## Scenario coverage in the contract

The decision table covers:

- KR corp_code plus instrument evidence;
- US CIK plus instrument evidence;
- multiple share classes;
- ticker reuse after delisting and ticker change with issuer continuity;
- ISIN correction and duplicate active ISIN;
- provider and regulatory name mismatch;
- unavailable corp_code/CIK;
- one-to-many and many-to-one mapping candidates;
- historical correction and revocation;
- issuer verified while security remains unresolved; and
- strong issuer evidence with weak instrument evidence.

## Documentation safety gates

- `pwsh -NoProfile -File .\scripts\secret-scan.ps1`: `PASS`, exit `0`.
- `pwsh -NoProfile -File .\scripts\policy-scan.ps1`: `PASS`, exit `0`.
- Known randomized secret-scan self-canary P2 reproduced: `NO`.
- Scanner, threshold, filter and scope changes: `0`.
- Policy bypass: `0`.

These results are re-run after this result record is staged so the final commit
content, rather than an earlier draft, is the tested documentation set.

## Checkpoint status

- CP3-C1: `PASS — CLOSED`
- CP3-C2-A: `PLANNING — AWAITING GPT INDEPENDENT REVIEW`
- CP3-C2 implementation: `NOT STARTED`
- CP3-D: `NOT STARTED`
- PR/main merge/tag/release: `0`
