# Phase 2 CP3-C2 Canonical Promotion Authority Contract

- Contract status: `ACCEPTED — CP3-C2-A CONTRACT APPROVED AND CLOSED`
- Planning checkpoint: `CP3-C2-A`
- Initial planning starting SHA: `42cfee25418251f998e6f79981352390d9bf2540`
- Independent-review remediation starting SHA: `0a7463cfbc93b9f19f247577edd73b993efa2766`
- Branch: `feature/phase-02-toss`
- Research and retrieval date: `2026-08-26` (`Asia/Seoul`)
- Production implementation: `NOT STARTED`
- Automatic checkpoint progression: `PROHIBITED`

This contract defines the authority and evidence required before a Toss
`provider_security_identity` can be linked to a canonical issuer and security.
It does not perform that linkage. CP3-C2-A changes documentation only and does
not authorize application code, a migration, fixtures, tests, API routes,
frontend work, a scheduler, connector changes, credentials, or a live provider
request.

Normative terms such as **MUST**, **MUST NOT**, **REQUIRED**, and **MAY** apply
to a later separately authorized CP3-C2 implementation. This proposal is not an
accepted production decision until GPT independent review and explicit user
approval are complete.

## 1. Decision summary

1. Final canonical promotion is **not automatic**. A machine may collect and
   validate evidence and may produce `READY_FOR_MANUAL_REVIEW`, but it MUST NOT
   create a canonical issuer, canonical security, or current
   `ProviderIdentityMapping(mapping_status=VERIFIED)` without an explicit human
   approval event.
2. The human approver is the authenticated local data steward/repository owner.
   Codex, GPT review, the Toss provider, a scheduled job, and an authority-source
   parser are not approval authorities.
3. Human approval cannot override unresolved contradictory authority evidence.
   A conflict must be resolved by a later authoritative correction or additional
   in-scope evidence; otherwise the candidate remains `UNRESOLVED` or is
   quarantined.
4. Issuer authority and instrument authority are separate. A verified issuer
   does not imply a verified security.
5. A provider name, symbol/ticker, provider market label, or provider-supplied
   identifier is an observation, not a regulatory identifier and not an
   automatic promotion authority.
6. Korea uses OpenDART for the disclosure-registry issuer identifier and KRX for
   the instrument, standard code, market, share-kind, and listing lifecycle.
7. The United States uses SEC EDGAR for CIK and registered-class evidence, and
   the primary listing exchange for current listing/ticker status. CGS is the US
   CUSIP/ISIN authority, but its data is not usable by this repository unless a
   compliant license and approved access path exist.
8. Provider and canonical identities remain separate. Promotion adds an
   append-only linkage and MUST NOT rekey or rewrite provider history.
9. CP3-C2 SHOULD be split into `CP3-C2-B` issuer authority/mapping and
   `CP3-C2-C` security authority/final mapping. The split materially reduces P0
   issuer/security conflation and share-class risk.
10. A KRX listing establishes a listing venue, not the issuer's legal
    jurisdiction. `market=KR`, KOSPI/KOSDAQ/KONEX membership, `corp_cls`,
    `stock_code`, provider market/name, and Korean trading currency MUST NOT
    imply `Issuer.jurisdiction=KR`.
11. SEC `registrant_cik` MUST come from authoritative registrant/filer metadata
    in accepted filing/submission evidence. The first ten accession-number
    digits identify the EDGAR login CIK and MUST NOT be interpreted as the
    registrant CIK.

## 2. Non-negotiable invariants

The fail-closed default is `mapping_status=UNRESOLVED`.

If approved authority evidence is incomplete, contradictory, stale, ambiguous,
unavailable, outside its authority scope, or not legally usable, a later
implementation MUST:

- create no canonical `Issuer`;
- create no canonical `Security`;
- create no current `ProviderIdentityMapping(VERIFIED)`;
- preserve all provider staging observations and identifier history;
- append candidate evidence and explicit missing/conflict reasons;
- quarantine all affected candidates when a collision is present; and
- select no arbitrary winner.

Promotion MUST NOT change any of the following:

- `provider_security_identity_id`;
- `allocation_anchor_hash`;
- provider source/version/raw history;
- provider identifier history;
- Security Master normalized records;
- existing provider observations or state events; or
- a historical provider record's identity or content.

Promotion adds linkage only. Canonical IDs MUST NOT be derived from a Toss
symbol, ticker, display name, raw observation order, database row ID, hash
lexicographic order, job ID, clock value, or `fetched_at`.

`fetched_at` records retrieval chronology only. It MUST NOT be fabricated as an
identifier effective date, listing date, symbol-change date, correction date,
or mapping validity date.

KRX market membership and OpenDART disclosure membership are likewise scoped
observations, not legal-jurisdiction evidence. If the issuer's actual legal
jurisdiction is not positively established and representable by the current
canonical contract, even a valid DART `corp_code` and KRX ISIN cannot produce
`READY_FOR_MANUAL_REVIEW` or any canonical write.

## 3. Current repository boundary discovered by CP3-C2-A

The current repository is sufficient for CP3-C1 staging but not for the full
authority workflow proposed here:

- `ProviderIdentityMapping(VERIFIED)` currently requires `issuer_id`,
  `security_id`, and `approved_at` together. It cannot represent "issuer
  approved, security unresolved."
- `MappingStatus` contains only `UNRESOLVED` and `VERIFIED`; it cannot express a
  review-ready, revoked, superseded, or evidence-stale decision event.
- the mapping row stores only one provider `evidence_source_version_id`; it
  cannot faithfully reference a cross-source OpenDART/KRX or SEC/exchange
  authority bundle, an approver identity, a reason, or a revocation source;
- Phase 1 `Issuer` validation says KR/US fixtures require synthetic
  `corp_code`/CIK. Existing synthetic Phase 1 fixtures are historical test data
  only. They are **grandfathered for regression and explicitly forbidden as
  authority for any new canonical promotion**;
- `ShareClass` currently contains only `COMMON`, which cannot safely distinguish
  multiple registered common classes, preferred classes, ADRs, or other
  instruments; and
- `Jurisdiction` currently contains only `KR` and `US`, so a foreign issuer
  listed in either the United States or Korea cannot be silently coerced to the
  listing market's legal jurisdiction. A KRX-listed foreign corporation whose
  actual jurisdiction is not positively established as `KR` or `US` must remain
  `UNRESOLVED / jurisdiction-contract-required` with canonical issuer/security,
  `READY_FOR_MANUAL_REVIEW`, and `ProviderIdentityMapping(VERIFIED)` writes all
  equal to zero.

No schema, enum, migration, or production implementation is changed in
CP3-C2-A. Before CP3-C2-B or CP3-C2-C can implement this proposal, a separately
authorized versioned runtime contract and additive migration design MUST close
the applicable gaps. Existing migrations `0001` through `0004` remain
immutable.

## 4. Source classification method

Classification is field- and scope-specific. A source being official does not
make every field it exposes authoritative.

| Classification | Meaning in this contract |
|---|---|
| `OFFICIAL_AUTHORITY` | The issuing regulator, registry, numbering agency, or listing venue is authoritative for the named field and scope. It may still be insufficient alone for promotion. |
| `SUPPORTING_EVIDENCE` | Useful corroboration from an official or governed source, but not the issuer of the decisive identifier/status and never sufficient alone. |
| `DISCOVERY_ONLY` | May enumerate or locate candidates. Its values cannot create or verify a canonical linkage. |
| `UNSUITABLE_FOR_AUTOMATIC_PROMOTION` | May be authoritative in some context, but access, licensing, scope, interaction, timeliness, or ambiguity prevents unattended use in this contract. |
| `UNVERIFIED` | Authority, current contract, provenance, or permitted use was not established as of the retrieval date. It is treated as absent. |

For every source, conflict behavior is `FAIL_CLOSED` unless a narrower rule is
stated. One source never wins a conflict outside its own authority scope.

## 5. Korea authority registry

All URLs below were re-checked on `2026-08-26`. No credentialed API call was
made.

| Source and URL | Classification | Retrieved | Relevant field | Authority scope | Limitations | Conflict behavior |
|---|---|---|---|---|---|---|
| [OpenDART corporation code guide](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DE001&apiId=AE00004) | `OFFICIAL_AUTHORITY` | 2026-08-26 | `corp_code`, formal name, English name, listed `stock_code`, `modify_date` | FSS/DART disclosure-filer identity; `corp_code` is the 8-digit DART corporation code | A corp code identifies a DART disclosing company, not a security, ISIN, share class, or court-registry legal entity by itself; the list is cumulative and change-aware | Duplicate, malformed, missing, or inconsistent `corp_code` blocks issuer creation and mapping |
| [OpenDART company overview guide](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019002) | `SUPPORTING_EVIDENCE` | 2026-08-26 | formal name, `stock_code`, `corp_cls`, `jurir_no`, business registration number, establishment date | Current DART company profile for a supplied `corp_code` | DART publishes `jurir_no` but is not the court registry that issues it; `stock_code` is not an ISIN and does not identify share class alone | A mismatch with the corp-code list or KRX issue data blocks promotion; no field is silently overwritten |
| [Supreme Court Internet Registry](https://www.iros.go.kr/) | `UNSUITABLE_FOR_AUTOMATIC_PROMOTION` | 2026-08-26 | legal registered name, corporate registration number, legal events | Korean court-registry legal entity record | Interactive identity/security controls, document issuance workflow, possible fees, and no approved stable public bulk API in this checkpoint | May support exceptional human review only; screenshots, copied names, or search hits cannot drive unattended promotion |
| [KRX Standard Code System](https://isin.krx.co.kr/main/main.do) | `OFFICIAL_AUTHORITY` | 2026-08-26 | Korean securities standard code/ISIN and issue reference | KRX-issued/maintained standard security identifiers within the Korean market | Access method and redistribution terms must be preserved; an identifier does not alone establish the provider-to-issuer bridge or current listing state | Duplicate active ISIN or an ISIN referring to a different issue/class quarantines every affected candidate |
| [KRX Open API service list](https://openapi.krx.co.kr/contents/OPP/INFO/service/OPPINFO004.cmd) and [KOSPI issue-basic service](https://openapi.krx.co.kr/contents/OPP/USES/service/OPPUSES002_S2.cmd?BO_ID=PiwgMdTwmsenXhmqqxuj), with corresponding KOSDAQ/KONEX services | `OFFICIAL_AUTHORITY` | 2026-08-26 | issue code, short code, issue name, market, issue/security group, stock kind/share-kind, listing date | KRX-listed instrument and market metadata; public API coverage begins in 2010 for the listed services | Market-specific coverage and published fields must be checked per service version; it does not issue `corp_code` | Any DART/KRX bridge mismatch or multi-row ambiguity remains unresolved; no market or class is inferred |
| [KRX foreign-company listing guidance](https://global.krx.co.kr/contents/GLB/03/0304/0304030000/GLB0304030000.jsp) and [KOSPI listing criteria](https://global.krx.co.kr/contents/GLB/03/0307/0307020000/GLB0307020000T02.jsp) | `OFFICIAL_AUTHORITY` | 2026-08-26 | domestic/foreign applicant distinction and KRX listing eligibility | KRX listing eligibility and venue membership | KRX expressly permits foreign corporations to list. Listing eligibility, market, Korean trading currency, and the foreign-applicant legal review do not establish the issuer's legal jurisdiction for this repository | KRX membership never coerces `Issuer.jurisdiction`; unrepresentable jurisdiction remains unresolved |
| [KRX delisting information](https://data.krx.co.kr/contents/MDC/STAT/issue/MDCSTAT238.jsp) and [new-listing information](https://data.krx.co.kr/contents/MDC/STAT/issue/MDCSTAT200.jsp) | `OFFICIAL_AUTHORITY` | 2026-08-26 | listing date, delisting date, delisting reason, market, issue/stock kind | KRX listing lifecycle | Site data carries as-of/retrieval limitations and may be corrected; absence from one current page is not proof of delisting | Use explicit listing/delisting records and official dates; never substitute retrieval time or discovery disappearance |
| [KRX KIND listed-company information](https://kind.krx.co.kr/corpgeneral/corpList.do?method=loadInitPage&scrnmode=1) | `SUPPORTING_EVIDENCE` | 2026-08-26 | listed company, issue and disclosure/corporate-action notices | KRX disclosure and listed-company context | Search/display data is not a replacement for standard-code or issue-basic authority | May explain names or corporate actions; cannot resolve a contradictory ISIN/class by itself |
| [Korea Securities Depository](https://www.ksd.or.kr/en/) and [SEIBro](https://m.seibro.or.kr/cmmn/allView.do) | `SUPPORTING_EVIDENCE` | 2026-08-26 | depository/security reference data | Central securities depository and public security-information context | It is not the DART corp-code issuer and is not used here as the KRX standard-code authority | Agreement corroborates; disagreement requires review against the field-owning authority |
| [Toss Securities developer portal](https://developers.tossinvest.com/) and stored `/stocks/all`/`/stocks` observations | `DISCOVERY_ONLY` | 2026-08-26 | provider symbol, name, provider market/security type/status, provider-supplied ISIN/list date | Toss provider namespace and provider observation history only | Not a corporate registry, legal registry, standard-code issuer, or listing authority | Never create corp_code, legal identity, exchange, share class, or canonical linkage from provider values alone |
| Unofficial finance portals, search snippets, guessed mappings, synthetic identifiers | `UNVERIFIED` | 2026-08-26 | any | None | Provenance, completeness, revision policy, and authority are unverified | Treated as missing evidence; cannot enter an approval bundle |

### 5.1 KR field ownership

- `corp_code`: OpenDART authority.
- court-registry legal name and corporate registration number: Supreme Court
  registry authority, with OpenDART company overview only supporting.
- ISIN/standard security code: KRX Standard Code System authority.
- KOSPI/KOSDAQ/KONEX market, share/stock kind, listing/delisting: KRX authority.
- Toss symbol/name/status: provider observation only.

KRX cannot create or correct a `corp_code`, and OpenDART cannot settle a
contradictory ISIN/share-class/listing record. A disagreement across authority
scopes has no precedence winner; it blocks promotion.

OpenDART `corp_code` identifies a DART disclosing company. OpenDART `corp_cls`
and `stock_code`, and KRX market membership, do not establish Korean legal
jurisdiction. Legal jurisdiction MUST NOT be inferred from KOSPI/KOSDAQ/KONEX,
`corp_cls`, `stock_code`, provider market/name, or Korean trading currency.

## 6. United States authority registry

All URLs below were re-checked on `2026-08-26`. No SEC, exchange, CGS, FINRA,
state-registry, or provider API request using credentials was made.

| Source and URL | Classification | Retrieved | Relevant field | Authority scope | Limitations | Conflict behavior |
|---|---|---|---|---|---|---|
| [SEC Accessing EDGAR Data — CIK](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data) | `OFFICIAL_AUTHORITY` | 2026-08-26 | CIK, accepted submission accession, filer names/history | SEC filer identity. EDGAR states that CIK is unique to a filer and is not recycled | A CIK may belong to a fund, individual, filing agent, or inactive filer; CIK alone does not identify a listed instrument or prove legal incorporation | Require the candidate issuer to be the registrant in an accepted issuer filing; agent/fund/individual ambiguity blocks promotion |
| [SEC EDGAR Next login CIK guidance](https://www.sec.gov/submit-filings/filer-support-resources/how-do-i-guides/understand-select-set-default-login-cik) and [EDGAR Next roles](https://www.sec.gov/submit-filings/filer-support-resources/how-do-i-guides/understand-edgar-next-roles) | `OFFICIAL_AUTHORITY` for submission provenance; `UNSUITABLE_FOR_AUTOMATIC_PROMOTION` for issuer identity | 2026-08-26 | accession prefix/login CIK, filer-agent role and delegated filing authority | Identifies the CIK used to log in and make the submission | SEC states that the first ten accession digits reflect the login CIK, which may be the filer or a filing agent. It does not identify the registrant by itself | Store login/agent CIK only as separate audit provenance if useful; it has zero issuer authority and cannot enter an issuer or registered-class anchor |
| [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) and `data.sec.gov/submissions/CIK##########.json` | `SUPPORTING_EVIDENCE` | 2026-08-26 | current/former names, recent filings, exchanges and ticker metadata | Official SEC submission metadata and discovery of accepted filings | Ticker/exchange metadata is not primary-exchange listing authority; a latest-submissions view can omit older registration evidence without following archival files | Use to locate and revision-check filings; disagreement with accepted filing or exchange authority blocks promotion |
| [SEC company ticker files](https://www.sec.gov/files/company_tickers_exchange.json) | `DISCOVERY_ONLY` | 2026-08-26 | ticker↔CIK↔company name↔exchange association | EDGAR search convenience | SEC explicitly does not guarantee accuracy or scope; ticker reuse and class distinctions remain possible | Never promote, merge, or correct from this file alone |
| Accepted [Form 8-A](https://www.sec.gov/files/form8a.pdf) under the candidate registrant CIK | `OFFICIAL_AUTHORITY` | 2026-08-26 | registered class title, Section 12(b)/(g) basis, exchange, filing accession and exhibits | SEC registration evidence for a specific class of securities | It proves the filed registration, not continuing exchange listing by itself; amendments/incorporated documents must be followed | Later amendment/Form 25 or class ambiguity blocks current promotion until reconciled |
| Accepted issuer periodic/reporting filing, including [Form 10-K](https://www.sec.gov/files/form10-k.pdf) and applicable 10-Q/20-F/40-F cover data | `SUPPORTING_EVIDENCE` | 2026-08-26 | exact registrant name, title of each class, trading symbol, exchange | Issuer-reported regulatory statement preserved in an accepted SEC filing | SEC acceptance is not an independent certification of the issuer-reported ticker/listing; later amendments and primary-exchange evidence must be checked; it is not a CUSIP/ISIN authority | A class/ticker/exchange mismatch is unresolved, even if names match |
| Accepted [Form 25](https://www.sec.gov/files/form25.pdf) and [SEC removal final rule](https://www.sec.gov/rules-regulations/2005/07/removal-listing-registration-securities-pursuant-section-12d-securities-exchange-act-1934) | `OFFICIAL_AUTHORITY` | 2026-08-26 | issuer, exchange, class removed, filing/effective lifecycle | Removal from exchange listing and/or Section 12(b) registration | Effect dates and rule timing must be taken from the official event, not retrieval time | An effective Form 25 closes current-listing eligibility; no old ticker row remains current |
| [Nasdaq Trader Symbol Directory](https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs) | `OFFICIAL_AUTHORITY` | 2026-08-26 | Nasdaq symbol, security name, market category, test-issue flag, financial status, issue attributes | Current Nasdaq-listed issue status | Authority is limited to Nasdaq listings; the other-listed file is not treated as authority for another primary exchange; data/access terms and as-of date apply | SEC/Nasdaq disagreement blocks promotion; test issues and ineligible status are excluded |
| [NYSE Listings Directory](https://www.nyse.com/listings_directory/stock?ListedComp=US) and [NYSE listing notices](https://www.nyse.com/market-data/corporate-actions/listing-notices) | `OFFICIAL_AUTHORITY` | 2026-08-26 | NYSE-listed company/security/ticker and listing/delisting notices | Current NYSE-family listing within the identified venue | Some reference/security-master or notice feeds are commercial, delayed, or require separate access; public directory coverage must be verified | If usable current official evidence is unavailable, the candidate remains unresolved; Nasdaq/SEC data cannot impersonate NYSE authority |
| [FINRA OTC Symbol Directory and Daily List](https://otce.finra.org/otce/symbol-directory) | `UNSUITABLE_FOR_AUTOMATIC_PROMOTION` | 2026-08-26 | OTC symbol, issue type/status, symbol/name changes and deletions | FINRA OTC issue/symbol lifecycle | OTC is not a national-exchange listing and is outside the conservative CP3-C1 US exchange-listed automatic candidate universe | Preserve as discovery/support for manual scope review; do not coerce OTC to NYSE/Nasdaq/AMEX or auto-promote |
| [CUSIP Global Services ISIN service](https://isin.cusip.com/isin/login.html), [license policy](https://www.cusip.com/services/license-fees.html), and [terms of use](https://www.cusip.com/legal.html?section=termsOfUse) | `OFFICIAL_AUTHORITY` | 2026-08-26 | CUSIP and CGS-assigned US ISIN | CGS acts as the US national numbering agency for its identifiers | CGS data is proprietary; use/storage can require a license even when a fee is waived below a usage threshold, and the public-site terms restrict automation and master-file/database use. This project has no approved licensed CGS integration | Without a verified permitted license and authority record, CUSIP/ISIN is unavailable for promotion; provider-supplied values are not substituted |
| [GLEIF Global LEI Index](https://www.gleif.org/en/lei-data/global-lei-index) | `SUPPORTING_EVIDENCE` | 2026-08-26 | LEI, legal name, registration-authority reference, entity status | Authoritative/open LEI registry for entities that have an LEI | LEI coverage is not universal and LEI identifies a legal entity, not a security, CIK, share class, or listing | Can corroborate legal identity only; cannot create CIK or instrument mapping |
| Official state business registry, e.g. [Delaware Division of Corporations search](https://icis.corp.delaware.gov/ecorp/entitysearch/namesearch.aspx) | `UNSUITABLE_FOR_AUTOMATIC_PROMOTION` | 2026-08-26 | state legal entity/name/status | Legal existence in the issuing state registry | Fragmented by jurisdiction, access and field semantics; no single approved nationwide API; does not identify the SEC filer or listed class by itself | Exceptional human evidence only; name matches do not merge issuers |
| [OpenFIGI](https://www.openfigi.com/), commercial market-data sites, and search results | `DISCOVERY_ONLY` | 2026-08-26 | candidate identifiers and cross-references | Candidate discovery | Not the SEC, primary listing exchange, or CGS numbering authority; license and coverage differ | Cannot enter the minimum authority bundle or resolve a conflict |
| [Toss Securities developer portal](https://developers.tossinvest.com/) and stored provider observations | `DISCOVERY_ONLY` | 2026-08-26 | provider ticker/name/market/type/status and provider-supplied ISIN | Toss provider namespace only | A ticker is not a CIK, CUSIP, ISIN authority, legal identity, or immutable instrument identifier | Never use ticker as CIK/regulatory ID or as a canonical anchor; provider evidence must bridge to an independently established authority row |
| Undocumented ticker↔CIK/CUSIP crosswalks, inferred primary exchange, synthetic class labels | `UNVERIFIED` | 2026-08-26 | any | None | Provenance, current scope, correction behavior, and permitted use are not established | Treated as missing evidence; cannot enter an approval bundle |

### 6.1 US field ownership

- registrant CIK and accepted SEC registration/reporting record: SEC EDGAR
  authority, taken from authoritative registrant/filer metadata in the accepted
  evidence rather than parsed from an accession prefix.
- accession-prefix/login CIK and filing-agent CIK: submission provenance only,
  with zero issuer authority.
- current national-exchange ticker/listing status: the identified primary listing
  exchange, within that venue's scope.
- registered class: accepted SEC class-registration/reporting evidence,
  corroborated by the primary exchange for current status.
- CUSIP/US ISIN: CGS authority, subject to license and approved access.
- state legal existence/name: the relevant state registry; SEC/LEI evidence can
  support but does not replace it.
- Toss ticker/name/status: provider observation only.

The SEC ticker convenience files do not become authoritative because they are
hosted by the SEC. Their own stated accuracy/scope limitation controls.

## 7. Required evidence record and authority bundle

A later implementation MUST persist raw/source provenance before analysis and
represent each evidence fact independently. At minimum, an evidence record must
contain:

- authority source identifier and classification;
- exact public source URL or accepted filing accession;
- authority-provided `registrant_cik` when SEC issuer identity is asserted;
- optional login/accession-prefix or filing-agent CIK as separately typed audit
  provenance with zero candidate-identity authority;
- retrieval timestamp in UTC;
- source-provided publication, acceptance, effective, or as-of date, nullable
  when not supplied;
- exact raw/source content hash and parser/contract version;
- field name, raw value, normalized value, and authority scope;
- issuer/security candidate to which the evidence was applied;
- revision/correction/supersession relationship;
- access and license disposition;
- conflict/missing/stale status; and
- provider lineage evidence used only to bridge the provider observation to the
  authority-established candidate.

An `authority_bundle_id` must be a deterministic hash of the ordered immutable
evidence IDs/content hashes, candidate IDs, decision-rule version, and conflict
scan result. A refetch of identical immutable evidence must not change the
bundle identity merely because `fetched_at`, run ID, or database ID changed.
Freshness and retrieval chronology remain separate fields.

An accession-prefix/login CIK or filing-agent CIK MUST NOT be used in
`issuer_id`, an authority-bundle candidate identity, or a SEC registered-class
canonical security anchor. A parser that cannot independently resolve the
registrant CIK from authoritative registrant/filer metadata must fail closed.

A final approval event must include the authority bundle, authenticated human
approver ID, approval UTC time, decision reason, contract version, and applicable
validity interval. `approved_at` is an audit time and is not an instrument or
mapping effective date.

### 7.1 `REPO_POLICY / CONSERVATIVE_APPROVAL_FRESHNESS`

The 24-hour threshold below is a conservative repository approval policy. It
is not an OpenDART, KRX, SEC, Nasdaq, NYSE, or CGS mandated universal freshness
requirement. Authority-supplied publication, acceptance, effective, and as-of
dates remain separate from repository retrieval chronology; `fetched_at` never
substitutes for an authority effective date.

- Immutable accepted filings and historical registration/listing events do not
  expire by age, but the approval attempt must perform a latest-revision and
  later-event check.
- Evidence representing **current** company, listing, ticker, class, or status
  must be retrieved in the same approval attempt and be no more than 24 hours
  old at approval.
- The latest-revision/current-status check must include every field-owning
  authority in the bundle.
- If an authority is unavailable or current evidence is older than 24 hours, no
  new issuer/security/mapping is created. Last-known-good evidence remains
  historical; an outage is not evidence of revocation.

## 8. Provider identity → canonical Issuer decision matrix

### 8.1 Korea issuer path

| Decision dimension | Required contract |
|---|---|
| Minimum evidence | Unique, valid 8-digit OpenDART `corp_code`; matching current corporation-code row and company-overview response under that code; formal-name/history consistency or an explicit explained discrepancy; independently established legal jurisdiction that maps exactly to the current canonical `Jurisdiction` enum; no existing current canonical issuer with a conflicting authority anchor |
| Strong identifier | OpenDART `corp_code` in its disclosure-filer scope |
| Supporting identifiers | OpenDART `jurir_no`, formal/English name, business registration number, establishment date; court-registry record or LEI when lawfully obtained |
| Forbidden evidence | synthetic/fake corp_code, Toss symbol/name, KRX short code alone, name-only match, search result, guessed registration number; legal-jurisdiction inference from KOSPI/KOSDAQ/KONEX, `corp_cls`, `stock_code`, provider market/name, or Korean trading currency |
| Is one source sufficient? | OpenDART may identify a DART disclosure candidate in its own scope, but cannot by itself establish legal jurisdiction. It is never sufficient for `READY_FOR_MANUAL_REVIEW` or provider→canonical `VERIFIED` without independently established representable jurisdiction, instrument evidence, and manual approval |
| Cross-source agreement | Required before final provider mapping: the OpenDART issuer-to-stock bridge and KRX instrument record must agree |
| Collision behavior | Same corp_code mapped to contradictory current legal entities, or different corp_codes competing for one candidate, blocks all affected promotions; no merge/winner |
| Missing behavior | Missing/unavailable corp_code keeps issuer and provider mapping unresolved; `jurir_no`, name, or symbol cannot backfill it. Missing, ambiguous, or unrepresentable legal jurisdiction yields `UNRESOLVED / jurisdiction-contract-required`; canonical issuer/security, review-ready, and VERIFIED writes are zero |
| Correction/revision | Append the corrected DART evidence and relationship; do not mutate the old evidence or issuer anchor. If the authority says two entities are legally distinct, create separate canonical candidates after approval rather than merge by name |
| Historical preservation | Preserve every DART version, provider observation, former name, and prior mapping event |
| Approval authority | Explicit authenticated human data-steward approval; automation may only produce a review candidate |
| Automatic/manual boundary | Automatic final issuer creation and mapping: `NO`; manual approval only after machine validation |

Canonical issuer anchor proposal for a new production issuer whose legal
jurisdiction is independently verified as Korean:
`issuer-v1|KR|DART_CORP_CODE|<8-digit-corp-code>`. The display/legal name is
mutable evidence and never part of the anchor. A KRX listing or DART disclosure
row cannot satisfy the jurisdiction precondition.

### 8.2 United States issuer path

| Decision dimension | Required contract |
|---|---|
| Minimum evidence | Unique, zero-padded 10-digit `registrant_cik` obtained from authoritative registrant/filer metadata in accepted filing/submission evidence; at least one accepted issuer filing in which that candidate is the registrant, not merely the login CIK or a filing agent; current/former-name chain reconciled; no conflicting current canonical issuer anchor |
| Strong identifier | SEC `registrant_cik` in its filer/registrant scope, independently resolved from accepted evidence |
| Supporting identifiers | accepted-filing legal name and incorporation jurisdiction, state-registry identity, LEI and registration-authority reference |
| Forbidden evidence | synthetic/fake CIK, first ten accession-number digits, login CIK, filing-agent CIK, Toss ticker/name, SEC company-ticker file alone, EIN guess, name-only match, CUSIP/ISIN as an issuer ID |
| Is one source sufficient? | SEC EDGAR may establish an **issuer candidate** in SEC-filer scope when registrant status is proven. It is never sufficient for final provider→security mapping |
| Cross-source agreement | Required before final mapping: SEC class/ticker/exchange evidence and the primary exchange's current issue evidence must agree; state/LEI evidence is required only when legal-entity ambiguity remains |
| Collision behavior | One CIK appearing to identify contradictory current registrants, a filing-agent CIK, or multiple canonical candidates blocks all affected promotions |
| Missing behavior | Missing/unavailable or independently unresolvable registrant CIK keeps issuer and provider mapping unresolved with canonical writes zero; accession/login CIK, ticker, and name cannot substitute |
| Correction/revision | Preserve prior SEC names/filings. Follow accepted amendments and later filings; never rekey the canonical issuer on a name/ticker change |
| Historical preservation | Preserve CIK, former names, accessions, provider history, and every mapping decision |
| Approval authority | Explicit authenticated human data-steward approval |
| Automatic/manual boundary | Automatic final issuer creation and mapping: `NO`; manual approval only after machine validation |

Canonical issuer anchor proposal for a new US production issuer:
`issuer-v1|US|SEC_CIK|<10-digit-zero-padded-CIK>`. CIK format validation does
not prove registrant scope; the value MUST be the independently verified
registrant CIK, and the accepted-filing check remains mandatory. An
accession-prefix/login CIK has zero authority for this anchor.

Foreign issuers listed in either the United States or Korea, funds, individuals,
filing agents, and entities whose legal jurisdiction cannot be represented by
the current contract remain unresolved until a separately approved
jurisdiction/instrument contract exists.

## 9. Provider identity → canonical Security decision matrix

A canonical issuer approved under section 8 is a prerequisite, not sufficient
evidence. `ProviderIdentityMapping(VERIFIED)` is created only after both issuer
and security decisions are approved and consistent.

### 9.1 Korea security path

| Decision dimension | Required contract |
|---|---|
| Minimum evidence | Approved canonical issuer whose legal jurisdiction was independently established and is representable by the current contract; unique KRX ISIN/standard-code record; matching KRX issue-basic row for market, short code, stock/share kind and listing date; explicit current listing or historical interval; OpenDART `stock_code` bridge to that KRX issue; provider observation whose ISIN exactly matches the KRX ISIN; no collision or unresolved discrepancy |
| Strong identifier | KRX ISIN/standard security code for the specific instrument |
| Supporting identifiers | KRX short code, market, stock/share kind, list/delist dates; OpenDART stock code; provider symbol/name/list date |
| Forbidden evidence | Toss symbol/name alone, DART stock code alone, inferred exchange or legal jurisdiction, default `COMMON`, synthetic ISIN, name-only security merge |
| Is one source sufficient? | `NO`. KRX establishes the instrument, but OpenDART is required for the issuer bridge and provider evidence is required for the provider link |
| Cross-source agreement | Required among OpenDART issuer/stock code, KRX ISIN/issue/class/market/status, and provider ISIN/current observation |
| Collision behavior | Duplicate active ISIN, multiple KRX rows for one current class, or one provider identity with multiple current candidates quarantines all affected candidates; identities are not merged or rekeyed |
| Missing behavior | Missing KRX ISIN, share-kind, market, issuer bridge, current status, or provider-to-ISIN match leaves security and final mapping unresolved |
| Correction/revision | Append KRX correction evidence. If ISIN correction refers to the same economic instrument, retain canonical security anchor and record identifier validity only when KRX supplies that relationship/effective date; otherwise create a new candidate and require review |
| Historical preservation | Preserve prior ISIN, symbol, market/class/status, source evidence, canonical security, and mapping events; never rewrite provider records |
| Approval authority | Explicit authenticated human approval of the full authority bundle |
| Automatic/manual boundary | Automatic final security creation/VERIFIED mapping: `NO`; review-ready candidate generation only |

Canonical security anchor proposal for a new KR production security:
`security-v1|<issuer-id>|KRX_ISIN|<12-character-ISIN>`. Later ticker/name
changes do not affect the anchor. A genuine authority correction does not permit
silent rekey; it follows section 12.

### 9.2 United States security path

| Decision dimension | Required contract |
|---|---|
| Minimum evidence | Approved canonical SEC issuer; an accepted SEC registered-class anchor (prefer Form 8-A, otherwise an explicitly approved equivalent filing contract); exact class title and exchange; a current primary-exchange row for the same ticker/class/exchange; no effective Form 25 or later contradictory filing; provider current ticker/market matching that official exchange row; no collision or unexplained discrepancy |
| Strong identifier | A licensed CGS CUSIP/US ISIN when permitted, **or** the immutable accepted SEC class-registration anchor `verified registrant CIK + accession + class-row identity` |
| Supporting identifiers | SEC periodic-filing ticker/exchange cover row, primary-exchange ticker/status/name, provider ISIN/ticker/name/market, LEI |
| Forbidden evidence | ticker as CIK or canonical anchor, accession-prefix/login CIK or filing-agent CIK as registrant/security anchor, SEC company-ticker file alone, provider-supplied CUSIP/ISIN without authority verification, name-only merge, default share class, OpenFIGI/commercial portal alone |
| Is one source sufficient? | `NO`. SEC establishes filer/class registration; the primary exchange establishes current listing. CGS is separately required if CUSIP/ISIN is used as the strong identifier |
| Cross-source agreement | Required between accepted SEC class evidence and the field-owning primary exchange; provider evidence must bridge to that exact current row. Licensed CGS evidence must also agree when used |
| Collision behavior | Duplicate active CUSIP/ISIN, ticker reuse ambiguity, multiple classes under one ticker, or one provider identity with multiple current candidates blocks every affected promotion |
| Missing behavior | CIK or registered-class evidence missing means no issuer/security. Strong issuer but weak instrument evidence means issuer may be approved separately, while security and final provider mapping remain unresolved |
| Correction/revision | Follow SEC amendments, later periodic filings, exchange corporate actions, Form 25, and licensed identifier corrections. Append evidence/events; do not mutate or rekey the provider identity or an established security without a separately approved correction decision |
| Historical preservation | Preserve former ticker, class title, exchange, registration/delisting filings, identifier intervals, canonical records, and mapping events |
| Approval authority | Explicit authenticated human approval of the complete authority bundle |
| Automatic/manual boundary | Automatic final security creation/VERIFIED mapping: `NO`; review-ready candidate generation only |

If a permitted licensed CGS identifier exists, the proposed security anchor is
`security-v1|<issuer-id>|CGS_CUSIP|<CUSIP>` or
`security-v1|<issuer-id>|CGS_ISIN|<ISIN>`. Without licensed CGS evidence, the
only proposed free official anchor is
`security-v1|<issuer-id>|SEC_REGISTERED_CLASS|<verified-registrant-CIK>/<accepted-accession>/<class-row-id>`.
The class-row ID must be deterministically tied to the immutable accepted
document and exact class row, not to mutable ticker text or parser iteration.
The CIK component MUST be the independently verified registrant CIK, never the
accession-prefix/login CIK or filing-agent CIK. Those provenance values have
zero authority for the issuer ID, bundle candidate identity, and security
anchor.
This alternate anchor requires explicit CP3-C2-C review approval before
implementation.

## 10. Promotion state and decision workflow

A later implementation must use the following order:

```text
provider staging remains UNRESOLVED
  -> collect authority evidence without mutating staging
  -> validate provenance, access rights, scope and freshness
  -> establish legal jurisdiction independently from listing market
  -> separate SEC registrant CIK from login/accession-prefix provenance
  -> resolve issuer candidate and scan issuer collisions
  -> resolve security candidate and scan instrument/class/listing collisions
  -> compare all field-owning authorities
  -> INCOMPLETE / CONFLICT / STALE / UNAVAILABLE
       => UNRESOLVED or QUARANTINED; publish no canonical linkage
  -> complete and non-contradictory
       => READY_FOR_MANUAL_REVIEW only
  -> explicit authenticated human approval
       => append canonical issuer/security as needed
       => append VERIFIED provider linkage
       => leave provider identity and all provider history unchanged
```

The planning states `READY_FOR_MANUAL_REVIEW`, `REJECTED`, `REVOKED`, and
`SUPERSEDED` are evidence/decision workflow concepts. They MUST NOT be squeezed
into the current two-value `MappingStatus` without a separately approved
versioned contract.

### 10.1 Approval validity

- At most one current verified security mapping may exist for one provider
  identity.
- Non-overlapping historical mappings MAY exist only when authority-supplied
  effective intervals unambiguously separate them and each has its own manual
  approval.
- Many provider identities MAY link to one canonical security only when each
  provider linkage independently satisfies the authority bundle. They are not
  merged or rekeyed.
- A single provider identity MUST NOT have multiple simultaneous canonical
  candidates or current verified mappings.
- Canonical security creation and final provider mapping must occur in one
  transaction only after the approval event and all constraints validate.
- Failure at any point rolls back canonical writes but never deletes evidence or
  provider staging history.

## 11. Conflict rules

1. **Authority scope, not generic precedence.** OpenDART/SEC owns issuer
   regulatory identity; KRX/primary exchange owns listing fields; KRX/CGS owns
   standard identifiers in its scope. No source overwrites a different
   authority's field.
2. **Duplicate unique identifier.** A duplicate active ISIN/CUSIP/authority
   class anchor is not unique evidence. All affected candidates are quarantined,
   eligible count is zero, canonical writes are zero, and no first-writer wins.
3. **Name mismatch.** Names never create a link. A provider-name mismatch may be
   reviewed only after strong IDs already agree and an official former-name,
   transliteration, or display-name record explains it. An unexplained
   regulatory-name mismatch blocks promotion.
4. **Ticker/symbol change.** Preserve issuer/security/provider IDs. Append
   official effective-dated ticker history. A current provider observation must
   match the current official row; the old ticker is not current.
5. **Ticker reuse.** Treat reuse after delisting as a different listing interval
   and usually a different security. No symbol-based continuity is permitted.
6. **Share class.** CIK/corp_code identifies the issuer, not a share class. Each
   official class/ISIN/registration anchor creates a distinct security
   candidate. If the current contract cannot represent it, remain unresolved.
7. **Manual review is not a conflict override.** A reviewer may accept explained
   aliases or authoritative corrections, but may not choose between unresolved
   contradictory official candidates.
8. **Market is not legal jurisdiction.** KRX or US-exchange membership cannot
   populate `Issuer.jurisdiction`. Missing/unrepresentable jurisdiction blocks
   review-ready and canonical states.
9. **SEC submission provenance is not registrant identity.** The accession
   prefix/login CIK may identify a filing agent. It never substitutes for an
   independently resolved registrant CIK or participates in an issuer/security
   candidate anchor.

## 12. Required scenario decisions

| Scenario | Required outcome |
|---|---|
| KR unique corp_code + instrument evidence | OpenDART may establish issuer candidate; only unique KRX ISIN/class/market/status + OpenDART bridge + provider ISIN agreement can reach manual review. After explicit approval, create linkage without rekey |
| KRX-listed foreign corporation + valid OpenDART corp_code + valid KRX ISIN | Preserve provider staging and authority evidence. Do not fabricate `Jurisdiction.KR`; create no canonical issuer/security, no review-ready state, and no VERIFIED mapping. Remain `UNRESOLVED / jurisdiction-contract-required` until a separately approved jurisdiction model represents the actual legal jurisdiction |
| US unique CIK + instrument evidence | SEC registrant/CIK plus accepted class evidence and primary-exchange agreement can reach manual review; ticker file alone cannot. Explicit approval required |
| Accepted Form 8-A: registrant CIK A, accession/login CIK B belonging to filing agent | Canonical issuer candidate is A only. B is separate audit provenance with zero issuer authority; no A↔B merge. A parser that treats B as registrant fails closed, while the evidence bundle preserves both roles without substitution |
| Registrant identity cannot be independently resolved | `UNRESOLVED`; canonical issuer/security and VERIFIED mapping writes are zero. Accession/login CIK cannot fill the gap |
| Same company, multiple share classes | One canonical issuer, one distinct canonical security per authoritative class anchor; no merge by corp_code/CIK or name. Unsupported class stays unresolved |
| Same ticker reused after delisting | Distinguish by official listing intervals and instrument/class anchors. Old and new securities remain separate; ambiguous provider identity is quarantined |
| Ticker changed, legal issuer unchanged | Preserve canonical issuer/security and provider identity when official class continuity is explicit; append old/new ticker intervals and never use the new ticker to rekey |
| ISIN corrected | Append correction and authority relationship. Preserve historical ISIN. Same security only if the numbering/listing authority explicitly establishes continuity; otherwise new candidate/manual review |
| Duplicate active ISIN | Quarantine all affected candidates; eligible/VERIFIED/canonical writes are zero; no arbitrary winner |
| Provider name mismatch | Name is not decisive. Strong authority agreement plus official alias/former-name evidence may proceed to manual review; otherwise unresolved |
| Regulatory name mismatch | Follow official name history only when the same strong issuer identifier proves continuity. Different/unexplained authority identity remains unresolved |
| corp_code/CIK unavailable | No canonical issuer, security, or VERIFIED mapping. Preserve candidate evidence and provider staging |
| One provider identity maps to multiple canonical candidates | No current mapping; quarantine. Historical non-overlapping mappings require authority-supplied intervals and separate approvals |
| Multiple provider identities appear to map to one canonical security | Do not merge provider identities. Allow many-to-one linkage only after each independent bundle passes and same-provider duplicate/collision review is clear |
| Historical mapping correction | Append correction/supersession event and evidence; preserve old mapping and canonical/provider IDs. Apply official effective date only when supplied |
| Mapping revocation | Append revocation decision; stop current canonical use without deleting history. Do not invent an instrument-effective date when only review time is known |
| Issuer verified but security unresolved | Canonical issuer/approved issuer linkage may exist only in the future CP3-C2-B evidence model; provider `mapping_status` stays `UNRESOLVED`, no `ProviderIdentityMapping(VERIFIED)`, no canonical security |
| Strong issuer evidence but weak instrument evidence | Issuer candidate may be reviewed in CP3-C2-B; security and final mapping remain unresolved. Ticker/name cannot fill the gap |

## 13. Corrections, revisions, revocation and history

- Authority evidence is append-only. Raw records and accepted filings are never
  overwritten.
- A correction links to the superseded evidence and records the field-owning
  authority's published/effective date when supplied.
- If the authority supplies no effective date, the system records only
  `observed_at`/`retrieved_at`/decision time. It does not invent `valid_from` or
  `valid_to`.
- A mapping revocation is a new approval decision, not deletion. The old mapping
  remains queryable as historical evidence.
- Source unavailability or staleness blocks a new promotion but does not by
  itself prove a previously verified mapping false. It creates a review-needed
  condition while preserving last-known evidence.
- If corrected evidence proves the canonical security itself was wrong, no
  automatic rekey occurs. Close/revoke the linkage through an approved event,
  create a separately anchored canonical candidate if justified, and preserve
  both records.
- Historical provider records, identifier history, allocation anchor, and raw
  trace are immutable even when a canonical decision is corrected.

## 14. CP3-C2 split decision

**Recommendation: split implementation.**

### CP3-C2-B — Canonical issuer authority and mapping

Authorized only after this plan passes independent review and the user starts
the checkpoint. Its proposed scope is:

- versioned authority-evidence/bundle/approval contract;
- additive evidence and issuer-decision storage if separately approved;
- OpenDART corp-code and SEC CIK/registrant validation using offline fixtures
  and official-source adapters only within approved access policy;
- canonical issuer candidate creation after explicit human approval;
- an approved provider→issuer linkage that does **not** create a canonical
  security and does **not** set current `ProviderIdentityMapping` to `VERIFIED`;
- collision, correction, history, provenance and no-fake-ID acceptance tests.

### CP3-C2-C — Canonical security authority and final mapping

Authorized only after CP3-C2-B approval and a separate user start decision. Its
proposed scope is:

- KRX instrument/standard-code/listing evidence and SEC class/primary-exchange
  evidence;
- licensed CGS integration only if separately authorized and legally permitted;
- versioned multi-class/instrument anchor representation;
- canonical Security creation after explicit human approval;
- final append-only `ProviderIdentityMapping(VERIFIED)` linkage;
- ticker reuse/change, duplicate identifier, listing/delisting,
  correction/revocation and deterministic replay tests.

This split prevents issuer evidence from being mistaken for instrument evidence,
allows "issuer verified, security unresolved" to remain truthful, and isolates
the higher-risk share-class/listing/licensing decisions. Implementing both as
one checkpoint is not recommended.

## 15. Later implementation acceptance gates

No item below is implemented by CP3-C2-A. A later checkpoint cannot claim PASS
without exact tests showing:

- synthetic/fake corp_code created: `0`;
- synthetic/fake CIK created: `0`;
- symbol/ticker used as regulatory identifier or canonical anchor: `0`;
- name-only issuer/security merge: `0`;
- symbol-only canonical merge: `0`;
- automatic final promotion: `0`;
- arbitrary collision winner: `0`;
- canonical writes under conflicting/stale/unavailable evidence: `0`;
- provider identity/allocation-anchor rekeys: `0`;
- provider/source/identifier/observation history rewrites: `0`;
- canonical Security created without approved instrument evidence: `0`;
- legal jurisdiction inferred from KRX/US market, market class, provider fields,
  or trading currency: `0`;
- KRX-listed foreign issuer with unrepresentable jurisdiction reaching
  `READY_FOR_MANUAL_REVIEW`, canonical write, or VERIFIED mapping: `0`;
- accession-prefix/login or filing-agent CIK used as registrant, `issuer_id`,
  authority-bundle candidate identity, or SEC registered-class anchor: `0`;
- independently unresolved registrant CIK producing a canonical write: `0`;
- duplicate-active-identifier affected candidates all quarantined;
- response/input order produces identical canonical ordered evidence/decision
  dumps;
- issuer-approved/security-unresolved state is representable without a false
  `VERIFIED` mapping;
- correction and revocation are append-only and effective dates are never
  fabricated; and
- credential, Toss API, order/account/WebSocket and unauthorized external
  network usage: `0` in standard regression.

## 16. CP3-C2-A checkpoint result

- CP3-C1: `PASS — CLOSED`
- CP3-C2-A: `PASS — CONTRACT APPROVED AND CLOSED`
- CP3-C2-B: `NOT STARTED — REQUIRES SEPARATE USER START APPROVAL`
- CP3-C2-C: `NOT STARTED`
- CP3-D: `NOT STARTED`
- Application changes: `0`
- Migration changes: `0`
- Automatic canonical promotion proposed: `NO`
- Automatic checkpoint progression: `PROHIBITED`
