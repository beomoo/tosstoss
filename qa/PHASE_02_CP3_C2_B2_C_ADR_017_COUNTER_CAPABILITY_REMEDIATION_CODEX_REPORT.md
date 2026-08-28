# Phase 02 CP3-C2-B2-C ADR-017 Counter-Capability Remediation — Codex Report

- Date: `2026-08-28`
- Repository: `beomoo/tosstoss`
- Branch: `feature/phase-02-toss`
- Authoritative starting SHA:
  `c76fe7616db65c53ffc5a81d3e3c0cb390c0fa3b`
- Independent-review verdict: `CHANGES REQUIRED`
- Findings: P0 `0`, P1 `1`, P2 `2`
- Scope: `DOCUMENTATION / CONTROL-PLANE ONLY`
- ADR-015 / ADR-016: `ACCEPTED`
- ADR-017: `PROPOSED — CHANGES REQUIRED / RG-06 OPEN`
- ADR-018: `PROPOSED`
- `0006`: `PASS — CLOSED`
- Future `0007`: `NOT CREATED / NOT AUTHORIZED`
- R1: `NOT STARTED / BLOCKED`

## 1. Review findings

### P1-RG-06 — counter capability derivation

The selected `webauthn==3.0.0` verified-registration result exposes the
credential ID, public key, `sign_count`, AAGUID, format, credential type,
verification/attestation/device/backup facts, but no authoritative
signature-counter-capability field. WebAuthn permits a counter-supporting
per-credential authenticator to begin at zero and permits an authenticator with
no counter to remain at zero. Registration zero is therefore ambiguous.

Frozen `0005` nevertheless requires one immutable database union before the
credential row can exist:

```text
SIGN_COUNT_SUPPORTED + non-null registration_sign_count
OR
NO_USABLE_COUNTER + null registration_sign_count
```

No browser claim, AAGUID, attachment, Windows username, backup flag, caller
input, payload JSON, undocumented Windows Hello assumption, FIDO Metadata
Service or vendor attestation trust is approved as the missing signal.

### P2-RG-07 — COSE canonical terminology

ADR-017 now names the WebAuthn-required **CTAP2 canonical CBOR encoding form**
for `credentialPublicKey`. RFC 8949 remains the underlying CBOR reference, not
the canonical-form authority. The normative references are:

- W3C WebAuthn Level 3 sections 5.8.1, 6.1.1 and 6.5.6:
  `https://www.w3.org/TR/webauthn-3/`
- FIDO CTAP 2.2 section 6.5.4.1:
  `https://fidoalliance.org/specs/fido-v2.2-ps-20250714/fido-client-to-authenticator-protocol-v2.2-ps-20250714.html`

## 2. First-principles options audit

| Option | Truthfulness and security | Compatibility | Verdict |
|---|---|---|---|
| A — registration zero permanently becomes `NO_USABLE_COUNTER` | It can be truthfully described only as a repository policy, not a demonstrated physical capability. Every real counter that begins at zero permanently loses clone-detection history. | Broadly admits zero registrations. | `REJECTED` because it violates the preference to preserve genuine counter evidence. |
| B — reject registration zero as `COUNTER_CAPABILITY_UNRESOLVED` | Fully fail-closed; it asserts no false capability. | It rejects a standards-valid authenticator class. Because real Windows Hello is outside this task, usability cannot be proved; for a Windows Hello-only product the policy is unacceptably brittle and may make enrollment unusable. | `REJECTED AS PRODUCT POLICY`; retained as the failure behavior when continuation cannot complete safely. |
| C — fresh post-registration assertion | It observes behavior of the exact pending credential: verified `0 -> positive` proves usable advancement; verified `0 -> 0` establishes the repository no-usable-counter admission mode. Both observations remain immutable audit facts. | Preserves zero-registration compatibility without guessing. | `SELECTED PROPOSAL`. |

Option C best satisfies the selection rule: no false physical-capability claim,
immutable audit truth, Windows Hello compatibility, clone-detection retention,
unchanged WebAuthn verification and no recovery/reusable login state.

## 3. Selected Option C contract

The selected design is proposed, not accepted:

1. First enrollment starts in a durable pre-admission ledger. It is not an
   active credential and cannot approve an issuer decision or authenticate any
   other credential operation.
2. Positive registration `signCount` is immediately admissible as
   `SIGN_COUNT_SUPPORTED` with that exact immutable registration value.
3. Registration zero consumes the registration challenge once, persists the
   verified public material and raw observed zero, and atomically issues one
   fresh five-minute `COUNTER_CAPABILITY_ASSERTION` challenge.
4. The assertion must verify `webauthn.get`, the exact fresh challenge, RP ID
   `localhost`, exact origin `http://localhost:3000`, cross-origin false, UP,
   UV, exact pending credential ID and signature under the pending public key.
5. `0 -> positive` admits `SIGN_COUNT_SUPPORTED`, stores frozen
   `registration_sign_count=0`, and records the assertion as the first counter-
   union edge. `0 -> 0` admits `NO_USABLE_COUNTER`, stores frozen
   `registration_sign_count=null`, and preserves the two zeros only in the
   bootstrap audit.
6. Every failed/expired/replayed/mismatched assertion terminalizes the attempt
   without a public credential. Any later try is a wholly fresh first-
   enrollment ceremony linked to the terminal predecessor, not recovery,
   reset, login or reusable authorization state.

`counter_capability` is explicitly an immutable **repository admitted counter-
evidence mode**. It is not a vendor or hardware capability assertion.

## 4. Frozen-schema sufficiency audit

Result: `INSUFFICIENT FOR OPTION C`.

| Frozen contract | Why Option C cannot be represented faithfully |
|---|---|
| `0005 reviewer_webauthn_credentials` | The exact union is mandatory at insert and immutable. There is no unresolved/pending credential state and no legal later update. |
| `0006` registration consumption | Successful `REGISTRATION_CREATE` requires classified registered credential fields and a terminal outcome; it cannot consume zero and wait. |
| `0006` challenge state machine | `FIRST_ENROLLMENT` permits only `REGISTRATION_CREATE`. The sole continuation is the reverse flow: add/replace assertion to registration. |
| `0006` authentication events | `reviewer_credential_operation_authentication_events.operation_type` excludes `FIRST_ENROLLMENT`; issuer authentication would falsely grant issuer-decision semantics. |
| `0006` outcome/authorization | First-enrollment success is rooted in the registration consumption and explicitly has no authorization-authentication event. A capability assertion cannot be reverse-bound without changing the contract. |
| `0006` counter union | The two guards union only issuer and credential-operation assertion ledgers. A bootstrap `0 -> positive` stored elsewhere would become an unrecorded first advancement during restart/reconstruction. |

Using frozen rows would therefore lose one-time challenge consumption, create
an unaudited assertion, falsify registration count, violate FIRST_ENROLLMENT
constraints, break the counter union, or omit the first advancement. This is a
new runtime-to-schema requirement; it does not reopen the reviewed `0006`.

## 5. ADR-018 and minimum future amendment

ADR-018 — WebAuthn Counter Capability Bootstrap Amendment is required and is
`PROPOSED`, not accepted. Correct Option C requires a future migration, proposed
name `0007_phase_02_cp3_c2_b2_c_counter_bootstrap`; that migration is necessary
but `NOT CREATED / NOT AUTHORIZED`.

The minimum amendment is three append-only tables:

1. `reviewer_webauthn_counter_bootstrap_challenges`: root registration and
   optional single assertion child, exact principal/SID/expected empty state/
   operation binding, 32-byte challenge digest, RP/origin/type/UV policy,
   issue/expiry, and child binding to the pending credential/public key.
2. `reviewer_webauthn_counter_bootstrap_consumptions`: unique terminal
   consumption, full WebAuthn verification facts, verified public registration
   material, raw registration observation, assertion previous/asserted counts,
   continuation/finalization link, immutable content hash and UTC time.
3. `reviewer_webauthn_counter_bootstrap_finalizations`: exactly one terminal
   classification per root, observed counts, selected frozen union, disposition
   and exact IDs/hashes of every frozen operation/challenge/consumption/outcome/
   credential/event/authorization projection.

Required unique/check/FK/trigger guards enforce one root, one child, one
consumption per challenge, linear predecessors, exact child-to-registration
binding, exact-copy projection, no credential on failure and one atomic
`BEGIN IMMEDIATE` finalization. A future `0007` must also version-replace only
the two counter-union trigger definitions so a supported bootstrap edge joins
the registration baseline and the two existing assertion ledgers. It must not
rewrite any historical row or migration `0001`–`0006` file.

Exact canonical preimages and calculator-generated hashes for these new rows
remain a mandatory pre-implementation review item. No expected hash was
manually fabricated in this remediation.

## 6. Counter decision vectors

These are decision/state-machine vectors, not cryptographic hash vectors. They
contain no invented digest or opaque identity.

| Vector | Verified observations and stored proof | Disposition |
|---|---|---|
| CV-01 — positive registration | registration `signCount=7`; all create checks pass | `ACCEPTED` as `SIGN_COUNT_SUPPORTED`; frozen registration count `7`; no continuation |
| CV-02 — zero registration | registration `signCount=0`; all create checks pass; no assertion yet | `REQUIRES CONTINUATION`; registration challenge consumed; fresh exact-credential assertion issued; public credential absent |
| CV-03 — zero then positive | CV-02 followed by fully verified assertion `0 -> 1` | `ACCEPTED` as `SIGN_COUNT_SUPPORTED`; frozen registration count `0`; bootstrap edge `0 -> 1` is first union edge |
| CV-04 — zero then zero | CV-02 followed by fully verified assertion `0 -> 0` | `ACCEPTED` as `NO_USABLE_COUNTER`; frozen registration count `null`; bootstrap retains observed `0 -> 0`; no numeric union edge |
| CV-05 — restart after classification | supported credential has frozen registration `0`, exact finalization, bootstrap edge `0 -> 1`, then existing verified edge `1 -> 2` | `ACCEPTED`; reconstruction has one linear leaf `2`. Missing/forked/duplicate bootstrap projection would be rejected fail-closed |
| CV-06 — failed continuation | CV-02 followed by expired, replayed, mismatched, wrong-credential, non-UV or invalid-signature assertion | `REJECTED`; attempt terminal, no credential/outcome projection and no reusable state |

For the `NO_USABLE_COUNTER` restart counterpart, the frozen count remains null,
the finalization proves the immutable `0 -> 0` admission evidence, and all
later no-counter authentication events use null/null as already required.

## 7. CTAP2 canonical wording and golden-vector consistency

A separate standard-library encoder applied CTAP2 shortest integer/length,
definite-length, no-tag, duplicate-rejection and map-key ordering rules. For the
approved integer-label maps the key order is:

```text
ES256 {1, 3, -1, -2, -3} -> encoded keys 01 03 20 21 22
RS256 {1, 3, -1, -2}     -> encoded keys 01 03 20 21
```

Results against frozen GV-02/GV-03:

| Vector | Hex | Base64url | Fingerprint |
|---|---|---|---|
| ES256 | byte-identical | byte-identical | `sha256:72080e17877c7fe10b105ea40eea474975a16cf7773c03745aa64c025b6a4e63` |
| RS256 | byte-identical | byte-identical | `sha256:1f9704f5f7703f630f3e38815adda23add3f51cf760f0321e89a361e70288270` |

There is no vector conflict. The ten existing vectors are preserved. GV-05's
bytes remain unchanged; ADR-018 only adds the required bootstrap provenance for
admitting that frozen no-usable-counter credential preimage.

## 8. Change inventory and frozen blobs

Exact changed paths:

```text
CHANGELOG.md
DECISIONS.md
KNOWN_ISSUES.md
STATUS.md
plans/PHASE_02_CP3_C2_B1_RUNTIME_CONTRACT.md
plans/PHASE_02_CP3_C2_B2_C_SCHEMA_REMEDIATION.md
plans/PHASE_02_EXECUTION_PLAN.md
qa/PHASE_02_CP3_C2_B2_C_ADR_017_COUNTER_CAPABILITY_REMEDIATION_CODEX_REPORT.md
qa/PHASE_02_CP3_C2_B2_C_RUNTIME_CANONICALIZATION_GAP_CODEX_REPORT.md
```

Frozen migration blobs at the authoritative start and after this documentation
task:

| Migration | Git blob |
|---|---|
| `0001_phase_01_foundation.py` | `d00355c2456021e6ffb195e50833adc32c74a4ad` |
| `0002_phase_02_cp3_foundation.py` | `53f40664eca2ea2466cc6154b8579c5db506e0ba` |
| `0003_phase_02_cp3_b_invariants.py` | `47d5a69009949b155211cd68209640136a7cacd9` |
| `0004_phase_02_cp3_c1_security_master.py` | `91b4d96a445be23e7aa55e08b9310dc7334a026d` |
| `0005_phase_02_cp3_c2_b_issuer_authority.py` | `81976b8f70a1f6107526a13acadf23f369b196e3` |
| `0006_phase_02_cp3_c2_b2_c_reviewer_operations.py` | `f10e7f5bc21e232fc68b38144f5b8fb124f31698` |

Scope counts:

```text
application/runtime changes: 0
schema/migration changes: 0
new migrations / 0007 files: 0
test changes: 0
dependency/lock changes: 0
frontend changes: 0
real Windows Hello ceremonies: 0
issuer approval runtime/authentication/writes: 0
```

## 9. QA evidence

| Check | Result |
|---|---|
| authoritative branch/HEAD/remote feature | PASS — all started at `c76fe7616db65c53ffc5a81d3e3c0cb390c0fa3b` |
| remote `main` before work | PASS — `353159da45cfbe3a7f444bf476ce86fa9aece17c` |
| Option A/B/C and frozen-schema audit | PASS — Option C selected; schema insufficient; ADR-018/future 0007 required |
| CTAP2 independent ES256/RS256 re-encoding | PASS — exact hex/base64url/fingerprint equality |
| `git diff --check` / `git diff --cached --check` | PASS |
| exact docs-only changed-path allowlist | PASS — exactly the nine paths in section 8; unexpected `0` |
| application/migration/test/dependency/frontend paths | PASS — changed paths `0` |
| migration `0001`–`0006` blobs | PASS — exact six IDs in section 8 |
| `scripts/secret-scan.ps1` | PASS on staged content; the pre-stage attempt correctly refused an index/working-tree mismatch, then passed without suppression after exact staging |
| `scripts/policy-scan.ps1` | PASS |
| real Windows Hello / issuer approval | NOT RUN, as required |

Frontend/backend lint, typecheck, unit/integration, migration, fixture, build and
E2E suites were not rerun because application, migration, test, dependency and
frontend changes are all zero in this documentation-only task. GitHub CI
execution evidence is absent and remains non-blocking for this documentation-
only proposal; LOCAL checks are not represented as GitHub CI. Final branch and
remote SHAs are verified after commit/push.

## 10. Final control-plane state

ADR-015 and ADR-016 remain `ACCEPTED`. ADR-017 remains `PROPOSED — CHANGES
REQUIRED / RG-06 OPEN`; ADR-018 is `PROPOSED`. `0006` remains `PASS — CLOSED`.
Future `0007` is `NOT CREATED / NOT AUTHORIZED`. R1 is `NOT STARTED / BLOCKED`.
B2-D, CP3-C2-C and CP3-D are `NOT STARTED`. Automatic checkpoint progression
is `PROHIBITED`.
