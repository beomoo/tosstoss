# Phase 2 CP3-C2-B2-C — ADR-018 Counter-Capability Schema Proposal

## 1. Control-plane status

- ADR-017: `ACCEPTED` (`2026-08-29`)
- ADR-018: `ACCEPTED` (`2026-08-29`)
- ADR-019: `PROPOSED — AWAITING GPT REVIEW / USER ACCEPTANCE`, decision date
  `NONE`
- `0006`: `PASS — CLOSED`
- proposed future migration:
  `0007_phase_02_cp3_c2_b2_c_counter_capability_bootstrap`
- `0007`: `NOT CREATED / NOT AUTHORIZED`
- R1: `NOT STARTED / BLOCKED — ADR-019 DECISION REQUIRED`
- automatic progression: `PROHIBITED`

This document is the implementation-ready, normative schema companion to
accepted ADR-018. It describes a future additive migration only. It does not
authorize or create that migration and does not alter `0001`–`0006`.

## 2. Selected state machine

The ambiguity applies to every newly created credential from exactly
`FIRST_ENROLLMENT`, `ADD_CREDENTIAL`, and `REPLACE_CREDENTIAL`.
`REVOKE_CREDENTIAL` creates no credential and never enters this state machine.

A verified positive registration counter uses the unchanged `0006` terminal
registration path. A verified zero registration counter does not yet consume
the frozen `0006` registration challenge and does not create a public
credential. Instead, one pending-registration row and one exact-credential
assertion challenge are committed. The assertion challenge expires no later
than the still-live parent registration challenge.

The assertion is a mandatory continuation of the original operation, not a
login or reusable session. It has a non-empty `allowCredentials` list containing
exactly the pending credential ID. The server verifies type, challenge, exact
origin, RP ID hash, cross-origin false, UP, UV, credential ID, optional returned
user handle, signature under the pending public key, expiry, and replay.

- verified `0 -> positive`: admit `SIGN_COUNT_SUPPORTED` with truthful frozen
  `registration_sign_count=0`; the assertion is the first counter-union edge;
- verified `0 -> 0`: admit repository mode `NO_USABLE_COUNTER` with frozen
  `registration_sign_count=NULL`; both observed zeros remain in the proposed
  bootstrap ledger;
- any failure: no public credential or lifecycle authorization; terminalize the
  original `0006` operation with its expected state unchanged.

For `ADD_CREDENTIAL` and `REPLACE_CREDENTIAL`, the already-committed successful
authorization assertion, its `VERIFIED` authentication event, and any supported
authorizing-credential counter edge remain immutable in every later branch.

## 3. Why frozen `0006` remains the terminal projection

The proposal uses the already-issued `0006` `REGISTRATION_CREATE` challenge as
the parent. This preserves the exact operation, principal, state, authorizing
assertion, and continuation facts already frozen by `0006`. The pending row is
an alternative durable use marker while the parent has no frozen consumption.
Every terminal bootstrap branch then inserts exactly one ordinary frozen
registration consumption and exactly one ordinary frozen outcome.

This projection is necessary for the existing predecessor contract. A successor
operation still references an exact row in
`reviewer_credential_operation_outcomes`; it never depends on hidden runtime
state or on a proposed-table-only terminal marker.

The original parent registration challenge remains time authoritative. A
successful capability assertion MUST be consumed before both the child and
parent expiration instants. The child `expires_at` MUST be less than or equal to
the parent `expires_at`. If capability classification cannot finish before the
parent expires, the parent projects `terminal_result=EXPIRED`, the outcome is
`EXPIRED`, and state is unchanged. If the child fails or expires while the
parent is still live, the parent projects `FAILED_CLOSED` with an exact safe
code naming the capability-assertion cause. Thus the frozen expiry trigger is
never bypassed or contradicted.

## 4. Common proposed-0007 rules

All three tables are append-only. IDs are preallocated, opaque CSPRNG values.
All timestamps are server-owned UTC strings accepted by `julianday`, end in
`Z`, and use the ADR-017 timestamp form. Every hash is `sha256:` plus 64
lowercase hexadecimal characters. Every Boolean is SQLite integer `0` or `1`.
Every exact-copy FK below is `DEFERRABLE INITIALLY DEFERRED` where the parent and
child can be inserted in the same transaction. `PRAGMA foreign_keys=ON` and
`BEGIN IMMEDIATE` are mandatory.

All JSON-backed content hashes use ADR-017 common canonical JSON. The listed
preimage fields are exhaustive; unlisted fields are forbidden. `payload_json`
is diagnostic only, has zero authority, and is excluded from every hash and
guard decision. Row creation timestamps are also excluded except for challenge
`issued_at` and `expires_at`, which are binding fields.

## 5. Table 1 — verified zero registration

Exact name:
`reviewer_webauthn_counter_capability_registrations`.

| Column | Type | Null | Exact rule |
|---|---|---:|---|
| `counter_capability_registration_id` | `VARCHAR(128)` | no | PK; opaque preallocated ID |
| `contract_version` | `VARCHAR(64)` | no | `reviewer-counter-capability-registration/0.1.0` |
| `counter_capability_registration_content_hash` | `VARCHAR(71)` | no | UNIQUE; exact section 5.2 preimage |
| `reviewer_credential_operation_id` | `VARCHAR(128)` | no | exact frozen operation |
| `operation_content_hash` | `VARCHAR(71)` | no | exact frozen operation hash |
| `operation_type` | `VARCHAR(32)` | no | first/add/replace only |
| `reviewer_principal_id` | `VARCHAR(128)` | no | exact steward principal |
| `reviewer_role` | `VARCHAR(32)` | no | `LOCAL_DATA_STEWARD` |
| `principal_content_hash` | `VARCHAR(71)` | no | exact principal hash |
| `os_owner_sid_hash` | `VARCHAR(71)` | no | exact principal SID binding |
| `expected_credential_state_hash` | `VARCHAR(71)` | no | exact frozen operation value |
| `registration_challenge_id` | `VARCHAR(128)` | no | UNIQUE; existing `0006` challenge |
| `registration_challenge_purpose` | `VARCHAR(32)` | no | `REGISTRATION_CREATE` |
| `registration_challenge_binding_hash` | `VARCHAR(71)` | no | exact existing binding |
| `prerequisite_authentication_event_id` | `VARCHAR(128)` | yes | null for first; verified prior event for add/replace |
| `prerequisite_authentication_content_hash` | `VARCHAR(71)` | yes | same nullability group |
| `prerequisite_authentication_result` | `VARCHAR(16)` | yes | null or `VERIFIED` |
| `webauthn_credential_id` | `VARCHAR(512)` | no | UNIQUE; canonical unpadded base64url |
| `credential_id_fingerprint` | `VARCHAR(71)` | no | UNIQUE; SHA-256 of raw credential ID |
| `cose_public_key_canonical` | `TEXT` | no | CTAP2-canonical bytes as unpadded base64url |
| `public_key_fingerprint` | `VARCHAR(71)` | no | UNIQUE; SHA-256 of canonical raw COSE bytes |
| `public_key_algorithm` | `VARCHAR(32)` | no | `ES256` or `RS256` |
| `authenticator_aaguid` | `VARCHAR(64)` | yes | null or lowercase hyphenated UUID |
| `authenticator_attachment` | `VARCHAR(16)` | no | `platform` |
| `authenticator_transports_json` | `TEXT` | no | exact ADR-017 sorted compact array |
| `rp_id` | `VARCHAR(255)` | no | `localhost` |
| `exact_origin` | `VARCHAR(255)` | no | `http://localhost:3000` |
| `resident_key_required` | `INTEGER` | no | `1` |
| `require_resident_key` | `INTEGER` | no | `1` |
| `user_verification_required` | `INTEGER` | no | `1` |
| `attestation_conveyance` | `VARCHAR(16)` | no | `none` |
| `cred_props_requested` | `INTEGER` | no | `1` |
| `cred_props_rk` | `INTEGER` | yes | null when absent; otherwise only `1` |
| `registration_policy_version` | `VARCHAR(64)` | no | `issuer-steward-webauthn/0.1.0` |
| `observed_registration_sign_count` | `INTEGER` | no | exactly `0` |
| `client_data_type_verified` | `INTEGER` | no | exactly `1` |
| `challenge_verified` | `INTEGER` | no | exactly `1` |
| `origin_verified` | `INTEGER` | no | exactly `1` |
| `cross_origin_false_verified` | `INTEGER` | no | exactly `1` |
| `rp_id_hash_verified` | `INTEGER` | no | exactly `1` |
| `user_presence_verified` | `INTEGER` | no | exactly `1` |
| `user_verification_verified` | `INTEGER` | no | exactly `1` |
| `platform_authenticator_verified` | `INTEGER` | no | exactly `1` |
| `resident_key_verified` | `INTEGER` | no | exactly `1` |
| `public_key_material_verified` | `INTEGER` | no | exactly `1` |
| `safe_result_code` | `VARCHAR(128)` | no | `COUNTER_CAPABILITY_CONTINUATION_REQUIRED` |
| `continuation_challenge_id` | `VARCHAR(128)` | no | UNIQUE; exact section 6 challenge |
| `verified_at` | `VARCHAR(35)` | no | server UTC audit time |
| `payload_json` | `TEXT` | no | non-authoritative diagnostic object |

### 5.1 Keys, FKs, checks, and indexes

- PK: `counter_capability_registration_id`.
- UNIQUE: content hash, `registration_challenge_id`,
  `continuation_challenge_id`, credential ID, credential-ID fingerprint, and
  public-key fingerprint.
- Exact operation FK uses the frozen eight-column
  `uq_reviewer_credential_operations_exact_binding` tuple.
- Exact registration-challenge FK uses frozen challenge ID, operation ID,
  principal ID, operation type, purpose, and binding hash.
- Nullable exact prerequisite-authentication FK uses event ID, authentication
  content hash, operation ID, principal ID, and result. All three nullable
  columns are null together or result is `VERIFIED`.
- Deferred child FK uses `(continuation_challenge_id,
  counter_capability_registration_id)` and the corresponding UNIQUE pair in
  section 6.
- `FIRST_ENROLLMENT` requires null prerequisite columns. `ADD_CREDENTIAL` and
  `REPLACE_CREDENTIAL` require the exact `VERIFIED` prerequisite copied from the
  existing registration challenge.
- The existing challenge must be unconsumed in the frozen consumption table and
  absent from this table. Its operation must have no frozen outcome.
- `verified_at < parent expires_at`; the registration verification cannot create
  pending state after parent expiry.
- Index:
  `ix_counter_capability_registrations_operation`
  on `(reviewer_credential_operation_id, reviewer_principal_id)`.

### 5.2 Exact content-hash preimage

The preimage contains every section 5 column from `contract_version` through
`continuation_challenge_id`, including the row ID and both preallocated
challenge IDs, except
`counter_capability_registration_content_hash`. It excludes only
`verified_at` and `payload_json`. Nullable AAGUID, `cred_props_rk`, and
prerequisite fields are present as JSON null. SQLite Booleans are JSON
Booleans. No counter classification appears because it is unresolved.

## 6. Table 2 — exact pending-credential assertion challenge

Exact name:
`reviewer_webauthn_counter_capability_challenges`.

| Column | Type | Null | Exact rule |
|---|---|---:|---|
| `counter_capability_challenge_id` | `VARCHAR(128)` | no | PK; equals registration continuation ID |
| `contract_version` | `VARCHAR(64)` | no | `reviewer-counter-capability-challenge/0.1.0` |
| `challenge_digest` | `VARCHAR(71)` | no | UNIQUE; SHA-256 of raw 32-byte challenge |
| `challenge_binding_hash` | `VARCHAR(71)` | no | UNIQUE; section 6.2 preimage |
| `challenge_nonce_length` | `INTEGER` | no | `32` |
| `challenge_purpose` | `VARCHAR(32)` | no | `COUNTER_CAPABILITY_ASSERTION` |
| `counter_capability_registration_id` | `VARCHAR(128)` | no | UNIQUE; exact pending registration |
| `counter_capability_registration_content_hash` | `VARCHAR(71)` | no | exact pending hash |
| `reviewer_credential_operation_id` | `VARCHAR(128)` | no | exact operation |
| `operation_content_hash` | `VARCHAR(71)` | no | exact operation hash |
| `operation_type` | `VARCHAR(32)` | no | first/add/replace only |
| `reviewer_principal_id` | `VARCHAR(128)` | no | exact principal |
| `reviewer_role` | `VARCHAR(32)` | no | `LOCAL_DATA_STEWARD` |
| `principal_content_hash` | `VARCHAR(71)` | no | exact principal hash |
| `os_owner_sid_hash` | `VARCHAR(71)` | no | exact SID binding |
| `expected_credential_state_hash` | `VARCHAR(71)` | no | exact operation expected state |
| `parent_registration_challenge_id` | `VARCHAR(128)` | no | exact existing `0006` parent |
| `parent_registration_challenge_binding_hash` | `VARCHAR(71)` | no | exact parent binding |
| `webauthn_credential_id` | `VARCHAR(512)` | no | exact pending credential |
| `credential_id_fingerprint` | `VARCHAR(71)` | no | exact pending fingerprint |
| `public_key_fingerprint` | `VARCHAR(71)` | no | exact pending key fingerprint |
| `rp_id` | `VARCHAR(255)` | no | `localhost` |
| `allowed_origin` | `VARCHAR(255)` | no | `http://localhost:3000` |
| `client_data_type` | `VARCHAR(32)` | no | `webauthn.get` |
| `user_verification_required` | `INTEGER` | no | `1` |
| `allow_credentials_count` | `INTEGER` | no | `1` |
| `allowed_webauthn_credential_id` | `VARCHAR(512)` | no | equals pending credential ID |
| `user_handle_contract_version` | `VARCHAR(64)` | no | `issuer-steward-webauthn-user-handle/0.1.0` |
| `authentication_policy_version` | `VARCHAR(64)` | no | `issuer-steward-webauthn/0.1.0` |
| `issued_at` | `VARCHAR(35)` | no | server UTC, hash-bound |
| `expires_at` | `VARCHAR(35)` | no | server UTC, hash-bound |
| `payload_json` | `TEXT` | no | non-authoritative diagnostic object |

### 6.1 Keys, FKs, checks, and indexes

- PK: `counter_capability_challenge_id`.
- UNIQUE: digest, binding hash, `counter_capability_registration_id`, and
  `(counter_capability_challenge_id, counter_capability_registration_id)`.
- Exact pending-registration FK copies registration ID, content hash, operation,
  principal, expected state, parent challenge, and all three credential
  fingerprints. A proposed UNIQUE exact-copy index on section 5 supplies this
  FK target.
- Exact operation FK uses the frozen eight-column operation tuple.
- Checks require `allowed_webauthn_credential_id=webauthn_credential_id`,
  `issued_at < expires_at`, duration at most five minutes, and
  `expires_at <= parent 0006 registration challenge expires_at`.
- Index:
  `ix_counter_capability_challenges_expiry`
  on `(reviewer_principal_id, expires_at)`.

### 6.2 Exact challenge-binding preimage

The preimage contains every section 6 column from
`counter_capability_challenge_id` through `expires_at`, including
`challenge_digest`, except `challenge_binding_hash`. It excludes only
`payload_json`. Raw challenge bytes never appear. The challenge ID and pending
registration ID are preallocated opaque values, so the DAG has no cycle.

## 7. Table 3 — assertion terminalization and frozen projection

Exact name:
`reviewer_webauthn_counter_capability_assertions`.

| Column | Type | Null | Exact rule |
|---|---|---:|---|
| `counter_capability_assertion_id` | `VARCHAR(128)` | no | PK; opaque event ID |
| `contract_version` | `VARCHAR(64)` | no | `reviewer-counter-capability-assertion/0.1.0` |
| `assertion_content_hash` | `VARCHAR(71)` | no | UNIQUE; section 7.2 preimage |
| `counter_capability_challenge_id` | `VARCHAR(128)` | no | UNIQUE; consumes one child challenge |
| `challenge_binding_hash` | `VARCHAR(71)` | no | exact child binding |
| `counter_capability_registration_id` | `VARCHAR(128)` | no | UNIQUE; terminalizes one pending row |
| `counter_capability_registration_content_hash` | `VARCHAR(71)` | no | exact pending hash |
| `reviewer_credential_operation_id` | `VARCHAR(128)` | no | exact original operation |
| `operation_content_hash` | `VARCHAR(71)` | no | exact operation hash |
| `operation_type` | `VARCHAR(32)` | no | first/add/replace only |
| `reviewer_principal_id` | `VARCHAR(128)` | no | exact principal |
| `reviewer_role` | `VARCHAR(32)` | no | `LOCAL_DATA_STEWARD` |
| `principal_content_hash` | `VARCHAR(71)` | no | exact principal hash |
| `os_owner_sid_hash` | `VARCHAR(71)` | no | exact SID binding |
| `expected_credential_state_hash` | `VARCHAR(71)` | no | exact operation expected state |
| `webauthn_credential_id` | `VARCHAR(512)` | no | exact pending credential |
| `credential_id_fingerprint` | `VARCHAR(71)` | no | exact pending fingerprint |
| `public_key_fingerprint` | `VARCHAR(71)` | no | exact pending key fingerprint |
| `challenge_terminal_result` | `VARCHAR(32)` | no | frozen `0006` challenge-result enum |
| `safe_result_code` | `VARCHAR(128)` | no | exact closed server code |
| `client_data_type_verified` | `INTEGER` | no | Boolean |
| `challenge_verified` | `INTEGER` | no | Boolean |
| `origin_verified` | `INTEGER` | no | Boolean |
| `cross_origin_false_verified` | `INTEGER` | no | Boolean |
| `rp_id_hash_verified` | `INTEGER` | no | Boolean |
| `user_presence_verified` | `INTEGER` | no | Boolean |
| `user_verification_verified` | `INTEGER` | no | Boolean |
| `credential_id_verified` | `INTEGER` | no | Boolean |
| `signature_verified` | `INTEGER` | no | Boolean |
| `replay_rejected` | `INTEGER` | no | Boolean; `1` means fresh use established |
| `user_handle_status` | `VARCHAR(24)` | no | `MATCHED`, `ABSENT_ALLOWED`, `MISMATCHED`, or `NOT_EVALUATED` |
| `observed_registration_sign_count` | `INTEGER` | no | exactly `0` |
| `previous_sign_count` | `INTEGER` | yes | `0` only on cryptographically verified assertion |
| `asserted_sign_count` | `INTEGER` | yes | nonnegative only after signature verification |
| `selected_counter_capability` | `VARCHAR(32)` | yes | success only; supported or no-usable |
| `selected_registration_sign_count` | `INTEGER` | yes | `0` only for supported; null otherwise |
| `classification_verified` | `INTEGER` | no | `1` only on successful exact classification |
| `projected_registration_consumption_id` | `VARCHAR(128)` | no | exact frozen terminal consumption |
| `projected_registration_consumption_content_hash` | `VARCHAR(71)` | no | exact frozen hash |
| `projected_registration_challenge_purpose` | `VARCHAR(32)` | no | exactly `REGISTRATION_CREATE`; required child column for the frozen six-column consumption FK |
| `projected_registration_terminal_result` | `VARCHAR(32)` | no | success, failed-closed, or parent expiry |
| `projected_registration_safe_result_code` | `VARCHAR(128)` | no | exact overall-registration code |
| `projected_operation_outcome_id` | `VARCHAR(128)` | no | exact frozen outcome |
| `projected_operation_outcome_content_hash` | `VARCHAR(71)` | no | exact frozen outcome hash |
| `projected_operation_terminal_result` | `VARCHAR(16)` | no | `SUCCEEDED`, `FAILED_CLOSED`, or `EXPIRED` |
| `projected_resulting_credential_state_hash` | `VARCHAR(71)` | no | exact frozen resulting state |
| `projected_credential_content_hash` | `VARCHAR(71)` | yes | success only; exact public credential hash |
| `projected_registered_event_id` | `VARCHAR(128)` | yes | success only |
| `projected_registered_event_content_hash` | `VARCHAR(71)` | yes | success only |
| `projected_registered_authorization_content_hash` | `VARCHAR(71)` | yes | success only |
| `projected_superseded_event_id` | `VARCHAR(128)` | yes | replace success only |
| `projected_superseded_event_content_hash` | `VARCHAR(71)` | yes | replace success only |
| `projected_superseded_authorization_content_hash` | `VARCHAR(71)` | yes | replace success only |
| `consumed_at` | `VARCHAR(35)` | no | server UTC audit time |
| `payload_json` | `TEXT` | no | non-authoritative diagnostic object |

### 7.1 Keys, FKs, checks, and indexes

- PK: `counter_capability_assertion_id`.
- UNIQUE: assertion hash, child challenge ID, pending-registration ID,
  projected frozen consumption ID, and projected frozen outcome ID.
- Exact challenge and pending-registration FKs copy their IDs, hashes,
  operation/principal/state tuple, and credential fingerprints.
- Exact operation FK uses the frozen eight-column operation tuple.
- Deferred exact frozen-consumption FK has child columns, in this exact order:
  `(projected_registration_consumption_id,
  reviewer_credential_operation_id, reviewer_principal_id,
  projected_registration_challenge_purpose,
  projected_registration_terminal_result,
  projected_registration_consumption_content_hash)`. It targets frozen
  `uq_reviewer_credential_operation_consumptions_exact_terminal` in its exact
  existing order. The new purpose column is fixed to `REGISTRATION_CREATE`;
  an implied SQL constant cannot be used as an SQLite composite-FK child.
- The deferred exact frozen-outcome FK uses future additive parent index
  `uq_0007_reviewer_credential_operation_outcomes_bootstrap_projection`. Its
  child columns, in exact order, are
  `(projected_operation_outcome_id,
  projected_operation_outcome_content_hash,
  reviewer_credential_operation_id, operation_content_hash,
  reviewer_principal_id, reviewer_role, principal_content_hash,
  os_owner_sid_hash, operation_type, projected_operation_terminal_result,
  projected_registration_consumption_id,
  projected_registration_consumption_content_hash,
  expected_credential_state_hash,
  projected_resulting_credential_state_hash)`.
- On success, a deferred FK binds the pending credential ID plus projected
  content hash to `uq_reviewer_credentials_exact_content`; deferred FKs bind the
  registered and optional superseded IDs to their immutable event rows.
  Exact-copy triggers additionally match both event content and authorization
  content hashes to the same successful operation/outcome.
- Index:
  `ix_counter_capability_assertions_operation`
  on `(reviewer_credential_operation_id, projected_operation_terminal_result)`.

Successful assertion checks require every verification Boolean to be `1`,
`user_handle_status` to be `MATCHED` or `ABSENT_ALLOWED`, previous count `0`,
and asserted count nonnegative. An asserted positive value requires
`SIGN_COUNT_SUPPORTED`, selected registration count `0`, and
`classification_verified=1`. Asserted zero requires `NO_USABLE_COUNTER`, null
selected registration count, and `classification_verified=1`.

Successful projection checks require frozen registration consumption and
operation outcome `SUCCEEDED`, a changed state hash, a public credential, one
registered event, and one registered authorization. Replace success additionally
requires exactly one superseded event and authorization for the operation's old
target. First/add success requires every superseded projection field null.

Failure checks require classification and every credential/lifecycle projection
field null. If `consumed_at` is before the parent registration expiry, the
frozen registration consumption and outcome are both `FAILED_CLOSED`; if at or
after parent expiry, both are `EXPIRED`. In both cases resulting state equals
expected state. A failed row can retain an asserted count only when the signature
was verified; the count has no classification authority.

### 7.2 Exact assertion-content-hash preimage

The preimage contains every section 7 column from `contract_version` through
`projected_superseded_authorization_content_hash`, including the event ID, child
challenge ID, all exact-copy hashes, counter observations, result codes, and
projection IDs. This includes the newly explicit
`projected_registration_challenge_purpose`. It excludes only
`assertion_content_hash`, `consumed_at`, and `payload_json`. Nullable counters,
classification, credential, and lifecycle projection fields are explicit JSON
null. Verification integers are JSON Booleans.

## 8. Exact additive trigger and index design

### 8.0 Exact proposed index inventory

The future migration creates the following named indexes. A listed UNIQUE index
is also the exact parent key for any composite FK described above.

| Index | Table | Columns / predicate |
|---|---|---|
| `uq_0007_cc_registration_content` | registrations | UNIQUE `(counter_capability_registration_content_hash)` |
| `uq_0007_cc_registration_parent` | registrations | UNIQUE `(registration_challenge_id)` |
| `uq_0007_cc_registration_child` | registrations | UNIQUE `(continuation_challenge_id)` |
| `uq_0007_cc_registration_credential` | registrations | UNIQUE `(webauthn_credential_id)` |
| `uq_0007_cc_registration_credential_fingerprint` | registrations | UNIQUE `(credential_id_fingerprint)` |
| `uq_0007_cc_registration_public_key_fingerprint` | registrations | UNIQUE `(public_key_fingerprint)` |
| `uq_0007_cc_registration_exact_copy` | registrations | UNIQUE `(counter_capability_registration_id, counter_capability_registration_content_hash, reviewer_credential_operation_id, operation_content_hash, operation_type, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, expected_credential_state_hash, registration_challenge_id, registration_challenge_binding_hash, webauthn_credential_id, credential_id_fingerprint, public_key_fingerprint, continuation_challenge_id)` |
| `uq_0007_cc_registration_assertion_copy` | registrations | UNIQUE `(counter_capability_registration_id, counter_capability_registration_content_hash, reviewer_credential_operation_id, operation_content_hash, operation_type, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, expected_credential_state_hash, webauthn_credential_id, credential_id_fingerprint, public_key_fingerprint)` |
| `ix_counter_capability_registrations_operation` | registrations | `(reviewer_credential_operation_id, reviewer_principal_id)` |
| `uq_0007_cc_challenge_digest` | challenges | UNIQUE `(challenge_digest)` |
| `uq_0007_cc_challenge_binding` | challenges | UNIQUE `(challenge_binding_hash)` |
| `uq_0007_cc_challenge_registration` | challenges | UNIQUE `(counter_capability_registration_id)` |
| `uq_0007_cc_challenge_exact_child` | challenges | UNIQUE `(counter_capability_challenge_id, counter_capability_registration_id)` |
| `uq_0007_cc_challenge_exact_copy` | challenges | UNIQUE `(counter_capability_challenge_id, challenge_binding_hash, counter_capability_registration_id, counter_capability_registration_content_hash, reviewer_credential_operation_id, operation_content_hash, operation_type, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, expected_credential_state_hash, webauthn_credential_id, credential_id_fingerprint, public_key_fingerprint)` |
| `ix_counter_capability_challenges_expiry` | challenges | `(reviewer_principal_id, expires_at)` |
| `uq_0007_cc_assertion_content` | assertions | UNIQUE `(assertion_content_hash)` |
| `uq_0007_cc_assertion_challenge` | assertions | UNIQUE `(counter_capability_challenge_id)` |
| `uq_0007_cc_assertion_registration` | assertions | UNIQUE `(counter_capability_registration_id)` |
| `uq_0007_cc_assertion_consumption_projection` | assertions | UNIQUE `(projected_registration_consumption_id)` |
| `uq_0007_cc_assertion_outcome_projection` | assertions | UNIQUE `(projected_operation_outcome_id)` |
| `ix_counter_capability_assertions_operation` | assertions | `(reviewer_credential_operation_id, projected_operation_terminal_result)` |
| `uq_0007_reviewer_credential_operation_outcomes_bootstrap_projection` | frozen outcomes | UNIQUE `(credential_operation_outcome_id, outcome_content_hash, reviewer_credential_operation_id, operation_content_hash, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, operation_type, terminal_result, terminal_consumption_id, terminal_consumption_content_hash, expected_credential_state_hash, resulting_credential_state_hash)` |
| `uq_0007_credential_event_authorization_projection` | frozen event authorizations | UNIQUE `(credential_event_id, credential_event_content_hash, authorization_content_hash, webauthn_credential_id, reviewer_credential_operation_id, credential_operation_outcome_id, credential_operation_outcome_content_hash, event_type, authorization_kind)` |

PK indexes are implicit and are not duplicated. No partial index changes frozen
active-state or lifecycle semantics. This inventory is exhaustive. In
particular, there is no remaining “may add exact-copy indexes” discretion.

### 8.0.1 Frozen outcome parent-key audit — P1-FR-01

Frozen `uq_reviewer_credential_operation_outcomes_exact_terminal` contains the
terminal consumption ID but omits `outcome_content_hash` and most copied trust
fields. Frozen
`uq_reviewer_credential_operation_outcomes_exact_success` contains the outcome
hash and trust tuple but omits `terminal_consumption_id` and its content hash.
Neither is an eligible SQLite parent for the intended child tuple. ADR-018
therefore selects remediation A: future `0007` MUST create the one exact
additive UNIQUE index named above before it creates the assertion FK. No frozen
row or trigger meaning changes. Schema creation must fail if the index cannot
be created; splitting the binding or relying on reverse triggers is not an
authorized substitute.

### 8.1 New insert guards

| Trigger | Exact responsibility |
|---|---|
| `trg_0007_counter_capability_registrations_insert_guard` | exact unconsumed live parent registration challenge; no outcome; exact operation/principal/state/prerequisite tuple; canonical credential/key material; registration count exactly zero; registration proof flags and request contract exact; pending credential absent from both pending and public ledgers. The forward child is not queried by this immediate trigger; the deferred `(continuation_challenge_id, counter_capability_registration_id)` FK requires it at COMMIT. |
| `trg_0007_counter_capability_challenges_insert_guard` | raw-32-byte digest contract; exact pending copy; exactly one allow credential; exact user-handle policy; child expiry no later than parent; no existing assertion |
| `trg_0007_counter_capability_assertions_insert_guard` | exact one-time challenge; time/result match; full verification matrix; optional user-handle result; classification union; frozen projection IDs/hashes/results; failure zero-write rule; same-operation registration and replace lifecycle patterns |
| `trg_0007_operation_consumptions_bootstrap_projection_guard` | when the frozen registration challenge has a pending row, reject any consumption unless exactly one same-transaction assertion row projects every new frozen value; also rejects frozen consumption before bootstrap terminalization |
| `trg_0007_operation_outcomes_bootstrap_projection_guard` | when terminal registration consumption belongs to pending bootstrap, require the exact assertion projection and exact success/failure state relation |
| `trg_0007_credentials_counter_bootstrap_guard` | any new public credential with `registration_sign_count=0` or `NO_USABLE_COUNTER` requires exactly one successful assertion projection; positive registration path is unaffected |
| `trg_0007_credential_event_authorizations_counter_bootstrap_guard` | before either forward-reference authorization is inserted, require the already-existing successful assertion to project its exact event ID/hash, authorization hash, credential, operation, outcome ID/hash, event type, and authorization kind; failure projections cannot authorize lifecycle rows |
| `trg_0007_credential_events_counter_bootstrap_guard` | projected `REGISTERED` and, for replace, `SUPERSEDED` events and authorization hashes must match the single successful assertion and outcome; no such rows may exist for a failed assertion |
| `trg_0007_counter_capability_assertions_counter_union_guard` | supported `0 -> positive` is the first and unique union edge; no issuer/operation/bootstrap fork or duplicate may exist |

All new-table UPDATE and DELETE operations are denied by six append-only
triggers: one UPDATE and one DELETE trigger for each of the three tables.

### 8.2 Existing trigger replacement audit

Only these frozen trigger definitions must be dropped and recreated by the
future additive migration, under the same names, because the SQL union itself
must gain the successful supported bootstrap assertion source:

1. `trg_reviewer_authentication_events_counter_union_guard`;
2. `trg_reviewer_credential_operation_authentication_counter_union_guard`.

Their base and leaf/prior/duplicate subqueries add
`reviewer_webauthn_counter_capability_assertions` where
`challenge_terminal_result='SUCCEEDED'`,
`classification_verified=1`, and
`selected_counter_capability='SIGN_COUNT_SUPPORTED'`, using
`webauthn_credential_id`, `previous_sign_count`, and `asserted_sign_count`.
The new-table counter trigger uses the identical three-source union. No trigger
weakens strict advancement.

The following frozen triggers are **not** replaced:

- `trg_reviewer_credential_operations_insert_guard`: every bootstrap terminal
  branch creates an exact frozen outcome, so the predecessor contract remains
  sufficient. The amendment only changes reconstruction to regard an
  unconsumed parent with one pending row as in-progress.
- `trg_reviewer_credential_operation_challenges_insert_guard`: `0006` continues
  to create only its normal registration challenge; the capability child lives
  in its own table.
- `trg_reviewer_credential_operation_consumptions_insert_guard`: its exact
  challenge, replay, expiry, continuation, and outcome mapping remain valid;
  the additive cross-ledger projection guard further restricts it.
- `trg_reviewer_webauthn_credentials_requires_registration_proof`: every
  admitted credential still has the exact successful frozen registration proof;
  the additive credential guard requires bootstrap proof where necessary.
- `trg_reviewer_webauthn_credential_events_requires_authorization` and
  `trg_reviewer_webauthn_credential_events_chain_guard`: successful projections
  use their existing exact lifecycle pattern; failures create no lifecycle row.
- `trg_reviewer_credential_operation_authentication_active_guard` and
  `trg_reviewer_authentication_events_credential_active_guard`: pending
  credentials do not enter either frozen authentication table, and old
  authorizers still must be active.
- `trg_reviewer_credential_operation_outcomes_insert_guard`: the projected
  outcome preserves its exact one/two/zero authorization counts and reverse
  binding; the additive outcome guard only adds bootstrap linkage.

No frozen append-only trigger is changed. The two exact additive UNIQUE indexes
on frozen tables are exhaustively named in section 8.0. They support composite
deferred FKs/projections and change neither existing data nor semantics.

## 9. Exact transaction projections

### 9.1 Zero-registration continuation transaction

One `BEGIN IMMEDIATE` transaction inserts the section 5 verified-zero row and
the section 6 child challenge. It inserts no frozen consumption, outcome,
credential, event, or authorization. For add/replace, the prior frozen
authorization assertion consumption, `VERIFIED` event, counter edge, and parent
registration challenge already exist and are unchanged.

### 9.2 Exact executable successful insertion order — P1-FR-02

The following is executable row order, not merely an inventory. Every operation
uses one `BEGIN IMMEDIATE` transaction with foreign keys enabled.

For `FIRST_ENROLLMENT` and `ADD_CREDENTIAL` success the exact order is:

1. insert the section 7 successful assertion. Its immediate guard reads only
   the already-committed pending row and child challenge and validates its
   self-contained projection. The FKs to the future frozen consumption,
   outcome, public credential and event are deliberately deferred;
2. insert the frozen `REGISTRATION_CREATE/SUCCEEDED` consumption. Frozen
   `trg_reviewer_credential_operation_consumptions_insert_guard` sees the
   already-existing frozen challenge and validates replay/expiry/outcome
   mapping. Additive
   `trg_0007_operation_consumptions_bootstrap_projection_guard` sees the
   already-existing assertion. Its FK to the future outcome remains deferred;
3. insert the `BOOTSTRAP_REGISTRATION` authorization for first or
   `AUTHORIZED_REGISTRATION` authorization for add. The additive authorization
   guard sees the assertion. The frozen table's FKs to the future public
   credential, lifecycle event, and outcome are deliberately deferred. For add,
   its old authorizing authentication event already exists from the earlier
   immutable assertion transaction;
4. insert the public credential. Frozen
   `trg_reviewer_webauthn_credentials_requires_registration_proof` now finds
   both the consumption from step 2 and authorization from step 3. The additive
   credential guard finds the assertion from step 1;
5. insert `REGISTERED`. Frozen
   `trg_reviewer_webauthn_credential_events_requires_authorization` now finds
   both the authorization and public credential; the chain guard proves a
   unique root. The additive event guard sees the assertion/authorization;
6. insert the frozen successful outcome last. Frozen
   `trg_reviewer_credential_operation_outcomes_insert_guard` now sees the exact
   successful consumption and one required authorization. The additive outcome
   guard sees the assertion. This resolves every remaining outcome FK; COMMIT
   resolves the authorization/assertion forward-reference cycles.

For `REPLACE_CREDENTIAL` success the exact order is:

1. section 7 successful assertion;
2. frozen successful registration consumption;
3. new-credential `AUTHORIZED_REGISTRATION` authorization;
4. old-target `AUTHORIZED_SUPERSESSION` authorization;
5. new public credential;
6. new `REGISTERED` root event;
7. old-target `SUPERSEDED` event, whose predecessor is the old target's already-
   existing `REGISTERED` root;
8. frozen successful outcome last.

Steps 1–2 have the same trigger/deferred-FK reasons as above. Both authorization
rows must exist before their events, and the registered authorization must
exist before the new credential. At step 7 the frozen authorization and chain
guards find the old public credential, exact authorization, and unsucceeded old
root. At step 8 the frozen outcome guard finds exactly two authorizations — one
registered/new and one superseded/old — for the same operation/principal/
outcome. COMMIT then resolves every deferred FK atomically. The prior authorizer
authentication/counter rows are never updated.

### 9.3 Exact executable failed or expired insertion order

For first, add, and replace, one `BEGIN IMMEDIATE` inserts exactly:

1. the section 7 failed/expired assertion projection. Its final frozen-row FKs
   are deferred and every credential/lifecycle projection is null;
2. the original frozen registration consumption with the exact failure or
   expiry terminal mapping. The frozen immediate guard sees the original
   challenge; the additive consumption guard sees step 1; its outcome FK is
   still deferred;
3. the frozen terminal outcome last. The frozen outcome guard now sees the
   consumption and requires zero lifecycle authorizations for an unsuccessful
   outcome; the additive outcome guard sees the exact projection.

Credential, lifecycle-event, and lifecycle-authorization inserts are exactly
zero. Expected and resulting state hashes are identical. COMMIT resolves the
assertion/consumption/outcome cycle. For add/replace the earlier authorizing
authentication/counter event remains immutable; for replace the old target
remains active. The exact frozen outcome is a legal predecessor for one fresh
successor operation.

### 9.4 Disposable SQLite proof

On `2026-08-29`, an uncommitted temporary Python/SQLite harness applied the
actual frozen `0001`–`0006`, materialized all three proposed table surfaces,
the complete FK and index design above, and the affected additive guards, then
executed the exact orders in sections 9.2/9.3 for:

- first `0 -> positive`, `0 -> 0`, and bootstrap failure;
- add `0 -> positive`, `0 -> 0`, and bootstrap failure; and
- replace `0 -> positive`, `0 -> 0`, and bootstrap failure.

Schema creation produced no foreign-key mismatch. All nine transactions
committed, and `PRAGMA foreign_key_check` returned zero rows for every database.
The proof code and all disposable databases were deleted and are not repository
artifacts. This is local design evidence, not a created migration or CI result.

## 10. Restart and replay reconstruction

For each `0006` operation, reconstruction is exactly one of:

1. no parent challenge use marker: await the original ceremony while live;
2. one section 5 pending row plus its child and no section 7 row: await exactly
   that child while both child and parent are live;
3. one section 7 row plus exact frozen consumption/outcome projection: terminal;
4. ordinary frozen parent consumption with no pending row: positive-registration
   path and terminal;
5. any other combination: corruption/fail closed.

UNIQUE constraints prevent a second pending use, child, assertion, frozen
consumption, or outcome. A replay cannot become a second counter edge. The
server retains no raw challenge, browser memory, session, recovery token, or
login state.

## 11. User-handle schema sufficiency

This is a deliberate two-layer account model. Each credential slot is a
distinct WebAuthn user-account namespace at the authenticator layer, even
though WebAuthn says a handle ought normally be shared by credentials of one
user account. The deviation is necessary because the accepted product permits
multiple active credentials while requiring discoverable platform credentials,
and an authenticator stores at most one discoverable credential for an
`(rpId,userHandle)` pair. Every slot nevertheless maps server-side to exactly
the same `LOCAL_DATA_STEWARD` authorization principal. It does not create
multiple reviewer principals, login discovery, or recovery state.

No user-handle value column is required in `0007` or in the frozen credential
table. For a pending credential, the exact operation ID is copied into all three
proposed rows. For an admitted credential, restart follows its unique root
`REGISTERED` event to its exact event authorization and therefore to the exact
registering operation. The server recomputes the 32 raw bytes from the immutable
principal and operation IDs.

The challenge binds the handle-contract version but not a duplicate handle
value. Returned raw `userHandle` is transient and never logged or persisted.
Section 7 stores only `MATCHED`, `ABSENT_ALLOWED`, `MISMATCHED`, or
`NOT_EVALUATED`. A mismatch cannot produce a verified assertion. This is
sufficient for deterministic restart reconstruction and avoids a second
possibly divergent identity field.

## 12. Hash dependency DAG

```text
canonical Windows SID text -> os_owner_sid_hash -> principal_content_hash
principal ID + credential-creating operation ID -> raw 32-byte user handle
raw credential ID -> canonical credential ID + credential_id_fingerprint ----+
raw COSE_Key -> CTAP2 canonical bytes -> public_key_fingerprint --------------+-> pending-registration hash
raw parent challenge -> frozen challenge_digest -> frozen challenge binding --+
pending-registration hash + raw child challenge digest + child timing/options
  -> child challenge binding hash
child binding + verified assertion + preallocated frozen projection IDs/hashes
  -> assertion content hash
assertion projection -> frozen registration consumption -> public credential
  + lifecycle authorization + frozen outcome
supported bootstrap assertion edge -> later three-ledger counter-union leaf
```

Preallocated IDs are independent random inputs. No content hash contains a
descendant content hash that points back to it. The assertion may contain the
already-calculable frozen projection hashes; no frozen hash contains the
assertion hash. The graph is acyclic.

## 13. Scope and gate

This proposal changes application, migration, test, dependency, fixture, and
frontend files by `0`. It performs no trusted-human WebAuthn or issuer-approval
runtime. ADR-017 and ADR-018 are accepted. Revised ADR-019 is vendor-neutral,
remains proposed, and changes none of this schema companion unless separately
accepted. `0007` is not created and not authorized. R1, B2-D, CP3-C2-C, and
CP3-D remain not started. R1 remains blocked on ADR-019.
