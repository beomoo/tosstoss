# Phase 02 CP3-C2-B2-C Runtime Canonicalization Gap — Codex Report

- Date: `2026-08-28`
- Authoritative starting SHA:
  `391fa38808033640081565ca9649bbba3501f071`
- Branch: `feature/phase-02-toss`
- Verdict: `BLOCKED — APPROVED RUNTIME CONTRACT GAP / ADR-017 PROPOSED`
- ADR-015: `ACCEPTED`
- ADR-016: `ACCEPTED`
- ADR-017: `PROPOSED`, decision date `NONE`
- `0006`: `PASS — CLOSED`
- R1 runtime implementation: `NOT STARTED`, runtime changed files `0`

Post-review addendum: independent review of the resulting authoritative SHA
`c76fe7616db65c53ffc5a81d3e3c0cb390c0fa3b` returned `CHANGES REQUIRED`, P0
`0`, P1 `1`, P2 `2`. ADR-017 is now `PROPOSED — CHANGES REQUIRED / RG-06 OPEN`;
ADR-018 is `PROPOSED`; future `0007` is `NOT CREATED / NOT AUTHORIZED`. The
original evidence below remains a historical snapshot. RG-01 through RG-05 and
all ten vector bytes remain unchanged; the remediation report is
`qa/PHASE_02_CP3_C2_B2_C_ADR_017_COUNTER_CAPABILITY_REMEDIATION_CODEX_REPORT.md`.

## 1. Scope and stop decision

The pre-implementation audit confirmed that the approved schema did not fully
determine the persisted runtime bytes. Implementing R1 before an accepted
amendment would choose an undocumented identity contract. Codex therefore made
no application, schema, migration, test, script, frontend, fixture, dependency
or lock-file change and did not invoke Windows Hello.

| Gap | Exact missing boundary | Resolution proposed by ADR-017 |
|---|---|---|
| RG-01 | principal hash preimage | exact six-key principal object |
| RG-02 | credential hash preimage | exact 18-key credential object, null/counter/transport rules |
| RG-03 | COSE bytes/TEXT/algorithm | CTAP2 canonical CBOR bytes, unpadded base64url TEXT, raw-byte hash, `-7/-257` only; RFC 8949 is the underlying CBOR reference |
| RG-04 | challenge digest/binding | raw 32-byte digest plus exact operation and issuer binding objects |
| RG-05 | authentication hash | exact operation and issuer relational preimages |

### 1.1 Exact proposed preimage inventory

All JSON objects use ADR-017's NFC, recursive unsigned-UTF-8 key order and
compact UTF-8 serialization. Listed nullable keys are explicit JSON `null`;
SQLite verification integers become JSON Booleans. Unlisted keys are excluded
and forbidden.

- `principal_content_hash` keys exactly: `contract_version`,
  `enrollment_policy_version`, `os_owner_sid_hash`, `principal_state`,
  `reviewer_principal_id`, `reviewer_role`. Excluded: its own hash,
  `registered_at`, `payload_json` and process/audit identity.
- `credential_content_hash` keys exactly: `authenticator_aaguid`,
  `authenticator_attachment`, `authenticator_transports`, `contract_version`,
  `cose_public_key_canonical`, `counter_capability`,
  `credential_id_fingerprint`, `principal_content_hash`,
  `public_key_algorithm`, `public_key_fingerprint`,
  `registration_policy_version`, `registration_sign_count`,
  `resident_key_required`, `reviewer_principal_id`, `reviewer_role`, `rp_id`,
  `user_verification_required`, `webauthn_credential_id`. Excluded: its own
  hash, `registered_at`, `payload_json` and process/audit identity.
- Operation `challenge_binding_hash` keys exactly: `allowed_origin`,
  `authentication_policy_version`, `challenge_digest`,
  `challenge_nonce_length`, `challenge_purpose`, `client_data_type`,
  `contract_version`, `expected_credential_state_hash`, `expires_at`,
  `issued_at`, `operation_content_hash`, `operation_type`,
  `os_owner_sid_hash`, `platform_attachment_required`,
  `prerequisite_authentication_content_hash`,
  `prerequisite_authentication_event_id`,
  `prerequisite_authentication_result`, `principal_content_hash`,
  `resident_key_required`, `reviewer_credential_operation_challenge_id`,
  `reviewer_credential_operation_id`, `reviewer_principal_id`,
  `reviewer_role`, `rp_id`, `target_credential_id_fingerprint`,
  `target_webauthn_credential_id`, `user_verification_required`. Excluded:
  its own binding hash, payload and later consumption/authentication/outcome.
- Operation `authentication_content_hash` keys exactly: `asserted_sign_count`,
  `authentication_policy_version`, `authentication_result`,
  `authorizing_webauthn_credential_id`, `challenge_binding_hash`,
  `challenge_consumption_content_hash`, `challenge_consumption_id`,
  `challenge_purpose`, `challenge_terminal_result`, `contract_version`,
  `counter_capability`, `counter_verified`, `credential_id_fingerprint`,
  `exact_origin`, `expected_credential_state_hash`, `operation_content_hash`,
  `operation_type`, `origin_verified`, `os_owner_sid_hash`,
  `previous_sign_count`, `principal_content_hash`, `public_key_fingerprint`,
  `replay_rejected`, `reviewer_credential_operation_challenge_id`,
  `reviewer_credential_operation_id`, `reviewer_principal_id`,
  `reviewer_role`, `rp_id`, `rp_id_hash_verified`, `safe_result_code`,
  `signature_verified`, `user_presence_verified`,
  `user_verification_verified`. Excluded: event ID, its own hash,
  `authenticated_at` and payload.
- Issuer `challenge_binding_hash` keys exactly: `allowed_origin`,
  `authentication_policy_version`, `authority_bundle_id`, `challenge_digest`,
  `contract_version`, `expected_bundle_content_hash`,
  `expected_decision_content_hash`, `expires_at`, `issued_at`,
  `issuer_approval_challenge_id`, `issuer_decision_id`,
  `predecessor_approval_event_id`, `predecessor_link_id`,
  `principal_content_hash`, `proposed_issuer_id`,
  `provider_security_identity_id`, `requested_disposition`,
  `reviewer_principal_id`, `reviewer_role`, `rp_id`,
  `successor_decision_id`, `user_verification_required`. Excluded: its own
  binding hash, payload and later consumption/authentication/approval fields.
- Issuer `authentication_content_hash` keys exactly: `asserted_sign_count`,
  `authentication_policy_version`, `authentication_result`,
  `authority_bundle_id`, `challenge_consumption_id`, `contract_version`,
  `counter_capability`, `counter_verified`, `credential_id_fingerprint`,
  `exact_origin`, `expected_bundle_content_hash`,
  `expected_decision_content_hash`, `issuer_approval_challenge_id`,
  `issuer_decision_id`, `origin_verified`, `previous_sign_count`,
  `public_key_fingerprint`, `replay_rejected`, `requested_disposition`,
  `reviewer_principal_id`, `reviewer_role`, `rp_id`, `rp_id_hash_verified`,
  `safe_result_code`, `signature_verified`, `user_presence_verified`,
  `user_verification_verified`, `webauthn_credential_id`. Excluded: event ID,
  its own hash, `authenticated_at` and payload.

Both challenge digests are SHA-256 of exactly the raw 32 OS-CSPRNG bytes; raw
bytes are transient. Credential-ID TEXT is canonical unpadded base64url of raw
ID bytes and its fingerprint hashes those raw bytes. COSE TEXT is canonical
unpadded base64url of CTAP2 canonical CBOR and its fingerprint hashes those raw
CBOR bytes. The only algorithm mappings are `-7 -> ES256` and
`-257 -> RS256`; unknown or alternate encodings fail closed. Existing event,
operation, consumption, outcome, authorization and credential-state preimages
remain unchanged.

## 2. Hash-DAG audit

Result: `PASS — NO CRYPTOGRAPHIC CYCLE`.

```text
SID -> SID hash -> principal hash
credential bytes -> credential ID/fingerprint -----------------------------+
COSE_Key -> CTAP2 canonical CBOR -> public-key fingerprint ----------------+-> credential hash
principal + credential/event leaves -> credential-state hash
principal + expected state + preallocated challenge ID -> operation hash
raw challenge -> digest
operation hash + digest + preallocated challenge ID -> operation binding hash
operation binding -> consumption hash -> operation authentication hash
operation authentication + consumption -> outcome hash -> authorization hash

decision + bundle + principal + raw challenge digest + preallocated ID
  -> issuer binding hash -> issuer consumption hash
  -> issuer authentication hash -> approval/link hashes
```

Opaque IDs are independently preallocated and are never derived from a child
hash. An ancestor never contains a descendant hash. The existing exact event,
operation, consumption, authorization, outcome and state preimages are not
changed.

## 3. Golden-vector method

The temporary, uncommitted Python 3.13 calculator applied Unicode NFC,
recursive unsigned-UTF-8 key order, compact UTF-8 JSON and
`sha256:<lowerhex>`. For the two restricted COSE key maps it used
`cbor2.dumps(map, canonical=True)`, re-decoded for semantic equality, then
passed both COSE keys through
`webauthn.helpers.decode_credential_public_key` and
`decoded_public_key_to_cryptography`. It was run twice and the complete output
was byte-identical.

P2-RG-07 clarification: WebAuthn requires the **CTAP2 canonical CBOR encoding
form** for `credentialPublicKey`; RFC 8949 is only the underlying CBOR
reference. Generic `cbor2` canonical output is not claimed to be a general
CTAP2 encoder. A later independent standard-library CTAP2 encoder reproduced
the exact GV-02/GV-03 hex, base64url and fingerprints because the approved maps
contain only the fixed integer labels shown below. No vector byte changed.

```text
vector_count: 10
first_run == second_run: true
complete_output_sha256: e247854da41eb43b0bdc5559e69f8f99791a8c73c20ef71a19a9532db47b5da6
Python: 3.13.15
webauthn: 3.0.0
cbor2: 6.1.4
```

For JSON vectors, each `serialized UTF-8` payload is the complete exact input
object after canonicalization and the exact byte sequence to hash, with no BOM
or terminal newline. Where labeled as chunks, concatenate the physical payload
lines with no separator or newline. For CBOR vectors, the diagnostic map is the
exact semantic input and `CTAP2 canonical CBOR hex` is the exact byte sequence.

### GV-01 — principal content

```text
serialized UTF-8:
{"contract_version":"issuer-steward-webauthn/0.1.0","enrollment_policy_version":"issuer-steward-webauthn/0.1.0","os_owner_sid_hash":"sha256:49e334455cab2a7cc0a98862d1c6d2ddfb1274f224acb56f9432fcbf1a7ed4c2","principal_state":"ACTIVE","reviewer_principal_id":"rvp_0123456789abcdef0123456789abcdef","reviewer_role":"LOCAL_DATA_STEWARD"}
expected principal_content_hash:
sha256:d48459e52349d73b433179f02ce735acb153201ab0700ff103135b7f9e9a2029
```

The SID digest input label was the explicitly synthetic ASCII text
`synthetic-os-owner-sid`; no real SID was read or persisted for this vector.

### GV-02 — ES256 CTAP2 canonical COSE_Key

```text
diagnostic map (`-2`/`-3` hex lines are concatenated with no separator):
1=2, 3=-7, -1=1
-2:
6b17d1f2e12c4247
f8bce6e563a440f2
77037d812deb33a0
f4a13945d898c296
-3:
4fe342e2fe1a7f9b
8ee7eb4a7c0f9e16
2bce33576b315ece
cbb6406837bf51f5
CTAP2 canonical CBOR hex:
a50102032620012158206b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c2962258204fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5
expected cose_public_key_canonical:
pQECAyYgASFYIGsX0fLhLEJH-Lzm5WOkQPJ3A32BLeszoPShOUXYmMKWIlggT-NC4v4af5uO5-tKfA-eFivOM1drMV7Oy7ZAaDe_UfU
expected public_key_fingerprint:
sha256:72080e17877c7fe10b105ea40eea474975a16cf7773c03745aa64c025b6a4e63
```

### GV-03 — RS256 CTAP2 canonical COSE_Key

```text
diagnostic map:
{1:3,3:-257,-1:h'c7000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001',-2:h'010001'}
CTAP2 canonical CBOR hex:
a401030339010020590100c70000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000012143010001
expected cose_public_key_canonical:
pAEDAzkBACBZAQDHAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABIUMBAAE
expected public_key_fingerprint:
sha256:1f9704f5f7703f630f3e38815adda23add3f51cf760f0321e89a361e70288270
```

### GV-04 — credential with supported counter

```text
serialized UTF-8 chunks (concatenate physical lines with no separator/newline):
{"authenticator_aaguid":"00112233-4455-6677-8899-aabbccddeeff","authenticator_attachment":"platform","authenticator_transports":["hybrid","internal"],"contract_version":"issuer-steward-webauthn/0.1.0","cose_public_key_canonical":"pQECAyYgASFYIGs
X0fLhLEJH-Lzm5WOk
QPJ3A32BLeszoPSh
OUXYmMKWIlggT-NC
4v4af5uO5-tKfA-e
FivOM1drMV7Oy7ZA
aDe_UfU","counter_capability":"SIGN_COUNT_SUPPORTED","credential_id_fingerprint":"sha256:a8faed6abbf35c12a4b26e40f6feb19d736d90045c83b9f9a31f638d323e6811","principal_content_hash":"sha256:d48459e52349d73b433179f02ce735acb153201ab0700ff103135b7f9e9a2029","public_key_algorithm":"ES256","public_key_fingerprint":"sha256:72080e17877c7fe10b105ea40eea474975a16cf7773c03745aa64c025b6a4e63","registration_policy_version":"issuer-steward-webauthn/0.1.0","registration_sign_count":7,"resident_key_required":true,"reviewer_principal_id":"rvp_0123456789abcdef0123456789abcdef","reviewer_role":"LOCAL_DATA_STEWARD","rp_id":"localhost","user_verification_required":true,"webauthn_credential_id":"ABEiM0RVZneImaq7zN3u_w"}
expected credential_content_hash:
sha256:c2982bdd18f8d1029cfbd568242b986259438f47666c1d1275f595aeba85e1a3
```

### GV-05 — credential with no usable counter

Under the ADR-018 proposal this unchanged credential vector is admissible only
after a fully verified bootstrap observation `registration 0 -> assertion 0`.
The two observed zeros live in the proposed bootstrap audit; the frozen
credential preimage truthfully retains `registration_sign_count:null`.

```text
serialized UTF-8 chunks (concatenate physical lines with no separator/newline):
{"authenticator_aaguid":"00112233-4455-6677-8899-aabbccddeeff","authenticator_attachment":"platform","authenticator_transports":["hybrid","internal"],"contract_version":"issuer-steward-webauthn/0.1.0","cose_public_key_canonical":"pQECAyYgASFYIGs
X0fLhLEJH-Lzm5WOk
QPJ3A32BLeszoPSh
OUXYmMKWIlggT-NC
4v4af5uO5-tKfA-e
FivOM1drMV7Oy7ZA
aDe_UfU","counter_capability":"NO_USABLE_COUNTER","credential_id_fingerprint":"sha256:a8faed6abbf35c12a4b26e40f6feb19d736d90045c83b9f9a31f638d323e6811","principal_content_hash":"sha256:d48459e52349d73b433179f02ce735acb153201ab0700ff103135b7f9e9a2029","public_key_algorithm":"ES256","public_key_fingerprint":"sha256:72080e17877c7fe10b105ea40eea474975a16cf7773c03745aa64c025b6a4e63","registration_policy_version":"issuer-steward-webauthn/0.1.0","registration_sign_count":null,"resident_key_required":true,"reviewer_principal_id":"rvp_0123456789abcdef0123456789abcdef","reviewer_role":"LOCAL_DATA_STEWARD","rp_id":"localhost","user_verification_required":true,"webauthn_credential_id":"ABEiM0RVZneImaq7zN3u_w"}
expected credential_content_hash:
sha256:19ec318af96da20e23e65169373522fb34d96be7538e91ae1c8d8fcad1bd1e76
```

### GV-06 — fixed raw 32-byte challenge digest

```text
raw challenge hex:
000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f
expected challenge_digest:
sha256:630dcd2966c4336691125448bbb25b4ff412a49c732db2c8abc1b8581bd710dd
```

### GV-07 — operation challenge binding

```text
serialized UTF-8:
{"allowed_origin":"http://localhost:3000","authentication_policy_version":"issuer-steward-webauthn/0.1.0","challenge_digest":"sha256:630dcd2966c4336691125448bbb25b4ff412a49c732db2c8abc1b8581bd710dd","challenge_nonce_length":32,"challenge_purpose":"REGISTRATION_CREATE","client_data_type":"webauthn.create","contract_version":"reviewer-credential-operation-challenge/0.1.0","expected_credential_state_hash":"sha256:fd93f03531ea3126c3ada3db3cb57f85d3c856561592b88ddedd6c1152794ea4","expires_at":"2026-08-28T00:05:00Z","issued_at":"2026-08-28T00:00:00Z","operation_content_hash":"sha256:ca68c9d4f03c5559416e4c319df97d774d45830fad5e8cffc511848f11e8640d","operation_type":"FIRST_ENROLLMENT","os_owner_sid_hash":"sha256:49e334455cab2a7cc0a98862d1c6d2ddfb1274f224acb56f9432fcbf1a7ed4c2","platform_attachment_required":true,"prerequisite_authentication_content_hash":null,"prerequisite_authentication_event_id":null,"prerequisite_authentication_result":null,"principal_content_hash":"sha256:d48459e52349d73b433179f02ce735acb153201ab0700ff103135b7f9e9a2029","resident_key_required":true,"reviewer_credential_operation_challenge_id":"rch_0123456789abcdef0123456789abcdef","reviewer_credential_operation_id":"rop_0123456789abcdef0123456789abcdef","reviewer_principal_id":"rvp_0123456789abcdef0123456789abcdef","reviewer_role":"LOCAL_DATA_STEWARD","rp_id":"localhost","target_credential_id_fingerprint":null,"target_webauthn_credential_id":null,"user_verification_required":true}
expected challenge_binding_hash:
sha256:e888577fa8be92e87eb86f66692ffbeec778e2e0e397eb48fc5322d620d6befa
```

### GV-08 — operation authentication content

```text
serialized UTF-8:
{"asserted_sign_count":8,"authentication_policy_version":"issuer-steward-webauthn/0.1.0","authentication_result":"VERIFIED","authorizing_webauthn_credential_id":"ABEiM0RVZneImaq7zN3u_w","challenge_binding_hash":"sha256:4bd807586f0e89511f921054e646fbfb22a422f710e38dbf798074e495dba3d5","challenge_consumption_content_hash":"sha256:520eeddd8ffa0efed5b774110926aaa3ec627dc0cacb2e259ff95da6523d8ea4","challenge_consumption_id":"rcc_0123456789abcdef0123456789abcdef","challenge_purpose":"AUTHORIZATION_ASSERTION","challenge_terminal_result":"SUCCEEDED","contract_version":"reviewer-credential-operation-authentication/0.1.0","counter_capability":"SIGN_COUNT_SUPPORTED","counter_verified":true,"credential_id_fingerprint":"sha256:a8faed6abbf35c12a4b26e40f6feb19d736d90045c83b9f9a31f638d323e6811","exact_origin":"http://localhost:3000","expected_credential_state_hash":"sha256:197aba8ad5396f9c941ed20773cdf77ab15bc3295fd4588f11bd69763ae90280","operation_content_hash":"sha256:c19c3ec47fce14380f4cbcfc8b2f31bd5fbb872c139f29dfdac4d6a911a68235","operation_type":"ADD_CREDENTIAL","origin_verified":true,"os_owner_sid_hash":"sha256:49e334455cab2a7cc0a98862d1c6d2ddfb1274f224acb56f9432fcbf1a7ed4c2","previous_sign_count":7,"principal_content_hash":"sha256:d48459e52349d73b433179f02ce735acb153201ab0700ff103135b7f9e9a2029","public_key_fingerprint":"sha256:72080e17877c7fe10b105ea40eea474975a16cf7773c03745aa64c025b6a4e63","replay_rejected":true,"reviewer_credential_operation_challenge_id":"rch_fedcba9876543210fedcba9876543210","reviewer_credential_operation_id":"rop_fedcba9876543210fedcba9876543210","reviewer_principal_id":"rvp_0123456789abcdef0123456789abcdef","reviewer_role":"LOCAL_DATA_STEWARD","rp_id":"localhost","rp_id_hash_verified":true,"safe_result_code":"AUTHENTICATION_VERIFIED","signature_verified":true,"user_presence_verified":true,"user_verification_verified":true}
expected authentication_content_hash:
sha256:4f379de5567f92ce2f1215ea2339b7ee8938d940c294c22fa5bbd4b25812d193
```

### GV-09 — issuer challenge digest and binding

```text
raw challenge hex:
202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f
expected challenge_digest:
sha256:72dbb7336c76780023f83da4c355f2eeea85733b13d3477697917790c1229084
serialized UTF-8:
{"allowed_origin":"http://localhost:3000","authentication_policy_version":"issuer-steward-webauthn/0.1.0","authority_bundle_id":"abn_0123456789abcdef0123456789abcdef","challenge_digest":"sha256:72dbb7336c76780023f83da4c355f2eeea85733b13d3477697917790c1229084","contract_version":"issuer-approval-challenge/0.1.0","expected_bundle_content_hash":"sha256:f798cb21cc07b6ba03f1621b3a6bffc120e3a55b6fb56e6811a5e9fe37b96aa6","expected_decision_content_hash":"sha256:f7ab91fa9362bafa970057c2c7af33c0566ecbf37abf7635f1ba9dbf33c4a67b","expires_at":"2026-08-28T00:05:00Z","issued_at":"2026-08-28T00:00:00Z","issuer_approval_challenge_id":"iac_0123456789abcdef0123456789abcdef","issuer_decision_id":"idc_0123456789abcdef0123456789abcdef","predecessor_approval_event_id":null,"predecessor_link_id":null,"principal_content_hash":"sha256:d48459e52349d73b433179f02ce735acb153201ab0700ff103135b7f9e9a2029","proposed_issuer_id":"isr_0123456789abcdef0123456789abcdef","provider_security_identity_id":"psi_0123456789abcdef0123456789abcdef","requested_disposition":"APPROVED","reviewer_principal_id":"rvp_0123456789abcdef0123456789abcdef","reviewer_role":"LOCAL_DATA_STEWARD","rp_id":"localhost","successor_decision_id":null,"user_verification_required":true}
expected challenge_binding_hash:
sha256:63d824e6d016ba693c716b0d0c4b882eeeb8c2eb91d5fc65e3736ac0ef78a1ef
```

### GV-10 — issuer authentication content

```text
serialized UTF-8:
{"asserted_sign_count":8,"authentication_policy_version":"issuer-steward-webauthn/0.1.0","authentication_result":"VERIFIED","authority_bundle_id":"abn_0123456789abcdef0123456789abcdef","challenge_consumption_id":"iacn_0123456789abcdef0123456789abcdef","contract_version":"issuer-steward-webauthn/0.1.0","counter_capability":"SIGN_COUNT_SUPPORTED","counter_verified":true,"credential_id_fingerprint":"sha256:a8faed6abbf35c12a4b26e40f6feb19d736d90045c83b9f9a31f638d323e6811","exact_origin":"http://localhost:3000","expected_bundle_content_hash":"sha256:f798cb21cc07b6ba03f1621b3a6bffc120e3a55b6fb56e6811a5e9fe37b96aa6","expected_decision_content_hash":"sha256:f7ab91fa9362bafa970057c2c7af33c0566ecbf37abf7635f1ba9dbf33c4a67b","issuer_approval_challenge_id":"iac_0123456789abcdef0123456789abcdef","issuer_decision_id":"idc_0123456789abcdef0123456789abcdef","origin_verified":true,"previous_sign_count":7,"public_key_fingerprint":"sha256:72080e17877c7fe10b105ea40eea474975a16cf7773c03745aa64c025b6a4e63","replay_rejected":true,"requested_disposition":"APPROVED","reviewer_principal_id":"rvp_0123456789abcdef0123456789abcdef","reviewer_role":"LOCAL_DATA_STEWARD","rp_id":"localhost","rp_id_hash_verified":true,"safe_result_code":"AUTHENTICATION_VERIFIED","signature_verified":true,"user_presence_verified":true,"user_verification_verified":true,"webauthn_credential_id":"ABEiM0RVZneImaq7zN3u_w"}
expected authentication_content_hash:
sha256:9080a5955173c30f9c58444946e128d9ddfa6fca4d59386f8ec8698df6092bdb
```

## 4. WebAuthn feasibility evidence

The isolated audit imported `webauthn==3.0.0` under Python 3.13.15 and exposed
the expected four high-level APIs:

```text
generate_registration_options
verify_registration_response
generate_authentication_options
verify_authentication_response
```

The library returns raw credential public-key COSE bytes. Its helper CBOR
encoder is not itself a complete contract boundary, so ADR-017 requires a
validated map, CTAP2 canonical CBOR re-encoding, semantic re-decode equality
and original-byte equality. RFC 8949 remains the underlying CBOR reference.
Both approved algorithms passed the library's COSE decode and cryptography
conversion in this audit. No repository dependency was installed or changed
during this documentation task.

## 5. Change inventory

Documentation changes are limited to the user allowlist. Final application
surface counts are:

```text
application files changed: 0
schema/migration files changed: 0
new migrations: 0
0007: 0
runtime files changed: 0
tests/scripts/frontend/fixtures changed: 0
dependency or lock files changed: 0
actual Windows Hello ceremonies: 0
issuer approvals/authentications written: 0
```

Exact changed paths:

```text
CHANGELOG.md
DECISIONS.md
KNOWN_ISSUES.md
STATUS.md
plans/PHASE_02_CP3_C2_B1_RUNTIME_CONTRACT.md
plans/PHASE_02_CP3_C2_B2_C_SCHEMA_REMEDIATION.md
plans/PHASE_02_EXECUTION_PLAN.md
qa/PHASE_02_CP3_C2_B2_C_RUNTIME_CANONICALIZATION_GAP_CODEX_REPORT.md
```

Frozen migration Git blob IDs at the authoritative start and after this task:

```text
0001_phase_01_foundation.py                         d00355c2456021e6ffb195e50833adc32c74a4ad
0002_phase_02_cp3_foundation.py                    53f40664eca2ea2466cc6154b8579c5db506e0ba
0003_phase_02_cp3_b_invariants.py                  47d5a69009949b155211cd68209640136a7cacd9
0004_phase_02_cp3_c1_security_master.py            91b4d96a445be23e7aa55e08b9310dc7334a026d
0005_phase_02_cp3_c2_b_issuer_authority.py         81976b8f70a1f6107526a13acadf23f369b196e3
0006_phase_02_cp3_c2_b2_c_reviewer_operations.py  f10e7f5bc21e232fc68b38144f5b8fb124f31698
```

## 6. QA results

LOCAL closeout results:

| Gate | Result |
|---|---|
| authoritative clean start | PASS — local HEAD and remote feature were `391fa38808033640081565ca9649bbba3501f071`; remote main was `353159da45cfbe3a7f444bf476ce86fa9aece17c` |
| `git diff --check` | PASS |
| `git diff --cached --check` | PASS |
| exact docs-only changed-path allowlist | PASS — exactly the 8 paths in section 5; unexpected/missing/unstaged/untracked `0` |
| no application/runtime/test/script/frontend/fixture/dependency change | PASS — implied and explicitly checked by the exact allowlist |
| `0001`–`0006` blob equality | PASS — all six exact IDs in section 5 |
| golden-vector generation | PASS — 10 vectors, two full outputs byte-identical |
| report-vector independent recalculation | PASS — canonical JSON `7`, CTAP2 canonical COSE `2`, raw challenge `2` |
| ADR/status/plan consistency | PASS — 11 checks; ADR-017 not recorded accepted, later checkpoints not started, no `0007` path |
| `scripts/secret-scan.ps1` | PASS on final staged content |
| `scripts/policy-scan.ps1` | PASS — Phase 2 CP3-C2-B2-C scope policy |
| real Windows Hello/issuer approval | NOT RUN, as required |

The first secret-scan attempt reported three high-entropy findings in the
public synthetic COSE vector. No exception, filter, skip or suppression was
added. The same exact bytes were rendered as explicitly concatenated short
chunks, the vector hashes were recalculated successfully, and the unchanged
repository scanner then passed. This preserves both reproducibility and the
existing security policy.

Final branch/remote SHA and unchanged remote `main` are verified after commit
and push because the commit SHA does not exist while this report is authored.

GitHub CI execution evidence remains absent and non-blocking for this
documentation proposal. LOCAL checks are not represented as GitHub CI.

## 7. Final control-plane state

ADR-017 is a proposal awaiting independent GPT review and explicit user
acceptance. This report does not accept it. R1 remains blocked and not started.
CP3-C2-B2-D, CP3-C2-C and CP3-D remain not started, with automatic progression
prohibited.
