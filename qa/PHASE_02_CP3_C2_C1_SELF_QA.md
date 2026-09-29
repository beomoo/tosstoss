# CP3-C2-C1 design self-QA — 2026-09-29

Status: **REMEDIATED — GPT INDEPENDENT RE-REVIEW REQUIRED**. Independent review of the previous C1 candidate `289266f1a230637d545ed0eef8f6fd73a933bbde` was **FAIL — DESIGN REMEDIATION REQUIRED** (Critical 0, Major 3). This is documentation and relational feasibility evidence, not an implemented migration or a Phase PASS.

## Bounded remediation result

| Finding | Design correction | Disposable proof | Still NOT VERIFIED |
|---|---|---|---|
| Major-01 | Successful Security authentication and terminal challenge consumption commit in the outer `BEGIN IMMEDIATE`; later disposition writes use a business SAVEPOINT. On post-authentication failure, roll back only that SAVEPOINT, commit the authentication domain, then return a typed failure. Two successfully authenticated supersession assertions both remain terminal after pair-business failure. | Single and two-auth business rollback leave consumption/authentication rows durable, business event/link/head rows absent, and replay rejected. | Actual Security WebAuthn ceremony and final writer. |
| Major-02 | Supersession A binds `SUPERSEDED` to exact OLD decision/bundle/approval/link/Security; B binds `APPROVED` to distinct SUCCESSOR READY decision/bundle/Security and common provider/issuer context. Composite FKs, unique keys, checks, deferred pair references, pre-release pair completeness check, and head CAS define atomic pair semantics. | Correct d1/old bundle to d2/successor bundle pair commits; both d2, both d1, swapped bundles, shared auth/challenge/consumption, wrong predecessor/provider/Security, and partial pair fail. | Full 23-table Alembic DDL and C3 runtime enforcement. |
| Major-03 | Future C3 adds Security `VERIFIED` authentication edges to the existing R1 credential-operation plus issuer-authentication read set. The existing R1 counter algorithm, capability, replay, and acceptance semantics stay unchanged; no Security-only counter truth is introduced. | Minimal three-source edge view represents issuer 5→6, Security 6→7, issuer 7→8; lifecycle and replacement histories; cross-family same-predecessor fork rejected. | Actual mixed R1/Security reader, Windows ceremony, and writer race behavior. |

Command: `python3 /tmp/c2c1_schema_probe_remediation.py > /tmp/c2c1_schema_probe_remediation_result.txt` → exit `0`, **31 checks, 0 failures**. The review ZIP includes the exact disposable script and output; they are not migration artifacts. The previous probe and its historical results remain described below.

Documentation integrity assertions: **7 checks, 0 failures** (`/tmp/c2c1_doc_integrity_result.txt` in the review package). `git diff --check` exited `0`.

The updated contract separates pre-authentication failures from post-authentication business failures. An A-success/B-failure supersession attempt leaves A terminal; two successful assertions whose business pair fails leave both terminal. A fresh attempt needs new challenges. The pair completeness check runs before releasing the business SAVEPOINT, including SQLite deferred-FK inspection, so a missing deferred business row cannot surface only at outer commit and roll back the authentication domain.

No implementation/full runtime QA was run for this design-only remediation. Full 23-table Alembic DDL, actual R1 + Security mixed counter runtime, actual Windows WebAuthn Security ceremony, B writer cascade runtime, and live KRX/SEC/current-exchange contracts remain **NOT VERIFIED**.

## Historical initial C1 self-QA (before independent FAIL)

Routing: L2 architecture/schema design; user-requested Astra/High, WSL, Codex App Local in this new chat. Serena was used for read-only source discovery; filesystem/Git and Python standard-library `sqlite3` were used for the isolated design and feasibility probe. Computer Use OFF, nested Codex CLI OFF, no external-source tool or credentialed collection. The requested model/reasoning setting is recorded as routing, not independently attested by the repository.

## Identity and preservation

- `git fetch origin` exit `0`; `origin/feature/phase-02-toss` matched required `07c8a2a5d53cd3413d7479f56194aa12d63bb1e7`; base tree `2d2344bd4418de2bd04c070d264cffdca1adf54a`.
- Isolated branch: `feature/phase-02-c2c1-security-authority-contract` in a managed worktree. The pre-existing R1 branch and its four untracked QA CSV files were left untouched.
- Source audit covered the required Phase 2 plans, contracts/enums/security/authority/provider identity, storage models/repositories, 0001–0007, reviewer primitives, issuer authority, master/security/acceptance docs, status/decisions/issues. Observed `ShareClass=COMMON` only, `MappingStatus=VERIFIED|UNRESOLVED`, and Phase 1 ticker/class and current legacy VERIFIED constraints.
- No frozen B contract, migration, application, test, fixture, frontend, dependency or scanner file was edited. `0008` file count created: `0`.

## Design result

- `plans/PHASE_02_CP3_C2_C1_SECURITY_AUTHORITY_CONTRACT.md` specifies separate Security evidence/decision/human/link contracts, 23 proposed 0008 tables, additive B binding indexes and safety triggers, v2 immutable canonical Security subjects/profiles, a single guarded Security head projection, KR and US authority paths, source policy, legacy boundary, issuer cascade, collision and 30-scenario matrix.
- ADR-020 in `DECISIONS.md` is `PROPOSED`. STATUS/CHANGELOG/execution plan record the C1 design-only state.
- Chosen legacy policy: new C3 v1 VERIFIED mapping row `0`; effective VERIFIED is the v2 head read projection. Existing fixture rows retain their historical regression meaning. Later C3 must migrate current readers and integrate B issuer-head writer before any operational approval.

## Disposable SQLite feasibility probe

Command: `python3 /tmp/c2c1_schema_probe.py > /tmp/c2c1_schema_probe_result.txt` → exit `0`; SQLite `3.46.1`, `PRAGMA foreign_keys=1`, `18` focused checks, `0` failed. Both script and output are included in the independent-review ZIP under `schema_feasibility/`; they are outside the tracked migration/runtime tree.

The probe exercised a subset of the proposed 0008 relations with B/provider parent-table stubs: exact approved issuer-link bundle FK, exact bundle/decision hash FK, policy maximum-weight trigger, one decision root and no predecessor fork, one challenge terminal consumption, one initial human disposition per decision, no approval-event or Security-link predecessor fork, append-only link trigger, guarded head CAS, issuer-head safety trigger, head subject binding, and deferred two-authorization supersession pair. A one-sided pair failed at COMMIT; a complete A/B pair committed with two CAS steps; reuse of one assertion for both slots failed.

Two prototype errors were discovered and corrected **only in the disposable prototype/design**: SQLite composite FK to challenge consumption requires an explicit UNIQUE parent tuple `(challenge_id, authentication_event_id)` even though `challenge_id` is PK; and a SUPERSEDED→APPROVED link chain requires two guarded head CAS steps within one transaction when the head guard permits only a direct successor. The design document records both. The probe does **not** instantiate all 23 tables, execute an Alembic migration, prove full C2/C3 implementation, verify cryptography, or exercise real data.

## Scope and verification

| Check | Result |
|---|---|
| `git diff --check` | exit `0` |
| frozen `0001`–`0007` compared to base | no changes |
| production Python/runtime/test/frontend/dependency/fixture/scanner edits | `0` |
| live KRX / SEC / CGS / Toss calls | `0` |
| WebAuthn ceremonies / production DB writes / canonical Security or final mapping writes | `0` |
| full frontend/backend QA | **NOT RUN**: design-only checkpoint; implementation gates belong to later authorized C2/C3 |
| GPT independent architecture verdict | **NOT VERIFIED** |

## Open and later gates

Current official source adapter fields, access/license disposition and freshness policy require renewed validation at C2 admission if changed since frozen CP3-C2-A research. Full 0008 DDL/migration upgrade and downgrade, integration with B writer and provider/current Security readers, Windows-native WebAuthn/OWNER execution, complete collision publication safety and all runtime acceptance tests are **NOT VERIFIED**. `0008` implementation, CP3-C2-C2 and CP3-C2-C3 are **NOT AUTHORIZED**. Stop for GPT independent review; do not infer PASS/CLOSED.
