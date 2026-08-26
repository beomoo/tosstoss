# Phase 2 CP3-C2-B1 Codex Independent-Review Remediation Report

CP3-C2-B1:
`REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW`

ADR-014:
`PROPOSED — AWAITING GPT INDEPENDENT RE-REVIEW`

CP3-C2-B implementation:
`NOT STARTED`

CP3-C2-C:
`NOT STARTED`

CP3-D:
`NOT STARTED`

Automatic checkpoint progression:
`PROHIBITED`

This is Codex local documentation evidence for remediation of the first B1
independent review. It is not a GPT re-review verdict, does not mark a P1 closed,
does not accept ADR-014, and does not authorize runtime or migration work.

## Repository and revision

- Repository path: `C:\Users\beomoo\Documents\ChatGPT\tosstoss`
- Repository: `beomoo/tosstoss`
- Branch: `feature/phase-02-toss`
- Initial B1 design starting SHA:
  `959f78415aade27e57d191db3025c66ea4266999`
- Independent-review remediation starting SHA:
  `adfb76285af7ae5884cfc60a0223591bb7e9c913`
- Starting remote branch: same reviewed SHA
- Final SHA: the documentation commit containing this report; returned after
  commit and fast-forward push. A commit cannot contain its own final SHA
  without changing that SHA.
- Remediation date: `2026-08-26` (`Asia/Seoul`)

## Independent review input

- Verdict: `CHANGES REQUIRED`
- P0: `0`
- P1: `4`
- P2: `1`
- ADR-014 at review: `PROPOSED`
- Runtime implementation at review: `NOT STARTED`

The original design strengths remain: automatic final promotion zero, machine
maximum `READY_FOR_MANUAL_REVIEW`, exact human disposition, no conflict
override, issuer/security separation, issuer-only link, append-only history,
no first-writer-wins, no provider rekey, unchanged `MappingStatus`, and no B
Security/VERIFIED writes.

## Exact changed paths

- `plans/PHASE_02_CP3_C2_B1_RUNTIME_CONTRACT.md`
- `qa/PHASE_02_CP3_C2_B1_CODEX_REPORT.md`
- `STATUS.md`
- `DECISIONS.md`
- `plans/PHASE_02_EXECUTION_PLAN.md`

Application, service, migration, fixture, executable test, script, connector,
API route, frontend, scheduler, dependency, credential, and network
configuration paths changed: `0`.

## P1-01 — authenticated-human trust root

The revised contract closes the previously deferred authentication policy at
design level:

- Windows Hello-backed WebAuthn/passkey platform credential is the only
  `LOCAL_DATA_STEWARD` approval trust root;
- stable principal/role are created and resolved by the server, never accepted
  as caller authority;
- exact RP ID `localhost` and approval origin `http://localhost:3000`;
- repository stores only registered public credential identity, canonical COSE
  public key/fingerprint and safe audit; private credential/key is never stored;
- every disposition requires a fresh OS-CSPRNG one-time challenge with exactly
  five-minute expiry and no reusable authentication session;
- challenge binds principal, decision/bundle IDs, expected decision/bundle
  content hashes, disposition, predecessor/successor context, RP/origin and
  policy;
- exact origin/RP, user presence, user verification, signature, credential
  binding, optional supported counter advance, expiry and one-time consumption
  must all verify;
- replay, cross-decision/cross-bundle reuse, tampering, invalid signature,
  missing UV and any unverifiable element fail closed; and
- no password, PIN, biometric template, private key, cookie, bearer token,
  authorization header, session secret or credential secret is stored.

The later acceptance matrix now contains missing authentication, caller-supplied
fake principal/role, expired/reused/cross-bundle challenge, invalid signature,
UV absent and valid authenticated steward approval cases. No WebAuthn route,
credential enrollment runtime or approval implementation was added.

## P1-02 — exact legal-jurisdiction authority

Korea now requires the field-owning Supreme Court/Internet Registry path:

- verified original official corporate-registry document and authenticity
  result;
- Korean-law domestic entity rather than foreign branch/registration;
- exact court corporate registration reference bridged to raw OpenDART
  `jurir_no` for the exact corp-code candidate; and
- human-assisted ingestion bound to its own authenticated operation challenge,
  original bytes and official verification reference.

Screenshot, copied/search-result name, printed/reconstructed page, manually
typed registration number, KRX/listing/provider/DART membership field, KRW,
Korean-language name and OpenDART impersonation of court authority are rejected.
If the verifiable court path is unavailable, the exact state is
`UNRESOLVED / jurisdiction-contract-required`; review-ready and all canonical/
VERIFIED writes are zero.

United States jurisdiction now requires an individually admitted relevant
formation-state legal registry record. A foreign qualification is insufficient.
Accepted SEC registrant metadata/filing and an exact non-name-only bridge are
required regulatory/supporting evidence, while SEC/CIK/LEI/exchange/provider
fields cannot replace the state registry. Foreign private issuers outside the
current KR/US enum remain unresolved.

The contract adds an explicit authority-source × scope × maximum-weight matrix.
Only the KR court registry or exact relevant US formation-state registry can be
decisive for `LEGAL_JURISDICTION`; arbitrary parser enum labels have weight zero
unless the exact immutable source policy admits the combination.

## P1-03 — ADR-013 provenance and exact application

`AuthorityEvidence` now explicitly represents:

- exact source-policy/source identifier and classification;
- exact public/official verification locator and authority document reference;
- exact raw document bytes hash and exact `raw_claim_value` used for
  normalization;
- normalized claim, parser contract, field path, scope, subject role,
  authority times, correction relation and access/license disposition; and
- immutable production/test origin lineage.

The separately versioned immutable `AuthorityEvidenceApplication` records the
exact evidence fact, provider identity/observations, proposed issuer/candidate,
scope/target field, source policy, application state, effective weight, sorted
reason codes, relation-head hash and rule version. Conflict, stale, unusable,
source-policy and subject mismatch are application states; missing evidence is
represented explicitly on the immutable bundle scope result without fabricating
an evidence row.

`AuthorityBundle` now references exact evidence-application IDs/content hashes,
not bare evidence. A raw document hash cannot substitute for the exact raw field
value used by normalization.

## P1-04 — production source admission and acceptance matrix

The revised immutable `AuthoritySourcePolicy` registry defines exact namespace,
document kinds, source owner/classification, allowed scopes/roles, maximum
weight, ingestion mode, adapter/parser versions, production eligibility,
access/license requirements and permanent fixture/test taint.

The normal production bundle builder rejects all `SourceSystem.FIXTURE_*`,
`DataMode.FIXTURE`, `fixture://`, Phase 1 synthetic issuer identifiers, test-only
adapters, synthetic source documents, copied/relabelled fixture descendants and
format-valid identifiers without original admitted authority evidence. Test
inputs may later exercise isolated parsers/rules but cannot obtain a production
policy or call the normal production bundle/canonical issuer path.

The expanded later-implementation matrix specifies for every scenario the
expected machine state, canonical Issuer writes, canonical Security writes,
`ProviderIdentityMapping(VERIFIED)` writes, provider identity/allocation rekeys,
human disposition eligibility and exact outcome. It includes all requested
automatic/fake/name-only/stale/unavailable/conflict/collision/foreign/CIK-role/
correction/revocation/replay/authentication/issuer-only scenarios.

## Proposed additive migration remains unimplemented

- Proposed revision: `0005_phase_02_cp3_c2_b_issuer_authority`
- Exact proposed down revision: `0004_phase_02_cp3_c1_security_master`
- Proposed additions now include source policy, reviewer public credential and
  lifecycle, one-time challenges/consumptions, safe authentication audits,
  evidence applications and bundle-application/scope membership alongside the
  original evidence/decision/approval/link ledger.
- Migration file created: `0`
- Migration applied: `0`
- Existing table alteration/backfill/rebuild/rekey: `0`

Starting and final-check migration SHA-256 baseline:

| Migration | SHA-256 |
|---|---|
| `0001_phase_01_foundation.py` | `6eba164ef2f8bab42583076805255268e4daba29311e8f6e956f4177c0445762` |
| `0002_phase_02_cp3_foundation.py` | `4b6b716999c5f3f6b52be1e85a53685c14c181fb4991e9ead892080717abaee6` |
| `0003_phase_02_cp3_b_invariants.py` | `b59e74b5e817b6a5606d9f89f1f57eec3e0ba3616918d117d3cc28af4f5c420b` |
| `0004_phase_02_cp3_c1_security_master.py` | `cd1cbcae309f1e56ba923e6463863749c79a84b4c10499801f5da28b0a3a0f4f` |

## Scope and safety counters

- Application changes: `0`.
- Migration files created/applied: `0`.
- Existing migrations `0001`–`0004` modified: `0`.
- Runtime WebAuthn/authentication routes implemented: `0`.
- Canonical Issuer rows created: `0` in this documentation checkpoint.
- Canonical Security rows created: `0`.
- `ProviderIdentityMapping(VERIFIED)` writes: `0`.
- Existing `MappingStatus` changes: `0`.
- Provider identity/allocation/history rekeys: `0`.
- Fake/synthetic corp code or CIK created: `0`.
- Actual credentials used: `0`.
- External authority/provider/live/API requests: `0`.
- Toss/OpenDART/KRX/IROS/SEC/state-registry/exchange/CGS/LEI requests: `0`.
- OpenAI API requests: `0`.
- Account/order/WebSocket code or request: `0`.
- LIVE_VERIFIED scope expansion: `0`.
- PR/main merge/tag/release: `0`.

The requested Git fast-forward push is repository delivery, not an external data
or live authority request.

## Documentation safety gates

The exact five-file documentation set was staged before these local checks:

- `git diff --check` completed with exit `0`.
- `git diff --cached --check` completed with exit `0`.
- The required secret scanner command completed with exit `0`; its final
  output was `Validated narrow generated-hash exceptions: 2147` and
  `Secret scan passed`.
- The required policy scanner command completed with exit `0`; its final
  output was `Phase 2 CP3-C1 scope policy scan passed`.
- Scanner/policy/script changes: `0`.

These commands are rerun after this result record is staged so the reported
result covers the final pre-commit documentation content.

## CI evidence limitation

No GitHub status or workflow run exists for reviewed SHA
`adfb76285af7ae5884cfc60a0223591bb7e9c913`. No CI result is fabricated or
inferred. Documentation diff review and the commands above are distinctly local
Codex evidence. This is non-blocking for the B1 documentation checkpoint and
remains for GPT independent re-review to consider.

## Checkpoint result

- P1 remediation is submitted, not self-declared closed.
- ADR-013 remains `ACCEPTED` and unchanged.
- ADR-014 remains `PROPOSED — AWAITING GPT INDEPENDENT RE-REVIEW`.
- CP3-C2-B1 remains
  `REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW`.
- CP3-C2-B implementation remains `NOT STARTED`.
- CP3-C2-C remains `NOT STARTED`.
- CP3-D remains `NOT STARTED`.
- Automatic checkpoint progression remains `PROHIBITED`.
