# CP3-C2-C2 Machine Security Authority Engine — Self-QA

## Current consolidated remediation evidence boundary — 2026-09-30

- Prior candidate: `8d02d24562f0567375c465cdcd79bb5e3f8c3dfc`; integration base: `120194fe6631db51c115776a49c55d3a25d93e7e`; same implementation branch. The prior candidate remains FAIL and is not eligible for integration.
- R1–R5 corrections and `tests/backend/test_security_authority_remediation.py` address all 14 consolidated counterexamples, additional missing/excluded provenance paths, SUPPORT-only cover controls, joint KR type/kind checks, repository corruption, prerequisite loss, exact replay and restoration.
- Repository READY reconstruction checks current issuer/provider membership, exact admitted scope composition, evidence/policy hashes, adapter/parser and relation head, required-source freshness, class facts, canonical binding, adverse facts and global collision. It does not trust SATISFIED labels supplied by the draft.
- Full Windows QA must run from the beginning after focused/regression PASS, on the byte-identical mirror with an index matching its worktree. All gate counts/exits, final scanner pins, before/after equality, frozen proof and final commit/tree are recorded in the fresh external final review package. This source snapshot does not claim full-QA success from historical runs below.
- Successful maximum: `CP3-C2-C2 REMEDIATED — GPT FINAL INDEPENDENT RE-VERIFICATION REQUIRED`. No integration merge, C3, live authority, production writes, shared counter runtime or Security-head reader cutover is part of this work.

## Historical initial C2 self-QA (unchanged prior candidate evidence)

- Date: 2026-09-30
- Branch: `feature/phase-02-c2c2-machine-security-authority`
- Base: `120194fe6631db51c115776a49c55d3a25d93e7e`

## Scope

The engine evaluates immutable, normalized stored evidence through a closed server-owned registry and can produce at most `READY_FOR_MANUAL_REVIEW`. It reconstructs correction heads, binds the approved issuer link and current provider observation, applies source-specific freshness, builds immutable applications/claims/bundles/decisions, and evaluates contradictions and global collisions in a writer-locked transaction.

KR production readiness is limited to the reviewed KRX standard-code, issue-basic, human-assisted listing-lifecycle, and OpenDART bridge evidence. US positive readiness requires accepted SEC Form 8-A class evidence and current Nasdaq primary evidence. SEC Form 25 is negative/removal authority; periodic cover evidence is support only. NYSE and CGS remain `production_eligible=0`. Caller-supplied authority, fixture/test lineage, arbitrary policies, and generic repository writes cannot manufacture positive decisions.

The candidate adds no migration and does not implement live KRX/SEC/Nasdaq/NYSE/CGS/Toss requests, C3 WebAuthn or human disposition, canonical Security writes, Security link/head mutation, legacy `VERIFIED` mappings, production DB mutation, or public exposure.

## Focused and regression coverage

The C2 engine tests include complete KR and SEC+Nasdaq positive paths; unsupported NYSE; SEC accession-prefix/registrant identity; issuer/provider prerequisites; class/title/ticker agreement; instrument-family rejection; missing, stale, contradictory and ambiguous authority; Form 25; correction-head and fork handling; fixture-taint preservation; global collision quarantine; replay idempotency; and concurrent positive evaluations. The engine boundary tests verify that generic repository callers remain blocked from production admission and positive C2 decisions, and that C2 does not write C3 or legacy mapping rows.

The standard Windows backend suite also reran the 0008 contracts/repository/migration tests, B issuer authority, B2-B decisions, B2-D disposition, provider security-master, and migration revision coverage. No schema or migration file changed.

## Windows standard QA, attempt 06

The repository-standard `scripts/test.ps1` ran from the beginning in the fixed Windows QA mirror `C:\Users\beomoo\c2c2-machine-authority-qa-20260930`. The run completed with exit code **0**. Before staging, the exact synchronized candidate must pass the full suite from the beginning; that run's evidence belongs in the final handoff package.

| Gate | Result |
|---|---|
| Initial policy | PASS, exit 0; external requests 0, credentials used 0 |
| Backend pytest | 1,294 passed; 0 failed, skipped, xfailed, or deselected; exit 0 |
| Ruff / format | PASS, exit 0; 133 files formatted, all checks passed |
| Mypy | PASS, exit 0; 74 source files, no issues |
| Frontend lint | PASS, exit 0 |
| Frontend typecheck | PASS, exit 0 |
| Frontend build | PASS, exit 0 |
| Frontend unit | 43 passed in 10 files; 0 failed, skipped, xfailed, or deselected; exit 0 |
| API contract | PASS, exit 0 |
| Migration repeat / downgrade / re-upgrade | PASS, exit 0 |
| Fixture idempotency | PASS, exit 0; first import inserted 13, second inserted 0 and left 13 unchanged |
| E2E | 2 passed; 0 failed, skipped, xfailed, or deselected; exit 0 |
| Final secret scan | PASS, exit 0 |
| Final policy scan | PASS, exit 0 |

The backend pytest summary was `1294 passed in 1772.47s (0:29:32)`. The frontend unit summary was `43 passed (43)` across 10 files. Playwright reported `2 passed (13.7s)`. The fixed policy-canary check reported 4 positive and 35 negative URL cases, one exact approved source span, and zero network authority. The secret scanner reported 74 source files, 861 metadata files, 1,722 mypy proofs, 1,717 mypy findings, 2,415 applied findings, and 5 proof-only unregistered findings.

Scanner byte identity at attempt 06:

```text
scripts/secret-scan.ps1 SHA-256:
9fb0e899c1914bd049af4690c0d38d7a479d1eb284fa498dfdb62d289ea20162

policy-control inventory:
98 files, SHA-256 69bca14fc545c0c81ba7a72f39e996c5c38938cd56346f8cfa46b262e63944e4
```

Scanner edits synchronize the measured test/control inventory and the exact reviewed SEC/Nasdaq locator roots in the C2 registry. Detector thresholds, exception behavior, and exclusions were not relaxed.

## Final synchronized Windows standard QA, attempt 09

The exact 376-file candidate was byte-identical to the Windows QA mirror before and after this standard run. The WSL candidate index was empty before the post-QA stage. Windows Python 3.13.15 launched PowerShell 7.6.6 in the existing mirror with a fixed Windows-native PATH/PATHEXT; Node was 24.19.0. The repository-standard `scripts/test.ps1` ran from the beginning and exited **0**. No external requests or credentials were used.

| Gate | Result |
|---|---|
| Initial policy | PASS, exit 0 |
| Backend pytest | 1,294 passed; failed 0, skipped 0, xfailed 0, deselected 0; exit 0 |
| Ruff / format | PASS, exit 0; 133 files formatted, all checks passed |
| Mypy | PASS, exit 0; 74 source files, no issues |
| Frontend lint | PASS, exit 0 |
| Frontend typecheck | PASS, exit 0 |
| Frontend build | PASS, exit 0 |
| Frontend unit | 43 passed in 10 files; failed 0, skipped 0, xfailed 0, deselected 0; exit 0 |
| API contract | PASS, exit 0 |
| Migration repeat / downgrade / re-upgrade | PASS, exit 0 |
| Fixture idempotency | PASS, exit 0; first import inserted 13; second inserted 0 and left 13 unchanged |
| E2E | 2 passed in 13.5s; failed 0, skipped 0, xfailed 0, deselected 0; exit 0 |
| Final secret scan | PASS, exit 0 |
| Final policy scan | PASS, exit 0 |

Backend pytest completed in 1,767.77 seconds. The secret scanner reported 74 source files, 861 metadata files, 1,722 mypy proofs, 1,717 mypy findings, 2,415 applied findings, and 5 proof-only unregistered findings. Fixed policy URL canaries reported 4 positive and 35 negative cases, one exact approved source span, and zero network authority.

The scanner SHA-256 and 98-file policy-control inventory digest recorded above were unchanged at attempt 09. Detector thresholds, exception behavior, and exclusions were not relaxed. This final synchronized tree must pass the complete standard suite from the beginning before staging.

## Frozen-scope and preservation checks

Against base `120194fe6631db51c115776a49c55d3a25d93e7e`:

- Migrations `0001`–`0008` are byte-identical; migration diff is empty.
- R1 WebAuthn, counter, and OWNER code/tests are unchanged.
- B2-D issuer disposition code/tests are unchanged.
- Global `MappingStatus` and `ShareClass` definitions are unchanged.
- The four pre-existing diagnostic CSVs remain only in the main checkout; the isolated candidate does not include or modify them.
- After attempt 06, the candidate and Windows mirror matched for all 375 files; attempt 09 reran against the synchronized 376-file candidate, with zero missing files or mismatches. The WSL index was empty before staging.

## Remaining boundaries

`NOT VERIFIED`: live source endpoints, current KRX/SEC/Nasdaq authority, production locator licensing beyond the approved matrix, production mapping, and public deployment. `NOT IMPLEMENTED`: C3 WebAuthn/human approval, canonical subject/profile promotion, Security links/heads, mixed R1 counter runtime, B writer safety cascade, and the current Security-head reader. CP3-C2-C3 and CP3-D remain unstarted.
