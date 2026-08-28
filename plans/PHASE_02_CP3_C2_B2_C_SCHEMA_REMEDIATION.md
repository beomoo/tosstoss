# Phase 2 CP3-C2-B2-C Schema Contract Remediation

- Status:
  `APPROVED VIA ADR-015 AND ADR-016 / 0006 IMPLEMENTATION AUTHORIZED`
- Checkpoint state:
  `0006 SCHEMA IMPLEMENTATION IN PROGRESS — AWAITING IMPLEMENTATION AND INDEPENDENT REVIEW`
- Repository: `beomoo/tosstoss`
- Branch: `feature/phase-02-toss`
- Initial implementation-entry starting SHA:
  `60f2805d2390c91a026b3381877006be9000dedb`
- Independent-review remediation starting SHA:
  `fd0535fdd022f0171a63a83cb2861e924a92da64`
- Final-terminalization remediation starting SHA:
  `e016fc59973e5c81181e7cf20c1ebe3d7aada043`
- Independently reviewed and user-approved schema-contract SHA:
  `f73115ea1182e27259787460307a01b4c3874312`
- Implementation-gap amendment starting SHA:
  `f73115ea1182e27259787460307a01b4c3874312`
- Design date: `2026-08-28` (`Asia/Seoul`)
- Governing contracts: ADR-013 `ACCEPTED`, ADR-014 `ACCEPTED`,
  `plans/PHASE_02_CP3_C2_B1_RUNTIME_CONTRACT.md`
- Governing schema decision: ADR-015 `ACCEPTED` (`2026-08-28`)
- Narrow implementation amendment: ADR-016 `ACCEPTED` (`2026-08-28`)
- Runtime implementation: `0`
- Migration file creation/application: `0`
- Automatic progression: `PROHIBITED`

## 1. Purpose and terminal boundary

This document is the ADR-015/ADR-016-approved schema architecture for the
minimum additive ledger needed before CP3-C2-B2-C can faithfully implement
Windows Hello/WebAuthn steward enrollment and credential lifecycle
authorization. GPT independent review of SHA
`4104973d84307b80a236d9b737b2d29339b27153` returned P0 `0` / P1 `0`, and the
user explicitly accepted ADR-016 on `2026-08-28`.

The user separately authorized only implementation of migration `0006` under
this exact contract. Migrations `0001`–`0005` remain immutable. WebAuthn/runtime,
real enrollment, issuer disposition execution, canonical Issuer/Security,
`ProviderIdentityMapping(VERIFIED)`, issuer-link mutation and live authority/
Toss requests remain unauthorized.

The ADR-016 design gate is closed and the separately authorized `0006`
implementation is in progress. The implementation must not be declared PASS or
CLOSED before GPT independent review. This authorization does not resume B2-C
runtime work.

## 2. Confirmed gap and corrected non-gap

### 2.1 SG-01 — first-enrollment bootstrap

The accepted B1 contract requires a server-created, Windows-owner-SID-bound,
single-use first-enrollment bootstrap before any credential exists. Frozen
`0005` has the principal, public credential, and credential-event tables, but
no relational challenge/expiry/terminal-consumption record that exists before a
credential row.

`reviewer_principals.payload_json` cannot close the gap. The principal is
immutable, so the same row cannot acquire a terminal consumption state.
JSON-only state would not prove a unique challenge consumption, an expired or
failed terminal attempt, or exact linkage to the resulting credential.

### 2.2 SG-02 — credential-management reauthentication

Adding or replacing a credential must be authorized by a fresh assertion from
an already-active credential. Frozen `0005`
`reviewer_authentication_events` is intentionally and correctly bound to an
issuer decision, authority bundle, and one issuer disposition. Reusing it for
credential administration would falsify the audit meaning.

The new credential-management assertion must also participate in the same
append-only signature-counter history as issuer-approval assertions. Omitting
the assertion would create an unexplained counter gap at the next issuer
approval.

### 2.3 `SUPERSEDED` is not a schema blocker

No amendment is proposed for issuer-approval `SUPERSEDED`. Existing `0005` can
represent:

```text
old APPROVED link
  -> separately authenticated old SUPERSEDED link
  -> separately authenticated successor APPROVED link
  -> guarded final link-head CAS
```

Both assertions/events/link versions can be validated and appended inside one
`BEGIN IMMEDIATE` transaction. This proposal does not weaken or reinterpret
that lifecycle.

### 2.4 GPT independent review of the first proposal

GPT independently reviewed SHA
`fd0535fdd022f0171a63a83cb2861e924a92da64` and returned `CHANGES REQUIRED`,
P0 `0`, P1 `2`, and P2 `1` non-blocking because GitHub CI execution evidence
is absent. SG-01, SG-02, and additive Option A were accepted in principle.

This revision remediates, but does not self-close, the two new design findings:

- P1-SR-01: authenticated revocation of the final active credential is allowed
  and produces the exact empty active set. The resulting lockout is truthful
  fail-closed state, not a reason to invent recovery.
- P1-SR-02: the exact versioned credential-state preimage, empty-state
  derivation, active-member reconstruction and server/SQLite validation
  boundary are defined below. A mandatory deferred lifecycle-event-to-
  successful-outcome binding closes the event-without-CAS gap while retaining
  six additive tables.

GPT subsequently independently re-reviewed SHA
`e016fc59973e5c81181e7cf20c1ebe3d7aada043` and returned `CHANGES REQUIRED`,
P0 `0`, P1 `1`, and P2 `1` non-blocking because GitHub CI execution evidence
is absent. That re-review verified P1-SR-01 and P1-SR-02 `CLOSED` and identified
P1-SR-03: every operation-terminal challenge result must append the unique
operation outcome before the terminal result is returned.

The terminalization revision remediated, but did not self-close, P1-SR-03.
GPT then independently reviewed SHA
`f73115ea1182e27259787460307a01b4c3874312` and returned `PASS WITH CLOSEOUT
CONDITION`, P0 `0`, P1 `0`, and P2 `1` non-blocking because GitHub CI execution
evidence is absent. That review closed SG-01, SG-02, P1-SR-01, P1-SR-02 and
P1-SR-03. The user explicitly accepted ADR-015 on `2026-08-28`; the six-table
schema architecture is therefore approved.

### 2.5 IG-01 / IG-02 — implementation-discovered exact-binding gaps

During the separately authorized `0006` implementation attempt, Codex stopped
without changing files or creating `0006` because two exact SQLite bindings in
the approved prose were incomplete. GPT independently confirmed both gaps:

- IG-01: `authorization_kind` named bootstrap and registration tokens but did
  not name the exact tokens required for `SUPERSEDED` and `REVOKED` lifecycle
  authorizations.
- IG-02: the authorization and outcome child schemas required the approved
  eight-column operation FK but omitted three non-null child columns:
  `reviewer_role`, `principal_content_hash`, and `os_owner_sid_hash`.

ADR-016 proposes only the exact enum/matrix, copied trust columns, eight-column
FKs and corresponding hash-preimage coverage stated below. It does not weaken
the approved parent key, add a subset identity, change the six-table surface,
or authorize migration/runtime implementation.

## 3. Selected migration strategy

### 3.1 Decision

Select option **A: additive new bootstrap/credential-operation tables**, plus
additive indexes and insert-guard triggers on existing reviewer tables.

No existing table is rebuilt. No existing column is added, removed, renamed,
or reinterpreted.

| Option | Decision | Reason |
|---|---|---|
| A — additive tables and additive schema objects | **selected** | Preserves every `0005` row and issuer-approval FK while creating a separate, purpose-bound credential-operation ledger |
| B — rebuild selected `0005` tables | rejected | Expands migration risk and would mix credential administration into the already exact issuer-disposition contract |
| C — combination | rejected | A reverse mandatory association can be enforced with deferred companion FKs plus insert guards; table rebuild is not needed |

The design deliberately mirrors the challenge → terminal consumption →
authentication/audit pattern without generalizing issuer-approval tables.
Issuer approval and credential administration therefore cannot substitute for
one another.

The six-table surface is minimal for the required proofs:

- the operation row is the stable bootstrap/management intent and state-CAS
  parent;
- challenge and consumption must remain separate so an immutable issued
  challenge can have exactly one separately appended terminal attempt;
- authentication must remain separate from consumption because rejected and
  verified `webauthn.get` counter/signature facts share the consumption but are
  not credential lifecycle events;
- lifecycle authorization is a mandatory companion for the already frozen
  `0005` credential-event table;
- the outcome is the unique terminal operation/state-CAS fact required to
  serialize retries and later operations.

Merging any of these would either require mutating an issued row, hide
cryptographic authorization in JSON, or rebuild `0005`.

## 4. Future migration identity

The future, separately authorized migration contract is:

| Property | Exact proposal |
|---|---|
| Filename | `services/api/alembic/versions/0006_phase_02_cp3_c2_b2_c_reviewer_operations.py` |
| Revision | `0006_phase_02_cp3_c2_b2_c_reviewer_operations` |
| Down revision | `0005_phase_02_cp3_c2_b_issuer_authority` |
| Strategy | additive tables, indexes, and triggers only |
| `0001`–`0005` | byte-identical |
| Persistent application in this task | `0` |

The migration must pin and verify the SHA-256/blob hashes of `0001`–`0005`
before implementation. It must reject pre-existing object-name collisions and
clean up only objects created by a failed `0006` attempt.

## 5. Versioned contracts and canonical hashing

The proposed versions are:

| Contract | Version |
|---|---|
| Credential operation/bootstrap | `reviewer-credential-operation/0.1.0` |
| Operation challenge | `reviewer-credential-operation-challenge/0.1.0` |
| Terminal challenge consumption | `reviewer-credential-operation-consumption/0.1.0` |
| Credential-operation authentication | `reviewer-credential-operation-authentication/0.1.0` |
| Credential-event authorization | `reviewer-credential-event-authorization/0.1.0` |
| Credential-operation outcome | `reviewer-credential-operation-outcome/0.1.0` |
| Credential ownership/lifecycle state | `reviewer-credential-state/0.1.0` |

All content and binding hashes use canonical UTF-8/NFC JSON. Object keys are
sorted by unsigned lexicographic UTF-8 byte order after NFC; arrays preserve
order only where the contract assigns it. There is no insignificant whitespace,
and SHA-256 is rendered as `sha256:<lowerhex>`.

Operation, challenge, consumption, and authentication IDs are server-generated
opaque identifiers with at least 128 CSPRNG bits. They are audit identities and
never enter issuer evidence, bundle, decision, canonical issuer, or link
semantic IDs.

The server draws a fresh 32-byte OS-CSPRNG challenge nonce. Only the challenge
digest and binding hash are stored. The binding includes the operation,
principal, SID hash, purpose, current credential-state hash, RP/origin/policy,
issue time, and expiry. Raw private authenticator material is never stored.

Every new `VARCHAR(71)` hash column has an exact relational CHECK equivalent to
`length(value)=71 AND substr(value,1,7)='sha256:' AND
substr(value,8) NOT GLOB '*[^0-9a-f]*'`. Every new Boolean integer is checked
in `(0,1)`, every enum is closed to the values in this document, and every
nullable reference group is constrained all-null or all-non-null. These checks
are schema invariants; `payload_json` is never consulted to satisfy them.

### 5.1 Exact credential-state membership

Credential state represents ownership and current lifecycle membership for one
exact steward principal. It does not represent authentication-counter progress.
The server reconstructs it from all relevant rows; no caller supplies a member
list.

A credential is `ACTIVE` only when all of these conditions hold:

1. its immutable `reviewer_webauthn_credentials` row belongs to the exact
   principal tuple in the state object;
2. it has exactly one authorized lifecycle root whose event type is
   `REGISTERED` and whose predecessor is null;
3. every lifecycle successor is authorized, uses the same credential and
   principal, and forms one acyclic, fork-free chain under
   `supersedes_credential_event_id`; and
4. the unique current leaf is the `REGISTERED` root itself, meaning it has no
   `REVOKED` or `SUPERSEDED` successor.

A unique leaf of `REVOKED` or `SUPERSEDED` makes that credential inactive and
therefore excludes it from `active_credentials`. An orphan credential, missing
authorization companion, second root, fork, cycle, cross-principal or cross-
credential edge, missing leaf, multiple leaves, duplicate credential ID,
credential-ID fingerprint, public-key fingerprint, or member sort key makes the
entire state reconstruction invalid. The server returns a typed fail-closed
error; it never silently drops or deduplicates the bad row.

The frozen `0005` credential/event rows plus the proposed root/successor indexes,
same-subject chain guard and mandatory authorization companion are sufficient to
derive that set. No seventh membership/current-state table is proposed. A
stored projection would duplicate the authoritative append-only graph and
could hide an omitted member.

### 5.2 Exact canonical state-hash preimage

The logical preimage is exactly this object:

```json
{
  "active_credentials": [
    {
      "authenticator_attachment": "platform",
      "counter_capability": "SIGN_COUNT_SUPPORTED",
      "credential_contract_version": "issuer-steward-webauthn/0.1.0",
      "credential_id_fingerprint": "sha256:<64-lowerhex>",
      "lifecycle_leaf": {
        "credential_event_content_hash": "sha256:<64-lowerhex>",
        "credential_event_contract_version": "issuer-steward-webauthn/0.1.0",
        "credential_event_id": "<opaque-event-id>",
        "event_type": "REGISTERED"
      },
      "public_key_algorithm": "<approved-COSE-algorithm>",
      "public_key_fingerprint": "sha256:<64-lowerhex>",
      "registration_policy_version": "<server-policy-version>",
      "resident_key_required": true,
      "rp_id": "localhost",
      "user_verification_required": true,
      "webauthn_credential_id": "<canonical-base64url-id>"
    }
  ],
  "contract_version": "reviewer-credential-state/0.1.0",
  "os_owner_sid_hash": "sha256:<64-lowerhex>",
  "principal_content_hash": "sha256:<64-lowerhex>",
  "reviewer_principal_id": "<server-owned-principal-id>",
  "reviewer_role": "LOCAL_DATA_STEWARD"
}
```

The example counter capability token is replaced by the exact stored value,
`SIGN_COUNT_SUPPORTED` or `NO_USABLE_COUNTER`. Object keys are recursively
sorted by the same unsigned UTF-8 rule. Text is NFC-normalized. JSON Booleans
are literal `true`; there is no BOM, trailing newline or insignificant
whitespace. `webauthn_credential_id` is the RFC 4648 section 5 URL-safe base64
encoding of the credential-ID bytes with no `=` padding; padded, alternate or
non-canonical encodings are rejected rather than normalized. Active members are sorted
by the tuple
`(credential_id_fingerprint, webauthn_credential_id,
lifecycle_leaf.credential_event_id)` using unsigned lexicographic UTF-8 byte
ordering after NFC. Duplicate sort/identity keys are an error, never a
`DISTINCT` operation.

For future lifecycle events, `credential_event_content_hash` is the SHA-256 of
exactly this canonical JSON object (the predecessor value is a string or JSON
`null`):

```json
{
  "contract_version": "issuer-steward-webauthn/0.1.0",
  "event_type": "REGISTERED",
  "reviewer_principal_id": "<server-owned-principal-id>",
  "structured_reason_code": "<closed-server-reason-code>",
  "supersedes_credential_event_id": null,
  "webauthn_credential_id": "<canonical-unpadded-base64url-id>"
}
```

The example event type and predecessor are replaced by the exact stored values.
`credential_event_id`, `occurred_at`, `payload_json`, DB/run/request identity
and insertion order are excluded. The trusted server computes and insert-
verifies this semantic content hash; SQLite only checks its form and exact
copies.

`operation_content_hash` covers every relational operation column in section
7.1 from `contract_version` through `operation_policy_version`, including the
server-preallocated `initial_challenge_id` and `initial_challenge_purpose`, but
excluding `reviewer_credential_operation_id`, `operation_content_hash`,
`created_at` and `payload_json`. Including the initial challenge ID creates no
hash cycle because the challenge binding is computed only after this operation
hash and is not copied back into the operation.

`consumption_content_hash` covers every relational consumption column in
section 7.3 from `contract_version` through the terminal-outcome or
continuation companion fields, excluding only `challenge_consumption_id`,
`consumption_content_hash`, `consumed_at` and `payload_json`. It includes a
preallocated terminal outcome ID or continuation challenge ID, never an
`outcome_content_hash` or continuation challenge binding hash; therefore the
two deferred companion cycles are relational, not cryptographic hash cycles.

`outcome_content_hash` is likewise SHA-256 over one exact canonical object with
these keys and their exact relational values: `contract_version`,
`reviewer_credential_operation_id`, `operation_content_hash`,
`reviewer_principal_id`, `reviewer_role`, `principal_content_hash`,
`os_owner_sid_hash`, `operation_type`, `terminal_result`,
`terminal_consumption_id`, `terminal_consumption_content_hash`,
`terminal_challenge_purpose`, `terminal_challenge_result`,
`authorization_authentication_event_id`,
`authorization_authentication_content_hash`,
`authorization_authentication_result`, `registration_consumption_id`,
`registration_consumption_content_hash`, `registration_challenge_purpose`,
`registration_terminal_result`, `expected_credential_state_hash`,
`resulting_credential_state_hash`, and `safe_result_code`. Nullable reference
values are explicit JSON `null`. `credential_operation_outcome_id`,
`completed_at` and `payload_json` are excluded; the separately stored opaque
outcome ID is still part of the exact deferred FK binding.

`authorization_content_hash` covers every relational column listed in section
7.5 from `credential_event_id` through `resulting_credential_state_hash`,
including the exact outcome ID/hash/result and all checked nullable reference
fields. In particular, it includes `reviewer_role`, `principal_content_hash`,
and `os_owner_sid_hash`. It excludes only `authorization_content_hash`,
`recorded_at`, and `payload_json`. Nullable values are explicit JSON `null`;
the global canonical key-order/NFC rules apply.

The state digest is:

```text
credential_state_hash =
  "sha256:" + lowerhex(SHA256(UTF8(NFC(canonical_state_json))))
```

The empty active state is not a global constant. For principal `P`, it is the
same exact canonical object with `"active_credentials":[]` and all exact
principal/version/SID fields retained:

```text
empty_credential_state_hash(P) = sha256(canonical state for P with [])
```

No zero hash, null, magic literal or omitted array represents empty. For the
same principal, the pre-first-enrollment and post-final-revocation active-set
hashes are identical. Historical successful `REGISTERED` authorization and
operation rows—not the empty hash—permanently distinguish those states and
prevent `FIRST_ENROLLMENT` from restarting.

### 5.3 Explicit state-hash exclusions

The following never enter the credential-state preimage:

- `registration_sign_count`, `previous_sign_count`, `asserted_sign_count`, the
  reconstructed current counter, authentication-event IDs/hashes, and all
  issuer/credential-operation authentication history;
- `credential_content_hash`, because its wider preimage may contain the
  immutable registration counter or audit metadata;
- `registered_at`, `occurred_at`, operation/challenge issue/expiry/consumption/
  authentication/completion time, payload JSON, request/session/run/DB identity
  and insertion order;
- challenge nonce/digest, operation/challenge/consumption/outcome IDs,
  authenticator transports, AAGUID and canonical COSE bytes. The public-key
  fingerprint binds the key without duplicating those bytes.

`counter_capability` is included because it is immutable verification-policy
classification, but every counter value is excluded. Therefore a valid
signature-counter advancement alone cannot change the credential-state hash.

### 5.4 Trusted-server versus SQLite validation boundary

There is no approved SQLite SHA-256 UDF contract. No migration, trigger or
connection may assume a `sha256()` SQL function.

Under the same `BEGIN IMMEDIATE` writer transaction, trusted server code must:

1. load every principal credential, lifecycle event and authorization companion;
2. validate the exact active-member graph above;
3. build the canonical preimage and compute the current hash;
4. bind that hash at operation and challenge issuance;
5. recompute it before challenge consumption/authentication;
6. validate and freeze the exact server-owned proposed credential/event rows,
   allocate every opaque `credential_event_id`, and compute each exact event
   content hash;
7. project those exact event IDs/hashes onto the current graph in memory and
   compute the candidate post-state hash;
8. allocate the opaque outcome ID and compute the exact outcome and
   authorization content hashes from that frozen candidate tuple;
9. insert the deferred authorization companion(s), then any new public
   credential and lifecycle event rows;
10. reload the complete transaction-visible relational graph and independently
   recompute the post-state hash; and
11. require byte-for-byte equality with the candidate hash before inserting the
    exact outcome. Any missing/extra member or mismatch aborts the entire
    lifecycle write transaction.

SQLite enforces only relational facts: hash syntax, copied stored-hash equality,
FKs, unique root/successor/consumption/outcome constraints, same-principal and
same-credential edges, purpose/result/event patterns, mandatory authorization,
operation-chain continuity and append-only history. For a successor operation,
SQLite also requires its stored expected hash to equal its predecessor
outcome's stored resulting hash. The server independently recomputes both.
SQLite never calculates or attests the aggregate SHA-256.

## 6. Exact operation state model

`operation_type` is one of:

- `FIRST_ENROLLMENT`
- `ADD_CREDENTIAL`
- `REPLACE_CREDENTIAL`
- `REVOKE_CREDENTIAL`

There is no `RECOVER_CREDENTIAL`, `RESET_CREDENTIAL`, `FORCE`, or
`ADMIN_OVERRIDE` value. After any credential has ever been successfully
registered, `FIRST_ENROLLMENT` is permanently closed. If the active set later
becomes empty, issuer approval, `ADD_CREDENTIAL`, `REPLACE_CREDENTIAL` and
further `REVOKE_CREDENTIAL` all fail closed because no active credential can
authenticate. Empty does not mean never enrolled, and no recovery path appears.

`challenge_purpose` is one of:

- `REGISTRATION_CREATE` — exact `webauthn.create` ceremony
- `AUTHORIZATION_ASSERTION` — exact `webauthn.get` ceremony

The required step matrix is:

| Operation | Existing-credential assertion | Registration challenge | Credential lifecycle events |
|---|---:|---:|---|
| `FIRST_ENROLLMENT` | no | exactly one | one `REGISTERED` |
| `ADD_CREDENTIAL` | exactly one | exactly one after successful assertion | one `REGISTERED` |
| `REPLACE_CREDENTIAL` | exactly one | exactly one after successful assertion | one new `REGISTERED` and one old `SUPERSEDED` |
| `REVOKE_CREDENTIAL` | exactly one | none | one `REVOKED` |

A replace may use the target credential to authorize its own replacement, but
the new credential registration and old credential supersession commit
atomically. A currently active credential may also authenticate its own
`REVOKE_CREDENTIAL`, including when it is the final active credential. That
successful transition produces the exact principal-specific empty state.
Unauthenticated recovery remains outside the contract.

### 6.1 Terminal operation versus the sole resumable intermediate state

Every challenge consumption is classified relationally as exactly one of:

1. **operation-terminal** — every failure, and every successful final required
   step; it must be deferred-bound to exactly one operation outcome in the same
   transaction; or
2. **continuation-bearing** — only a successful `AUTHORIZATION_ASSERTION` for
   `ADD_CREDENTIAL` or `REPLACE_CREDENTIAL`; it must be deferred-bound to the
   exact verified authentication event and to the one immediately issued
   `REGISTRATION_CREATE` challenge for that operation in the same transaction.

There is no third state. In particular, a consumed failure cannot be a
resumable intermediate state. The continuation-bearing success is not an
indefinite authentication session: the registration challenge is issued under
the same `BEGIN IMMEDIATE`, has the ordinary maximum five-minute lifetime, and
can be consumed only once. The verified assertion can authorize only that one
operation and that one registration challenge.

The exact closed mapping is:

| Challenge terminal result | Operation outcome | Rule |
|---|---|---|
| `SUCCEEDED` | `SUCCEEDED` | required when this is `FIRST_ENROLLMENT` registration, `ADD_CREDENTIAL`/`REPLACE_CREDENTIAL` registration, or `REVOKE_CREDENTIAL` assertion and the complete lifecycle/CAS transition commits |
| `SUCCEEDED` | none yet | permitted only for the continuation-bearing add/replace assertion described above; the exact next registration challenge must commit in the same transaction |
| `EXPIRED` | `EXPIRED` | no authentication or lifecycle authority is created |
| `INVALID_SIGNATURE` | `REJECTED` | a rejected authentication audit is appended only when the attempt is attributable to an exact registered credential |
| `USER_PRESENCE_ABSENT` | `REJECTED` | same attributable-audit rule |
| `USER_VERIFICATION_ABSENT` | `REJECTED` | same attributable-audit rule |
| `INVALID_REGISTRATION` | `REJECTED` | no synthetic credential or lifecycle row is created |
| `BINDING_MISMATCH` | `FAILED_CLOSED` | caller binding cannot be trusted |
| `ORIGIN_RP_MISMATCH` | `FAILED_CLOSED` | origin/RP trust boundary failed |
| `COUNTER_REJECTED` | `FAILED_CLOSED` | rollback, equality, gap, fork, or inconsistent counter history |
| `REPLAY_REJECTED` | `FAILED_CLOSED` | the challenge or credential history is not reusable |
| `FAILED_CLOSED` | `FAILED_CLOSED` | all other closed, enumerated terminal failures |

`safe_result_code` refines the closed result without changing it. No parser,
caller, payload JSON, or implementation branch may invent an unlisted mapping.
Every non-`SUCCEEDED` challenge result is operation-terminal even when no
authentication event can safely be attributed.

For every failed outcome:

- credential lifecycle event and lifecycle authorization counts are both zero;
- the trusted server reloads the full lifecycle graph and requires
  `resulting_credential_state_hash == expected_credential_state_hash`;
- the outcome identifies the exact terminal consumption ID/content hash;
- no public credential, synthetic credential, state transition, recovery, or
  reset row is created; and
- the outcome commits before the typed failure is returned.

If an add/replace authorization assertion has already produced a valid
`VERIFIED` authentication event and its registration attempt later fails, that
authentication event and its signature-counter advancement remain immutable.
The failed outcome names both the earlier verified event and the exact failed
registration consumption, while credential ownership state remains unchanged.
A successor operation reconstructs counter state including that verified
event.

### 6.2 Successor and first-enrollment retry contract

A retry after any terminal failure is a new successor operation. It references
the failed predecessor operation, and its trusted-server-computed
`expected_credential_state_hash` must equal the predecessor outcome's
`resulting_credential_state_hash` byte-for-byte.

A failed `FIRST_ENROLLMENT` may have a successor `FIRST_ENROLLMENT` only when no
credential has ever been successfully registered for that principal. It uses
the same exact principal-specific empty state but a fresh operation ID, nonce,
challenge and expiry. After any historical successful registration,
`FIRST_ENROLLMENT` remains permanently prohibited, including after the final
active credential is revoked.

## 7. Proposed tables

All six tables below are append-only and receive `BEFORE UPDATE` and
`BEFORE DELETE` abort triggers.

### 7.1 `reviewer_credential_operations`

This is the immutable operation intent. A `FIRST_ENROLLMENT` row is the
server-created bootstrap identity.

| Column | Type/nullability | Invariant proved |
|---|---|---|
| `reviewer_credential_operation_id` | `VARCHAR(128) NOT NULL PK` | one opaque server-created operation identity |
| `contract_version` | `VARCHAR(64) NOT NULL` | exact operation contract |
| `operation_content_hash` | `VARCHAR(71) NOT NULL UNIQUE` | immutable relational binding cannot be silently changed |
| `reviewer_principal_id` | `VARCHAR(128) NOT NULL` | server-owned steward |
| `reviewer_role` | `VARCHAR(32) NOT NULL` | fixed `LOCAL_DATA_STEWARD` |
| `principal_content_hash` | `VARCHAR(71) NOT NULL` | exact immutable principal version |
| `os_owner_sid_hash` | `VARCHAR(71) NOT NULL` | exact server-resolved Windows owner binding; no raw SID |
| `operation_type` | `VARCHAR(32) NOT NULL` | exact permitted lifecycle action |
| `target_webauthn_credential_id` | `VARCHAR(512) NULL` | exact existing credential for replace/revoke only |
| `target_credential_id_fingerprint` | `VARCHAR(71) NULL` | prevents ID-only target ambiguity |
| `expected_credential_state_hash` | `VARCHAR(71) NOT NULL` | trusted-server-computed `reviewer-credential-state/0.1.0` pre-state used as CAS input |
| `initial_challenge_id` | `VARCHAR(128) NOT NULL` | exact first required challenge allocated with the operation |
| `initial_challenge_purpose` | `VARCHAR(32) NOT NULL` | `REGISTRATION_CREATE` for first enrollment; `AUTHORIZATION_ASSERTION` otherwise |
| `predecessor_operation_id` | `VARCHAR(128) NULL` | one linear operation history per principal |
| `operation_policy_version` | `VARCHAR(64) NOT NULL` | server-owned policy, not a request field |
| `created_at` | `VARCHAR(35) NOT NULL` | aware UTC audit time, never authority-effective time |
| `payload_json` | `TEXT NOT NULL` | duplicate audit payload that must insert-or-verify relational columns |

Required FKs/checks:

- Composite FK
  `(reviewer_principal_id, reviewer_role, principal_content_hash,
  os_owner_sid_hash)` → exact principal-owner unique key.
- Composite self-FK `(predecessor_operation_id, reviewer_principal_id)` →
  `(operation_id, reviewer_principal_id)` rejects cross-principal grafts.
- Composite target FK
  `(target_webauthn_credential_id, reviewer_principal_id,
  target_credential_id_fingerprint)` → exact registered credential.
- A circular `DEFERRABLE INITIALLY DEFERRED` composite FK binds
  `(initial_challenge_id, operation_id, principal_id, operation_type,
  initial_challenge_purpose)` to the exact initial challenge. The challenge
  independently binds back to the exact operation content hash. The server
  allocates the challenge ID before hashing the operation; the operation
  content preimage includes that opaque ID and purpose, but never a challenge
  binding hash, so there is no hash cycle.
- `reviewer_role='LOCAL_DATA_STEWARD'`.
- Operation enum is exact.
- `FIRST_ENROLLMENT` and `ADD_CREDENTIAL` require both target columns null;
  `REPLACE_CREDENTIAL` and `REVOKE_CREDENTIAL` require both non-null.
- A root operation must be `FIRST_ENROLLMENT`.
- Operation and initial challenge are inserted in one issuance transaction;
  the deferred FK makes an operation without that challenge uncommittable.

### 7.2 `reviewer_credential_operation_challenges`

This table stores both first/new-credential registration challenges and
existing-credential authorization challenges. Its purpose enum prevents
issuer-disposition reuse.

| Column | Type/nullability | Invariant proved |
|---|---|---|
| `reviewer_credential_operation_challenge_id` | `VARCHAR(128) NOT NULL PK` | one server-issued challenge |
| `contract_version` | `VARCHAR(64) NOT NULL` | exact challenge contract |
| `challenge_digest` | `VARCHAR(71) NOT NULL UNIQUE` | raw challenge need not be persisted |
| `challenge_binding_hash` | `VARCHAR(71) NOT NULL UNIQUE` | tamper-evident exact binding |
| `challenge_nonce_length` | `INTEGER NOT NULL` | must equal 32 bytes |
| `reviewer_credential_operation_id` | `VARCHAR(128) NOT NULL` | exact operation |
| `operation_content_hash` | `VARCHAR(71) NOT NULL` | exact immutable operation version |
| `reviewer_principal_id` | `VARCHAR(128) NOT NULL` | bound steward |
| `reviewer_role` | `VARCHAR(32) NOT NULL` | fixed role |
| `principal_content_hash` | `VARCHAR(71) NOT NULL` | exact principal |
| `os_owner_sid_hash` | `VARCHAR(71) NOT NULL` | exact OS-owner binding |
| `operation_type` | `VARCHAR(32) NOT NULL` | cannot be relabelled after issue |
| `challenge_purpose` | `VARCHAR(32) NOT NULL` | create versus get, never issuer approval |
| `expected_credential_state_hash` | `VARCHAR(71) NOT NULL` | exact operation pre-state copied from the server-computed binding and recomputed by the server at consumption |
| `target_webauthn_credential_id` | `VARCHAR(512) NULL` | exact replace/revoke target copied from operation |
| `target_credential_id_fingerprint` | `VARCHAR(71) NULL` | exact target fingerprint |
| `prerequisite_authentication_event_id` | `VARCHAR(128) NULL` | successful existing-credential assertion required before add/replace registration |
| `prerequisite_authentication_content_hash` | `VARCHAR(71) NULL` | binds the exact immutable prerequisite assertion, not only its row ID |
| `prerequisite_authentication_result` | `VARCHAR(16) NULL` | when present, fixed to `VERIFIED` |
| `rp_id` | `VARCHAR(255) NOT NULL` | fixed `localhost` |
| `allowed_origin` | `VARCHAR(255) NOT NULL` | fixed `http://localhost:3000` |
| `client_data_type` | `VARCHAR(32) NOT NULL` | `webauthn.create` or `webauthn.get` from purpose |
| `user_verification_required` | `INTEGER NOT NULL` | fixed 1 |
| `platform_attachment_required` | `INTEGER NULL` | fixed 1 for registration, null for assertion |
| `resident_key_required` | `INTEGER NULL` | fixed 1 for registration, null for assertion |
| `authentication_policy_version` | `VARCHAR(64) NOT NULL` | exact server policy |
| `issued_at` | `VARCHAR(35) NOT NULL` | aware UTC audit |
| `expires_at` | `VARCHAR(35) NOT NULL` | finite expiry, no caller clock |
| `payload_json` | `TEXT NOT NULL` | duplicate safe audit only |

Required FKs/checks:

- Composite FK to the exact operation copies the non-null operation identity,
  content hash, principal, role, principal hash, SID, operation type and
  expected state. The insert guard compares the nullable target pair with
  SQLite null-safe `IS`; including nullable target columns in the FK would
  incorrectly disable the whole FK whenever the target is absent.
- A `DEFERRABLE INITIALLY DEFERRED` prerequisite composite FK points only to a `VERIFIED`
  `reviewer_credential_operation_authentication_events` row for the same
  operation and principal, matching its authentication content hash.
- The three prerequisite columns are either all null or all non-null.
- `challenge_nonce_length=32`, exact RP/origin, and UV required.
- `expires_at>issued_at` and
  `julianday(expires_at)<=julianday(issued_at,'+5 minutes')`.
- Purpose/client type and platform/resident-key checks are exact.
- `FIRST_ENROLLMENT` permits only `REGISTRATION_CREATE` with no prerequisite.
- `ADD_CREDENTIAL`/`REPLACE_CREDENTIAL` permit one
  `AUTHORIZATION_ASSERTION` without a prerequisite and one later
  `REGISTRATION_CREATE` with a verified prerequisite.
- `REVOKE_CREDENTIAL` permits only `AUTHORIZATION_ASSERTION`.

### 7.3 `reviewer_credential_operation_challenge_consumptions`

Exactly one row terminally consumes a challenge. Failed verification consumes
the challenge and remains immutable.

| Column | Type/nullability | Invariant proved |
|---|---|---|
| `challenge_consumption_id` | `VARCHAR(128) NOT NULL PK` | immutable attempt identity |
| `contract_version` | `VARCHAR(64) NOT NULL` | exact consumption contract |
| `reviewer_credential_operation_challenge_id` | `VARCHAR(128) NOT NULL UNIQUE` | at most one terminal attempt |
| `reviewer_credential_operation_id` | `VARCHAR(128) NOT NULL` | exact operation |
| `reviewer_principal_id` | `VARCHAR(128) NOT NULL` | exact principal |
| `operation_type` | `VARCHAR(32) NOT NULL` | exact action |
| `challenge_purpose` | `VARCHAR(32) NOT NULL` | exact create/get purpose |
| `challenge_binding_hash` | `VARCHAR(71) NOT NULL` | exact immutable challenge binding |
| `terminal_result` | `VARCHAR(32) NOT NULL` | safe terminal outcome |
| `safe_result_code` | `VARCHAR(128) NOT NULL` | non-secret typed reason |
| `client_data_type_verified` | `INTEGER NOT NULL` | exact browser ceremony type checked |
| `challenge_verified` | `INTEGER NOT NULL` | submitted challenge matched digest/binding |
| `origin_verified` | `INTEGER NOT NULL` | exact origin checked |
| `cross_origin_false_verified` | `INTEGER NOT NULL` | cross-origin use rejected |
| `rp_id_hash_verified` | `INTEGER NOT NULL` | exact localhost RP hash checked |
| `user_presence_verified` | `INTEGER NOT NULL` | UP audit |
| `user_verification_verified` | `INTEGER NOT NULL` | UV audit |
| `platform_authenticator_verified` | `INTEGER NULL` | required for successful registration |
| `resident_key_verified` | `INTEGER NULL` | required for successful registration |
| `public_key_material_verified` | `INTEGER NULL` | successful registration produced supported public key |
| `registered_webauthn_credential_id` | `VARCHAR(512) NULL` | new public credential on registration success only |
| `registered_credential_content_hash` | `VARCHAR(71) NULL` | exact immutable public-credential row authorized by registration |
| `registered_credential_id_fingerprint` | `VARCHAR(71) NULL` | exact new credential |
| `registered_public_key_fingerprint` | `VARCHAR(71) NULL` | exact canonical public key |
| `registered_rp_id` | `VARCHAR(255) NULL` | exact RP copied into the public credential row |
| `registered_counter_capability` | `VARCHAR(32) NULL` | exact supported/no-counter classification |
| `registered_sign_count` | `INTEGER NULL` | immutable registration counter |
| `terminal_operation_outcome_id` | `VARCHAR(128) NULL` | preallocated exact outcome for every operation-terminal consumption |
| `terminal_operation_outcome_result` | `VARCHAR(16) NULL` | exact closed mapping from section 6.1 |
| `outcome_expected_credential_state_hash` | `VARCHAR(71) NULL` | exact operation pre-state copied into the terminal outcome |
| `outcome_resulting_credential_state_hash` | `VARCHAR(71) NULL` | exact terminal post-state; equals expected on every failure |
| `continuation_challenge_id` | `VARCHAR(128) NULL` | sole nonterminal continuation, allocated for successful add/replace assertion |
| `continuation_challenge_purpose` | `VARCHAR(32) NULL` | when present, fixed to `REGISTRATION_CREATE` |
| `consumption_content_hash` | `VARCHAR(71) NOT NULL UNIQUE` | immutable complete safe audit |
| `consumed_at` | `VARCHAR(35) NOT NULL` | aware UTC terminal time |
| `payload_json` | `TEXT NOT NULL` | no raw attestation or secret |

Required FKs/checks:

- Composite FK to the exact challenge proves
  challenge/operation/principal/type/purpose/binding hash.
- The optional new-credential composite FK to
  `reviewer_webauthn_credentials` is `DEFERRABLE INITIALLY DEFERRED`, allowing
  the proof row to be inserted before the guarded credential row in one
  transaction. It binds credential ID/content hash, principal, credential and
  public-key fingerprints, RP, and counter capability. The insert guard also
  compares nullable `registration_sign_count` with SQLite `IS`.
- The four terminal-outcome companion columns are all null or all non-null.
  When non-null, a circular `DEFERRABLE INITIALLY DEFERRED` composite FK points
  to the exact operation outcome tuple: preallocated outcome ID, operation,
  this consumption ID, mapped outcome result, and both state hashes. The
  outcome binds back to this consumption's content hash and terminal challenge
  result. `consumption_content_hash` includes the opaque preallocated outcome
  ID/result/state copies, but not `outcome_content_hash`, avoiding a hash
  cycle.
- The two continuation columns are all null or all non-null. When non-null, a
  `DEFERRABLE INITIALLY DEFERRED` composite FK points to the exact
  `REGISTRATION_CREATE` challenge for the same operation and principal.
  `consumption_content_hash` includes only its preallocated challenge ID and
  purpose, not the later challenge binding hash, avoiding a hash cycle.
- Exactly one companion group is non-null. Every operation-terminal
  consumption uses the outcome group. Only a successful
  `AUTHORIZATION_ASSERTION` for `ADD_CREDENTIAL`/`REPLACE_CREDENTIAL` uses the
  continuation group.
- Terminal enum:
  `SUCCEEDED|EXPIRED|BINDING_MISMATCH|ORIGIN_RP_MISMATCH|
  USER_PRESENCE_ABSENT|USER_VERIFICATION_ABSENT|INVALID_REGISTRATION|INVALID_SIGNATURE|
  COUNTER_REJECTED|REPLAY_REJECTED|FAILED_CLOSED`.
- All verification flags are 0/1.
- `SUCCEEDED` requires `consumed_at < expires_at` and all common checks; the
  challenge is expired at the exact expiry instant.
- Successful `REGISTRATION_CREATE` additionally requires platform, resident
  key, public-key verification and all registered-credential fields. The
  registration count alone may be null, and only for `NO_USABLE_COUNTER`.
- Successful `AUTHORIZATION_ASSERTION` requires registered-new-credential
  fields null; signature/counter details live in the authentication-event row.
- Any non-registration success or failed consumption requires the entire
  registered-credential field group null. This prevents partially populated
  failure rows from masquerading as registration proof.
- `EXPIRED` requires `consumed_at >= expires_at`. Every other failure is terminal
  and cannot be retried because the challenge FK is unique. Every failure also
  requires the exact terminal-outcome companion; a consumed failed challenge
  without its operation outcome cannot commit.

### 7.4 `reviewer_credential_operation_authentication_events`

This is the append-only `webauthn.get` audit for credential administration. It
contains no issuer decision, bundle, disposition, or issuer-approval challenge
column.

| Column | Type/nullability | Invariant proved |
|---|---|---|
| `credential_operation_authentication_event_id` | `VARCHAR(128) NOT NULL PK` | exact authentication audit |
| `contract_version` | `VARCHAR(64) NOT NULL` | exact operation-auth contract |
| `reviewer_credential_operation_challenge_id` | `VARCHAR(128) NOT NULL` | assertion challenge only |
| `challenge_binding_hash` | `VARCHAR(71) NOT NULL` | exact immutable assertion-challenge binding |
| `challenge_consumption_id` | `VARCHAR(128) NOT NULL UNIQUE` | one audit per terminal consumption |
| `challenge_consumption_content_hash` | `VARCHAR(71) NOT NULL` | exact immutable terminal attempt |
| `challenge_purpose` | `VARCHAR(32) NOT NULL` | fixed to `AUTHORIZATION_ASSERTION` |
| `challenge_terminal_result` | `VARCHAR(32) NOT NULL` | must agree with verified/rejected authentication result |
| `reviewer_credential_operation_id` | `VARCHAR(128) NOT NULL` | exact operation |
| `operation_content_hash` | `VARCHAR(71) NOT NULL` | immutable operation |
| `operation_type` | `VARCHAR(32) NOT NULL` | never issuer disposition |
| `expected_credential_state_hash` | `VARCHAR(71) NOT NULL` | exact operation pre-state copied relationally; trusted server independently recomputes it before authorization |
| `reviewer_principal_id` | `VARCHAR(128) NOT NULL` | exact steward |
| `reviewer_role` | `VARCHAR(32) NOT NULL` | fixed role |
| `principal_content_hash` | `VARCHAR(71) NOT NULL` | exact principal version |
| `os_owner_sid_hash` | `VARCHAR(71) NOT NULL` | exact local owner context |
| `authorizing_webauthn_credential_id` | `VARCHAR(512) NOT NULL` | credential that signed |
| `credential_id_fingerprint` | `VARCHAR(71) NOT NULL` | exact credential |
| `public_key_fingerprint` | `VARCHAR(71) NOT NULL` | exact stored public key |
| `authentication_result` | `VARCHAR(16) NOT NULL` | `VERIFIED` or `REJECTED` |
| `authentication_policy_version` | `VARCHAR(64) NOT NULL` | server-owned policy |
| `rp_id` | `VARCHAR(255) NOT NULL` | fixed localhost |
| `exact_origin` | `VARCHAR(255) NOT NULL` | fixed frontend origin |
| `user_presence_verified` | `INTEGER NOT NULL` | UP result |
| `user_verification_verified` | `INTEGER NOT NULL` | UV result |
| `origin_verified` | `INTEGER NOT NULL` | exact origin result |
| `rp_id_hash_verified` | `INTEGER NOT NULL` | exact RP result |
| `signature_verified` | `INTEGER NOT NULL` | COSE signature result |
| `counter_capability` | `VARCHAR(32) NOT NULL` | exact stored capability |
| `previous_sign_count` | `INTEGER NULL` | reconstructed prior counter |
| `asserted_sign_count` | `INTEGER NULL` | authenticator assertion counter |
| `counter_verified` | `INTEGER NOT NULL` | linear-history verification result |
| `replay_rejected` | `INTEGER NOT NULL` | one-time replay protection result |
| `safe_result_code` | `VARCHAR(128) NOT NULL` | non-secret typed result |
| `authentication_content_hash` | `VARCHAR(71) NOT NULL UNIQUE` | immutable audit |
| `authenticated_at` | `VARCHAR(35) NOT NULL` | aware UTC audit time |
| `payload_json` | `TEXT NOT NULL` | safe duplicate audit only |

Required FKs/checks:

- Composite FKs bind the exact `AUTHORIZATION_ASSERTION` challenge and exact
  terminal consumption by their binding/content hashes, operation, principal,
  purpose and terminal result.
- Composite credential FK binds the authorizing credential to the same
  principal, fingerprints, RP, and counter capability.
- The operation enum excludes `FIRST_ENROLLMENT`.
- Exact role/RP/origin, result enum, boolean and counter-capability checks mirror
  the accepted issuer-authentication contract.
- A `VERIFIED` event requires UP, UV, origin, RP hash, signature, counter, and
  replay checks all true, `challenge_terminal_result='SUCCEEDED'`, and an exact
  successful assertion consumption. A `REJECTED` event cannot point to a
  `SUCCEEDED` consumption.
- Supported counters require non-negative prior/asserted values and strict
  advancement. No-counter credentials require null/null and never fabricate
  zero.

### 7.5 `reviewer_webauthn_credential_event_authorizations`

This mandatory companion row proves which bootstrap or successful
credential-operation authentication authorized each existing `0005`
credential lifecycle event.

| Column | Type/nullability | Invariant proved |
|---|---|---|
| `credential_event_id` | `VARCHAR(128) NOT NULL PK` | every lifecycle event has at most one authorization |
| `contract_version` | `VARCHAR(64) NOT NULL` | exact authorization contract |
| `credential_event_content_hash` | `VARCHAR(71) NOT NULL` | exact immutable lifecycle transition, including its predecessor relation |
| `webauthn_credential_id` | `VARCHAR(512) NOT NULL` | exact affected public credential |
| `webauthn_credential_content_hash` | `VARCHAR(71) NOT NULL` | exact immutable public-credential payload affected by the transition |
| `reviewer_principal_id` | `VARCHAR(128) NOT NULL` | exact steward |
| `reviewer_role` | `VARCHAR(32) NOT NULL` | copied server-owned operation role; fixed to `LOCAL_DATA_STEWARD` |
| `principal_content_hash` | `VARCHAR(71) NOT NULL` | copied exact immutable principal version |
| `os_owner_sid_hash` | `VARCHAR(71) NOT NULL` | copied exact server-resolved Windows owner binding |
| `event_type` | `VARCHAR(16) NOT NULL` | `REGISTERED|REVOKED|SUPERSEDED` |
| `reviewer_credential_operation_id` | `VARCHAR(128) NOT NULL` | exact operation |
| `operation_content_hash` | `VARCHAR(71) NOT NULL` | exact immutable operation version |
| `operation_type` | `VARCHAR(32) NOT NULL` | exact lifecycle intent |
| `authorization_kind` | `VARCHAR(32) NOT NULL` | exact closed enum: `BOOTSTRAP_REGISTRATION|AUTHORIZED_REGISTRATION|AUTHORIZED_SUPERSESSION|AUTHORIZED_REVOCATION` |
| `registration_consumption_id` | `VARCHAR(128) NULL` | exact successful create ceremony |
| `registration_consumption_content_hash` | `VARCHAR(71) NULL` | exact immutable registration terminal attempt |
| `registration_challenge_purpose` | `VARCHAR(32) NULL` | when present, fixed to `REGISTRATION_CREATE` |
| `registration_terminal_result` | `VARCHAR(32) NULL` | when present, fixed to `SUCCEEDED` |
| `credential_operation_authentication_event_id` | `VARCHAR(128) NULL` | exact successful existing-credential assertion |
| `credential_operation_authentication_content_hash` | `VARCHAR(71) NULL` | exact immutable authorizing assertion |
| `credential_operation_authentication_result` | `VARCHAR(16) NULL` | when present, fixed to `VERIFIED` |
| `credential_operation_outcome_id` | `VARCHAR(128) NOT NULL` | exact successful operation whose atomic CAS includes this lifecycle event |
| `credential_operation_outcome_content_hash` | `VARCHAR(71) NOT NULL` | immutable successful outcome version |
| `credential_operation_outcome_result` | `VARCHAR(16) NOT NULL` | fixed to `SUCCEEDED`; a failed operation cannot authorize lifecycle state |
| `expected_credential_state_hash` | `VARCHAR(71) NOT NULL` | exact server-computed pre-state copied from operation and outcome |
| `resulting_credential_state_hash` | `VARCHAR(71) NOT NULL` | exact server-computed post-state copied from the successful outcome |
| `authorization_content_hash` | `VARCHAR(71) NOT NULL UNIQUE` | immutable exact linkage |
| `recorded_at` | `VARCHAR(35) NOT NULL` | aware UTC audit |
| `payload_json` | `TEXT NOT NULL` | duplicate safe audit only |

Required FKs/checks:

- A `DEFERRABLE INITIALLY DEFERRED` composite FK points to the exact existing
  credential event tuple
  `(event_id, event_content_hash, credential_id, principal_id, event_type)`.
- A separate exact credential FK binds credential ID/content hash and is
  `DEFERRABLE INITIALLY DEFERRED`, so a registration authorization companion
  may precede the guarded new credential in the same transaction. The event's
  principal and operation principal must equal the credential principal under
  the insert guard; frozen `0005` cannot be trusted to prove that cross-table
  equality by its two independent single-column FKs alone.
- The exact ordered child tuple
  `(reviewer_credential_operation_id, operation_content_hash,
  reviewer_principal_id, reviewer_role, principal_content_hash,
  os_owner_sid_hash, operation_type, expected_credential_state_hash)` has a
  `DEFERRABLE INITIALLY DEFERRED` composite FK to
  `uq_reviewer_credential_operations_exact_binding` in precisely that order.
  No weaker subset operation identity is created.
- `reviewer_role` is checked equal to `LOCAL_DATA_STEWARD`.
  `principal_content_hash` and `os_owner_sid_hash` are each checked as exactly
  `sha256:` followed by 64 lowercase hexadecimal characters. These copies are
  server-owned facts and never caller authority.
- Registration consumption FK can reference only a `SUCCEEDED`
  `REGISTRATION_CREATE` row for the same operation/principal and the same
  affected credential.
- Authentication FK can reference only a `VERIFIED` operation-authentication
  row for the same operation/principal.
- A `DEFERRABLE INITIALLY DEFERRED` composite FK binds the authorization to the
  exact `SUCCEEDED` operation outcome by outcome ID/content hash, operation ID/
  content hash, principal, role, principal content hash, OS-owner SID hash,
  terminal result, expected state and resulting state. This makes operation,
  outcome and authorization copies of all three trust fields relationally
  identical and makes a lifecycle event and its CAS result commit together. Its
  exact ordered child tuple is
  `(credential_operation_outcome_id,
  credential_operation_outcome_content_hash,
  reviewer_credential_operation_id, operation_content_hash,
  reviewer_principal_id, reviewer_role, principal_content_hash,
  os_owner_sid_hash, credential_operation_outcome_result,
  expected_credential_state_hash, resulting_credential_state_hash)` and it
  references `uq_reviewer_credential_operation_outcomes_exact_success` in the
  exact parent order listed in section 7.7.
- The closed operation/event/authorization matrix is exact:
  - `FIRST_ENROLLMENT + REGISTERED -> BOOTSTRAP_REGISTRATION` with successful
    registration consumption and a null authentication event;
  - `ADD_CREDENTIAL + REGISTERED -> AUTHORIZED_REGISTRATION` with both the
    successful assertion and registration;
  - `REPLACE_CREDENTIAL + REGISTERED -> AUTHORIZED_REGISTRATION` with both the
    successful assertion and registration;
  - `REPLACE_CREDENTIAL + SUPERSEDED -> AUTHORIZED_SUPERSESSION` with the
    successful assertion; and
  - `REVOKE_CREDENTIAL + REVOKED -> AUTHORIZED_REVOCATION` with the successful
    assertion.
- Every other `operation_type` / `event_type` / `authorization_kind`
  combination is rejected by the proposed CHECK/insert guard. There is no
  generic `AUTHORIZED_LIFECYCLE` fallback, free-form token, or `payload_json`
  authority.
- No FK targets `reviewer_authentication_events` or
  `issuer_approval_challenges`; issuer and credential-operation assertions are
  not substitutable.
- Each optional authorization reference is an all-null or all-non-null column
  group. Constants (`REGISTRATION_CREATE`, `SUCCEEDED`, `VERIFIED`) are stored
  as checked relational columns so an FK never depends on a partial index or
  JSON predicate.

Although this subsection precedes the outcome table for readability, the
future migration must create the two mutually commit-bound tables in an order
supported by SQLite and create all deferred FKs/guards before use. All six
tables and both sides of the deferred relationship must exist before any
credential ceremony can run.

### 7.6 `reviewer_credential_operation_outcomes`

This is the unique immutable terminal operation result and credential-state
CAS output. Every operation-terminal challenge consumption—successful or
failed—must be mutually deferred-bound to exactly one row here before the
server returns the terminal result. The only consumed challenge without an
outcome is the continuation-bearing successful add/replace assertion from
section 6.1, which is instead atomically bound to its next registration
challenge.

| Column | Type/nullability | Invariant proved |
|---|---|---|
| `credential_operation_outcome_id` | `VARCHAR(128) NOT NULL PK` | terminal audit identity |
| `contract_version` | `VARCHAR(64) NOT NULL` | exact outcome contract |
| `outcome_content_hash` | `VARCHAR(71) NOT NULL UNIQUE` | immutable result |
| `reviewer_credential_operation_id` | `VARCHAR(128) NOT NULL UNIQUE` | exactly one terminal outcome per operation |
| `operation_content_hash` | `VARCHAR(71) NOT NULL` | exact operation |
| `reviewer_principal_id` | `VARCHAR(128) NOT NULL` | exact steward |
| `reviewer_role` | `VARCHAR(32) NOT NULL` | copied server-owned operation role; fixed to `LOCAL_DATA_STEWARD` |
| `principal_content_hash` | `VARCHAR(71) NOT NULL` | copied exact immutable principal version |
| `os_owner_sid_hash` | `VARCHAR(71) NOT NULL` | copied exact server-resolved Windows owner binding |
| `operation_type` | `VARCHAR(32) NOT NULL` | exact lifecycle action |
| `terminal_result` | `VARCHAR(16) NOT NULL` | `SUCCEEDED|REJECTED|EXPIRED|FAILED_CLOSED` |
| `terminal_consumption_id` | `VARCHAR(128) NOT NULL` | exact challenge attempt ending the operation |
| `terminal_consumption_content_hash` | `VARCHAR(71) NOT NULL` | exact immutable terminal challenge attempt |
| `terminal_challenge_purpose` | `VARCHAR(32) NOT NULL` | identifies which operation step terminated |
| `terminal_challenge_result` | `VARCHAR(32) NOT NULL` | exact result of that challenge consumption |
| `authorization_authentication_event_id` | `VARCHAR(128) NULL` | exact verified prerequisite or attributable rejected assertion, when applicable |
| `authorization_authentication_content_hash` | `VARCHAR(71) NULL` | exact immutable assertion audit |
| `authorization_authentication_result` | `VARCHAR(16) NULL` | exact `VERIFIED` or `REJECTED` audit result |
| `registration_consumption_id` | `VARCHAR(128) NULL` | exact terminal registration attempt for first/add/replace when registration is reached |
| `registration_consumption_content_hash` | `VARCHAR(71) NULL` | exact immutable registration attempt |
| `registration_challenge_purpose` | `VARCHAR(32) NULL` | when present, fixed to `REGISTRATION_CREATE` |
| `registration_terminal_result` | `VARCHAR(32) NULL` | exact success/failure result of that registration consumption |
| `expected_credential_state_hash` | `VARCHAR(71) NOT NULL` | exact trusted-server-computed `reviewer-credential-state/0.1.0` pre-state |
| `resulting_credential_state_hash` | `VARCHAR(71) NOT NULL` | exact trusted-server-computed post-state, including the principal-specific empty state after final revoke |
| `safe_result_code` | `VARCHAR(128) NOT NULL` | non-secret terminal reason |
| `completed_at` | `VARCHAR(35) NOT NULL` | aware UTC audit |
| `payload_json` | `TEXT NOT NULL` | duplicate safe audit only |

Required FKs/checks:

- The exact ordered child tuple
  `(reviewer_credential_operation_id, operation_content_hash,
  reviewer_principal_id, reviewer_role, principal_content_hash,
  os_owner_sid_hash, operation_type, expected_credential_state_hash)` has a
  `DEFERRABLE INITIALLY DEFERRED` composite FK to
  `uq_reviewer_credential_operations_exact_binding` in precisely that order.
  No weaker subset operation identity is created.
- `reviewer_role` is checked equal to `LOCAL_DATA_STEWARD`.
  `principal_content_hash` and `os_owner_sid_hash` are each checked as exactly
  `sha256:` followed by 64 lowercase hexadecimal characters. These copies are
  server-owned facts and never caller authority.
- Terminal consumption must belong to that operation and match its exact
  purpose, terminal result and content hash.
- Optional authentication and registration references are composite-bound to
  that same operation and exact stored result.
- Each optional reference group is all null or all non-null, so SQLite's
  nullable-composite-FK exemption cannot turn a partial reference into proof.
- The reference matrix is exact: successful non-first operations require a
  `VERIFIED` authentication; an attributable assertion failure may reference
  its `REJECTED` audit; add/replace registration-stage success or failure
  retains the earlier `VERIFIED` authorization; and expired or otherwise
  unattributable failures have a null authentication group. A registration
  group is required whenever `REGISTRATION_CREATE` is the terminal step and
  must identify the same row as `terminal_consumption_id`; it is null when an
  authorization assertion terminated the operation.
- The terminal challenge/result pair must follow the closed section 6.1
  mapping. A failed outcome requires no credential lifecycle event or
  lifecycle authorization rows and preserves the pre-state as the resulting
  state.
- Every outcome is reverse-bound from its exact terminal consumption through a
  deferred composite FK. An outcome whose consumption does not name it, or a
  terminal consumption whose outcome is absent, cannot commit.
- A successful outcome is accepted only after the required exact credential
  event authorization rows exist, each is pre-bound to that exact deferred
  successful outcome tuple, and all relational event-pattern rules pass. The
  trusted server—not the insert guard—reconstructs the transaction-visible
  active set and computes `resulting_credential_state_hash` immediately before
  outcome insertion.
- `FIRST_ENROLLMENT`, `ADD_CREDENTIAL`, `REPLACE_CREDENTIAL` and
  `REVOKE_CREDENTIAL` successes all change membership and therefore require a
  resulting hash different from the expected hash. A successful final revoke
  is valid and uses the exact empty-state hash from section 5.2.

### 7.7 Exact composite-FK parent keys

SQLite requires every composite parent key to match a primary key or one exact
non-partial UNIQUE key. The future migration must create the following named
parent keys before creating dependent tables or guards; a merely similar index
is not sufficient.

| Parent key | Exact ordered columns | Used by / invariant |
|---|---|---|
| `uq_reviewer_principals_exact_owner_binding` | `reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash` | operations bind the exact server-owned steward and hashed OS owner |
| `uq_reviewer_credentials_exact_target` | `webauthn_credential_id, reviewer_principal_id, credential_id_fingerprint` | replace/revoke target cannot cross principals or credential fingerprints |
| `uq_reviewer_credentials_exact_content` | `webauthn_credential_id, credential_content_hash` | lifecycle authorization binds the exact immutable public credential row |
| `uq_reviewer_credentials_exact_registration` | `webauthn_credential_id, credential_content_hash, reviewer_principal_id, credential_id_fingerprint, public_key_fingerprint, rp_id, counter_capability` | successful create consumption authorizes the exact immutable public credential; nullable registration count is checked null-safely by trigger |
| `uq_reviewer_credential_events_exact_authorization` | `credential_event_id, credential_event_content_hash, webauthn_credential_id, reviewer_principal_id, event_type` | deferred companion FK names the exact lifecycle event rather than only its ID |
| `uq_reviewer_credential_operations_exact_binding` | `reviewer_credential_operation_id, operation_content_hash, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, operation_type, expected_credential_state_hash` | challenge/authorization/outcome children copy every non-null operation authority field |
| `uq_reviewer_credential_operations_exact_subject` | `reviewer_credential_operation_id, reviewer_principal_id` | self-FK rejects a predecessor from another steward |
| `uq_reviewer_credential_operation_challenges_exact_operation_step` | `reviewer_credential_operation_challenge_id, reviewer_credential_operation_id, reviewer_principal_id, operation_type, challenge_purpose` | deferred initial/continuation FKs prove the exact operation step without introducing a content-hash cycle |
| `uq_reviewer_credential_operation_challenges_exact_binding` | `reviewer_credential_operation_challenge_id, reviewer_credential_operation_id, reviewer_principal_id, operation_type, challenge_purpose, challenge_binding_hash` | consumption/authentication names the exact immutable ceremony |
| `uq_reviewer_credential_operation_consumptions_exact_terminal` | `challenge_consumption_id, reviewer_credential_operation_id, reviewer_principal_id, challenge_purpose, terminal_result, consumption_content_hash` | authentication/authorization/outcome binds the exact terminal attempt and result; the consumption row itself already binds its unique challenge |
| `uq_reviewer_credential_operation_consumptions_exact_registration` | `challenge_consumption_id, reviewer_credential_operation_id, reviewer_principal_id, challenge_purpose, terminal_result, registered_webauthn_credential_id, registered_credential_content_hash, consumption_content_hash` | lifecycle authorization proves that the successful registration produced the same affected credential |
| `uq_reviewer_credential_operation_authentication_exact_result` | `credential_operation_authentication_event_id, authentication_content_hash, reviewer_credential_operation_id, reviewer_principal_id, authentication_result` | prerequisite/lifecycle references require exact `VERIFIED`; terminal outcomes can bind the exact stored `VERIFIED` or attributable `REJECTED` result |
| `uq_reviewer_credential_operation_outcomes_exact_terminal` | `credential_operation_outcome_id, reviewer_credential_operation_id, reviewer_principal_id, terminal_result, terminal_consumption_id, expected_credential_state_hash, resulting_credential_state_hash` | a consumption deferred-binds its preallocated exact terminal result/state without introducing an outcome-hash cycle |
| `uq_reviewer_credential_operation_outcomes_exact_success` | `credential_operation_outcome_id, outcome_content_hash, reviewer_credential_operation_id, operation_content_hash, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, terminal_result, expected_credential_state_hash, resulting_credential_state_hash` | deferred lifecycle authorization binds the exact successful CAS result and identical operation trust tuple; checked copied result is `SUCCEEDED` |

The FK tuples use those exact column orders. Nullable target columns are
verified by null-safe insert guards, not placed in a composite FK. Optional
reference groups carry all of their ID/hash/purpose/result columns together and
are constrained to be either entirely null or entirely non-null.

## 8. Proposed indexes and the invariant each proves

| Index | Target | Invariant |
|---|---|---|
| `uq_reviewer_principals_active_local_steward` | `reviewer_principals(reviewer_role) WHERE principal_state='ACTIVE'` | at most one active `LOCAL_DATA_STEWARD` principal |
| `uq_reviewer_principals_exact_owner_binding` | exact tuple in section 7.7 | enables exact composite SID-bound FK |
| `uq_reviewer_credentials_exact_target` | exact tuple in section 7.7 | enables replace/revoke target FK |
| `uq_reviewer_credentials_exact_content` | exact tuple in section 7.7 | enables exact lifecycle-authorization credential FK |
| `uq_reviewer_credentials_exact_registration` | exact tuple in section 7.7 | enables exact deferred registration-proof FK |
| `uq_reviewer_credential_events_exact_authorization` | exact tuple in section 7.7 | enables exact deferred lifecycle-authorization FK |
| `uq_reviewer_credential_events_root` | credential ID where predecessor is null | one registration root per credential |
| `uq_reviewer_credential_operations_exact_binding` | exact tuple in section 7.7 | enables exact challenge/outcome operation FKs |
| `uq_reviewer_credential_operations_exact_subject` | exact tuple in section 7.7 | enables same-principal predecessor FK |
| `uq_reviewer_credential_operations_root` | principal where predecessor is null | one first-enrollment root per steward |
| `uq_reviewer_credential_operations_successor` | predecessor operation where non-null | one linear operation child; concurrent forks fail |
| `uq_reviewer_credential_operation_challenges_exact_operation_step` | exact tuple in section 7.7 | enables deferred operation-initial and consumption-continuation FKs |
| `uq_reviewer_credential_operation_challenges_exact_binding` | exact tuple in section 7.7 | enables exact consumption/authentication challenge FKs |
| `uq_reviewer_credential_operation_challenge_step` | operation ID/challenge purpose | at most one create and one get challenge per operation |
| `ix_reviewer_credential_operation_challenge_expiry` | principal/expiry | exact unconsumed-expiry lookup |
| `uq_reviewer_credential_operation_consumptions_exact_terminal` | exact tuple in section 7.7 | enables result-qualified authentication/authorization/outcome FKs |
| `uq_reviewer_credential_operation_consumptions_exact_registration` | exact tuple in section 7.7 | binds a successful create result to the lifecycle event's exact credential |
| `uq_reviewer_credential_operation_authentication_exact_result` | exact tuple in section 7.7 | enables result-qualified prerequisite/authorization/outcome FKs |
| `uq_reviewer_credential_operation_outcomes_exact_terminal` | exact tuple in section 7.7 | makes every operation-terminal consumption and outcome mutually commit-bound |
| `uq_reviewer_credential_operation_outcomes_exact_success` | exact tuple in section 7.7 | enables deferred event-authorization binding to the exact successful CAS outcome |
| `uq_reviewer_credential_event_authorization_step` | operation ID/event type | one required lifecycle event of each type |
| `ix_reviewer_authentication_counter_chain` | existing issuer auth credential/result/prior/asserted | deterministic cross-ledger counter reconstruction |
| `ix_reviewer_credential_operation_counter_chain` | operation auth credential/result/prior/asserted | deterministic cross-ledger counter reconstruction |

Existing `uq_reviewer_webauthn_credential_events_supersedes` remains unchanged
and continues to prevent two successor lifecycle events from sharing one
predecessor.

## 9. Proposed triggers and the invariant each proves

### 9.1 Append-only triggers

Each of the six new tables receives:

- `trg_<table>_append_only_update`
- `trg_<table>_append_only_delete`

Each raises `ABORT`. There is no mutable operation, challenge, consumption,
authentication, authorization, outcome, or current-counter row.

### 9.2 Insert guards

| Trigger | Invariant |
|---|---|
| `trg_reviewer_credential_operations_insert_guard` | exact active principal/SID; root/retry rules; predecessor is unique current terminal leaf; successor's stored expected hash equals the predecessor outcome's stored resulting hash; first enrollment only before any successful registration; non-first operations require an active credential; initial challenge ID/purpose follow the exact operation matrix. The deferred initial-challenge FK makes an orphan operation uncommittable. Trusted server separately recomputes the state hash |
| `trg_reviewer_credential_operation_challenges_insert_guard` | operation has no outcome; challenge step is valid for operation; challenge copies the operation's stored expected hash; the initial challenge satisfies the operation's reverse deferred FK; add/replace registration challenge has an exact verified prerequisite and is the sole continuation named by the successful assertion consumption. Trusted server separately proves that pre-state is current |
| `trg_reviewer_credential_operation_consumptions_insert_guard` | challenge is current/unconsumed; server clock and expiry map to the exact section 6.1 result; success verification matrix is complete; failure still consumes; exactly one deferred companion is selected: terminal outcome for every operation-terminal result, or the unique next registration challenge for only a successful add/replace assertion |
| `trg_reviewer_webauthn_credentials_requires_registration_proof` | every future public credential insert has both a pre-inserted successful exact deferred registration consumption and an exact pending `REGISTERED` authorization companion for the same operation/principal/ID/fingerprints/counter metadata; a consumption alone cannot create trusted credential state |
| `trg_reviewer_webauthn_credential_events_requires_authorization` | every future lifecycle event has a pre-inserted exact deferred authorization companion |
| `trg_reviewer_webauthn_credential_events_chain_guard` | `REGISTERED` is the only root; successor uses the same credential/principal; `REVOKED`/`SUPERSEDED` are terminal; cross-credential chain grafts fail |
| `trg_reviewer_credential_operation_authentication_active_guard` | the authorizing credential belongs to the same principal and has exactly one valid current `REGISTERED` lifecycle leaf at verification; target and copied stored-state binding remain exact; a verified add/replace assertion is bound through the consumption to exactly one immediately issued registration challenge. It does not assert aggregate SHA-256 |
| `trg_reviewer_credential_operation_outcomes_insert_guard` | terminal challenge result maps to the closed operation result; the exact terminal consumption reverse-names this outcome; success has the exact relational event/authorization pattern and every companion names this exact successful outcome; failure has no lifecycle event/authorization writes and preserves the stored pre-state; incomplete replace fails; authenticated final revoke and its empty active set are permitted. Trusted server computes/revalidates both hashes |
| `trg_reviewer_authentication_events_credential_active_guard` | every future issuer-approval authentication event uses a same-principal credential whose complete authorized lifecycle has one current `REGISTERED` leaf; a revoked/superseded credential cannot authenticate issuer approval after final or partial revoke |
| `trg_reviewer_authentication_events_counter_union_guard` | an issuer-approval assertion sees the union of both authentication ledgers; registration base, previous value, unique leaf, fork/gap/rollback rules hold |
| `trg_reviewer_credential_operation_authentication_counter_union_guard` | a credential-operation assertion obeys the same union counter chain and cannot race an issuer assertion |

The two counter triggers operate on relational columns in
`reviewer_authentication_events` and
`reviewer_credential_operation_authentication_events`. For
`SIGN_COUNT_SUPPORTED` they require:

1. the first verified event's `previous_sign_count` equals immutable
   `registration_sign_count`;
2. every later previous value equals the one unique asserted-count leaf across
   both ledgers;
3. no two verified rows use the same previous value or asserted value;
4. asserted is strictly greater than previous; and
5. a pre-existing gap or fork blocks all later verified inserts.

For `NO_USABLE_COUNTER` both counts remain null. Challenge uniqueness,
signature, RP/origin, and UV still apply.

The B2-C issuer-approval service must also reconstruct the complete credential
lifecycle graph under its existing `BEGIN IMMEDIATE` approval writer lock before
accepting an assertion. The additive active guard provides relational defense in
depth for direct inserts; neither layer trusts the frozen `0005` credential FK
alone, because an immutable public credential row remains present after revoke.

## 10. Transaction and concurrency contract

Every issuance, consumption, credential write, lifecycle write, and outcome
uses SQLite `BEGIN IMMEDIATE` with `PRAGMA foreign_keys=ON`.
Aggregate state-hash computation is a trusted-server transaction step, never a
SQLite trigger claim. FKs, unique indexes, checks and guards enforce the
relational graph on which that computation operates.

### 10.1 First enrollment

1. Resolve the application-data owner SID from the Windows OS token.
2. Insert-or-verify the one active steward principal.
3. Prove that no successful historical `FIRST_ENROLLMENT + REGISTERED`
   authorization exists, compute the exact principal-specific empty-state hash,
   allocate the operation and challenge IDs, and insert the root/retry
   `FIRST_ENROLLMENT` operation and its one `REGISTRATION_CREATE` challenge in
   the same issuance transaction. The circular deferred FK prevents either
   half from committing alone.
4. At the first terminal attempt, enter the writer transaction and evaluate the
   registration response. On failure, follow section 10.4 and append the unique
   failed consumption/outcome before returning.
5. On success, freeze the proposed credential/event tuple; allocate the exact
   event ID and compute its content hash; project that exact event to compute the
   candidate post-state; then allocate the outcome ID and compute the
   consumption, outcome and authorization hashes. Insert in this order:
   deferred successful consumption proof, deferred exact `REGISTERED`
   authorization companion, public credential, credential event,
   transaction-visible graph revalidation, and successful operation outcome.
   The consumption and companion both name that exact deferred outcome tuple;
   commit-time FKs reject any incomplete sequence.

The root and predecessor-child unique indexes make parallel bootstrap issuance
or retry produce a typed concurrency conflict. The losing transaction creates
no credential or lifecycle row.

### 10.2 Add or replace

1. Allocate the IDs and insert an operation bound to the exact current
   active-credential-state hash and its one `AUTHORIZATION_ASSERTION` challenge
   in the same issuance transaction.
2. Enter the writer transaction and verify the existing credential, signature,
   RP/origin/UP/UV, replay and union counter chain.
3. On assertion failure, append the terminal consumption and failed outcome
   under section 10.4.
4. On success, preallocate the authentication-event and continuation-challenge
   IDs, compute the consumption, authentication and next-challenge bindings in
   that acyclic order, and append the successful consumption, immutable
   `VERIFIED` event and one `REGISTRATION_CREATE` challenge in the same
   `BEGIN IMMEDIATE`. The consumption's deferred continuation FK and the
   challenge's deferred prerequisite FK make all three commit together.
5. Enter a later writer transaction to terminally evaluate the registration
   challenge. Failure follows section 10.4; success continues below.
6. Freeze the proposed `REGISTERED` event and, for replace, the target's
   `SUPERSEDED` event; allocate every exact event ID and compute its event hash;
   project those exact events to compute the candidate post-state; then allocate
   the outcome ID and compute the authorization/outcome hashes.
7. Insert the deferred authorization companion(s) first, then the new public
   credential and lifecycle event(s). Reload the transaction-visible graph,
   recompute its exact versioned state hash in trusted server code, require it
   to equal the candidate byte-for-byte, and append the unique successful
   outcome to which every authorization is already deferred-bound.

The registration challenge retains the ordinary five-minute maximum lifetime.
The verified existing-credential assertion is not a reusable session and
cannot issue a second registration challenge. If registration later fails, the
verified event and any valid counter advancement remain; section 10.4 appends a
failed outcome with unchanged credential state.

If another operation changes the state hash, relation leaf, or counter first,
the stale operation is terminally failed; it cannot be forced or retried.

### 10.3 Revoke

Revoke requires the same assertion flow and appends one exact `REVOKED` event.
The currently active credential may authenticate its own revocation, including
when it is the final active credential. The server reconstructs the resulting
graph prospectively using a preallocated exact event ID/content hash, computes
the candidate post-state and outcome/authorization hashes, inserts the deferred
authorization companion before the event, reloads and recomputes the
transaction-visible graph, and only then records the exact outcome. For the
final credential, the post-state is the principal-specific empty-state hash.
This is a successful, append-only lockout transition—not a failed operation.

After final revocation, issuer-approval authentication, `ADD_CREDENTIAL`,
`REPLACE_CREDENTIAL` and further `REVOKE_CREDENTIAL` are unavailable because
there is no active authorizing credential. Historical successful registration
prevents `FIRST_ENROLLMENT` from reopening. Recovery/reset remains absent, and
all principal, public credential, lifecycle, authentication, authorization and
operation rows remain queryable. Operators who want continued approval
capability should add a backup credential before intentionally revoking the
last active credential.

### 10.4 Failure durability

A terminal failure uses this exact order:

1. `BEGIN IMMEDIATE` with foreign keys enabled.
2. Load and revalidate the operation, exact challenge, current principal,
   lifecycle graph, credential state and any prerequisite verified event.
3. Allocate the outcome ID in trusted server memory and insert the unique
   terminal challenge consumption with its deferred terminal-outcome companion.
4. If the attempt is sufficiently attributable to an exact registered
   credential and the audit contract permits it, append one safe `REJECTED`
   credential-operation authentication event. An expired, malformed or
   otherwise unattributable attempt has no synthetic authentication event.
5. Reload the trusted-server current credential graph and recompute the exact
   versioned state hash.
6. Prove that no public credential, lifecycle event, or lifecycle authorization
   transition was inserted by this terminal attempt.
7. Append exactly one terminal operation outcome using the closed section 6.1
   mapping and the exact failed consumption ID/content hash.
8. Require byte-for-byte
   `resulting_credential_state_hash == expected_credential_state_hash`.
9. Commit the consumption, optional rejected audit and outcome atomically.
10. Only after commit, return the typed failure to the caller.

The circular deferred consumption/outcome FK makes a failed consumed challenge
without its unique outcome uncommittable. Conversely, the outcome's exact
terminal-consumption FK prevents an invented outcome without the failed
attempt. A process crash before commit leaves neither terminal fact; after
commit it leaves both.

If add/replace has already completed the prior authorization assertion and its
registration attempt fails, the immutable `VERIFIED` authentication event and
valid signature-counter advancement remain. No new credential, `REGISTERED`,
`SUPERSEDED`, or authorization companion commits. The failed outcome references
the earlier verified event and the exact failed registration consumption,
preserves the expected credential-state hash, and allows the successor to
reconstruct the advanced counter history.

An `EXPIRED` challenge is terminalized as `EXPIRED` consumption plus `EXPIRED`
operation outcome. It is not left as an outcome-less dead operation. A retry is
always a fresh successor operation and fresh challenge under section 6.2.

An attempt that arrives after the challenge already has its unique consumption
does not append a second consumption or outcome. Under the writer lock it must
load the existing row and require either its exact terminal outcome or the sole
valid continuation graph; otherwise it reports ledger corruption. The caller
receives a typed replay result only after that check. Stored
`REPLAY_REJECTED -> FAILED_CLOSED` applies when an otherwise unconsumed
challenge's submitted authenticator/client material is itself detected as a
replay and is being terminalized for the first time.

### 10.5 No orphan operation or reusable authorization state

An operation and its first required challenge are inserted under one
`BEGIN IMMEDIATE` issuance transaction. The operation's deferred exact
initial-challenge FK prevents a committed operation with no challenge. A
committed nonterminal operation is therefore in exactly one safe state:

- its exact initial challenge is unconsumed and either usable or ready to be
  terminalized as expired; or
- for add/replace only, the successful assertion consumption, exact `VERIFIED`
  authentication event and one unconsumed `REGISTRATION_CREATE` continuation
  challenge all committed atomically.

Every consumed operation-terminal challenge is mutually deferred-bound to its
unique outcome. Every successful add/replace intermediate consumption is
instead deferred-bound to its one continuation challenge, whose prerequisite
is the exact verified authentication event. The unique operation/purpose index
prevents a second continuation. No committed state may have a consumed
terminal challenge with no outcome, a verified assertion with no bounded next
step, or an operation with neither challenge nor outcome.

On process restart, the server reconstructs these relational states. If a
supposed terminal consumption lacks its outcome, or an operation lacks its
required challenge/outcome/continuation graph, it reports typed ledger
corruption and refuses both continuation and successor creation. It never
silently repairs the graph or treats an old assertion as authorization.

### 10.6 No arbitrary first-writer authority

The unique steward/operation/consumption constraints serialize a server-owned
ceremony; they do not choose between competing identity claims. The principal
and SID come from one server/OS trust boundary, and every credential is bound to
that same principal through exact composite FKs. If two issuance writers start
from one state hash, `BEGIN IMMEDIATE` plus the root/successor uniqueness lets
only one commit an operation and initial challenge; the loser has no committed
operation and therefore writes no outcome. Once an operation has committed,
any challenge-terminal concurrency/CAS failure follows section 10.4 and appends
its unchanged-state outcome before returning. No committed operation can return
a terminal failure with outcome writes zero.
A duplicate credential ID or fingerprint is a conflict and never reassigns
credential ownership. Historical public credential, challenge, consumption,
authentication, authorization, and lifecycle rows remain queryable.

## 11. Authority boundary and forbidden storage

The caller may request only a safe operation action and, for replace/revoke, an
opaque public credential selection hint. The server reloads the current
principal, SID, credential, fingerprints, lifecycle leaf, state hash, policy,
RP/origin, and challenge binding.

The following are never accepted as authoritative request fields:

- principal ID, role, SID or SID hash;
- authenticated/verified booleans or authentication-event IDs;
- expected/current credential-state hash;
- credential ownership, active state, counter capability or prior counter;
- RP ID, origin, policy version, challenge digest/binding or expiry;
- public-key verification result, lifecycle-event authorization, force,
  override, recovery, or reset.

No table stores a password, Windows credential, PIN, biometric template,
private key, cookie, bearer token, raw authenticator secret, raw challenge
nonce, localStorage/sessionStorage value, or credential secret. Existing
`reviewer_webauthn_credentials` remains limited to public/non-secret material.

## 12. Migration upgrade, downgrade, and failure safety

The future upgrade must:

1. verify exact `0001`–`0005` hashes;
2. verify all target table/index/trigger names are absent;
3. fail closed if any existing reviewer principal, credential, credential
   event, authentication, challenge-consumption, approval event, or approval
   link row lacks a provable authorization lineage; no synthetic backfill is
   allowed;
4. create operation, challenge, consumption, operation-authentication, outcome,
   then lifecycle-authorization tables in FK-safe order; the outcome insert
   guard is installed only after the authorization table exists;
5. create indexes and then insert-guard/append-only triggers;
6. run `PRAGMA foreign_key_check` and schema inventory assertions; and
7. leave the Alembic head at `0005` if any later DDL step fails.

Because B2-C runtime has never been implemented, the expected persistent
reviewer/approval tables are empty. An unexpected pre-`0006` row is a migration
review blocker, not a reason to manufacture bootstrap or authentication data.
Authority evidence/bundle/decision rows are unaffected.

Downgrade drops only `0006` triggers, indexes, and six new tables in reverse
dependency order. A non-disposable database with any `0006` audit row must
refuse downgrade unless a separately authorized destructive procedure exists.
Disposable empty-schema downgrade/re-upgrade remains required for tests.

## 13. Future migration and repository acceptance tests

The separately authorized implementation must add offline tests for at least:

- blank database `0001 -> 0006` upgrade;
- populated non-reviewer `0005 -> 0006` upgrade with all old rows unchanged;
- exact `0001`–`0005` hash equality and `0006` revision/down-revision;
- exact four-token `authorization_kind` enum and five allowed
  operation/event/authorization combinations; every other combination rejected;
- both authorization and outcome tables carry the three non-null copied trust
  columns and implement the exact ordered eight-column operation FK without a
  weaker subset parent key;
- authorization/outcome hash-preimage vectors change when any copied role,
  principal-content-hash or OS-owner-SID-hash value changes;
- unexpected pre-existing reviewer row fails without synthetic backfill;
- late-DDL failure removes only `0006` objects and retry succeeds;
- disposable empty downgrade/re-upgrade;
- first bootstrap single use, expiry, failed consumption, replay, and parallel
  issuance;
- server principal randomness and exact server-resolved SID binding;
- non-Windows operational fail closed and caller SID rejection;
- add/replace require a currently active same-principal credential assertion;
- issuer-approval assertion cannot authorize credential lifecycle and a
  credential-operation assertion cannot authorize issuer approval;
- challenge failure consumes; simultaneous consumption has one terminal
  winner;
- invalid signature commits its consumption, attributable rejected audit and
  failed outcome before returning the typed error;
- expired challenge commits `EXPIRED` consumption and `EXPIRED` outcome;
- missing UP or UV commits a consumed challenge and mapped failed outcome;
- wrong origin/RP commits a consumed challenge and `FAILED_CLOSED` outcome;
- failed first enrollment creates no credential/lifecycle event, preserves the
  exact empty-state hash in its failed outcome, and permits only a fresh
  successor first-enrollment operation while registration history is empty;
- add registration failure after a verified existing-credential assertion
  preserves that immutable event and advanced counter, leaves credential state
  unchanged, appends the failed outcome, and lets the successor reconstruct
  the advanced counter history;
- replace registration failure leaves the old credential active, appends no
  `SUPERSEDED` event, and preserves the prior state in the failed outcome;
- revoke authentication failure leaves the target active and preserves the
  prior state in the failed outcome;
- process restart discovers the failed predecessor outcome and permits a valid
  successor whose expected state equals that outcome's resulting state;
- consumed operation-terminal challenge without an operation outcome is
  rejected as ledger corruption and cannot silently start a successor;
- operation commit without its first challenge, outcome, or exact
  continuation-bearing state is rejected by deferred integrity;
- deterministic closed mapping covers every challenge terminal enum and no
  implementation-defined fallback exists;
- successful add/replace authorization commits its consumption, verified event
  and exactly one registration challenge atomically; a second continuation or
  reusable authorization session is rejected;
- success immediately before expiry is representable, while an attempt exactly
  at or after `expires_at` is terminal `EXPIRED`;
- exact RP/origin/type/UP/UV/signature/platform/resident-key checks;
- public credential insert without successful registration proof rejected;
- credential event without exact authorization companion rejected;
- credential event without an exact deferred successful-operation outcome
  binding rejected at commit;
- cross-principal/cross-credential lifecycle graft rejected;
- replacement atomically registers new and supersedes old;
- one active credential can authenticate its own revoke and commit successfully;
- final revoke reconstructs exactly the principal-specific empty active set;
- after final revoke, issuer approval and add/replace/further-revoke operations
  fail closed, first enrollment does not restart, and recovery/reset count is
  zero;
- after final revoke, both the normal issuer-approval service path and a direct
  issuer-authentication-event insert using the revoked public credential fail;
- revoked credential and principal/lifecycle/authorization/authentication
  history remain queryable;
- no unauthenticated recovery/reset path;
- deterministic `reviewer-credential-state/0.1.0` hash is independent of query,
  input and insertion order;
- exact principal-specific empty-state hash is stable across process restart;
- add, replace and revoke each change the credential-state hash, and final
  revoke produces the exact empty-state hash;
- signature-counter advancement alone does not change credential-state hash;
- altering a lifecycle leaf changes credential-state hash;
- an omitted active credential fails trusted-server revalidation, while an
  extra inactive credential is excluded and cannot enter the active member
  array;
- planned post-state and reloaded transaction-visible post-state must match
  byte-for-byte before the deferred successful outcome can commit;
- two writers starting from the same state produce one valid successor and one
  typed conflict;
- state-hash tests and migrations work without any SQLite SHA function or
  undeclared UDF;
- union counter history across issuer approval and credential management:
  strict advance, equality, rollback, gap, fork, concurrency, and no-counter
  null/null;
- process-restart reconstruction from registration count plus both append-only
  ledgers;
- UPDATE/DELETE rejected for all new tables;
- no private/secret material in rows, logs, API, fixtures, or frontend storage;
- canonical Issuer/Security and VERIFIED mapping writes remain zero outside
  disposable authenticated approval tests; and
- no live authority/Toss request or real Windows Hello enrollment in automated
  QA.

## 14. Documentation checkpoint result

- ADR-013: `ACCEPTED`
- ADR-014: `ACCEPTED`
- ADR-015: `ACCEPTED` (`2026-08-28`)
- ADR-016: `ACCEPTED` (`2026-08-28`)
- SG-01 / SG-02 / P1-SR-01 / P1-SR-02 / P1-SR-03:
  independently verified `CLOSED`
- CP3-C2-B1: `PASS — CONTRACT APPROVED AND CLOSED`
- CP3-C2-B2-A: `PASS — CLOSED`
- CP3-C2-B2-B: `PASS — CLOSED`
- CP3-C2-B2-C: `0006 SCHEMA IMPLEMENTATION IN PROGRESS`
- CP3-C2-B2-D: `NOT STARTED`
- CP3-C2-C: `NOT STARTED`
- CP3-D: `NOT STARTED`
- Automatic progression: `PROHIBITED`
- Runtime/application/test/frontend/dependency changes: `0`
- Migration changes/application: `0`
- `0006` file created: `0`
- Real credential enrollment/approval/canonical/link writes: `0`
- Live authority/Toss requests: `0`

ADR-016 passed GPT independent review and was explicitly accepted by the user.
Only the separately authorized `0006` schema implementation may proceed. B2-C
WebAuthn/human-approval runtime remains `NOT STARTED / NOT AUTHORIZED`.
