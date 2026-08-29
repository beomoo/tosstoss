# Phase 2 CP3-C2-B2-C — ADR-017/ADR-018 Final Schema + Windows Trust-Boundary Remediation

## 1. Scope and verdict

- repository: `beomoo/tosstoss`
- branch: `feature/phase-02-toss`
- authoritative starting SHA:
  `09ced6c0d0000f911075154c97a0e1cf54656f86`
- independent verdict: `CHANGES REQUIRED`
- findings: P0 `0`, P1 `3`, P2 `1`
- preserved as closed in principle: RG-08, RG-09, RG-10 canonical SID byte
  representation, RG-11
- task surface: documentation/control-plane and disposable local SQLite proof
  only

ADR-017 and ADR-018 remain proposed and await GPT re-review. The provenance
audit requires proposed ADR-019, which awaits GPT review. None is accepted.
Frozen `0006` remains `PASS — CLOSED`. Future `0007` is not created or
authorized. R1 remains blocked/not started.

## 2. P1-FR-01 — exact frozen outcome parent-key audit

Frozen outcome parent candidates are:

| Frozen UNIQUE | Exact ordered columns | Missing from intended binding |
|---|---|---|
| `uq_reviewer_credential_operation_outcomes_exact_terminal` | `credential_operation_outcome_id, reviewer_credential_operation_id, reviewer_principal_id, terminal_result, terminal_consumption_id, expected_credential_state_hash, resulting_credential_state_hash` | outcome hash, operation hash/type, role, principal hash, SID hash, terminal-consumption content hash |
| `uq_reviewer_credential_operation_outcomes_exact_success` | `credential_operation_outcome_id, outcome_content_hash, reviewer_credential_operation_id, operation_content_hash, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, terminal_result, expected_credential_state_hash, resulting_credential_state_hash` | operation type, terminal-consumption ID and content hash |

SQLite requires an exact eligible parent key for a composite FK. Neither frozen
key can support the claimed complete assertion-to-outcome binding. The proposal
therefore selects remediation A and requires future `0007` to create exactly:

```text
uq_0007_reviewer_credential_operation_outcomes_bootstrap_projection
UNIQUE ON reviewer_credential_operation_outcomes (
  credential_operation_outcome_id,
  outcome_content_hash,
  reviewer_credential_operation_id,
  operation_content_hash,
  reviewer_principal_id,
  reviewer_role,
  principal_content_hash,
  os_owner_sid_hash,
  operation_type,
  terminal_result,
  terminal_consumption_id,
  terminal_consumption_content_hash,
  expected_credential_state_hash,
  resulting_credential_state_hash
)
```

The assertion child copies those same fields in the same order. The design also
adds non-null
`projected_registration_challenge_purpose='REGISTRATION_CREATE'`; without that
column the assertion cannot target frozen
`uq_reviewer_credential_operation_consumptions_exact_terminal`, because an
implied constant is not a composite-FK child column.

## 3. Exhaustive proposed/frozen UNIQUE index inventory

The full proposed inventory is:

| Index | Table | Role |
|---|---|---|
| `uq_0007_cc_registration_content` | pending registration | unique content hash |
| `uq_0007_cc_registration_parent` | pending registration | one use marker per frozen registration challenge |
| `uq_0007_cc_registration_child` | pending registration | one preallocated child |
| `uq_0007_cc_registration_credential` | pending registration | unique credential ID |
| `uq_0007_cc_registration_credential_fingerprint` | pending registration | unique credential fingerprint |
| `uq_0007_cc_registration_public_key_fingerprint` | pending registration | unique public-key fingerprint |
| `uq_0007_cc_registration_exact_copy` | pending registration | exact child-challenge parent key |
| `uq_0007_cc_registration_assertion_copy` | pending registration | exact assertion parent key |
| `ix_counter_capability_registrations_operation` | pending registration | operation lookup; non-unique |
| `uq_0007_cc_challenge_digest` | child challenge | raw-challenge digest uniqueness |
| `uq_0007_cc_challenge_binding` | child challenge | binding uniqueness |
| `uq_0007_cc_challenge_registration` | child challenge | one child per pending registration |
| `uq_0007_cc_challenge_exact_child` | child challenge | deferred registration forward-FK parent |
| `uq_0007_cc_challenge_exact_copy` | child challenge | exact assertion parent |
| `ix_counter_capability_challenges_expiry` | child challenge | expiry lookup; non-unique |
| `uq_0007_cc_assertion_content` | assertion | assertion hash uniqueness |
| `uq_0007_cc_assertion_challenge` | assertion | one assertion per child |
| `uq_0007_cc_assertion_registration` | assertion | one terminal assertion per pending row |
| `uq_0007_cc_assertion_consumption_projection` | assertion | one frozen consumption projection |
| `uq_0007_cc_assertion_outcome_projection` | assertion | one frozen outcome projection |
| `ix_counter_capability_assertions_operation` | assertion | operation/result lookup; non-unique |
| `uq_0007_reviewer_credential_operation_outcomes_bootstrap_projection` | frozen outcomes | complete exact outcome FK parent selected by FR-01 |
| `uq_0007_credential_event_authorization_projection` | frozen lifecycle authorizations | exact event/authorization reverse projection |

The frozen parent indexes used without replacement are:

- `uq_reviewer_credential_operations_exact_binding`;
- `uq_reviewer_credential_operation_challenges_exact_binding`;
- `uq_reviewer_credential_operation_consumptions_exact_terminal`;
- `uq_reviewer_credential_operation_authentication_exact_result`;
- `uq_reviewer_credentials_exact_content`; and
- `uq_reviewer_credential_events_exact_authorization` where its full tuple is
  available; otherwise the event PK plus exact reverse projection guard binds
  the copied event hash.

PK indexes are implicit. There is no remaining optional/may-add index language.

## 4. P1-FR-02 — executable immediate-trigger order

### FIRST_ENROLLMENT and ADD_CREDENTIAL success

1. Insert proposed assertion. The proposed assertion guard sees the durable
   pending row and child; its consumption/outcome/credential/event FKs remain
   deferred.
2. Insert frozen registration consumption. Frozen consumption guard requires
   the existing challenge and validates replay/expiry/outcome mapping. New
   bootstrap consumption guard requires step 1. Outcome FK remains deferred.
3. Insert `BOOTSTRAP_REGISTRATION` (first) or
   `AUTHORIZED_REGISTRATION` (add) authorization. The new authorization
   projection guard requires step 1. Frozen FKs to credential/event/outcome are
   intentional deferred forward references. ADD's old authorizing
   authentication event already exists and remains immutable.
4. Insert public credential. Frozen registration-proof guard now finds the
   consumption and authorization. New bootstrap credential guard finds the
   assertion.
5. Insert `REGISTERED`. Frozen authorization guard finds authorization plus
   credential; frozen chain guard establishes a unique root; new event guard
   finds the assertion/authorization projection.
6. Insert frozen successful outcome last. Frozen outcome guard sees exact
   consumption plus one required authorization; the new outcome guard sees the
   assertion. COMMIT resolves all deferred cycles.

### REPLACE_CREDENTIAL success

1. proposed assertion;
2. frozen successful registration consumption;
3. new-credential `AUTHORIZED_REGISTRATION` authorization;
4. old-target `AUTHORIZED_SUPERSESSION` authorization;
5. new public credential;
6. new `REGISTERED` root;
7. old-target `SUPERSEDED`, linked to the already-existing old `REGISTERED`
   root; and
8. frozen successful outcome last.

At step 7, both frozen lifecycle triggers find the old public credential, exact
authorization, and unsucceeded predecessor. At step 8, the frozen outcome guard
finds exactly the new-registration/old-supersession authorization pair for one
operation/principal/outcome. COMMIT resolves the forward references atomically.

### Failure or expiry — every operation

1. proposed failed/expired assertion with null credential/lifecycle projection;
2. frozen failed/expired registration consumption; and
3. frozen terminal outcome last.

The frozen outcome guard requires zero lifecycle authorizations. Credential,
event, and authorization writes are zero; expected/resulting state hashes are
equal. ADD/REPLACE's earlier authorizing event/counter edge remains immutable;
REPLACE's old target remains active. The frozen outcome is the exact legal
predecessor for one fresh successor operation.

## 5. Ephemeral SQLite DDL proof

An uncommitted temporary Python harness:

1. created a disposable SQLite template;
2. applied the actual frozen Alembic migrations `0001`–`0006` unchanged;
3. materialized the three proposed table surfaces, exact composite FKs, complete
   index inventory, append-only guards, affected cross-ledger guards, and the
   selected complete frozen outcome parent key;
4. cloned the template for nine representative transactions;
5. used the exact insertion order above; and
6. ran `PRAGMA foreign_key_check` after schema creation and every transaction.

Results:

| Case | Public credential count | Lifecycle-event count | Old credential active | FK check |
|---|---:|---:|---|---|
| FIRST `0 -> positive` | 1 | 1 | n/a | 0 rows |
| FIRST `0 -> 0` | 1 | 1 | n/a | 0 rows |
| FIRST bootstrap failure | 0 | 0 | n/a | 0 rows |
| ADD `0 -> positive` | 2 | 2 | yes | 0 rows |
| ADD `0 -> 0` | 2 | 2 | yes | 0 rows |
| ADD bootstrap failure | 1 | 1 | yes | 0 rows |
| REPLACE `0 -> positive` | 2 total / 1 active | 3 | no | 0 rows |
| REPLACE `0 -> 0` | 2 total / 1 active | 3 | no | 0 rows |
| REPLACE bootstrap failure | 1 | 1 | yes | 0 rows |

Schema creation produced no `foreign key mismatch`. Representative transactions
passed `9/9`. The temporary proof script and every database were deleted before
documentation staging. No migration/test/runtime file was created or changed.

## 6. P1-FR-03 — canonical app-data owner binding

The exact canonical production root already used by repository scripts is:

```text
PROJECT_ROOT = Path(__file__).resolve().parents[4]
canonical_app_data_root = resolve(PROJECT_ROOT / "var")
canonical_authority_database = canonical_app_data_root / "dashboard.db"
```

Production R1 cannot use CWD-relative interpretation, a browser/caller path, a
profile/environment name, in-memory SQLite, a fixture-hash database, a test
database, or an arbitrary `DASHBOARD_DATABASE_URL` override. The effective URL
must resolve to the canonical database above.

The exact owner proof is:

1. require Windows, a local filesystem object, and persistent ACL support;
2. when absent, create exactly `PROJECT_ROOT/var`, then verify it before DB
   creation; creation itself is not trusted ownership evidence;
3. open the directory with `CreateFileW`, `READ_CONTROL`, `OPEN_EXISTING`, all
   three share flags, and `FILE_FLAG_BACKUP_SEMANTICS |
   FILE_FLAG_OPEN_REPARSE_POINT`;
4. reject a reparse point and require handle-resolved normalized final path to
   equal the expected root;
5. use `GetVolumeInformationW` for the handle-resolved volume and reject a
   remote volume or filesystem flags without `FILE_PERSISTENT_ACLS`;
6. retrieve OWNER_SECURITY_INFORMATION with `GetSecurityInfo` and validate the
   returned owner SID;
7. independently open/query process `TOKEN_USER` and validate that SID;
8. require exact `EqualSid(app_data_owner_sid, token_user_sid)`; and
9. only then canonicalize/hash the process-token SID under the approved RG-10
   rule.

Owner/token raw SIDs and canonical SID text are transient and unlogged. Any
resolution, creation, open, volume, security-descriptor, token, validation,
comparison, or conversion failure fails closed. Group membership, elevation,
path access, profile name, and username do not substitute for owner equality.

## 7. Windows Hello provenance audit and ADR-019

Current registration requires platform attachment, UV, resident key, and none
attestation; it has no MDS, AAGUID allowlist, direct/enterprise attestation
trust path, hardware CA, or native broker. WebAuthn Level 3 says none
attestation provides no attestation information and an empty trust path.
Microsoft documents that Windows WebAuthn can route to Windows Hello, external
security keys, and plugin authenticators; Windows 11 24H2 supports plugin
passkey managers.

The present design therefore proves only a user-verifying platform WebAuthn
credential on Windows, not strict Windows Hello provenance. Accepted B1 is not
silently weakened. Proposed ADR-019 compares:

1. retain strict Hello-only and approve an independently verifiable provenance
   mechanism/trust path;
2. explicitly amend the product property to user-verifying Windows platform
   WebAuthn, with a threat model acknowledging non-Hello platform/plugin
   authenticators; and
3. independently prove and approve a stronger Windows-native architecture.

No option is selected. No weaker property, Metadata Service, enterprise/direct
attestation, AAGUID list, native broker, or trust root is authorized.

Primary references:

- W3C WebAuthn Level 3:
  `https://www.w3.org/TR/webauthn-3/`
- Microsoft WebAuthn APIs / plugin passkey managers:
  `https://learn.microsoft.com/en-us/windows/security/identity-protection/hello-for-business/webauthn-apis`
- Microsoft `GetSecurityInfo`:
  `https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-getsecurityinfo`
- Microsoft `EqualSid`:
  `https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-equalsid`

## 8. UserHandle account/slot semantics

Each credential slot deliberately forms a distinct WebAuthn user-account
namespace at the authenticator layer, while every slot maps server-side to the
single `LOCAL_DATA_STEWARD` authorization principal. This deliberate exception
to the usual shared-account handle guidance prevents a new required-
discoverable credential from replacing the prior `(rpId,userHandle)` entry on
the same authenticator. It creates neither multiple server principals nor
discoverable-account login. Every assertion uses a non-empty exact
`allowCredentials` list. Deterministic principal+registration-operation
reconstruction remains sufficient after restart; no handle column is added.

## 9. Golden-vector and dependency consistency

The FR changes add one relational copied constant and indexes/guards; they do
not change any ADR-017 hash input except the assertion hash inventory, which now
truthfully includes the explicit registration-purpose column. Existing ten
vectors and restricted CTAP2-canonical ES256/RS256 bytes remain unchanged. No
manual hash was introduced.

## 10. Exact changed paths

Documentation/control-plane paths only:

- `CHANGELOG.md`
- `DECISIONS.md`
- `KNOWN_ISSUES.md`
- `STATUS.md`
- `plans/PHASE_02_CP3_C2_B1_RUNTIME_CONTRACT.md`
- `plans/PHASE_02_CP3_C2_B2_C_ADR_018_COUNTER_CAPABILITY_SCHEMA_PROPOSAL.md`
- `plans/PHASE_02_CP3_C2_B2_C_SCHEMA_REMEDIATION.md`
- `plans/PHASE_02_EXECUTION_PLAN.md`
- `qa/PHASE_02_CP3_C2_B2_C_ADR_017_018_FINAL_SCHEMA_TRUST_REMEDIATION_CODEX_REPORT.md`

## 11. Frozen migrations

| Migration | Required Git blob |
|---|---|
| `0001` | `d00355c2456021e6ffb195e50833adc32c74a4ad` |
| `0002` | `53f40664eca2ea2466cc6154b8579c5db506e0ba` |
| `0003` | `47d5a69009949b155211cd68209640136a7cacd9` |
| `0004` | `91b4d96a445be23e7aa55e08b9310dc7334a026d` |
| `0005` | `81976b8f70a1f6107526a13acadf23f369b196e3` |
| `0006` | `f10e7f5bc21e232fc68b38144f5b8fb124f31698` |

No frozen migration is edited. No `0007` file exists.

## 12. Change counts and CI evidence

| Surface | Committed change count |
|---|---:|
| application/runtime | 0 |
| migration | 0 |
| test | 0 |
| dependency/lockfile | 0 |
| frontend | 0 |
| fixture/script | 0 |
| real Windows Hello | 0 |
| issuer approval runtime | 0 |

GitHub CI execution evidence is absent and non-blocking for this documentation-
only task. Disposable/local QA is not represented as GitHub CI evidence.

## 13. Local QA

| Check | Result |
|---|---|
| disposable proposed-DDL schema creation | PASS |
| nine representative relational transactions | PASS `9/9` |
| disposable `PRAGMA foreign_key_check` | PASS, zero rows |
| `git diff --check` | PASS |
| `git diff --cached --check` | PASS |
| exact docs-only path allowlist | PASS, exactly 9 paths |
| frozen `0001`–`0006` blobs | PASS, all six exact Git blobs |
| secret scan | PASS on the exact staged Git tree in a disposable detached worktree |
| policy scan | PASS |
| golden-vector reproducibility | PASS, all 10 existing vectors / 13 exact checks |
| ADR/status/plan consistency | PASS |

The first live-worktree secret-scan attempt stopped on an invalid-UTF-8 binary
inside the untracked active Next.js `.next/dev/cache`; it did not report a
secret. The successful rerun used the exact staged tree plus copied current
production-build evidence while excluding that dev/cache state, and the
disposable worktree was removed. No real Windows Hello ceremony is part of QA.

## 14. Final control plane

- ADR-015: `ACCEPTED`
- ADR-016: `ACCEPTED`
- ADR-017: `PROPOSED — AWAITING GPT RE-REVIEW`
- ADR-018: `PROPOSED — AWAITING GPT RE-REVIEW`
- ADR-019: `PROPOSED — AWAITING GPT REVIEW`
- `0006`: `PASS — CLOSED`
- `0007`: `NOT CREATED / NOT AUTHORIZED`
- R1: `BLOCKED / NOT STARTED`
- B2-D: `NOT STARTED`
- CP3-C2-C: `NOT STARTED`
- CP3-D: `NOT STARTED`
- automatic progression: `PROHIBITED`

Codex does not self-close the new findings, self-accept any ADR, create `0007`,
resume R1, or start a later checkpoint.
