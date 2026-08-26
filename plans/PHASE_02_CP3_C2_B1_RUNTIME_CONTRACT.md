# Phase 2 CP3-C2-B1 — Issuer Authority Runtime Contract and Additive Migration Design

- Checkpoint: `CP3-C2-B1`
- Status: `PLANNING — AWAITING GPT INDEPENDENT REVIEW`
- Starting SHA: `959f78415aade27e57d191db3025c66ea4266999`
- Branch: `feature/phase-02-toss`
- Design date: `2026-08-26` (`Asia/Seoul`)
- Governing decision: `ADR-013 — ACCEPTED`
- Production implementation: `NOT STARTED`
- Migration implementation: `NOT STARTED`
- Automatic checkpoint progression: `PROHIBITED`

This document proposes the versioned runtime contracts and additive schema needed
for CP3-C2-B issuer authority. It is a design checkpoint only. Normative terms
such as **MUST**, **MUST NOT**, **REQUIRED**, and **MAY** apply to a later,
separately authorized implementation after independent review and explicit user
approval.

No application code, ORM model, repository, migration, fixture, test, route,
frontend, scheduler, connector, credential, or live request is created by B1.
In particular, no `0005` file is created or applied here.

## 1. Scope and terminal boundary

CP3-C2-B1 designs only the issuer side of canonical authority:

- immutable official-authority evidence and retrieval audit;
- immutable evidence bundles tied to one provider identity and one issuer
  candidate;
- deterministic machine decisions whose maximum positive state is
  `READY_FOR_MANUAL_REVIEW`;
- authenticated human approval, rejection, revocation, and supersession events;
- an issuer-only provider linkage that truthfully represents
  `issuer approved / security unresolved`;
- append-only correction, revocation, supersession, and review-required history;
- concurrency and integrity rules; and
- a proposed additive `0005_phase_02_cp3_c2_b_issuer_authority` migration.

The following remain outside B1 and outside CP3-C2-B implementation authority:

- canonical `Security` creation;
- security class, ISIN/CUSIP, exchange, or listing final authority;
- `ProviderIdentityMapping(mapping_status=VERIFIED)`;
- mutation of the existing two-value `MappingStatus`;
- current price, scheduler, UI, live collection, or a new external connector;
- CP3-C2-C, CP3-D, PR/main merge, tag, or release; and
- automatic progression to any later checkpoint.

## 2. ADR-013 invariants preserved without modification

The later implementation MUST satisfy every invariant below:

1. Automatic canonical promotion count is `0`.
2. Machine maximum positive state is `READY_FOR_MANUAL_REVIEW`.
3. A canonical issuer and issuer-authority link require an authenticated human
   data-steward event.
4. No human or machine override flag exists for contradictory official
   evidence. A contradiction blocks approval.
5. Synthetic or fake OpenDART `corp_code` and SEC CIK count is `0`.
6. Name-only and symbol-only issuer merge count is `0`.
7. KRX membership, KOSPI/KOSDAQ/KONEX, OpenDART `corp_cls` or `stock_code`,
   provider market/name, and Korean trading currency have zero legal-
   jurisdiction authority.
8. A KRX-listed foreign issuer whose actual jurisdiction is unsupported or not
   independently established remains `UNRESOLVED` and cannot reach review-ready
   or canonical state.
9. SEC `registrant_cik` comes only from authoritative registrant/filer metadata
   for accepted evidence in which the candidate is the registrant.
10. Accession-prefix/login CIK and filing-agent CIK are provenance-only values
    with zero issuer authority.
11. Provider identity, allocation anchor, identifier history, source history,
    normalized records, observations, and provider prices are never rekeyed or
    rewritten by issuer approval.
12. `fetched_at`, approval time, or current clock never becomes an authority
    effective date, jurisdiction date, listing date, identifier interval, or
    mapping validity date.
13. Authority evidence, corrections, revocations, decisions, approval events,
    and link history are append-only.
14. CP3-C2-B creates no canonical `Security` and never writes
    `ProviderIdentityMapping(VERIFIED)`.

The existing `MappingStatus = VERIFIED | UNRESOLVED` remains byte- and
semantics-compatible. All states in this document live in new versioned
issuer-authority contracts.

## 3. Current schema gap

The repository head contains four immutable migrations and the following
relevant facts:

- `issuers` can represent KR or US canonical issuers and already enforces unique
  nullable `corp_code` and CIK values;
- `provider_security_identities` holds the immutable provider anchor and is
  intentionally unable to self-promote to `VERIFIED`;
- `provider_identity_mappings` requires issuer, security, and approval together
  for `VERIFIED`, so it cannot represent issuer-only approval;
- one `evidence_source_version_id` on the old mapping is insufficient for a
  cross-authority immutable bundle;
- existing provider source tables are Toss-provider lineage, not a generic
  OpenDART/SEC authority ledger; and
- no current table can prove authenticated human disposition or preserve an
  issuer-only correction/revocation chain.

The proposed design therefore adds a separate issuer-authority ledger and a
rebuildable current-head projection. It does not widen or reinterpret existing
tables.

## 4. Contract and identifier versions

### 4.1 Version registry

| Contract | Proposed version |
|---|---|
| AuthorityEvidence | `issuer-authority-evidence/0.1.0` |
| AuthorityBundle | `issuer-authority-bundle/0.1.0` |
| IssuerDecision | `issuer-decision/0.1.0` |
| IssuerApprovalEvent | `issuer-approval-event/0.1.0` |
| IssuerAuthorityLink | `issuer-authority-link/0.1.0` |
| Rule set | `issuer-authority-rules/0.1.0` |
| Semantic ID scheme | `issuer-authority-id/1` |

These versions are local repository contracts. They do not claim to be
OpenDART, KRX, SEC, exchange, or provider API versions and do not widen the
Phase 1 global `contract_version=0.1.0` literal.

### 4.2 Canonical serialization

Every semantic hash in this design uses canonical JSON with these exact rules:

- UTF-8 bytes;
- Unicode NFC for text before validation and hashing;
- sorted object keys and no insignificant whitespace;
- exact enum tokens and explicit `null` values where allowed;
- UTC timestamps rendered with `Z`, and date-only values as `YYYY-MM-DD`;
- arrays defined as sets are deduplicated and sorted by their contract key;
- arrays defined as event sequences remain in predecessor-chain order;
- no NaN, Infinity, binary float, implicit case folding, or locale-sensitive
  ordering; and
- SHA-256 rendered as lowercase hexadecimal, with content hashes stored as
  `sha256:<64 lowercase hex>`.

### 4.3 Semantic identity exclusions

The following MUST NOT affect any evidence, bundle, decision, issuer, approval,
or link semantic identity:

- `fetched_at`, `retrieved_at`, `built_at`, `evaluated_at`, `recorded_at`, or DB
  insert/update time;
- collection attempt, run, job, process, thread, request-correlation, or
  database row IDs;
- database insertion order, parser iteration order, response order, or the
  current clock;
- local absolute path, raw storage reference, URL presentation variant, or log
  locator; and
- authentication session ID, bearer/cookie value, or any credential.

Authority-supplied publication, acceptance, as-of, correction, and effective
times are semantic facts when present and therefore are included. Audit time is
stored and queryable but excluded from semantic IDs.

### 4.4 Deterministic issuer anchors

Only these issuer anchors are proposed for CP3-C2-B:

```text
issuer-v1|KR|DART_CORP_CODE|<authority-supplied-8-digit-corp-code>
issuer-v1|US|SEC_CIK|<authority-supplied-zero-padded-10-digit-registrant-cik>
```

The canonical ID is:

```text
issuer_id = "issuer_" + sha256(UTF8_NFC(anchor)).lowerhex
```

Names, symbols, tickers, provider markets, KRX markets, accessions, login CIKs,
filing-agent CIKs, retrieval times, and database IDs never enter the issuer
anchor.

## 5. State model separate from MappingStatus

### 5.1 Machine decision states

| State | Meaning | Machine may emit | Approval allowed |
|---|---|---:|---:|
| `UNRESOLVED` | Required authority, jurisdiction, provider bridge, or uniqueness is missing or contradictory | yes | no |
| `READY_FOR_MANUAL_REVIEW` | Exact immutable bundle is complete, current under repository policy, non-contradictory, and collision-free | yes; maximum positive state | yes, after transaction-time revalidation |
| `STALE` | Current evidence is older than repository policy or a latest-revision/current-status check cannot be completed | yes | no |
| `REVIEW_REQUIRED` | Later evidence, conflict, correction, unavailability, or claim collision requires a new human review | yes; negative safety state | no |
| `SUPERSEDED` | Exposed effective state of an older decision after a successor decision is appended | derived from append-only predecessor relation | no |

### 5.2 Human dispositions

| State | Meaning |
|---|---|
| `APPROVED` | Authenticated human approves the exact current `READY_FOR_MANUAL_REVIEW` decision and bundle |
| `REJECTED` | Authenticated human declines the exact decision; no canonical issuer/link write occurs |
| `REVOKED` | Authenticated human terminates current issuer-link authority through a new event; old approval remains |
| `SUPERSEDED` | Authenticated human closes an old approval in favor of a separately approved successor bundle/decision |

### 5.3 Link states

`IssuerAuthorityLink` uses `APPROVED`, `REVIEW_REQUIRED`, `REVOKED`, and
`SUPERSEDED`. A rejected decision creates no link. Every B-version link has
`security_resolution_state=UNRESOLVED`; there is no B-version `security_id`
field and no mapping-status promotion.

`STALE` is normally a pre-approval decision state. Staleness or source
unavailability discovered after approval appends a `REVIEW_REQUIRED` link
version. That safety hold does not assert that the old authority fact is false
and does not delete or rewrite the old approval.

## 6. AuthorityEvidence contract

`AuthorityEvidence` represents one immutable normalized authority fact from one
exact immutable source document. Multiple facts from one document are separate
evidence records, which prevents a provenance-only CIK from inheriting the
authority of a registrant CIK in the same filing.

### 6.1 Required fields

| Field | Rule |
|---|---|
| `evidence_id` | `aev_` plus full SHA-256 of the semantic payload below |
| `contract_version` | exact `issuer-authority-evidence/0.1.0` |
| `evidence_content_hash` | SHA-256 of the same canonical semantic payload |
| `authority_source` | exact source namespace, such as `OPENDART`, `SEC_EDGAR`, or an independently approved legal registry |
| `source_document_kind` | exact versioned document/response kind |
| `authority_external_key` | authority-issued document key, such as an accepted accession or versioned corp-code record key |
| `authority_source_document_id` | deterministic document identity derived from source namespace, exact authority external key, and raw content hash |
| `raw_content_hash` | hash of exact source bytes, never reserialized JSON |
| `parser_contract_version` | exact parser/normalizer policy version |
| `evidence_kind` | `ASSERTION`, `CORRECTION`, `REVOCATION`, or `PROVENANCE_ONLY` |
| `authority_classification` | `OFFICIAL_AUTHORITY`, `SUPPORTING_EVIDENCE`, `DISCOVERY_ONLY`, `UNSUITABLE`, or `UNVERIFIED` |
| `authority_scope` | field-owned scope such as `ISSUER_REGULATORY_ID`, `LEGAL_JURISDICTION`, `LEGAL_NAME`, `REGISTRANT_ROLE`, or `SUBMISSION_PROVENANCE` |
| `subject_role` | exact role including `DART_DISCLOSURE_FILER`, `SEC_REGISTRANT`, `SEC_LOGIN_CIK`, or `SEC_FILING_AGENT` |
| `issuer_authority_weight` | `DECISIVE`, `SUPPORTING`, or `ZERO` |
| `claim_field` / `normalized_claim_value` | one typed fact; empty strings and inferred defaults forbidden |
| authority time fields | nullable authority-supplied published/accepted/as-of/effective time or date, with explicit missing reasons |
| `access_disposition` | `PERMITTED`, `RESTRICTED`, or `UNVERIFIED`; only permitted evidence can satisfy a required scope |
| retrieval provenance | at least one separate `AuthorityEvidenceObservation` with fetched UTC and opaque raw reference is required before the evidence can enter a decision |

The evidence semantic payload contains all fields above except `evidence_id`,
`evidence_content_hash`, and the retrieval-provenance observation.

```text
evidence_id = "aev_" + sha256(canonical_evidence_semantics).lowerhex
```

An identical refetch yields the same `AuthorityEvidence`. Each retrieval appends
an `AuthorityEvidenceObservation` containing `evidence_id`, `fetched_at`, exact
raw hash, opaque raw storage reference, and safe retrieval status. The
observation ID may use retrieval time because it is explicitly an audit
identity; neither it nor retrieval time enters any semantic evidence, bundle,
issuer, or link ID. Retrieval chronology therefore does not fork semantic
evidence.

```text
authority_evidence_observation_id = "aeobs_" + sha256(
  evidence_id |
  fetched_at |
  raw_content_hash |
  secret-free-retrieval-fingerprint
).lowerhex
```

This is a deterministic audit ID, not a semantic authority ID. The retrieval
fingerprint contains no credential, token, unrestricted header, or local path.

### 6.2 Required role constraints

- `SEC_REGISTRANT` plus authoritative accepted registrant metadata may have
  `DECISIVE` weight for `ISSUER_REGULATORY_ID`.
- `SEC_LOGIN_CIK` and `SEC_FILING_AGENT` MUST use
  `authority_scope=SUBMISSION_PROVENANCE`,
  `evidence_kind=PROVENANCE_ONLY`, and `issuer_authority_weight=ZERO`.
- A login/agent CIK record can share a source document with a registrant record,
  but it must have a distinct evidence ID and cannot be substituted into the
  registrant field.
- Provider name, symbol, ticker, market, and provider-supplied identifier are
  provider lineage, not `AuthorityEvidence` decisive issuer facts.
- KRX market and OpenDART `corp_cls`/`stock_code` may support a provider bridge
  in their limited scope but have zero `LEGAL_JURISDICTION` weight.
- A fact with restricted or unverified permitted use cannot satisfy bundle
  completeness, even if the underlying organization is official.

### 6.3 Evidence corrections and relations

Corrections never update an old evidence row. A new evidence row is appended and
an immutable relation is appended with one of:

- `CORRECTS` — the successor supplies an authority correction;
- `REVOKES` — the authority explicitly withdraws the predecessor fact; or
- `SUPERSEDES` — the successor is the applicable later authority version.

`authority_evidence_relation_id` is `aer_` plus SHA-256 of the relation contract
version, predecessor evidence ID, successor evidence ID, relation type, and any
authority-supplied effective fact. Discovery time and fetched time are excluded.
Multiple contradictory successor claims are retained and produce a conflict;
the database must not choose the first relation inserted.

## 7. AuthorityBundle contract

`AuthorityBundle` is an immutable, reviewable snapshot for exactly one
`provider_security_identity_id` and one proposed issuer anchor. It never
contains a canonical security candidate.

### 7.1 Required fields

| Field | Rule |
|---|---|
| `authority_bundle_id` | `authb_` plus full SHA-256 of bundle semantics |
| `contract_version` | exact `issuer-authority-bundle/0.1.0` |
| `bundle_content_hash` | SHA-256 of the same canonical semantic payload |
| `provider_security_identity_id` | existing immutable provider identity; must be active and not quarantined/collision |
| `provider_observation_ids` | sorted exact CP3-C1 observations used for the provider bridge |
| `candidate_jurisdiction` | independently evidenced `KR` or `US`, never copied from listing market |
| `candidate_identifier_kind/value` | `DART_CORP_CODE`/8 digits or `SEC_REGISTRANT_CIK`/10 zero-padded digits |
| `proposed_issuer_anchor` / `proposed_issuer_id` | exact deterministic values from section 4.4 |
| `evidence_members` | sorted unique evidence ID/content-hash/role tuples |
| `required_scope_results` | sorted map of each required field-owned scope to `SATISFIED`, `MISSING`, `CONFLICT`, `UNSUPPORTED`, or `UNUSABLE` |
| `legal_jurisdiction_result` | `ESTABLISHED`, `UNRESOLVED`, or `UNSUPPORTED_BY_CONTRACT` |
| `collision_scan_result` | `CLEAR` or `CONFLICT`, including sorted claim/candidate fingerprints |
| `decision_rule_version` | exact `issuer-authority-rules/0.1.0` |
| `evidence_set_hash` / `provider_lineage_set_hash` / `collision_scan_hash` | deterministic subhashes |
| `built_at` | aware UTC audit time, excluded from all semantic hashes |

The semantic payload includes candidate identity, exact sorted evidence
membership, exact provider observation membership, rule version, required-scope
results, legal-jurisdiction result, and conflict scan result. It excludes
retrieval observations and all clocks.

```text
authority_bundle_id =
  "authb_" + sha256(canonical_bundle_semantics).lowerhex
```

Changing membership, a relation head, a conflict result, candidate identity, or
rule version creates a new bundle. Refetching byte-identical evidence at a later
time does not.

### 7.2 Bundle immutability and approval snapshot

- Evidence membership is stored in an immutable join table, not a mutable JSON
  list alone.
- Provider lineage references exact CP3-C1 observation rows, not only a symbol
  string or batch source.
- Bundle construction records identifier claims before any review-ready
  decision may be emitted.
- An approval request carries only the reviewed decision ID and expected bundle
  content hash. The server loads the bundle; it does not accept evidence members
  or candidate fields from the approval body.
- Approval-time freshness and latest-revision checks reference exact retrieval
  observations but do not mutate or re-identify the bundle.

## 8. IssuerDecision contract

`IssuerDecision` is an immutable machine evaluation of one exact bundle. Human
disposition is not smuggled into this record.

### 8.1 Required fields and ID

| Field | Rule |
|---|---|
| `issuer_decision_id` | `idec_` plus full SHA-256 of decision semantics |
| `contract_version` | exact `issuer-decision/0.1.0` |
| `authority_bundle_id` | exact immutable bundle |
| `provider_security_identity_id` / `proposed_issuer_id` | must equal bundle values |
| `decision_state` | `UNRESOLVED`, `READY_FOR_MANUAL_REVIEW`, `STALE`, or `REVIEW_REQUIRED` |
| `reason_codes` | sorted unique non-empty codes; no free-form override code |
| `latest_revision_check_hash` | deterministic authority relation-head result |
| `freshness_policy_version` / `freshness_result` | repository policy and state, not an external-authority rule |
| `collision_scan_hash` | must equal a transactionally current scan before approval |
| `supersedes_decision_id` | nullable predecessor; creates a linear append-only chain |
| `evaluated_at` | aware UTC audit time, excluded from semantic ID |
| `decision_content_hash` | hash of decision semantic content; audit evaluation metadata is hashed in a separate audit domain and cannot alter this value |

The semantic ID preimage contains contract/rule version, bundle ID, decision
state, sorted reason codes, check-result hashes, and predecessor decision ID.
It excludes `evaluated_at` and execution identity.

### 8.2 Decision rules

- Machine code may emit `READY_FOR_MANUAL_REVIEW` but never `APPROVED`.
- `READY_FOR_MANUAL_REVIEW` requires every required scope satisfied, legal
  jurisdiction established and representable, permitted source use, a clear
  global collision scan, current evidence within
  `REPO_POLICY / CONSERVATIVE_APPROVAL_FRESHNESS`, and no later correction or
  revocation.
- Source unavailability or evidence older than 24 hours is `STALE`; the 24-hour
  limit remains a repository approval policy, not a claim about an authority.
- Later contradictory/corrected evidence or duplicate identifier claim appends a
  new `REVIEW_REQUIRED` decision. The old decision is exposed as `SUPERSEDED`
  through the predecessor relation; it is not updated.
- Only the unique current decision-chain leaf may be approved.

## 9. IssuerApprovalEvent contract

`IssuerApprovalEvent` is an append-only authenticated-human disposition. Codex,
GPT, a connector, parser, scheduled job, provider, or unauthenticated local
request cannot be the reviewer.

### 9.1 Required authentication fields

- stable server-resolved `reviewer_principal_id`;
- exact `reviewer_role=LOCAL_DATA_STEWARD`;
- opaque non-secret `authentication_event_id` resolved by the server;
- approved authentication method/policy version;
- `authenticated_at` and `recorded_at` aware UTC audit fields;
- exact reviewed `issuer_decision_id`, `authority_bundle_id`, and expected
  bundle content hash;
- mandatory structured reason code and non-empty review note digest; and
- predecessor approval event and successor decision references where required.

The principal and authentication context MUST come from server-side authenticated
state, not free-form request fields. Passwords, session cookies, bearer values,
or other credentials are never stored in the event.

An exact local authentication policy and reauthentication lifetime must be
approved before runtime implementation. A process owner, loopback address,
command-line flag, environment variable, or possession of a decision ID alone
does not satisfy authenticated human approval.

### 9.2 Event states and deterministic ID

| Event state | Preconditions | Result |
|---|---|---|
| `APPROVED` | current decision leaf is exactly `READY_FOR_MANUAL_REVIEW`; bundle/hash/checks revalidate | canonical issuer insert-or-verify plus issuer-only link in one transaction |
| `REJECTED` | authenticated reviewer disposes the exact decision | no issuer/link creation |
| `REVOKED` | predecessor is the current approved event/link | append revoked event/link; old approval remains |
| `SUPERSEDED` | old current approval and separately approved successor are validated atomically | old link gets an append-only superseded version; successor becomes current |

```text
issuer_approval_event_id = "iap_" + sha256(
  contract_version |
  issuer_decision_id |
  authority_bundle_id |
  event_state |
  reviewer_principal_id |
  structured_reason_code |
  review_note_digest |
  predecessor_approval_event_id-or-null |
  successor_decision_id-or-null
).lowerhex
```

Audit clocks, authentication session identity, retrieval observations, run IDs,
and database row IDs are excluded from this semantic ID. The full immutable
event audit hash covers those non-secret audit references separately. An exact
retry is idempotent; the same semantic event ID with different immutable audit
content is a typed conflict, never an overwrite.

### 9.3 No contradiction override

There is deliberately no `force`, `override`, `ignore_conflict`, or
`accept_anyway` field. Transaction-time revalidation takes precedence over the
reviewer's requested action. If the bundle is stale, no longer the current leaf,
has a changed relation head, or has a duplicate claim, `APPROVED` is rejected and
a machine `REVIEW_REQUIRED` decision is appended where applicable.

## 10. IssuerAuthorityLink contract

`IssuerAuthorityLink` is the append-only provider-identity to canonical-issuer
authority history. It is not the existing provider-to-security mapping.

### 10.1 Required fields

| Field | Rule |
|---|---|
| `issuer_authority_link_id` | `ial_` plus full SHA-256 of link semantics |
| `contract_version` | exact `issuer-authority-link/0.1.0` |
| `provider_security_identity_id` | immutable existing provider identity |
| `issuer_id` | deterministic canonical issuer ID created/verified by the approved event |
| `authority_bundle_id` / `issuer_decision_id` | exact authority lineage |
| `approval_event_id` | required for `APPROVED`, `REVOKED`, `SUPERSEDED`; null only for a machine safety `REVIEW_REQUIRED` link version |
| `link_state` | `APPROVED`, `REVIEW_REQUIRED`, `REVOKED`, or `SUPERSEDED` |
| `security_resolution_state` | exact `UNRESOLVED` in this contract version |
| `supersedes_link_id` | nullable predecessor; one linear history per provider identity |
| `authority_valid_from/to` | nullable and present only when supplied by field-owning authority evidence |
| `recorded_at` | aware UTC audit time, excluded from semantic ID and never copied into validity |
| `link_content_hash` | hash of link semantic content; audit recording metadata is separate and cannot alter this value |

The B contract has no `security_id`. A runtime implementation MUST additionally
assert that existing `provider_security_identities.mapping_status` and every
current `provider_identity_mappings` row remain `UNRESOLVED`/absent as before.

```text
issuer_authority_link_id = "ial_" + sha256(
  contract_version |
  provider_security_identity_id |
  issuer_id |
  authority_bundle_id |
  issuer_decision_id |
  link_state |
  trigger-kind-and-id |
  supersedes_link_id-or-null |
  authority-supplied-validity-or-null
).lowerhex
```

### 10.2 Issuer-approved / security-unresolved truth table

| Fact | Required stored result after B approval |
|---|---|
| Canonical issuer exists | yes, deterministic insert-or-verify |
| IssuerAuthorityLink current state | `APPROVED` |
| Security resolution | `UNRESOLVED` |
| Canonical Security created | `0` |
| Existing ProviderIdentityMapping VERIFIED | `0` |
| Provider identity or anchor changed | `0` |
| Provider/source/identifier/observation history changed | `0` |

A rebuildable `issuer_authority_link_heads` projection points to the current
append-only link leaf for each provider identity. The head may be updated by
compare-and-swap; evidence, decisions, approval events, and link versions may
not be updated or deleted.

## 11. Korea issuer runtime contract

### 11.1 Required positive path

A KR issuer bundle can reach `READY_FOR_MANUAL_REVIEW` only when all of the
following are true:

1. An exact valid 8-digit OpenDART `corp_code` is present in authoritative
   corporation-code evidence.
2. Current company-overview evidence is retrieved under that exact code and is
   consistent with the corporation-code record or an official name-history
   correction explains the difference.
3. The issuer's actual legal jurisdiction is independently established as `KR`
   by evidence with legal-jurisdiction scope. KRX market membership and provider
   fields do not satisfy this item.
4. The provider bridge includes exact CP3-C1 observation lineage and more than
   name/symbol similarity. An OpenDART `stock_code` under the resolved corp code
   may support an exact provider-code bridge, but it is not the issuer anchor,
   legal-jurisdiction evidence, ISIN authority, or security approval.
5. Ticker reuse, multiple current corp-code candidates, current stock-code
   ambiguity, provider collision/quarantine, and unexplained names are absent.
6. No existing canonical issuer or claim ledger contains contradictory current
   authority evidence for the corp code or provider identity.
7. Current evidence passes the repository freshness/latest-correction check.

This bundle may authorize a KR canonical issuer and issuer-only link after human
approval. It does not authorize KRX instrument/class/ISIN/exchange truth or a
canonical Security.

### 11.2 Foreign KRX issuer fail-closed matrix

| Actual issuer jurisdiction | Available authority | B result |
|---|---|---|
| `KR` | complete OpenDART + independent KR jurisdiction + unambiguous provider bridge | may reach manual review |
| `US` | complete SEC registrant path and independent US jurisdiction; DART may be supporting cross-listing evidence | use the US issuer anchor only; never coerce to KR |
| unsupported country | valid DART corp code and KRX/provider observations | `UNRESOLVED / jurisdiction-contract-required` |
| unknown or contradictory | any listing evidence | `UNRESOLVED`; review-ready/canonical writes `0` |

KOSPI/KOSDAQ/KONEX, KRX listing eligibility, Korean currency, `corp_cls`,
`stock_code`, provider market, Korean name, or a DART disclosure row never
supplies the missing legal jurisdiction.

### 11.3 KR rejection cases

- malformed, missing, synthetic, duplicate, or contradictory corp code;
- corp code found only in a fixture, search result, provider field, or unofficial
  crosswalk;
- name-only or symbol-only candidate association;
- multiple DART companies competing for one provider identity;
- foreign issuer jurisdiction not representable as KR or US;
- fetched time used as company, correction, code, or validity date; or
- any attempt to create a Security or verified provider mapping.

## 12. United States issuer runtime contract

### 12.1 Required positive path

A US issuer bundle can reach `READY_FOR_MANUAL_REVIEW` only when all of the
following are true:

1. `registrant_cik` is an exact zero-padded 10-digit CIK obtained from
   authoritative registrant/filer metadata for an accepted filing/submission.
2. The accepted evidence identifies the candidate as the issuer registrant,
   not merely the login CIK, filing agent, fund, individual, or delegated filer.
3. At least one accepted issuer filing under that registrant CIK is included,
   with current/former legal name reconciled through official history.
4. Actual legal jurisdiction is established and maps exactly to the current
   canonical `Jurisdiction.US` contract. SEC registration or a US exchange does
   not itself prove US legal jurisdiction.
5. Exact provider observation lineage bridges to issuer-reported accepted
   filing metadata without relying on a ticker/name convenience file alone.
   Class, exchange, and instrument final authority remain CP3-C2-C.
6. No contradictory CIK/entity claim, ticker-reuse ambiguity, provider
   collision/quarantine, later authoritative correction, or unavailable current
   check exists.
7. Current evidence passes repository freshness and latest-filing checks.

### 12.2 Registrant and submission-provenance separation

For one accepted filing, the evidence ledger may contain all of these separate
facts:

| Fact | Role | Issuer authority |
|---|---|---:|
| authoritative registrant CIK | `SEC_REGISTRANT` | decisive within SEC issuer scope |
| first ten accession digits / login CIK | `SEC_LOGIN_CIK` | zero |
| separately identified filing-agent CIK | `SEC_FILING_AGENT` | zero |
| accepted accession | source-document identity/provenance | not a CIK substitute |

If registrant CIK A and login/agent CIK B differ, the issuer candidate is A.
There is no A-to-B merge. If authoritative registrant metadata cannot be
resolved independently, the result is `UNRESOLVED`, even if the accession
prefix is syntactically valid.

### 12.3 Foreign private issuer and private/non-issuer limitations

- A valid CIK and accepted Form 20-F or 40-F can establish SEC registrant scope
  but do not coerce the issuer's legal jurisdiction to `US`.
- If the foreign private issuer's actual jurisdiction is outside the current KR
  or US enum, the bundle is `UNRESOLVED / jurisdiction-contract-required`.
- If actual jurisdiction is KR and the KR authority path is complete, the KR
  DART anchor is used; the US listing and CIK remain additional authority
  evidence, not a reason to create a second name-matched issuer.
- A private issuer, exempt offering filer, fund, individual, filing agent, or
  other CIK holder is not promoted merely because EDGAR assigned a CIK.
- SEC company-ticker files, ticker search, provider ticker/name, accession
  prefix, or exchange membership alone cannot create or merge an issuer.

## 13. Correction, revocation, and supersession workflow

### 13.1 Authority correction before approval

1. Preserve old evidence and retrieval observations.
2. Append corrected evidence and an authority relation.
3. Append a new bundle with the new relation head and conflict result.
4. Append a decision superseding the old decision.
5. The old bundle/decision remains queryable and exposes effective
   `SUPERSEDED`; no canonical write occurs until a new approval.

### 13.2 Later evidence after approval

- Unavailability or staleness appends `REVIEW_REQUIRED`; it is not automatic
  proof that the old issuer was false.
- A new duplicate claim or contradictory official fact appends
  `REVIEW_REQUIRED` for every affected current link and suspends current issuer
  projection use. It does not select a winner.
- A corrected bundle must independently return to
  `READY_FOR_MANUAL_REVIEW` and receive a new authenticated approval.
- If the old issuer link was wrong, an authenticated `REVOKED` or `SUPERSEDED`
  event closes current use. The old approval, issuer row, and provider history
  are never deleted or rekeyed.

### 13.3 Effective times

Authority-supplied effective time/date is preserved when explicit. If absent,
the system stores only publication/acceptance/as-of, retrieval, evaluation, and
approval audit times in their distinct fields. It does not invent
`authority_valid_from`, `authority_valid_to`, or a correction-effective date.

## 14. Concurrency and integrity contract

### 14.1 Immutable-chain constraints

- One decision root per bundle and a unique non-null
  `supersedes_decision_id` produce a single decision chain with one leaf.
- One initial human disposition per exact decision prevents simultaneous
  `APPROVED` and `REJECTED` roots.
- A unique non-null `supersedes_approval_event_id` prevents approval-event
  forks.
- One link root per provider identity and a unique non-null
  `supersedes_link_id` produce one append-only link chain.
- Cycle detection and same-subject/same-bundle predecessor validation are
  mandatory repository checks. A deterministic child ID includes its parent.
- New ledger tables reject `UPDATE` and `DELETE` through repository policy and
  proposed database triggers. Only the rebuildable head projection is mutable.

### 14.2 Exact approval transaction

SQLite approval uses `BEGIN IMMEDIATE` and performs these steps in order:

1. Load the exact decision and bundle by ID; verify stored content hashes.
2. Require the decision to be the unique current leaf and exactly
   `READY_FOR_MANUAL_REVIEW`.
3. Recompute evidence-relation heads, global identifier claims, provider state,
   bundle membership, collision scan, latest revision, access disposition, and
   freshness under the approved rule version.
4. Require the reviewed expected bundle hash to match; never accept caller-
   supplied evidence or candidate fields.
5. Verify server-resolved human principal/authentication context and reviewer
   role.
6. Insert-or-verify the deterministic canonical issuer. An existing row must
   have the same deterministic ID, authority identifiers, jurisdiction, and
   semantic payload; otherwise fail closed.
7. Append the approval event and issuer-authority link.
8. Insert or compare-and-swap the link head using the expected prior head hash.
9. Assert canonical Security insert count `0`, verified provider-mapping insert
   or update count `0`, and provider/history update count `0`.
10. Commit atomically. On any failure, roll back issuer/approval/link/head writes
    while preserving pre-existing evidence, bundles, decisions, and provider
    history.

An exact duplicate approval event is idempotent. A different action or candidate
after disposition returns a typed conflict; it never overwrites the winner.

### 14.3 Duplicate authority identifiers: no first-writer-wins

The proposed claim ledger intentionally has no global unique index that would
silently retain the first candidate and reject only the second. Instead:

1. Every bundle appends its normalized strong-identifier claim and a candidate
   fingerprint before a review-ready decision can exist.
2. A claim scan groups by jurisdiction, identifier kind, and normalized value.
3. More than one distinct candidate fingerprint, or more than one strong issuer
   identifier competing for one provider identity, marks every affected bundle
   `UNRESOLVED` and every existing affected current link `REVIEW_REQUIRED`.
4. Approval transactions serialize and rerun the scan. The human cannot pick a
   winner while the claim set is contradictory.
5. A late conflict preserves any old approval as history but removes its
   operationally current `APPROVED` head through an append-only safety hold.

Bundle/claim creation and human approval cannot occur in the same request or
transaction. The reviewed immutable bundle and claim set must already exist,
which closes the simultaneous first-write window.

### 14.4 One decision bundle, one disposition

The database later SHOULD add partial unique indexes equivalent to:

```text
UNIQUE (authority_bundle_id) WHERE supersedes_decision_id IS NULL
UNIQUE (supersedes_decision_id) WHERE supersedes_decision_id IS NOT NULL
UNIQUE (issuer_decision_id)
  WHERE event_state IN ('APPROVED', 'REJECTED')
    AND supersedes_approval_event_id IS NULL
UNIQUE (supersedes_approval_event_id)
  WHERE supersedes_approval_event_id IS NOT NULL
UNIQUE (provider_security_identity_id)
  WHERE supersedes_link_id IS NULL
UNIQUE (supersedes_link_id) WHERE supersedes_link_id IS NOT NULL
```

Composite foreign keys bind each approval event to the exact
`(issuer_decision_id, authority_bundle_id)` pair and each link to its exact
decision, bundle, and event. Repository checks enforce same provider identity
and proposed issuer across those rows.

## 15. Proposed additive migration `0005`

### 15.1 Migration identity

- Proposed filename:
  `services/api/alembic/versions/0005_phase_02_cp3_c2_b_issuer_authority.py`
- Proposed revision:
  `0005_phase_02_cp3_c2_b_issuer_authority`
- Exact down revision:
  `0004_phase_02_cp3_c1_security_master`
- B1 action: proposal only; file creation and application count `0`.

### 15.2 Additive table proposal

| Table | Purpose and principal keys |
|---|---|
| `authority_evidence` | immutable semantic facts; PK `evidence_id`, unique semantic content hash, typed authority role/scope/claim/raw hash |
| `authority_evidence_observations` | append-only retrieval/freshness audit for evidence; FK evidence, fetched UTC, exact raw/ref metadata; never a semantic bundle member |
| `authority_evidence_relations` | append-only `CORRECTS`/`REVOKES`/`SUPERSEDES` edges between evidence rows |
| `authority_bundles` | immutable provider+issuer-candidate snapshot; PK bundle, FK provider identity, deterministic hashes and rule version |
| `authority_bundle_evidence` | immutable bundle/evidence membership and field role; composite PK plus deterministic ordinal |
| `authority_bundle_provider_observations` | exact bundle-to-CP3-C1 provider observation lineage; no symbol-only join |
| `authority_identifier_claims` | append-only normalized corp-code/registrant-CIK claims and candidate fingerprints; indexed but intentionally not first-writer unique |
| `issuer_decisions` | append-only linear machine-decision chain per bundle |
| `issuer_approval_events` | append-only authenticated-human disposition chain bound to exact decision/bundle |
| `issuer_approval_evidence_observations` | exact retrieval observations used by approval-time freshness/latest checks |
| `issuer_authority_links` | append-only provider-to-issuer link history with security state fixed to unresolved |
| `issuer_authority_link_heads` | rebuildable per-provider current leaf/state projection with CAS state hash |

All primary keys are deterministic text IDs except retrieval/authentication audit
identities, which are explicitly non-semantic and cannot enter evidence, bundle,
decision, issuer, approval, or link semantic hashes.

### 15.3 Required foreign keys and checks

- Every bundle provider ID references `provider_security_identities`.
- Provider-lineage membership references exact
  `provider_security_master_observations`, whose identity must equal the bundle
  provider identity.
- Every evidence relation references two existing evidence rows, rejects
  self-relations, and requires an exact allowed relation type.
- Evidence with role `SEC_LOGIN_CIK` or `SEC_FILING_AGENT` is constrained to
  provenance scope and zero authority.
- Candidate identifier kind and jurisdiction pairs are exact:
  `KR/DART_CORP_CODE` or `US/SEC_REGISTRANT_CIK`.
- Decision and event enums are stored in new columns and never in
  `MappingStatus`.
- Event composite foreign keys bind the exact decision/bundle pair.
- Approved/revoked/superseded link rows require an approval event;
  `REVIEW_REQUIRED` requires a machine decision trigger and no fake approval.
- Every B link has `security_resolution_state='UNRESOLVED'`.
- Validity intervals permit null and enforce ordering only when both endpoints
  are authority supplied.
- Payload JSON and relational columns must insert-or-verify each other; a
  mismatch is a typed contract conflict.

### 15.4 Append-only enforcement

The proposal includes `BEFORE UPDATE` and `BEFORE DELETE` fail-closed triggers
for evidence, observations, relations, bundle membership, claims, decisions,
approval events, approval-observation membership, and link versions. The head
projection is the sole mutable table and must use a one-statement conditional
update on its expected `state_hash`.

No trigger is added to an existing table in B unless independent review proves
it is necessary and compatible. Provider and canonical historical tables remain
unchanged.

### 15.5 Existing migration immutability baseline

The exact SHA-256 values at the B1 starting SHA are:

| Migration | SHA-256 |
|---|---|
| `0001_phase_01_foundation.py` | `6eba164ef2f8bab42583076805255268e4daba29311e8f6e956f4177c0445762` |
| `0002_phase_02_cp3_foundation.py` | `4b6b716999c5f3f6b52be1e85a53685c14c181fb4991e9ead892080717abaee6` |
| `0003_phase_02_cp3_b_invariants.py` | `b59e74b5e817b6a5606d9f89f1f57eec3e0ba3616918d117d3cc28af4f5c420b` |
| `0004_phase_02_cp3_c1_security_master.py` | `cd1cbcae309f1e56ba923e6463863749c79a84b4c10499801f5da28b0a3a0f4f` |

A later `0005` implementation must pin and recheck these exact hashes. It may add
new tables, indexes, and new-table triggers only. It may not edit, backfill,
rename, rebuild, or reinterpret existing tables or migrations.

### 15.6 Upgrade, failure, downgrade, and operational rollback

- Blank upgrade and existing `0001`/`0004` database upgrade must both work.
- Mid-DDL failure cleanup removes only objects created by that failed `0005`
  attempt and preserves the prior Alembic revision, all old rows, indexes,
  triggers, and any pre-existing sentinel.
- Test downgrade/re-upgrade occurs only on a disposable database.
- Production operational rollback stops new issuer-authority writes and preserves
  the ledger. It does not automatically downgrade or delete evidence/history.
- A destructive production downgrade requires backup, restore verification, and
  separate explicit user approval.
- `SQLiteMetadataRepository` public Phase 1 revision masking would be updated
  only in the later implementation so the additive internal head remains
  compatible; B1 changes no code.

## 16. Later implementation acceptance matrix

No test below is implemented in B1. A later CP3-C2-B implementation cannot claim
PASS without executable coverage for at least these cases.

| ID | Scenario | Required result |
|---|---|---|
| B1-ID-01 | same semantic evidence, different fetched/run/DB IDs | identical evidence ID/hash |
| B1-ID-02 | same members in different input order | identical bundle ID/hash and canonical membership order |
| B1-ID-03 | same decision evaluation under different clocks | identical semantic decision ID; audit time remains distinct |
| B1-KR-01 | unique DART corp code + independent KR jurisdiction + unambiguous bridge | machine may reach review-ready; no automatic issuer |
| B1-KR-02 | KRX-listed foreign issuer, unsupported jurisdiction | unresolved; issuer/security/verified mapping/review-ready counts zero |
| B1-KR-03 | KRX/provider fields used as jurisdiction | contract rejection |
| B1-US-01 | authoritative registrant CIK + accepted issuer filing + US jurisdiction | machine may reach review-ready |
| B1-US-02 | registrant CIK A, login/agent CIK B | A candidate only; B provenance weight zero |
| B1-US-03 | registrant unresolved but accession prefix present | unresolved; canonical writes zero |
| B1-US-04 | foreign private issuer outside KR/US | unresolved / jurisdiction-contract-required |
| B1-AUTH-01 | unauthenticated/Codex/job approval attempt | rejection; writes zero |
| B1-AUTH-02 | human tries conflict override | rejection; no override path exists |
| B1-CON-01 | concurrent approve/reject on one decision | exactly one disposition; loser typed conflict; no mixed rows |
| B1-CON-02 | two distinct candidate fingerprints claim one authority ID | all affected unresolved/review-required; no first-writer winner |
| B1-CON-03 | concurrent link-head writes | one CAS winner or idempotent duplicate; no mixed head/history |
| B1-HIST-01 | revoke approved issuer link | old approval/link remains; new revoked event/link appended |
| B1-HIST-02 | correct and supersede | old evidence/bundle/decision/link queryable; new chain explicit |
| B1-LINK-01 | issuer approved, security unresolved | issuer/link one; Security zero; VERIFIED mapping zero |
| B1-LINK-02 | approval after provider rekey attempt | hard rejection; all provider IDs/hashes unchanged |
| B1-MIG-01 | 0005 upgrade/downgrade/re-upgrade on disposable DB | old rows/hashes preserved and new constraints enforced |
| B1-MIG-02 | 0005 later-table failure | revision stays 0004; prior schema/data/sentinel unchanged; retry succeeds |

Additional exact counters required by ADR-013:

```text
automatic canonical issuer promotion = 0
synthetic/fake corp_code = 0
synthetic/fake CIK = 0
name-only merge = 0
symbol-only merge = 0
jurisdiction inferred from listing/provider fields = 0
login/accession/filing-agent CIK used as issuer authority = 0
canonical Security created = 0
ProviderIdentityMapping set to VERIFIED = 0
provider identity/allocation/history rekeys = 0
authority evidence/decision/approval/link deletes or rewrites = 0
```

## 17. Illustrative contract envelope

The following is a schema-shaped illustration only. Angle-bracket strings are
not fixture values, authority evidence, or approved identifiers.

```json
{
  "authority_bundle_id": "authb_<64-lowercase-hex>",
  "contract_version": "issuer-authority-bundle/0.1.0",
  "provider_security_identity_id": "tpsi_<64-lowercase-hex>",
  "candidate_jurisdiction": "KR",
  "candidate_identifier_kind": "DART_CORP_CODE",
  "candidate_identifier_value": "<authority-supplied-8-digit-corp-code>",
  "proposed_issuer_id": "issuer_<64-lowercase-hex>",
  "evidence_members": [
    {
      "evidence_id": "aev_<64-lowercase-hex>",
      "evidence_content_hash": "sha256:<64-lowercase-hex>",
      "role": "ISSUER_REGULATORY_ID"
    }
  ],
  "legal_jurisdiction_result": "ESTABLISHED",
  "collision_scan_result": "CLEAR",
  "decision_rule_version": "issuer-authority-rules/0.1.0"
}
```

An approved B projection would separately expose:

```json
{
  "link_state": "APPROVED",
  "issuer_id": "issuer_<64-lowercase-hex>",
  "provider_security_identity_id": "tpsi_<64-lowercase-hex>",
  "security_resolution_state": "UNRESOLVED"
}
```

It would not contain `security_id` and would not imply a verified provider
identity mapping.

## 18. B1 checkpoint result

- CP3-C1: `PASS — CLOSED`
- CP3-C2-A: `PASS — CONTRACT APPROVED AND CLOSED`
- ADR-013: `ACCEPTED` and unchanged
- CP3-C2-B1: `PLANNING — AWAITING GPT INDEPENDENT REVIEW`
- CP3-C2-B implementation: `NOT STARTED`
- Proposed `0005` file created/applied: `0`
- CP3-C2-C: `NOT STARTED`
- CP3-D: `NOT STARTED`
- Automatic progression: `PROHIBITED`

Independent review and explicit user approval are required before this proposed
contract or migration can become an accepted implementation contract. Even that
approval would not start CP3-C2-C or CP3-D.
