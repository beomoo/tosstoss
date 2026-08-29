# ADR-017 / ADR-018 Full R1 Implementability Remediation — Codex Report

## 1. Authority, verdict, and boundary

- Repository: `beomoo/tosstoss`
- Branch: `feature/phase-02-toss`
- Authoritative starting SHA:
  `c34d8ca5a25bbea8c4ff410b7d62dc451f357528`
- Independent verdict: `CHANGES REQUIRED`
- Findings: P0 `0`, P1 `3`, P2 `2`
- Scope: documentation/control-plane only
- ADR-017: `PROPOSED — AWAITING INDEPENDENT RE-REVIEW`
- ADR-018: `PROPOSED — AWAITING INDEPENDENT REVIEW`
- `0006`: `PASS — CLOSED`
- R1: `NOT STARTED / BLOCKED`
- proposed future
  `0007_phase_02_cp3_c2_b2_c_counter_capability_bootstrap`:
  `NOT CREATED / NOT AUTHORIZED`
- automatic progression: `PROHIBITED`

Codex does not declare RG-08, RG-09, or RG-10 closed and does not accept either
ADR. ADR-015/ADR-016 remain accepted. SG-01, SG-02, P1-SR-01, P1-SR-02,
P1-SR-03, IG-01, and IG-02 remain closed and were not reopened.

## 2. Findings remediated in the proposal

### P1-RG-08 — every new credential

The ambiguity applies to `FIRST_ENROLLMENT`, `ADD_CREDENTIAL`, and
`REPLACE_CREDENTIAL`; revoke is excluded. Positive registration remains on the
normal frozen path. Zero registration creates one pending verified-public-key
row and one fresh exact-credential assertion challenge, but no public credential
or frozen registration consumption yet.

For ADD/REPLACE, the earlier successful `AUTHORIZATION_ASSERTION` consumption,
`VERIFIED` authentication event, supported authorizer counter edge, and single
frozen registration challenge are immutable. Success finishes that same
operation. Failure terminalizes that operation without credential/lifecycle
writes and with expected state equal to resulting state. REPLACE success
atomically creates new `REGISTERED` plus old-target `SUPERSEDED`; failure leaves
the old target ACTIVE.

Every branch ultimately creates an exact frozen `0006` registration consumption
and outcome. This is the proof that a failed branch can be the exact predecessor
of one fresh successor operation. No proposed-only terminal state is substituted
for the frozen predecessor contract.

### P1-RG-09 — exact user entity and handle

The selected model is one deterministic credential-slot handle per credential-
creating operation, all mapped server-side to the same steward principal:

```text
SHA256(
  ASCII("issuer-steward-webauthn-user-handle/0.1.0") || 0x00 ||
  UTF8_NFC(reviewer_principal_id) || 0x00 ||
  UTF8_NFC(reviewer_credential_operation_id)
)
```

The result is exactly 32 raw bytes, with no `sha256:` prefix. Per-slot handles
are necessary because discoverable credentials are keyed by `(rpId,userHandle)`
on the authenticator; one stable principal handle could overwrite an earlier
credential and defeat the accepted multiple-active-credentials contract.

Exact display-only constants are `rp.name="localhost"`,
`user.name="local-data-steward"`, and
`user.displayName="Local Data Steward"`. They contain no personal identity and
provide no authority.

Every assertion has a non-empty `allowCredentials`. The capability assertion
contains exactly the pending credential; operation and future issuer assertions
contain only exact allowed active credentials. A present returned `userHandle`
must equal the reconstructed value; absence is permitted with the non-empty
allow list. Empty/discoverable-account login is outside R1.

No handle-value column is required. Pending state already stores the exact
operation. After admission, the unique root `REGISTERED` event and exact
authorization identify the registering operation. Restart therefore derives the
same bytes from immutable principal and operation IDs without browser memory.

### P1-RG-10 — exact SID bytes

Production Windows uses the current process access token, calls
`GetTokenInformation(..., TokenUser, ...)`, validates the exact `TOKEN_USER`
SID, and converts it using `ConvertSidToStringSidW`. The hash is:

```text
"sha256:" + lowerhex(SHA256(UTF8(canonical_windows_sid_text)))
```

No UTF-16 bytes, terminating NUL, case folding, whitespace, account name,
environment username, caller value, alias, binary SID, or textual digest prefix
enters the preimage. Raw SID text is transient and never persisted/logged.
OpenProcessToken, TokenUser, SID validation, or conversion failure fails closed;
non-Windows production fails closed.

### P2-RG-11 — exact registration proof

Registration requests `authenticatorAttachment=platform`,
`residentKey=required`, `requireResidentKey=true`, `userVerification=required`,
`attestation=none`, and `credProps=true`.

`platform_authenticator_verified=1` requires cryptographic success and returned
attachment exactly `platform`; null/cross-platform/unknown rejects.
`resident_key_verified=1` requires creation under the exact required option;
present `credProps.rk` must be true, false rejects, and absence does not by
itself contradict successful required-resident-key creation.
`public_key_material_verified=1` additionally requires canonical credential ID,
CTAP2-canonical COSE bytes, and exact ES256/RS256 allowlisting. These ceremony
outputs are not new attestation authority. No FIDO Metadata Service or vendor
trust root is added.

## 3. All-operation schema projection

The implementation-ready normative proposal is
`plans/PHASE_02_CP3_C2_B2_C_ADR_018_COUNTER_CAPABILITY_SCHEMA_PROPOSAL.md`.
It retains three tables because three distinct immutable facts are necessary and
sufficient:

| Exact table | Immutable fact |
|---|---|
| `reviewer_webauthn_counter_capability_registrations` | fully verified registration-zero public material against the existing frozen registration challenge |
| `reviewer_webauthn_counter_capability_challenges` | one fresh raw-32-byte-digest assertion challenge allowing exactly the pending credential |
| `reviewer_webauthn_counter_capability_assertions` | terminal assertion, classification/counter edge, and exact frozen consumption/outcome/credential/lifecycle projection |

The companion defines every column, SQL type, nullability, PK, UNIQUE,
composite deferred FK, conditional CHECK, index, append-only trigger, insert
guard, timestamp rule, exact content-hash field inventory, and `payload_json`
non-authority rule. No table is a session, recovery token, mutable credential,
or login state.

### Frozen trigger audit

Only these frozen definitions require version replacement under their existing
names because their SQL union must add the supported bootstrap edge:

1. `trg_reviewer_authentication_events_counter_union_guard`;
2. `trg_reviewer_credential_operation_authentication_counter_union_guard`.

The proposed assertion table gets the identical three-ledger union guard.
Existing predecessor, challenge, consumption, registration-proof, lifecycle,
active-credential, outcome, and append-only triggers remain unchanged and gain
additional named cross-ledger guards. In particular:

- the pending insert requires a live, unconsumed exact frozen parent;
- the child permits one pending credential and expires no later than the parent;
- a frozen registration consumption for a pending parent requires the exact
  terminal assertion projection;
- zero/no-counter public credential insertion requires successful bootstrap;
- failure forbids every credential/lifecycle authorization;
- replacement success requires the exact same-operation registered plus
  superseded pair.

### Transaction and parent-expiry proof

The frozen parent registration consumption is delayed until classification.
Therefore a successful child must complete before both child and parent expiry,
and child expiry is no later than parent expiry. This is required by the frozen
consumption expiry guard. If failure occurs while the parent is live, the parent
projects `FAILED_CLOSED`; if the parent has expired, it projects `EXPIRED`.
Either result creates a matching frozen terminal outcome with unchanged state.

## 4. Calculator-derived relational state leaves

All literal hashes below were generated with Python 3.13 SHA-256 over the exact
ADR-017/ADR-016 canonical objects; none was typed as an expected result. The
synthetic SID and credentials identify no person.

```text
P  = rvp_0123456789abcdef0123456789abcdef
SID hash = sha256:a8c06b3027d3fc4a6df6af7dc21e7f9376e5a28a3274a50f48a3782b1a852e3f
principal_content_hash = sha256:d06fdf1bfed1ed79be76b8959cc5bc01c28d8bef45201318e68419ae9232a876

H0 = sha256:6f6015fc83d0490a9838e33a25acdb18281847baab2a784a6f67e6d96b13045a
HA_SUPPORTED = sha256:606b4aaf6bdbbbbe57feb1419fbb319a5452c18b0044f58ee5126b66096ff65d
HA_NO_COUNTER = sha256:d881581d22c65cd3d788da3589407f2308fc6a0c9c80d882c72b8a47e0758a79
HAB_SUPPORTED = sha256:a5b0a01810adb5028e215c5ddfd56686152e3f2c3f3d7e4bd22dbca3a2a7cf50
HAB_NO_COUNTER = sha256:21fa406862090f09da87d6d51db9264adbbe748cca123ef103c3f9eda7cdbcaa
HC_SUPPORTED = sha256:edd95e22f419cebc2c2259dbe2b38602620c1cad232178fc56882bb5f47cee39
HC_NO_COUNTER = sha256:eb2eddfdde831cc85031ec8a07b01e279d6f28a2cc88734ce1fb0786c43b5221
```

`A` is the initial active credential, `B` is an added credential, and `C` is a
replacement. State members use exact synthetic IDs, calculated raw-ID/public-
key fingerprints, calculated `REGISTERED` event hashes, fixed policies, and the
stated capability. State sorting is the frozen unsigned-UTF-8 tuple. Counter
values never enter the credential-state hash.

## 5. Counter decision vectors

Notation: `AUTH:S` is the already-successful frozen authorizing consumption;
`REG:—/S/FC/E` means registration unconsumed/succeeded/failed-closed/expired;
`R/C/A` are proposed registration/challenge/assertion row counts. Credential and
lifecycle counts are immutable table totals after the vector. `leaf A:7->8`
means the prior authorization edge remains in the union. “Retry legal” means a
fresh successor operation may reference this exact terminal outcome.

### FIRST_ENROLLMENT

| Vector | Decision | `0006` operation; challenge/consumption | `0007` R/C/A | Credential rows; lifecycle rows | Outcome; expected -> resulting state | Counter leaf before -> after | Retry legal |
|---|---|---|---:|---|---|---|---|
| F-POS | ACCEPTED | terminal; `REG:S` | 0/0/0 | 1; 1 | `SUCCEEDED`; `H0 -> HA_SUPPORTED` | none -> registration base `7` | no |
| F-0-POS | REQUIRES CONTINUATION, then ACCEPTED | pending `REG:—`, then terminal `REG:S` | 1/1/1 | 1; 1 | `SUCCEEDED`; `H0 -> HA_SUPPORTED` | `0 -> 1` first union edge | no |
| F-0-0 | REQUIRES CONTINUATION, then ACCEPTED | pending `REG:—`, then terminal `REG:S` | 1/1/1 | 1; 1 | `SUCCEEDED`; `H0 -> HA_NO_COUNTER` | none -> none; observed `0->0` audit only | no |
| F-0-FAIL | REQUIRES CONTINUATION, then REJECTED | pending `REG:—`, then terminal `REG:FC` | 1/1/1 | 0; 0 | `FAILED_CLOSED`; `H0 -> H0` | none -> none | yes |
| F-0-EXP | REQUIRES CONTINUATION, then REJECTED | pending `REG:—`, then terminal `REG:E` at parent expiry | 1/1/1 | 0; 0 | `EXPIRED`; `H0 -> H0` | none -> none | yes |
| F-RETRY | REQUIRES CONTINUATION | fresh successor FIRST with fresh `REG:—`; predecessor is F-0-FAIL/E | 1/1/0 for successor | 0; 0 | pending; expected `H0` | none -> none | current attempt may terminalize; no reuse |

### ADD_CREDENTIAL

Initial totals are credential `1`, lifecycle `1`, state `HA_SUPPORTED`. The
authorizing credential A advances `7 -> 8` before registration begins.

| Vector | Decision | `0006` operation; challenge/consumption | `0007` R/C/A | Credential rows; lifecycle rows | Outcome; expected -> resulting state | Counter leaf before -> after | Retry legal |
|---|---|---|---:|---|---|---|---|
| A-POS | ACCEPTED | `AUTH:S`, terminal `REG:S` | 0/0/0 | 2; 2 | `SUCCEEDED`; `HA_SUPPORTED -> HAB_SUPPORTED` | A `7->8`; B registration base `5` | no |
| A-0-POS | REQUIRES CONTINUATION, then ACCEPTED | immutable `AUTH:S`, pending `REG:—`, terminal `REG:S` | 1/1/1 | 2; 2 | `SUCCEEDED`; `HA_SUPPORTED -> HAB_SUPPORTED` | A leaf `8` preserved; B `0->1` | no |
| A-0-0 | REQUIRES CONTINUATION, then ACCEPTED | immutable `AUTH:S`, pending `REG:—`, terminal `REG:S` | 1/1/1 | 2; 2 | `SUCCEEDED`; `HA_SUPPORTED -> HAB_NO_COUNTER` | A leaf `8` preserved; B none | no |
| A-0-FAIL | REQUIRES CONTINUATION, then REJECTED | immutable `AUTH:S`, terminal `REG:FC` | 1/1/1 | 1; 1 | `FAILED_CLOSED`; `HA_SUPPORTED -> HA_SUPPORTED` | A `7->8` remains; B none | yes |
| A-AUTH-IMMUTABLE | REJECTED branch invariant | prior auth consumption/event remain `S/VERIFIED`; no delete/update | 1/1/1 | 1; 1 | same exact A-0-FAIL outcome | unique A union leaf remains `8` | yes |
| A-SUCCESSOR | legal fresh successor ADD | predecessor exact A-0-FAIL; fresh `AUTHORIZATION_ASSERTION` and challenge | 0/0/0 before any new zero registration | 1; 1 | pending; expected `HA_SUPPORTED` | new A assertion must start at `8` | not a retry token |

### REPLACE_CREDENTIAL

Initial totals are credential `1`, lifecycle `1`, active state `HA_SUPPORTED`.
The old target/authorizer A advances `7 -> 8` before replacement registration.

| Vector | Decision | `0006` operation; challenge/consumption | `0007` R/C/A | Credential rows; lifecycle rows | Outcome; expected -> resulting state | Counter leaf before -> after | Retry legal |
|---|---|---|---:|---|---|---|---|
| R-POS | ACCEPTED | `AUTH:S`, terminal `REG:S` | 0/0/0 | 2; 3 | `SUCCEEDED`; `HA_SUPPORTED -> HC_SUPPORTED` | A `7->8`; C registration base `5` | no |
| R-0-POS | REQUIRES CONTINUATION, then ACCEPTED | immutable `AUTH:S`, pending `REG:—`, terminal `REG:S` | 1/1/1 | 2; 3 | `SUCCEEDED`; `HA_SUPPORTED -> HC_SUPPORTED` | A leaf `8`; C `0->1` | no |
| R-0-0 | REQUIRES CONTINUATION, then ACCEPTED | immutable `AUTH:S`, pending `REG:—`, terminal `REG:S` | 1/1/1 | 2; 3 | `SUCCEEDED`; `HA_SUPPORTED -> HC_NO_COUNTER` | A leaf `8`; C none | no |
| R-0-FAIL | REQUIRES CONTINUATION, then REJECTED | immutable `AUTH:S`, terminal `REG:FC` | 1/1/1 | 1; 1 | `FAILED_CLOSED`; `HA_SUPPORTED -> HA_SUPPORTED` | A `7->8` remains; C none | yes |
| R-OLD-ACTIVE | REJECTED branch invariant | no successful registration consumption, outcome success, or lifecycle authorization | 1/1/1 | 1; 1 | exact R-0-FAIL outcome; old root remains leaf | A remains active at leaf `8` | yes |
| R-ATOMIC | ACCEPTED invariant | same successful `REG:S` and outcome bind both authorizations | 1/1/1 | 2; 3 | exactly new `REGISTERED` + old `SUPERSEDED`; `HA_SUPPORTED -> HC_SUPPORTED` or `HC_NO_COUNTER` | old leaf preserved historically; new mode exact | no |

There is no vector in which a failed bootstrap writes a credential, registered
authorization, superseded event, or unrecorded counter advancement.

## 6. User-handle golden vectors

Input principal for all vectors:
`rvp_0123456789abcdef0123456789abcdef`.

| Vector | Operation ID | Raw 32-byte result hex | Unpadded base64url diagnostic | Result |
|---|---|---|---|---|
| UH-FIRST | `rop_0123456789abcdef0123456789abcdef` | `541ca365d7c1cd2d88b22283d4868a0bcdc2c7f4e2265f431f643b4c22decbd4` | `VByjZdfBzS2IsiKD1IaKC83Cx_TiJl9DH2Q7TCLey9Q` | registration `user.id`; ACCEPTED input |
| UH-ADD | `rop_fedcba9876543210fedcba9876543210` | `e570ddc91e29e4dd69d7374c18a7446fd2a43cbb9424b826aff1e427401df42d` | `5XDdyR4p5N1p1zdMGKdEb9KkPLuUJLgmr_HkJ0Ad9C0` | distinct slot; ACCEPTED input |
| UH-REPLACE | `rop_00112233445566778899aabbccddeeff` | `ed10a054f4da716c050b3c300e48c654a4b64f6543fc0db2035ca33101c4bcab` | `7RCgVPTacWwFCzwwDkjGVKS2T2VD_A2yA1yjMQHEvKs` | distinct slot; ACCEPTED input |
| UH-DISTINCT | same principal, the three operations above | all three raw values differ | n/a | ACCEPTED invariant |
| UH-MISMATCH | credential from UH-FIRST returns UH-ADD raw bytes | expected FIRST, received ADD | n/a | REJECTED as `BINDING_MISMATCH` / `USER_HANDLE_MISMATCH` |

The base64url column is diagnostic only; raw bytes are the WebAuthn `user.id`.

## 7. Synthetic SID golden vector

```text
canonical SID text:
S-1-5-21-1111111111-2222222222-3333333333-1001

UTF-8 bytes SHA-256:
sha256:a8c06b3027d3fc4a6df6af7dc21e7f9376e5a28a3274a50f48a3782b1a852e3f
```

The SID is synthetic but syntactically valid and is not a real user SID.

## 8. CTAP2 terminology and vector consistency

ADR-017 continues to require the WebAuthn `credentialPublicKey` CTAP2 canonical
CBOR encoding form. RFC 8949 remains only the underlying CBOR reference. An
independent restricted integer-map encoder and `cbor2==6.1.4` both reproduced
the frozen vectors byte-for-byte:

| Vector | Key order | Result | Fingerprint |
|---|---|---|---|
| GV-02 ES256 | encoded labels `01 03 20 21 22` | exact hex and base64url unchanged | `sha256:72080e17877c7fe10b105ea40eea474975a16cf7773c03745aa64c025b6a4e63` |
| GV-03 RS256 | encoded labels `01 03 20 21` | exact hex and base64url unchanged | `sha256:1f9704f5f7703f630f3e38815adda23add3f51cf760f0321e89a361e70288270` |

No vector conflict exists. The existing ten vectors are unchanged; the new
decision, handle, SID, and state vectors are additive.

## 9. Hash dependency DAG

```text
current process TOKEN_USER -> canonical SID UTF-8 -> SID hash -> principal hash
principal + credential-creating operation -> raw 32-byte user handle
credential ID/key bytes -> canonical values/fingerprints -> pending registration
parent challenge digest/binding + pending registration -> child challenge binding
child binding + assertion + preallocated frozen projection hashes -> assertion hash
assertion projection -> frozen consumption -> credential/lifecycle + outcome
supported bootstrap edge -> later issuer/operation/bootstrap counter-union leaf
```

No frozen hash includes the proposed assertion hash. Preallocated IDs are
independent random values. No arrow returns to an ancestor.

## 10. Exact changed paths

1. `CHANGELOG.md`
2. `DECISIONS.md`
3. `KNOWN_ISSUES.md`
4. `STATUS.md`
5. `plans/PHASE_02_EXECUTION_PLAN.md`
6. `plans/PHASE_02_CP3_C2_B1_RUNTIME_CONTRACT.md`
7. `plans/PHASE_02_CP3_C2_B2_C_SCHEMA_REMEDIATION.md`
8. `plans/PHASE_02_CP3_C2_B2_C_ADR_018_COUNTER_CAPABILITY_SCHEMA_PROPOSAL.md`
9. `qa/PHASE_02_CP3_C2_B2_C_ADR_017_018_FULL_RUNTIME_REMEDIATION_CODEX_REPORT.md`

Exact docs-only allowlist: root Markdown control-plane files, `plans/*.md`, and
`qa/*.md`. Application/runtime, migration, test, script, dependency/lock,
fixture, and frontend paths changed: `0`.

## 11. Frozen migration blobs

| Migration | Git blob |
|---|---|
| `0001` | `d00355c2456021e6ffb195e50833adc32c74a4ad` |
| `0002` | `53f40664eca2ea2466cc6154b8579c5db506e0ba` |
| `0003` | `47d5a69009949b155211cd68209640136a7cacd9` |
| `0004` | `91b4d96a445be23e7aa55e08b9310dc7334a026d` |
| `0005` | `81976b8f70a1f6107526a13acadf23f369b196e3` |
| `0006` | `f10e7f5bc21e232fc68b38144f5b8fb124f31698` |

## 12. Change counts and prohibited progression

| Surface | Count |
|---|---:|
| application/runtime | 0 |
| migrations created/edited/applied | 0 |
| tests | 0 |
| dependencies/lockfiles | 0 |
| frontend | 0 |
| fixtures/scripts | 0 |
| real Windows Hello | 0 |
| issuer approval runtime | 0 |

GitHub CI execution evidence is absent and non-blocking for this documentation-
only task. Local checks are not represented as GitHub CI evidence.

Final control plane remains:

- ADR-017: `PROPOSED — AWAITING INDEPENDENT RE-REVIEW`
- ADR-018: `PROPOSED — AWAITING INDEPENDENT REVIEW`
- `0006`: `PASS — CLOSED`
- `0007`: `NOT CREATED / NOT AUTHORIZED`
- R1: `BLOCKED / NOT STARTED`
- B2-D: `NOT STARTED`
- CP3-C2-C: `NOT STARTED`
- CP3-D: `NOT STARTED`
- automatic progression: `PROHIBITED`

## 13. QA evidence

The final post-edit results are recorded here after execution:

| Check | Result |
|---|---|
| `git diff --check` | PASS |
| `git diff --cached --check` | PASS |
| exact docs-only path allowlist | PASS — exactly the nine section 10 paths |
| frozen `0001`–`0006` blob verification | PASS — worktree and HEAD match all six expected blobs |
| no app/runtime/migration/test/dependency/frontend change | PASS — `0` |
| secret scan | PASS — unchanged scanner on exact final staged-tree detached worktree; no dev-cache/lock interference |
| policy scan | PASS — `Phase 2 CP3-C2-B2-C schema implementation scope policy scan passed.` |
| state/userHandle/SID vector reproducibility | PASS — SID `1`, handles `3`, principal `1`, state hashes `7` |
| ten-vector and CTAP2 reproducibility | PASS — six JSON hashes, two challenge digests, issuer binding, and two CBOR byte/base64/hash vectors; independent restricted CTAP2 decode/re-encode exact |
| ADR/status/plan consistency | PASS — both proposed/review-waiting, `0006` closed, `0007` unauthorized, R1 blocked, later checkpoints not started |

The first in-place secret-scan attempts did not report a secret: they stopped on
an ignored invalid-UTF-8 Turbopack metadata cache and then an open `.next/dev`
lock held by the running frontend dev process. The ignored cache was moved only
for diagnosis and restored byte-for-byte to its original workspace path. The
dev process was not interrupted. The unchanged scanner was then run against a
detached temporary worktree created from the exact staged Git tree, with copied
current production-build evidence and no dev cache; it passed. The temporary
worktree was removed afterward. No scanner exception, filter, allowlist, or
threshold changed.

No real Windows Hello ceremony is part of QA.
