# Phase 2 CP3-C1 Fix Codex Report

CP3-C1:
`REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW`

P1-01:
`REMEDIATED`

P1-02:
`REMEDIATED`

CP3-C2:
`NOT STARTED — USER DECISION REQUIRED`

CP3-D:
`NOT STARTED`

Independent re-review:
`NOT YET PERFORMED`

This report is a Codex self-report and is not an independent QA result.

## Repository and revision

- Repository: `C:\Users\beomoo\Documents\ChatGPT\tosstoss`
- Branch: `feature/phase-02-toss`
- Starting SHA: `4ba8e365f949adcc83ad4b2709455432302b70c1`
- Final SHA: the normal commit containing this report; reported after commit and fast-forward push in the final handoff. A commit cannot contain its own SHA without changing that SHA.
- Remote main and merge-base: `353159da45cfbe3a7f444bf476ce86fa9aece17c`
- Preserved CP3-B stash: not applied, popped, dropped, reset or modified.

## Exact changed paths

- `services/api/src/toss_dashboard_api/domain/security_master.py`
- `tests/backend/test_security_master_reconciliation.py`
- `scripts/test.ps1`
- `scripts/policy-scan.ps1`
- `qa/PHASE_02_CP3_C1_INDEPENDENT_QA.md`
- `qa/PHASE_02_CP3_C1_FIX_CODEX_REPORT.md`
- `STATUS.md`
- `CHANGELOG.md`
- `DECISIONS.md`
- `KNOWN_ISSUES.md`
- `plans/PHASE_02_EXECUTION_PLAN.md`

## P1-01 — current identifier resolution

Root cause: `_current_identifier()` selected the maximum history row by source chronology and then `identifier_history_id`. A symbol transition can emit more than one SYMBOL history row for the same source, so a content-derived ID could select the historical symbol as current.

Resolution rule:

- Source chronology orders observations, but `identifier_history_id` does not participate in semantic current-value resolution.
- A closed identifier is removed from the current set.
- A SYMBOL_CHANGE source observation replaces prior current symbols with its open replacement symbol set.
- Exactly one open semantic value is current.
- More than one contradictory current value fails closed as `UNRESOLVED_COLLISION`/`QUARANTINED`; no arbitrary winner is selected.
- Historical rows and the immutable identity/allocation anchor are preserved.
- A provider `listDate` or `fetched_at` is not fabricated as a symbol-change effective date. New symbol-change history uses `valid_from=null` when the provider supplies no change date.

Regression coverage includes OLD/ISIN X → NEW/ISIN X → NEW without additional strong identifier evidence, service-level current lookup through discovery/detail-missing staging, OLD non-current behavior, anchor preservation, identity count one, and malformed contradictory open current symbols.

## P1-02 — batch collision planning

Root cause: `reconcile_detail()` persisted each requested symbol immediately. In one STOCK_DETAIL source, A/ISIN X could therefore be published eligible before B/ISIN X exposed the collision.

Resolution behavior:

- The complete validated detail response is analyzed before any source observation is published.
- Duplicate non-null ISIN values are detected across the full response.
- Continuity candidates and relevant existing active histories are collected for every affected item and combined into one source-consistent collision plan.
- Every affected observation is persisted directly as `QUARANTINED`/`UNRESOLVED_COLLISION`; an eligible first writer is never emitted.
- New-candidate duplicates allocate no provider identity. Existing-identity duplicates transition every affected identity consistently. Auto merge, arbitrary winner, canonical mapping and canonical promotion remain zero.
- Equivalent `[A, B]` and `[B, A]` responses produce byte-identical canonical ordered staging dumps.

## Tests and inventories

- Added four backend tests: three-step rename/current lookup/partial behavior, ambiguous-current fail-closed, new-candidate same-source duplicate ISIN, and response-order independence.
- Strengthened C-M04/IR-F to inspect both affected observations from the collision source and require both to be non-eligible/quarantined with identical affected identity sets.
- Backend exact inventory: `540 → 544`; `544/544 PASS`.
- Frontend exact inventory: `43`; `43/43 PASS`.
- E2E exact inventory: `2`; `2/2 PASS`.

## Migration, promotion and false-green review

- Migration change: `0`.
- `0001`, `0002`, `0003` and `0004`: byte-identical to the starting SHA.
- New migration: `0`; `0005`: `0`.
- Canonical Issuer/Security creation or auto-promotion: `0`.
- Canonical mapping rows added by remediation tests: `0`.
- Deleted tests: `0`.
- Skip additions: `0`.
- Xfail additions: `0`.
- Assertion weakening: `0`.
- Exception swallowing: `0`.
- Unknown-to-known coercion: `0`.
- Empty collection bypass: `0`.
- Scanner weakening: `0`.
- Policy bypass: `0`.
- External network: `0`.
- The exact policy control-plane digest changes only for the legitimate test and exact inventory control updates; its file count remains unchanged.

## Final staged full regression

- Command: `pwsh -NoProfile -File .\scripts\test.ps1`
- Pre-final attempt record: one run stopped because a locally generated ignored root `.ruff_cache` contained binary Ruff cache input; only that verified generated cache was removed. Two later runs reached secret-scan after all functional gates but its randomized high-entropy invalid-UTF-8 self-canary was not rejected on those invocations. A 10,000-sample read-only reproduction found 319 random 48-byte Base64 values at or below the fixed 4.5 threshold, demonstrating that the baseline self-canary input can probabilistically miss its own rejection threshold. The unchanged secret-scan passed when rerun standalone. Scanner source, scope, filters and thresholds were not modified. The stopped attempts are not reported as the final full regression.
- Backend: `544/544 PASS`.
- Frontend: `43/43 PASS`.
- E2E: `2/2 PASS`.
- Migration: `PASS`.
- Fixture idempotency: `PASS`.
- OpenAPI: `PASS`.
- Build: `PASS`.
- Secret scan: `PASS`.
- Policy scan: `PASS`.
- Full regression: `PASS`, exit `0`.

## Security counts and preserved scope

- Actual credential usage: `0`.
- Actual Toss API requests: `0`.
- External provider requests: `0`.
- OpenAI API requests: `0`.
- Account/order/WebSocket requests or implementation: `0`.
- CP3-C2: `NOT STARTED — USER DECISION REQUIRED`.
- CP3-D: `NOT STARTED`.
- PR, main merge, tag and release: `0`.
