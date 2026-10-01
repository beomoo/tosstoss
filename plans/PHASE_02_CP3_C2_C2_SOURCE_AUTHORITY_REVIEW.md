# CP3-C2-C2 — Source Authority Review

- Review date: 2026-09-30
- Status: **USER-APPROVED OPERATIONAL SOURCE-ADMISSION MATRIX** under accepted ADR-020.
- Scope: C2 machine evaluation over stored normalized evidence. This record does not authorize live source requests, public redistribution, paid NYSE data, CGS, or C3.
- Provenance: source facts and access/licensing conclusions below were supplied and approved by the user for this checkpoint. No live API calls or independent live-source checks were performed during implementation.

## Exact admission outcomes

| Source | C2 admission and ownership |
|---|---|
| `KRX_STANDARD_CODE` | Exact KRX standard-code/ISIN authority and identifier provenance; instrument-class support. Local-only use subject to the KRX key, application, administrator approval, non-commercial terms, no third-party redistribution, 10,000 requests/day/key, and one-year renewable term. Automated adapter remains disabled until the exact approved service/key and official downloaded specification or approved response are captured. |
| `KRX_ISSUE_BASIC` | Exact issue class, listing venue, and KRX issuer-security bridge ownership; supports identifier and listing interval. `증권구분` and `주식종류` remain distinct; ticker/name cannot infer family. No live request or guessed external JSON key. |
| `KRX_LISTING_LIFECYCLE` | Human-assisted verified-document authority for listing status, interval, and venue. Preserve official URL/document identity, digest, reviewed time, and semantic dates. No scraper. Current-status ceiling is 96 hours; later delisting evidence takes precedence. |
| `OPENDART_CORP_CODE` | DART side of the issuer-security bridge only. `corp_code`, formal name, `stock_code`, and `modify_date` are source facts; `modify_date` is semantic, not retrieval time. Latest directory observation must be at most 48 hours old as an ingestion-completeness guard. |
| `SEC_ACCEPTED_8A` | Admitted registered-class and SEC identifier-provenance authority. Use registrant CIK, accepted accession/time, exact class title, and exchange text; never accession-prefix CIK, ticker, parser row number, or response order. Filing has no TTL; current contradiction check ceiling is 24 hours. EDGAR client must honor fair access at no more than 10 requests/second. |
| `SEC_ACCEPTED_25` | Admitted negative/removal authority. A later effective Form 25 blocks READY unless later official re-registration supersedes it. The filing itself has no TTL. |
| `SEC_PERIODIC_COVER` | Support/cross-check only; never current exchange listing or registered-class owner. |
| `NASDAQ_PRIMARY` | Admitted current listing authority for Nasdaq. Use official listed/security-master data; require current row, reject test issue, and block on later deletion/suspension. File Creation Time is the source clock, with a 36-hour ceiling. |
| `NYSE_PRIMARY` | Not admitted (`production_eligible=0`): applicable paid license/subscription is not authorized. Nasdaq `otherlisted.txt` is support/provenance only and cannot establish NYSE authority. |
| `TOSS_PROVIDER_OBSERVATION` | At most provider-bridge support. Never Security identifier, class, or listing authority. |
| `CGS` | Not admitted (`production_eligible=0`); no CUSIP authority or calls. |

## Freshness and runtime boundary

- KRX standard-code/issue-basic semantic clock is `basDd`; the newest stored official date is required, with a 96-hour ceiling. A later `basDd` makes an earlier record stale.
- KRX listing/delisting facts remain immutable; current-status verification expires after 96 hours.
- OpenDART `modify_date` selects the latest bridge fact; the 48-hour directory-observation bound checks collection completeness and is excluded from semantic evidence hashes.
- SEC 8-A/25 filing facts have no TTL. Current SEC submissions/contradiction observation is bounded to 24 hours.
- Nasdaq uses official File Creation Time with a 36-hour ceiling. Weekend/holiday expiry may produce STALE; do not widen the bound.
- C2 consumes normalized stored facts and must not invent KRX external JSON key spellings. The KRX automated adapter remains disabled until its exact approved specification or response is captured.
- Runtime fixture/test/synthetic lineage remains permanently zero authority. Deterministic production-contract fixtures are test-database setup only and are not runtime source evidence.
- No public deployment, third-party redistribution, production database mutation, live API call, or C3 behavior is authorized by this review.
