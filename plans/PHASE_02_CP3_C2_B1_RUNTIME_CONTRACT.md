# Phase 2 CP3-C2-B1 — Issuer Authority Runtime Contract and Additive Migration Design

- Checkpoint: `CP3-C2-B1`
- Status: `REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW`
- Initial design starting SHA: `959f78415aade27e57d191db3025c66ea4266999`
- Independent-review remediation starting SHA:
  `adfb76285af7ae5884cfc60a0223591bb7e9c913`
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
| AuthorityEvidenceApplication | `issuer-authority-evidence-application/0.1.0` |
| AuthoritySourcePolicy | `issuer-authority-source-policy/0.1.0` |
| AuthorityBundle | `issuer-authority-bundle/0.1.0` |
| IssuerDecision | `issuer-decision/0.1.0` |
| IssuerApprovalEvent | `issuer-approval-event/0.1.0` |
| IssuerAuthorityLink | `issuer-authority-link/0.1.0` |
| Local data-steward authentication | `issuer-steward-webauthn/0.1.0` |
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

`AuthorityEvidence` represents one reusable immutable source fact from one exact
immutable source document. Candidate-specific interpretation is deliberately
absent from this record and is stored in the separately versioned
`AuthorityEvidenceApplication` in section 6.4. Multiple facts from one document
are separate evidence records, which prevents a provenance-only CIK from
inheriting the authority of a registrant CIK in the same filing.

### 6.1 Required fields

| Field | Rule |
|---|---|
| `evidence_id` | `aev_` plus full SHA-256 of the semantic payload below |
| `contract_version` | exact `issuer-authority-evidence/0.1.0` |
| `evidence_content_hash` | SHA-256 of the same canonical semantic payload |
| `evidence_provenance_hash` | separate hash of every immutable stored provenance field, including locator/reference and exact raw claim value; a same-ID/different-provenance insert is a typed conflict |
| `authority_source_policy_id` | exact immutable admitted policy from section 6.5; parser text cannot create authority without it |
| `authority_source_identifier` | exact server-owned source namespace, such as `OPENDART_CORP_CODE`, `SEC_EDGAR_ACCEPTED_FILING`, `KR_SUPREME_COURT_IROS`, or one individually admitted US state-registry namespace |
| `authority_classification` | server-resolved classification from the source policy, not a free parser field |
| `authority_source_locator` | exact credential-free public HTTPS source URL when one exists; otherwise the approved official verification/issuance locator. Search-result and local-file URLs are forbidden |
| `authority_document_reference` | exact authority-issued accession, registry-document number, verification reference, or versioned record key; an accepted SEC accession may satisfy the public-document reference requirement |
| `source_document_kind` | exact policy-approved versioned document/response kind |
| `authority_external_key` | authority-issued fact/document natural key, never a run, row, or retrieval key |
| `authority_source_document_id` | deterministic document identity derived from source namespace, exact authority external key, and raw content hash |
| `raw_content_hash` | hash of exact source bytes, never reserialized JSON |
| `parser_contract_version` | exact parser/normalizer policy version |
| `evidence_kind` | `ASSERTION`, `CORRECTION`, `REVOCATION`, or `PROVENANCE_ONLY` |
| `authority_scope` | field-owned scope such as `ISSUER_REGULATORY_ID`, `LEGAL_JURISDICTION`, `LEGAL_ENTITY_BRIDGE`, `LEGAL_NAME`, `REGISTRANT_ROLE`, or `SUBMISSION_PROVENANCE` |
| `subject_role` | exact role including `DART_DISCLOSURE_FILER`, `KOREAN_REGISTERED_LEGAL_ENTITY`, `US_STATE_REGISTERED_LEGAL_ENTITY`, `SEC_REGISTRANT`, `SEC_LOGIN_CIK`, or `SEC_FILING_AGENT` |
| `policy_maximum_issuer_authority_weight` | source-policy ceiling `DECISIVE`, `SUPPORTING`, or `ZERO`; the parser and caller cannot raise it |
| `claim_field` | exact field name or deterministic field path in the source document |
| `raw_claim_value` | exact raw field value used by normalization, with type/encoding preserved; required even when the full raw document hash is present |
| `normalized_claim_value` | one typed normalized fact derived from `raw_claim_value`; empty strings, inferred defaults, and manual replacement values are forbidden |
| authority time fields | nullable authority-supplied published/accepted/as-of/effective time or date, with explicit missing reasons |
| `access_disposition` / `license_disposition` | exact `PERMITTED`, `RESTRICTED`, or `UNVERIFIED` values resolved under policy; both must permit the proposed use before a fact can satisfy a required scope |
| `origin_data_mode` / `origin_adapter_class` | immutable server-owned lineage (`PRODUCTION_AUTHORITY` or `TEST_ONLY`) used by the admission boundary; relabelling cannot clear test/fixture taint |
| retrieval provenance | at least one separate `AuthorityEvidenceObservation` with fetched UTC and opaque raw reference is required before the evidence can enter a decision |

The evidence semantic payload includes the exact source-policy identity,
source/document identity, raw document hash, parser version, fact role/scope,
field name, `raw_claim_value`, `normalized_claim_value`, authority-supplied time
facts, access/license disposition, and immutable origin lineage. A raw document
hash is never a substitute for `raw_claim_value`.

The exact public/verification locator and its presentation form are immutable
stored provenance and are covered by `evidence_provenance_hash`, but remain
excluded from semantic identity as required by section 4.3. Changing an
authority document reference, raw fact, raw bytes, policy, or parser creates a
new semantic evidence record. Changing only an equivalent URL presentation
does not silently mutate the prior row; it appends a new observation/locator
audit record that verifies the same evidence ID.

```text
evidence_id = "aev_" + sha256(canonical_evidence_semantics).lowerhex
```

An identical refetch yields the same `AuthorityEvidence`. Each retrieval appends
an `AuthorityEvidenceObservation` containing `evidence_id`, `fetched_at`, exact
raw hash, exact source locator/reference observed, opaque raw storage reference,
and safe retrieval status. The
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
  `evidence_kind=PROVENANCE_ONLY`, and
  `policy_maximum_issuer_authority_weight=ZERO`.
- A login/agent CIK record can share a source document with a registrant record,
  but it must have a distinct evidence ID and cannot be substituted into the
  registrant field.
- Provider name, symbol, ticker, market, and provider-supplied identifier are
  provider lineage, not `AuthorityEvidence` decisive issuer facts.
- KRX market and OpenDART `corp_cls`/`stock_code` may support a provider bridge
  in their limited scope but have zero `LEGAL_JURISDICTION` weight.
- A fact with restricted or unverified permitted use cannot satisfy bundle
  completeness, even if the underlying organization is official.
- `authority_scope`, `subject_role`, classification, and weight are accepted
  only when the exact source-policy row permits that combination. A parser that
  emits `LEGAL_JURISDICTION` for an unlisted combination produces an unusable
  application with effective weight `ZERO`; the enum label has no authority by
  itself.

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

### 6.4 AuthorityEvidenceApplication contract

`AuthorityEvidenceApplication` is the immutable statement of how one reusable
evidence fact was evaluated against one exact provider/issuer candidate under
one exact rule and source-policy version. Re-evaluation never mutates an old
application; a different candidate, status, reason, policy, rule, relation head,
or provider lineage creates a new application.

| Field | Rule |
|---|---|
| `evidence_application_id` | `aeapp_` plus full SHA-256 of the semantic payload below |
| `contract_version` | exact `issuer-authority-evidence-application/0.1.0` |
| `application_content_hash` | SHA-256 of the same semantic payload |
| `evidence_id` / `evidence_content_hash` | exact immutable source fact and verified content hash |
| `provider_security_identity_id` | exact existing provider subject to which the fact is applied |
| `provider_observation_ids` | sorted exact provider observations when the fact participates in a bridge; empty only for a candidate-wide authority fact |
| `proposed_issuer_id` / `candidate_fingerprint` | exact deterministic candidate application; name, ticker, and row order are excluded |
| `authority_scope` / `claim_target_field` | exact field-owned scope and candidate field being evaluated |
| `authority_source_policy_id` | exact policy that admits or rejects this source/document/scope/role combination |
| `application_status` | one of the exact states below |
| `effective_issuer_authority_weight` | `DECISIVE`, `SUPPORTING`, or `ZERO`; MUST be less than or equal to the source-policy maximum |
| `reason_codes` | sorted unique structured codes; free-form parser reasons cannot change authority |
| `authority_relation_head_hash` | exact correction/revocation/supersession head evaluated for this fact |
| `application_rule_version` | exact `issuer-authority-rules/0.1.0` or approved successor |
| `evaluated_at` | aware UTC audit time excluded from semantic identity |

Allowed `application_status` values are:

- `APPLIED_DECISIVE`;
- `APPLIED_SUPPORTING`;
- `PROVENANCE_ONLY`;
- `REJECTED_CONFLICT`;
- `REJECTED_STALE`;
- `REJECTED_UNUSABLE`;
- `REJECTED_SOURCE_POLICY`;
- `REJECTED_SUBJECT_MISMATCH`; and
- `REJECTED_UNVERIFIABLE`.

`MISSING` is represented at the exact candidate/scope level in
`AuthorityBundle.required_scope_results` with sorted structured reason codes.
The system MUST NOT fabricate an evidence row or nullable evidence application
to represent absence. Thus conflict, missing, stale, and unusable disposition
are all explicit without mutating reusable evidence or inventing a raw fact.

```text
evidence_application_id = "aeapp_" + sha256(
  contract_version |
  evidence_id | evidence_content_hash |
  provider_security_identity_id |
  sorted-provider-observation-ids |
  proposed_issuer_id | candidate_fingerprint |
  authority_scope | claim_target_field |
  authority_source_policy_id |
  application_status | effective-weight |
  sorted-reason-codes |
  authority_relation_head_hash |
  application_rule_version
).lowerhex
```

Retrieval/evaluation time, run/job/row identity, application insertion order,
and current clock are excluded. A bundle may use a fact only through its exact
application ID and content hash; directly adding a bare evidence ID to a
candidate bundle is forbidden.

### 6.5 AuthoritySourcePolicy and production admission boundary

`AuthoritySourcePolicy` is an immutable, versioned, server-owned registry of
which source/document/scope/subject combinations may carry issuer authority.
It is evaluated before an evidence application or production bundle can be
created. A source name, enum value, parser label, or syntactically valid
identifier has no weight without an exact admitted policy row.

Each policy row contains at least:

- `authority_source_policy_id` and exact
  `issuer-authority-source-policy/0.1.0` contract version;
- exact source namespace with no production wildcard;
- field-owning organization and authority classification;
- exact approved document kinds and credential-free source/verification root;
- allowed authority scopes and subject roles;
- maximum issuer-authority weight for every allowed scope/role pair;
- permitted ingestion mode: `AUTOMATED_OFFICIAL_PUBLIC`,
  `HUMAN_ASSISTED_VERIFIED_DOCUMENT`, `PROVENANCE_ONLY`, or
  `TEST_ISOLATED_ONLY`;
- exact admitted adapter and parser contract versions;
- `production_authority_eligible` boolean;
- required access and license disposition;
- allowed origin data modes and immutable test/synthetic-taint rule; and
- superseded policy reference and policy-effective fact, when supplied by the
  repository policy owner. Registration time is audit-only.

```text
authority_source_policy_id = "aspol_" + sha256(
  canonical-source-namespace |
  field-owner-and-classification |
  sorted-document-kinds-and-locator-roots |
  sorted-scope-role-maximum-weight-matrix |
  ingestion-mode-and-adapter/parser-versions |
  production-eligibility-and-access/license-rules |
  origin-mode-and-taint-rules |
  predecessor-policy-id-or-null
).lowerhex
```

Policy rows are append-only. A policy change creates a new deterministic ID and
does not retroactively upgrade old evidence applications. Each US state or
territory registry requires its own exact namespace and policy row, such as
`US_STATE_REGISTRY_DE`; a generic `US_STATE_REGISTRY_*` wildcard is never a
production admission rule.

#### 6.5.1 Authority source × scope × maximum-weight matrix

`DECISIVE` means the source may own that named field only when all admission and
bridge requirements pass. `SUPPORTING` can corroborate but can never satisfy a
required decisive scope by itself. Any unlisted combination has maximum weight
`ZERO`.

| Exact source namespace / document kind | Authority scope | Allowed subject role | Maximum weight | Permitted ingestion | Production-authority condition |
|---|---|---|---:|---|---|
| `KR_SUPREME_COURT_IROS` / verified original corporate-registry extract plus official verification result | `LEGAL_JURISDICTION` | `KOREAN_REGISTERED_LEGAL_ENTITY` | `DECISIVE` | `HUMAN_ASSISTED_VERIFIED_DOCUMENT` | Exact original bytes, official document reference and authenticity verification; record must identify a Korean-law domestic entity, and exact court-registry corporate registration reference must bridge to the candidate |
| `KR_SUPREME_COURT_IROS` / same verified record | `LEGAL_NAME`, `LEGAL_ENTITY_BRIDGE` | `KOREAN_REGISTERED_LEGAL_ENTITY` | `DECISIVE` | `HUMAN_ASSISTED_VERIFIED_DOCUMENT` | Same verification and exact subject bridge; screenshots/search results/manual values forbidden |
| `OPENDART_CORP_CODE` / official corporation-code record | `ISSUER_REGULATORY_ID` | `DART_DISCLOSURE_FILER` | `DECISIVE` | `AUTOMATED_OFFICIAL_PUBLIC` | Exact 8-digit raw corp code, permitted official bytes, current correction check, source policy admitted |
| `OPENDART_COMPANY_OVERVIEW` / official response | `LEGAL_ENTITY_BRIDGE`, `LEGAL_NAME` | `DART_DISCLOSURE_FILER` | `SUPPORTING` | `AUTOMATED_OFFICIAL_PUBLIC` | Exact corp-code request and raw `jurir_no`/name facts; cannot impersonate the court registry |
| `OPENDART_CORP_CODE` or `OPENDART_COMPANY_OVERVIEW` / DART membership, `corp_cls`, `stock_code`, language/name field | `LEGAL_JURISDICTION` | any | `ZERO` | any | Never production-decisive for jurisdiction |
| each exact admitted KRX namespace / KOSPI/KOSDAQ/KONEX listing field, plus KRW or Korean-language name | `LEGAL_JURISDICTION` | any | `ZERO` | any | Listing/market/currency/language never establishes jurisdiction |
| exact individually admitted `US_STATE_REGISTRY_<STATE>` / verified official legal-entity record | `LEGAL_JURISDICTION`, `LEGAL_NAME` | `US_STATE_REGISTERED_LEGAL_ENTITY` | `DECISIVE` | approved official public response or `HUMAN_ASSISTED_VERIFIED_DOCUMENT` | Relevant formation-state registry, exact domestic formation/charter reference rather than foreign qualification, authenticity/access verification, and exact non-name-only bridge to SEC candidate |
| `SEC_EDGAR_ACCEPTED_FILING` / authoritative registrant metadata and accepted issuer filing | `ISSUER_REGULATORY_ID`, `REGISTRANT_ROLE` | `SEC_REGISTRANT` | `DECISIVE` | `AUTOMATED_OFFICIAL_PUBLIC` | Exact accepted accession and registrant CIK; candidate must be registrant, not login/agent |
| `SEC_EDGAR_ACCEPTED_FILING` / accepted legal-name/incorporation facts | `LEGAL_ENTITY_BRIDGE`, `LEGAL_NAME` | `SEC_REGISTRANT` | `SUPPORTING` | `AUTOMATED_OFFICIAL_PUBLIC` | May bridge/corroborate the state record; cannot replace the state registry for jurisdiction |
| `SEC_EDGAR_LOGIN_PROVENANCE` / accession-prefix, login or agent metadata | `SUBMISSION_PROVENANCE` | `SEC_LOGIN_CIK`, `SEC_FILING_AGENT` | `ZERO` | `PROVENANCE_ONLY` | Audit only; never issuer ID, candidate, jurisdiction, or registered-class authority |
| `GLEIF_LEI` / current official LEI record | `LEGAL_ENTITY_BRIDGE`, `LEGAL_NAME` | `LEGAL_ENTITY` | `SUPPORTING` | approved official public response | May reconcile exact registration-authority references; cannot replace a KR court or US state registry |
| `US_PRIMARY_EXCHANGE`, `TOSS_OPEN_API`, ticker/name/provider/listing fields | `LEGAL_JURISDICTION` | any | `ZERO` | discovery/provider lineage only | Never establishes legal jurisdiction or issuer regulatory ID |
| `FIXTURE_*`, `TEST_*`, synthetic documents/adapters, or any fixture-tainted descendant | every issuer-authority scope | any | `ZERO` | `TEST_ISOLATED_ONLY` | `production_authority_eligible=false` permanently |

#### 6.5.2 Admission algorithm

Before any application can be `APPLIED_DECISIVE` or `APPLIED_SUPPORTING`, the
server MUST atomically verify all of the following:

1. The runtime authority environment is `PRODUCTION_AUTHORITY`; a caller cannot
   set or override it.
2. The exact server-owned source namespace, document kind, subject role, scope,
   adapter, parser, and ingestion mode match one immutable policy row.
3. The policy is production eligible, its access/license requirements pass,
   and the exact locator/document reference/raw bytes are retained.
4. The proposed effective weight does not exceed the policy matrix ceiling.
5. Every source-lineage ancestor is production admitted. Fixture, test, or
   synthetic taint is permanent across copy, parse, import, and relabel steps.
6. The raw and normalized field values, source document hash, candidate
   application, and correction head all verify.

Failure yields `REJECTED_SOURCE_POLICY` or `REJECTED_UNUSABLE`, effective weight
`ZERO`, and production bundle membership `0`. The parser cannot submit a
different namespace to evade this check.

The production path explicitly rejects:

- every `SourceSystem.FIXTURE_*`, including current
  `FIXTURE_KR_REGULATOR`, `FIXTURE_US_REGULATOR`, and `FIXTURE_MARKET`;
- every `DataMode.FIXTURE`, `fixture://` locator, test-only adapter, synthetic
  source document, copied fixture payload, and manually relabelled descendant;
- Phase 1 synthetic issuer IDs `issuer_kr_synthetic` and
  `issuer_us_synthetic`, corp code `90000001`, issuer CIK `9999999999`, and
  manager-only fixture CIK `9999999998`; and
- any format-valid 8-digit corp code or 10-digit CIK lacking admitted original
  authority evidence and an exact evidence application.

Test-only inputs may later exercise parsers, rules, collisions, and approval
failure logic inside an isolated test repository. The test factory cannot call
the production bundle builder, cannot obtain a production source-policy row,
and cannot create a canonical issuer through the normal runtime path.

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
| `evidence_application_members` | sorted unique application ID/content-hash tuples; each application proves exactly which source fact was applied to which provider/issuer candidate |
| `required_scope_results` | sorted map of each required field-owned scope to `SATISFIED`, `MISSING`, `CONFLICT`, `STALE`, `UNSUPPORTED`, or `UNUSABLE`, with sorted structured reason codes |
| `legal_jurisdiction_result` | `ESTABLISHED`, `UNRESOLVED`, or `UNSUPPORTED_BY_CONTRACT` |
| `collision_scan_result` | `CLEAR` or `CONFLICT`, including sorted claim/candidate fingerprints |
| `decision_rule_version` | exact `issuer-authority-rules/0.1.0` |
| `evidence_application_set_hash` / `source_policy_set_hash` / `provider_lineage_set_hash` / `collision_scan_hash` | deterministic subhashes |
| `built_at` | aware UTC audit time, excluded from all semantic hashes |

The semantic payload includes candidate identity, exact sorted evidence-
application membership, every referenced application/evidence/policy content
hash, exact provider observation membership, rule version, required-scope
results and reason codes, legal-jurisdiction result, and conflict scan result.
It excludes retrieval observations and all clocks.

```text
authority_bundle_id =
  "authb_" + sha256(canonical_bundle_semantics).lowerhex
```

Changing membership, a relation head, a conflict result, candidate identity, or
rule version creates a new bundle. Refetching byte-identical evidence at a later
time does not.

### 7.2 Bundle immutability and approval snapshot

- Evidence-application membership is stored in an immutable join table, not a
  mutable JSON list alone. Direct bare-evidence membership is forbidden.
- Every membership row verifies the exact application, evidence, source-policy,
  candidate fingerprint, provider identity, scope, status, and content hashes.
- A `MISSING` scope is stored in the immutable bundle scope-result rows and
  never filled by a fake evidence/application row.
- Provider lineage references exact CP3-C1 observation rows, not only a symbol
  string or batch source.
- Bundle construction records identifier claims before any review-ready
  decision may be emitted.
- The production bundle builder accepts only applications whose complete
  lineage is `PRODUCTION_AUTHORITY`, source policy is production eligible, and
  status is permitted for that scope. It has no API for test factories or
  fixture-tainted evidence.
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
  jurisdiction established and representable by an `APPLIED_DECISIVE`
  application from the exact field-owning KR court or relevant US state
  registry policy, permitted source use, a clear global collision scan, current
  evidence within
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

### 9.1 Concrete local data-steward authentication trust root

The only approval trust root for this contract is a registered Windows
Hello-backed WebAuthn/passkey platform credential bound to the server-owned
`LOCAL_DATA_STEWARD` principal. Loopback access, process ownership, a Windows
login by itself, Codex/GPT, a CLI flag, an environment variable, a cookie, or a
caller assertion of identity/role is not approval authentication.

#### 9.1.1 Principal and credential enrollment

- The server creates a stable opaque `reviewer_principal_id` from at least 128
  CSPRNG bits during a dedicated local enrollment ceremony. It assigns the
  exact immutable role `LOCAL_DATA_STEWARD`; neither value is accepted from an
  HTTP, CLI, job, parser, or approval caller.
- First enrollment is enabled only while no steward credential exists and only
  by a server-created single-use bootstrap record under the Windows account
  that owns the local application data. The server reads and hashes that
  account SID from the OS security token; the browser cannot submit it.
- The enrollment ceremony uses WebAuthn `create` with
  `authenticatorAttachment=platform`, `residentKey=required`, and
  `userVerification=required`. A credential registered without positive user
  verification or without the platform-authenticator result is rejected.
- The server stores the public credential ID, canonical COSE public key,
  algorithm, authenticator AAGUID/attachment metadata, public-key fingerprint,
  credential-ID fingerprint, counter capability/current counter, RP ID,
  principal binding, registration policy version, and non-secret verification
  audit. The public-key fingerprint is SHA-256 of canonical COSE-key bytes.
- The Windows Hello/private credential and private signing key never leave the
  authenticator and are never stored by this repository, its DB, files, logs,
  fixtures, tests, QA documents, browser storage, or environment.
- Adding or replacing a credential after first enrollment requires a fresh
  assertion from an already active credential. If all credentials are lost,
  approval stays fail-closed; credential recovery is a separate explicitly
  authorized ceremony and cannot approve a pending decision.

Enrollment and credential lifecycle are append-only audit events. Credential
revocation or supersession does not delete the registered public-key history.
The enrollment bootstrap cannot approve, reject, revoke, or supersede an issuer
decision.

#### 9.1.2 Exact relying party and origin

The proposed repository-compatible approval ceremony uses:

```text
WebAuthn RP ID: localhost
Allowed approval origin: http://localhost:3000
Required clientDataJSON type: webauthn.get
Required crossOrigin: false
```

The repository already admits `http://localhost:3000` as an exact local
frontend origin. For an approval assertion, `http://127.0.0.1:3000`, another
port/scheme/host, an origin alias, a missing origin, and an unverified
`topOrigin` are rejected. Non-approval UI use of another existing loopback URL
does not make it an approval RP/origin. RP ID and allowed origin are fixed in
`issuer-steward-webauthn/0.1.0`, not configurable through an approval request.

#### 9.1.3 One-time challenge and exact semantic binding

For every requested `APPROVED`, `REJECTED`, `REVOKED`, or `SUPERSEDED`
disposition, the server loads the current immutable rows and creates a fresh
challenge. The challenge binding contains exactly:

- server-owned `reviewer_principal_id` and exact role;
- exact `issuer_decision_id` and `decision_content_hash`;
- exact `authority_bundle_id` and `bundle_content_hash`;
- exact requested disposition;
- predecessor approval/link and successor decision IDs when required;
- RP ID, allowed origin, and authentication-policy version; and
- server issue/expiry audit timestamps.

The server draws a new 32-byte nonce from the Windows/OS CSPRNG and computes:

```text
challenge_bytes = sha256(
  "issuer-approval-challenge/0.1.0" |
  random-32-byte-nonce |
  canonical-challenge-binding
)
```

The base64url challenge is one-time, expires exactly five minutes after
issuance, and is unusable after its first verification attempt. The immutable
challenge row stores its digest and server-loaded binding; a unique append-only
consumption row records the one terminal attempt. The nonce, run ID, database
row ID, and retrieval clock never enter an authority/bundle/decision/link
semantic ID.

A challenge for another decision, bundle, bundle hash, decision hash,
principal, predecessor, or disposition is rejected. Changing a reviewed row
after challenge issuance causes transaction-time hash/current-leaf validation
to reject the approval even when the signature itself is valid.

#### 9.1.4 Assertion verification and replay rejection

Before creating an authentication event, the server MUST verify all of the
following against server-owned state:

1. challenge exists, is unexpired, has no prior consumption row, and its exact
   binding matches the requested disposition and current decision/bundle;
2. credential ID is active, registered to the bound principal, and was enrolled
   under the approved Windows Hello platform policy;
3. `clientDataJSON.type` is `webauthn.get`, challenge bytes match exactly,
   origin is exactly `http://localhost:3000`, and `crossOrigin` is false;
4. authenticator `rpIdHash` equals SHA-256 of `localhost`, user-presence and
   user-verification flags are both set, and authenticator data is well formed;
5. assertion signature over the exact authenticator data and client-data hash
   verifies with the registered COSE public key and algorithm;
6. a supported positive signature counter strictly advances; counter rollback
   or cloned-credential indication rejects and review-locks the credential; and
7. the challenge consumption insert succeeds exactly once.

For an authenticator whose registered metadata explicitly reports no usable
signature counter, a zero counter is not treated as identity evidence; the
one-time random challenge, exact binding, signature, RP/origin, and user-
verification checks remain mandatory. Any element that is missing, malformed,
ambiguous, unsupported by the approved policy, or unverifiable fails closed.
An invalid attempt consumes the challenge and records only a safe failed audit,
so the same assertion cannot be retried.

#### 9.1.5 Reauthentication lifetime and stored audit

There is no reusable approval login or cached reauthentication lifetime. Every
human disposition requires a new Windows Hello assertion for one exact
challenge, and that assertion authorizes at most one approval-event insert.
Five minutes is only the maximum challenge issuance-to-consumption window; it
does not authorize another decision or disposition.

The immutable authentication audit stores only non-secret fields:

- server-owned principal ID and role;
- registered credential-ID/public-key fingerprints and authentication policy;
- challenge digest, decision/bundle IDs and expected content hashes,
  disposition, issue/expiry/consumption times;
- RP ID, exact origin, user-presence/user-verification outcomes;
- signature/counter verification outcomes and safe error code; and
- an opaque server-generated `authentication_event_id` for a successful
  assertion.

It stores no password, PIN, biometric template, private key, cookie, bearer
token, session secret, raw credential secret, authorization header, or private
authenticator material. The approval-event row references the successful
server-resolved authentication event. It does not trust a request field named
`reviewer_principal_id`, `reviewer_role`, `authentication_status`, or
`authentication_event_id`.

#### 9.1.6 Approval request authority boundary

The caller may request a challenge for a decision and disposition, but the
server loads and binds all principal, role, bundle, content-hash, predecessor,
and candidate values. The assertion submission contains only the opaque
challenge reference, strict WebAuthn assertion fields, structured reason code,
and review note. Caller-supplied principal, role, authenticated boolean,
candidate, evidence membership, or server authentication event is rejected as
an extra field.

This section is the complete B1 authentication/reauthentication contract. B1
does not implement enrollment, WebAuthn, an approval route, or any runtime
authentication code.

Every `IssuerApprovalEvent` stores the server-resolved principal and role,
successful `authentication_event_id`, authentication policy version,
credential public fingerprint, exact decision/bundle IDs and expected content
hashes, disposition, structured reason code, non-empty review-note digest,
predecessor/successor references when applicable, and authenticated/recorded UTC
audit times. None of those server-owned authentication facts may be populated
from free-form caller fields.

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
  issuer_decision_id | decision_content_hash |
  authority_bundle_id | bundle_content_hash |
  event_state |
  reviewer_principal_id | reviewer_role |
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
3. The issuer's actual legal jurisdiction is established by an admitted
   `KR_SUPREME_COURT_IROS` corporate-registry record and its official
   authenticity verification. The record's exact corporate registration
   reference must equal the raw `jurir_no` published for the same corp-code
   candidate in admitted OpenDART company-overview evidence, and the authority
   record must identify a Korean-law domestic legal entity rather than a
   foreign-company branch/registration. Only the court-registry application may
   be `APPLIED_DECISIVE` for `LEGAL_JURISDICTION`; OpenDART is supporting bridge
   evidence.
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

### 11.2 Permitted KR human-assisted registry ingestion

The Supreme Court/Internet Registry path is not approved for unattended
automatic promotion. A later implementation may admit its evidence only through
this exact `HUMAN_ASSISTED_VERIFIED_DOCUMENT` sequence:

1. Original official issued/downloaded registry document bytes enter a
   non-authoritative quarantine only. The server computes the exact raw hash
   and resolves the expected document kind/source policy; caller-supplied
   source labels or hashes are not authoritative and no evidence exists yet.
2. The server issues a fresh Windows Hello/WebAuthn operation challenge to the
   registered `LOCAL_DATA_STEWARD`, bound to
   `AUTHORITY_EVIDENCE_INGEST`, exact candidate/provider identity, exact source
   policy, expected document kind, and server-computed raw document hash. This is an
   ingestion authentication event, not issuer approval.
3. The steward authenticates the exact quarantined document and supplies only
   its official document/verification reference. A screenshot,
   image capture, copied name, search-result page, printed-to-PDF page, manually
   typed corporate registration number, or manually reconstructed payload is
   rejected.
4. The admitted adapter verifies the original document through an approved
   official verification mechanism: a verifiable official digital signature
   chain or an exact official document-verification result bound to the same
   document reference and raw hash. Merely reaching `iros.go.kr` is not
   verification.
5. The approved parser extracts the exact raw legal name, corporate
   registration reference, registry jurisdiction/legal-entity facts, document
   issuance/authority time fields, domestic-versus-foreign registration kind,
   and normalized values. The steward cannot replace an extracted value. A
   foreign-company/branch record cannot normalize to `Jurisdiction.KR`.
6. A separate OpenDART authority record under the exact corp code supplies its
   raw `jurir_no`; byte/format normalization must produce exact equality with
   the court-registry reference. Name agreement alone is insufficient.
7. Source-policy admission, access/license, current-correction, collision, and
   application checks all pass before the bundle can be built. The later final
   issuer disposition still requires a new, separately bound WebAuthn approval
   assertion under section 9.

If original-document authenticity, official verification, exact registration-
reference bridge, access/license permission, or an admitted adapter/parser is
unavailable, the exact result is:

```text
machine state = UNRESOLVED
reason code = jurisdiction-contract-required
READY_FOR_MANUAL_REVIEW = 0
canonical Issuer writes = 0
canonical Security writes = 0
ProviderIdentityMapping VERIFIED writes = 0
```

KRX, KOSPI/KOSDAQ/KONEX, OpenDART `corp_cls`/`stock_code`, provider market/name,
KRW, Korean-language name, and mere OpenDART disclosure membership cannot
change that result.

### 11.3 Foreign KRX issuer fail-closed matrix

| Actual issuer jurisdiction | Available authority | B result |
|---|---|---|
| `KR` | complete OpenDART + independent KR jurisdiction + unambiguous provider bridge | may reach manual review |
| `US` | complete SEC registrant path and independent US jurisdiction; DART may be supporting cross-listing evidence | use the US issuer anchor only; never coerce to KR |
| unsupported country | valid DART corp code and KRX/provider observations | `UNRESOLVED / jurisdiction-contract-required` |
| unknown or contradictory | any listing evidence | `UNRESOLVED`; review-ready/canonical writes `0` |

KOSPI/KOSDAQ/KONEX, KRX listing eligibility, Korean currency, `corp_cls`,
`stock_code`, provider market, Korean name, or a DART disclosure row never
supplies the missing legal jurisdiction.

### 11.4 KR rejection cases

- malformed, missing, synthetic, duplicate, or contradictory corp code;
- corp code found only in a fixture, search result, provider field, or unofficial
  crosswalk;
- a screenshot, copied/search-result name, manually typed registration number,
  unverified registry document, or a DART record presented as court authority;
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
4. Actual legal jurisdiction is established by an official legal-entity record
   from the issuer's relevant formation-state registry under an individually
   admitted exact `US_STATE_REGISTRY_<STATE>` policy. The state record is the
   decisive `LEGAL_JURISDICTION` fact. SEC registration, a CIK, a US exchange,
   provider market, USD, or a state-of-incorporation parser label cannot replace
   it.
5. Exact provider observation lineage bridges to issuer-reported accepted
   filing metadata without relying on a ticker/name convenience file alone.
   Class, exchange, and instrument final authority remain CP3-C2-C.
6. No contradictory CIK/entity claim, ticker-reuse ambiguity, provider
   collision/quarantine, later authoritative correction, or unavailable current
   check exists.
7. Current evidence passes repository freshness and latest-filing checks.

### 12.2 Permitted US state-registry authority path

Every US positive path requires both the field-owning state registry and
accepted SEC registrant evidence. The exact state is selected from authoritative
formation/incorporation evidence, never from exchange/provider geography. A
state registry is production eligible only after its own source namespace,
official locator/verification method, document kinds, access/license terms,
adapter, and parser are admitted in `AuthoritySourcePolicy`; a generic national
or wildcard state-registry adapter is forbidden.

The state path must provide an exact official legal-entity record with the
formation jurisdiction, entity/charter number, legal name, entity type/status,
authority times when supplied, official document/record reference, source
locator, and exact raw bytes/value hashes. It must be bridged to the SEC
registrant by an admitted authoritative cross-reference that includes the same
state-registry entity reference and the exact registrant candidate, or by
another explicitly admitted non-name-only identifier pair published in the
applicable official records. A foreign qualification, registered-agent entry,
or authority-to-do-business record in a US state does not prove US formation
jurisdiction. Accepted SEC registrant CIK/accession evidence is
always required as supporting regulatory/bridge evidence. SEC or GLEIF may
corroborate legal name, formation state, LEI, and registration-authority
reference, but neither may silently become the field-owning state registry.

If a state offers only a human-interactive record/document path, section 11.2's
human-assisted controls apply with operation `AUTHORITY_EVIDENCE_INGEST`, the
exact US state source policy, original official bytes, and official state
verification reference. Search-result pages, screenshots, copied names,
manually typed entity numbers, unofficial aggregators, and name-plus-state
matching are not an issuer bridge.

If no individually admitted, verifiable state-registry record and non-name-only
bridge are available, the exact result is `UNRESOLVED /
jurisdiction-contract-required`; `READY_FOR_MANUAL_REVIEW`, canonical Issuer,
canonical Security, and `ProviderIdentityMapping(VERIFIED)` writes are all `0`.
A syntactically valid CIK and accepted filing do not relax this rule.

### 12.3 Registrant and submission-provenance separation

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

### 12.4 Foreign private issuer and private/non-issuer limitations

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
- Source policies, principal/credential lifecycle, challenges/consumptions,
  authentication audits, evidence applications, and all authority ledger rows
  reject destructive rewrite/delete through repository policy and proposed
  database triggers. Only rebuildable head/current projections use guarded
  mutation.

### 14.2 Exact approval transaction

SQLite approval uses `BEGIN IMMEDIATE` and performs these steps in order:

1. Strictly reject caller-supplied principal, role, authentication status,
   authentication-event, candidate, or evidence fields. Load the immutable
   server-issued challenge, registered credential, decision, and bundle.
2. Verify the exact WebAuthn assertion, RP/origin, user-verification, signature,
   credential/principal binding, five-minute expiry, decision/bundle content
   hashes, and requested disposition under section 9. Atomically append the
   unique challenge-consumption and authentication-audit rows. A missing,
   expired, reused, cross-bound, invalid, or unverifiable assertion commits only
   its safe terminal consumption audit and returns with all authority writes
   zero.
3. Verify stored decision, bundle, evidence-application, evidence, source-policy,
   and membership content hashes.
4. Require the decision to be the unique current leaf and exactly
   `READY_FOR_MANUAL_REVIEW`.
5. Recompute evidence-relation heads, production source admission, every exact
   evidence application, global identifier claims, provider state, bundle
   membership, collision scan, latest revision, access/license disposition, and
   freshness under the approved rule version.
6. Require the challenge-bound expected decision and bundle hashes to match;
   never accept caller-supplied evidence, candidate, principal, role, or hash as
   authority.
7. Insert-or-verify the deterministic canonical issuer. An existing row must
   have the same deterministic ID, authority identifiers, jurisdiction, and
   semantic payload; otherwise fail closed.
8. Append the approval event and issuer-authority link.
9. Insert or compare-and-swap the link head using the expected prior head hash.
10. Assert canonical Security insert count `0`, verified provider-mapping insert
   or update count `0`, and provider/history update count `0`.
11. Commit atomically. On a post-authentication business-validation failure,
    preserve the one-time authentication consumption/audit, append a machine
    `REVIEW_REQUIRED` decision when applicable, and commit no issuer/approval/
    link/head write. Pre-existing evidence, applications, bundles, decisions,
    approvals, links, and provider history remain intact.

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
UNIQUE (approval_challenge_id)  -- one terminal challenge consumption
UNIQUE (authentication_event_id)
  WHERE authentication_event_id IS NOT NULL  -- one disposition use
UNIQUE (provider_security_identity_id)
  WHERE supersedes_link_id IS NULL
UNIQUE (supersedes_link_id) WHERE supersedes_link_id IS NOT NULL
```

Composite foreign keys bind each approval event to the exact
`(issuer_decision_id, authority_bundle_id)` pair and each link to its exact
decision, bundle, and event. Repository checks enforce same provider identity
and proposed issuer across those rows. Authentication composite keys bind the
successful authentication event to the exact principal, challenge, decision,
bundle, expected content hashes, and disposition; a cross-decision or cross-
bundle event cannot satisfy the FK/check set.

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
| `authority_source_policies` | immutable exact source/document/scope/role admission registry; PK policy ID, source namespace, maximum weight, ingestion mode, production eligibility and access/license requirements |
| `reviewer_principals` | server-created stable local steward principal; exact role, OS-owner SID hash and enrollment policy; no caller-owned identity field |
| `reviewer_webauthn_credentials` | registered credential ID, COSE public key, public fingerprints, RP/principal binding and non-secret authenticator metadata; no private credential material |
| `reviewer_webauthn_credential_events` | append-only register/revoke/supersede lifecycle for public credentials |
| `issuer_approval_challenges` | immutable CSPRNG challenge digest and exact principal/decision/bundle/hash/disposition/RP/origin binding with five-minute expiry |
| `issuer_approval_challenge_consumptions` | one append-only terminal attempt per challenge; unique challenge FK provides replay rejection |
| `reviewer_authentication_events` | append-only safe WebAuthn verification audit; successful row bound to exact challenge/principal/credential/decision/bundle/disposition |
| `authority_evidence` | immutable reusable source facts; PK `evidence_id`, unique semantic/provenance hashes, exact locator/document reference, raw document hash, raw and normalized claim values, source-policy FK |
| `authority_evidence_observations` | append-only retrieval/freshness audit for evidence; FK evidence, fetched UTC, exact raw/ref metadata; never a semantic bundle member |
| `authority_evidence_relations` | append-only `CORRECTS`/`REVOKES`/`SUPERSEDES` edges between evidence rows |
| `authority_evidence_applications` | immutable exact evidence→provider/candidate/scope evaluation with status, effective weight, sorted reasons, policy/rule/relation-head hashes |
| `authority_bundles` | immutable provider+issuer-candidate snapshot; PK bundle, FK provider identity, deterministic hashes and rule version |
| `authority_bundle_evidence_applications` | immutable bundle/application membership; composite PK plus deterministic ordinal and exact application/evidence/policy hashes; bare evidence membership forbidden |
| `authority_bundle_scope_results` | exact candidate/scope result and sorted reason rows, including explicit `MISSING`, `CONFLICT`, `STALE`, and `UNUSABLE` states |
| `authority_bundle_provider_observations` | exact bundle-to-CP3-C1 provider observation lineage; no symbol-only join |
| `authority_identifier_claims` | append-only normalized corp-code/registrant-CIK claims and candidate fingerprints; indexed but intentionally not first-writer unique |
| `issuer_decisions` | append-only linear machine-decision chain per bundle |
| `issuer_approval_events` | append-only authenticated-human disposition chain bound to exact decision/bundle |
| `issuer_approval_evidence_observations` | exact retrieval observations used by approval-time freshness/latest checks |
| `issuer_authority_links` | append-only provider-to-issuer link history with security state fixed to unresolved |
| `issuer_authority_link_heads` | rebuildable per-provider current leaf/state projection with CAS state hash |

All authority semantic primary keys are deterministic text IDs. Enrollment,
challenge, retrieval, and authentication audit identities may be CSPRNG-backed
non-semantic IDs and cannot enter evidence, bundle, decision, issuer, or link
semantic hashes. The stable server-owned principal does enter the approval-event
semantic identity because it identifies the human disposition author; its
generation time and OS/account metadata do not.

### 15.3 Required foreign keys and checks

- Every bundle provider ID references `provider_security_identities`.
- Every production evidence row references an immutable production-eligible
  source policy whose exact namespace/document/scope/role/weight combination
  matches. Fixture/test/synthetic lineage is constrained to effective weight
  zero and cannot be joined to a production bundle.
- Every evidence application composite-references the exact evidence/content
  hash, source policy, provider identity, proposed issuer, scope, status, and
  effective weight at or below the policy ceiling.
- Bundle membership references the exact application/content hash and verifies
  that application candidate/provider values equal the bundle values. Direct
  bare-evidence bundle membership does not exist.
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
- A successful reviewer-authentication row requires one registered active
  Windows Hello credential, exact RP/origin/user-verification/signature results,
  and the unique terminal challenge consumption. One authentication event may
  authorize at most one exact matching approval disposition.
- Challenge rows are server-bound to principal, decision, bundle, decision and
  bundle content hashes, disposition, RP/origin, issue/expiry, and policy. The
  consumption table has a unique challenge FK; expired or cross-bound use
  cannot satisfy approval checks.
- Approved/revoked/superseded link rows require an approval event;
  `REVIEW_REQUIRED` requires a machine decision trigger and no fake approval.
- Every B link has `security_resolution_state='UNRESOLVED'`.
- Validity intervals permit null and enforce ordering only when both endpoints
  are authority supplied.
- Payload JSON and relational columns must insert-or-verify each other; a
  mismatch is a typed contract conflict.

### 15.4 Append-only enforcement

The proposal includes `BEFORE UPDATE` and `BEFORE DELETE` fail-closed triggers
for source policies, reviewer principal/public-credential history, challenges,
challenge consumptions, authentication audits, evidence, observations,
relations, applications, bundle/scope membership, claims, decisions, approval
events, approval-observation membership, and link versions. The link-head
projection is the sole mutable authority table and must use a one-statement
conditional update on its expected `state_hash`.

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
PASS without executable coverage for at least the following exact scenarios.
Every write count is the count caused by that scenario, not a total historical
row count. A valid-approval row explicitly begins with no canonical issuer so
its expected issuer insert count is deterministic.

| ID | Scenario | Expected machine state | Canonical Issuer writes | Canonical Security writes | `ProviderIdentityMapping(VERIFIED)` writes | Provider identity/allocation rekeys | Human approval/disposition permitted | Required outcome |
|---|---|---|---:|---:|---:|---:|---|---|
| B1-ID-01 | Same semantic evidence, different retrieval/run/DB row IDs | `READY_FOR_MANUAL_REVIEW` | 0 | 0 | 0 | 0 | yes, only later with fresh WebAuthn | Identical evidence/application/bundle/decision semantic IDs; audit observations differ |
| B1-ID-02 | Same evidence applications in different input order | `READY_FOR_MANUAL_REVIEW` | 0 | 0 | 0 | 0 | yes, only later with fresh WebAuthn | Identical ordered bundle content and hash |
| B1-ID-03 | Same decision under different evaluation clocks | `READY_FOR_MANUAL_REVIEW` | 0 | 0 | 0 | 0 | yes, only later with fresh WebAuthn | Identical decision ID; audit times remain distinct |
| B1-PROV-01 | Raw document hash present but exact `raw_claim_value` omitted | `UNRESOLVED` | 0 | 0 | 0 | 0 | no | Contract rejection; document hash cannot substitute for the raw field fact |
| B1-PROV-02 | Same evidence is claimed decisively by two conflicting candidate fingerprints | `UNRESOLVED` | 0 | 0 | 0 | 0 | no | Two distinct immutable application IDs; evidence row remains reusable and both conflicting candidates are blocked |
| B1-SRC-01 | `SourceSystem.FIXTURE_*` or `DataMode.FIXTURE` carries a format-valid issuer ID | `UNRESOLVED` | 0 | 0 | 0 | 0 | no | `REJECTED_SOURCE_POLICY`, effective weight zero, production bundle membership zero |
| B1-SRC-02 | Fixture/test payload copied and manually relabelled `OPENDART` or `SEC_EDGAR` | `UNRESOLVED` | 0 | 0 | 0 | 0 | no | Immutable fixture taint survives relabel; normal production builder rejects it |
| B1-SRC-03 | Parser emits `authority_scope=LEGAL_JURISDICTION` for an unlisted source/scope pair | `UNRESOLVED` | 0 | 0 | 0 | 0 | no | Policy maximum zero; enum label is non-authoritative |
| B1-AUTO-01 | Automatic final promotion attempted on an otherwise complete bundle | `READY_FOR_MANUAL_REVIEW` | 0 | 0 | 0 | 0 | yes, but only a separate valid steward ceremony | Machine stops at review-ready; automatic final promotion zero |
| B1-KR-01 | Exact DART corp code + verified IROS record + exact `jurir_no` bridge + unambiguous provider lineage | `READY_FOR_MANUAL_REVIEW` | 0 | 0 | 0 | 0 | yes, fresh exact-bundle WebAuthn required | Court registry owns jurisdiction; no automatic issuer write |
| B1-KR-02 | Valid DART corp code but no verifiable approved court-registry path | `UNRESOLVED` (`jurisdiction-contract-required`) | 0 | 0 | 0 | 0 | no | Review-ready zero; DART cannot impersonate court registry |
| B1-KR-03 | KRX/provider/DART listing, KRW, or Korean name used as jurisdiction | `UNRESOLVED` | 0 | 0 | 0 | 0 | no | Application rejected with legal-jurisdiction weight zero |
| B1-KR-04 | KRX-listed foreign issuer with actual jurisdiction outside KR/US | `UNRESOLVED` (`jurisdiction-contract-required`) | 0 | 0 | 0 | 0 | no | No coercion to KR despite corp code/listing evidence |
| B1-IDF-01 | Fake/synthetic but format-valid 8-digit corp code promotion | `UNRESOLVED` | 0 | 0 | 0 | 0 | no | Fake/synthetic corp-code authority use zero |
| B1-US-01 | Exact accepted registrant CIK + accepted issuer filing + admitted relevant state-registry record + exact non-name-only bridge | `READY_FOR_MANUAL_REVIEW` | 0 | 0 | 0 | 0 | yes, fresh exact-bundle WebAuthn required | State registry owns jurisdiction; SEC owns registrant scope |
| B1-US-02 | Valid CIK or US exchange listing without admitted state-registry path | `UNRESOLVED` (`jurisdiction-contract-required`) | 0 | 0 | 0 | 0 | no | CIK/exchange cannot establish US legal jurisdiction |
| B1-US-03 | Registrant CIK A and accession/login/filing-agent CIK B, all other positive evidence complete | `READY_FOR_MANUAL_REVIEW` | 0 | 0 | 0 | 0 | yes, fresh exact-bundle WebAuthn required | Candidate is A; B remains zero-weight submission provenance |
| B1-US-04 | Registrant independently unresolved but accession-prefix/login CIK exists | `UNRESOLVED` | 0 | 0 | 0 | 0 | no | Login/accession/agent CIK cannot fill registrant scope |
| B1-US-05 | Foreign private issuer's actual jurisdiction is outside KR/US | `UNRESOLVED` (`jurisdiction-contract-required`) | 0 | 0 | 0 | 0 | no | SEC registration/US listing does not coerce jurisdiction |
| B1-IDF-02 | Fake/synthetic but format-valid 10-digit CIK promotion | `UNRESOLVED` | 0 | 0 | 0 | 0 | no | Fake/synthetic CIK authority use zero |
| B1-BRIDGE-01 | Provider name/ticker-only issuer candidate | `UNRESOLVED` | 0 | 0 | 0 | 0 | no | Name-only and symbol-only merge zero |
| B1-FRESH-01 | Otherwise complete current evidence exceeds 24-hour repository approval policy | `STALE` | 0 | 0 | 0 | 0 | no | Last-known evidence retained; fetched time is not authority time |
| B1-FRESH-02 | Required current authority/latest-correction check unavailable | `STALE` | 0 | 0 | 0 | 0 | no | Outage is not revocation and cannot be approved |
| B1-CONFLICT-01 | Contradictory current official issuer evidence | `UNRESOLVED` | 0 | 0 | 0 | 0 | no | No human conflict override; all facts retained |
| B1-COLL-01 | Two distinct candidates claim one current corp code | `UNRESOLVED` (existing approved link: `REVIEW_REQUIRED`) | 0 | 0 | 0 | 0 | no | Every affected candidate blocked; no first-writer winner |
| B1-COLL-02 | Two distinct candidates claim one current registrant CIK | `UNRESOLVED` (existing approved link: `REVIEW_REQUIRED`) | 0 | 0 | 0 | 0 | no | Every affected candidate blocked; no first-writer winner |
| B1-AUTH-01 | Approval request has no WebAuthn authentication | decision remains `READY_FOR_MANUAL_REVIEW` | 0 | 0 | 0 | 0 | no for this attempt | Reject before authority writes |
| B1-AUTH-02 | Caller supplies fake `reviewer_principal_id`, role, or authenticated flag | decision remains `READY_FOR_MANUAL_REVIEW` | 0 | 0 | 0 | 0 | no for this attempt | Strict extra-field rejection; server identity unchanged |
| B1-AUTH-03 | WebAuthn challenge expired after five minutes | decision remains `READY_FOR_MANUAL_REVIEW` | 0 | 0 | 0 | 0 | no for this attempt | Challenge terminally consumed/rejected; new challenge required |
| B1-AUTH-04 | Previously consumed challenge/assertion reused | decision remains `READY_FOR_MANUAL_REVIEW` | 0 | 0 | 0 | 0 | no for this attempt | Unique consumption rejects replay |
| B1-AUTH-05 | Challenge issued for another bundle/decision/hash/disposition | decision remains `READY_FOR_MANUAL_REVIEW` | 0 | 0 | 0 | 0 | no for this attempt | Cross-decision/cross-bundle binding rejection |
| B1-AUTH-06 | Assertion signature invalid | decision remains `READY_FOR_MANUAL_REVIEW` | 0 | 0 | 0 | 0 | no for this attempt | Failed safe audit only; challenge cannot be retried |
| B1-AUTH-07 | User-presence or user-verification flag absent | decision remains `READY_FOR_MANUAL_REVIEW` | 0 | 0 | 0 | 0 | no for this attempt | Fail closed even on loopback/registered credential ID |
| B1-AUTH-08 | Valid registered Windows Hello steward assertion for a new, absent issuer and exact current bundle | `READY_FOR_MANUAL_REVIEW` (frozen machine decision); link becomes `APPROVED` | 1 | 0 | 0 | 0 | yes; this exact disposition only | One canonical issuer insert-or-verify, one approval/link, no security/final mapping |
| B1-AUTH-09 | Authenticated human attempts to override pre-approval contradictory official evidence | `UNRESOLVED` | 0 | 0 | 0 | 0 | no | Valid authentication cannot create authority or bypass conflict |
| B1-CON-01 | Concurrent approve/reject where approved transaction is barrier-forced to commit first | `READY_FOR_MANUAL_REVIEW` (frozen decision) | 1 | 0 | 0 | 0 | one approved disposition only | Reject transaction loses with typed conflict; no mixed event/link rows |
| B1-CON-02 | Concurrent approve/reject where rejected transaction is barrier-forced to commit first | `READY_FOR_MANUAL_REVIEW` (frozen decision) | 0 | 0 | 0 | 0 | one rejected disposition only | Approval loses with typed conflict; no issuer/link row |
| B1-CON-03 | Concurrent successor link-head writes for the same expected head | `REVIEW_REQUIRED` | 0 | 0 | 0 | 0 | only the exact serialized successor ceremony | One CAS winner or exact idempotent duplicate; no fork/mixed head |
| B1-HIST-01 | Historical official correction after an approved link, corrected bundle now complete | `READY_FOR_MANUAL_REVIEW` for successor | 0 | 0 | 0 | 0 | yes, new `SUPERSEDED`/successor approval ceremony | Old evidence/application/bundle/decision/approval/link remains queryable |
| B1-HIST-02 | Authenticated revocation of an approved issuer link | `REVIEW_REQUIRED` before disposition; link becomes `REVOKED` | 0 | 0 | 0 | 0 | yes, `REVOKED` only with fresh bound challenge | Old approval/link remains; new revocation event/link appended |
| B1-REPLAY-01 | Deterministic replay with evidence/application input order changed | same as original (`READY_FOR_MANUAL_REVIEW` for complete input) | 0 | 0 | 0 | 0 | same eligibility as original; replay itself cannot approve | Ordered semantic dump and hashes byte-identical; clocks/audit rows excluded |
| B1-LINK-01 | New issuer approved while security remains unresolved | `READY_FOR_MANUAL_REVIEW` (frozen decision); link `APPROVED` | 1 | 0 | 0 | 0 | yes and required | `IssuerAuthorityLink.security_resolution_state=UNRESOLVED`; existing mapping unchanged |
| B1-LINK-02 | Approval request attempts provider identity/allocation/history rekey | `REVIEW_REQUIRED` | 0 | 0 | 0 | 0 | no | Hard rejection; every pre-existing provider ID/hash remains exact |
| B1-MIG-01 | Proposed 0005 upgrade/downgrade/re-upgrade on disposable DB | N/A — migration-only | 0 | 0 | 0 | 0 | no | `0001`–`0004` rows/hashes preserved; new constraints enforced |
| B1-MIG-02 | Proposed 0005 fails at a later table/index/trigger | N/A — migration-only | 0 | 0 | 0 | 0 | no | Revision remains 0004; prior schema/data/sentinel unchanged; retry succeeds |

The suite must also assert these exact global counters without synonyms or
weaker thresholds:

```text
automatic final promotion = 0
fake/synthetic corp_code = 0
fake/synthetic CIK = 0
name-only merge = 0
symbol-only merge = 0
jurisdiction inference from listing/provider fields = 0
login/accession/filing-agent CIK issuer-authority use = 0
canonical Security creation = 0
ProviderIdentityMapping VERIFIED = 0
provider identity/history rekeys = 0
evidence/decision/approval/link destructive rewrite/delete = 0
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
  "evidence_application_members": [
    {
      "evidence_application_id": "aeapp_<64-lowercase-hex>",
      "application_content_hash": "sha256:<64-lowercase-hex>",
      "evidence_id": "aev_<64-lowercase-hex>",
      "evidence_content_hash": "sha256:<64-lowercase-hex>",
      "authority_source_policy_id": "aspol_<64-lowercase-hex>",
      "authority_scope": "ISSUER_REGULATORY_ID",
      "application_status": "APPLIED_DECISIVE"
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
- CP3-C2-B1:
  `REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW`
- CP3-C2-B implementation: `NOT STARTED`
- Proposed `0005` file created/applied: `0`
- CP3-C2-C: `NOT STARTED`
- CP3-D: `NOT STARTED`
- Automatic progression: `PROHIBITED`

GPT independent re-review and explicit user approval are required before this
proposed contract or migration can become an accepted implementation contract.
ADR-014 remains `PROPOSED — AWAITING GPT INDEPENDENT RE-REVIEW`. Even a later
approval would not start CP3-C2-B implementation, CP3-C2-C, or CP3-D without
their separately required start authorization.
