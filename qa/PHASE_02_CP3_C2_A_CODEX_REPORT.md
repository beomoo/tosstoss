# Phase 2 CP3-C2-A Codex Remediation Report

CP3-C2-A:
`REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW`

P1-01 KR jurisdiction boundary:
`REMEDIATED`

P1-02 SEC registrant/login CIK boundary:
`REMEDIATED`

P2 freshness labeling:
`REMEDIATED`

CP3-C1:
`PASS — CLOSED`

CP3-C2-B:
`NOT STARTED`

CP3-C2-C:
`NOT STARTED`

CP3-D:
`NOT STARTED`

Automatic checkpoint progression:
`PROHIBITED`

This report is a Codex self-report. It is not an independent QA result, does
not mark ADR-013 accepted, and does not authorize CP3-C2 implementation.

## Repository and scope

- Repository: `C:\Users\beomoo\Documents\ChatGPT\tosstoss`
- Branch: `feature/phase-02-toss`
- Starting SHA: `0a7463cfbc93b9f19f247577edd73b993efa2766`
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
- Preserved stash: not applied, popped, dropped, or modified.

## Exact changed paths

- `plans/PHASE_02_CP3_C2_PROMOTION_AUTHORITY.md`
- `qa/PHASE_02_CP3_C2_A_CODEX_REPORT.md`
- `qa/PHASE_02_CP3_C2_A_INDEPENDENT_QA.md`
- `STATUS.md`
- `DECISIONS.md`
- `plans/PHASE_02_EXECUTION_PLAN.md`

No production implementation path is part of this remediation.

## Independent-review finding and remediation

### P1-01 — KRX market versus legal jurisdiction

Root cause: the original contract called the KRX instrument path a KR path and
proposed a `Jurisdiction.KR` issuer anchor without expressly prohibiting a KRX
listing from supplying legal jurisdiction. KRX permits foreign corporations to
list, while OpenDART `corp_code`, `corp_cls`, and `stock_code` identify DART and
listing/disclosure context rather than the issuer's legal jurisdiction.

Remediation:

- `market=KR`, KOSPI/KOSDAQ/KONEX, `corp_cls`, `stock_code`, provider market or
  name, and Korean trading currency have zero legal-jurisdiction authority;
- a KRX-listed issuer needs independently established legal jurisdiction that
  is representable by the current canonical `Jurisdiction` contract;
- otherwise the state is `UNRESOLVED / jurisdiction-contract-required` with
  canonical issuer/security, `READY_FOR_MANUAL_REVIEW`, and VERIFIED mapping
  writes all zero; and
- the contract now covers foreign issuers listed in both Korea and the United
  States and includes the required KRX-listed foreign-corporation scenario.

### P1-02 — SEC registrant CIK versus accession/login CIK

Root cause: the original contract required an accepted registrant filing but
did not explicitly prohibit parsing the first ten accession digits into the
registrant CIK or distinguish login/filing-agent CIK provenance from issuer
identity.

Remediation:

- `registrant_cik` must come from authoritative registrant/filer metadata in
  accepted filing/submission evidence;
- the accession-prefix/login CIK and filing-agent CIK are separately typed
  audit provenance with zero issuer authority;
- those provenance CIKs cannot enter `issuer_id`, authority-bundle candidate
  identity, or a SEC registered-class security anchor;
- the free registered-class anchor now requires the independently verified
  registrant CIK; and
- the contract includes both the A-registrant/B-agent Form 8-A negative case
  and the independently unresolved registrant case, each fail-closed.

The SEC EDGAR Next official guidance checked on the retrieval date states that
the accession prefix reflects the login CIK, which may belong to the filer or a
filing agent.

### P2 — 24-hour freshness wording

The 24-hour approval threshold remains as
`REPO_POLICY / CONSERVATIVE_APPROVAL_FRESHNESS`. It is expressly not recorded as
a universal OpenDART/KRX/SEC/Nasdaq/NYSE/CGS rule. Authority publication,
acceptance, effective, and as-of dates remain separate, and `fetched_at` cannot
substitute for them.

## Preserved approved design

- automatic final promotion: `NO`;
- maximum machine-positive state: `READY_FOR_MANUAL_REVIEW`;
- final canonical writes require explicit authenticated human approval;
- humans cannot override unresolved contradictory official evidence;
- provider/canonical identity separation and provider rekey: unchanged / `0`;
- fake corp_code/CIK, name-only merge, symbol-only merge, arbitrary winner: `0`;
- CGS licensing boundary: unchanged;
- correction/revocation: append-only;
- issuer/security authority: separate; and
- split recommendation: CP3-C2-B followed by CP3-C2-C.

## Documentation safety gates

- `git diff --check`: `PASS`, exit `0`.
- `pwsh -NoProfile -File .\scripts\secret-scan.ps1`:
  `PASS`, exit `0`.
- `pwsh -NoProfile -File .\scripts\policy-scan.ps1`:
  `PASS`, exit `0`.
- Known randomized secret-scan self-canary P2 reproduced: `NO`.
- Scanner, threshold, filter, scope, and policy changes: `0`.

The final gate result is written here before commit. If a later documentation
change modifies the tested set, the gates are rerun.

## Checkpoint status

- CP3-C1: `PASS — CLOSED`
- CP3-C2-A: `REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW`
- CP3-C2-B: `NOT STARTED`
- CP3-C2-C: `NOT STARTED`
- CP3-D: `NOT STARTED`
- PR/main merge/tag/release: `0`
