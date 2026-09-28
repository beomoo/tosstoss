# GPT independent final verification request — TOSSTOSS CP3-C2-B2-D

Please independently review the bounded remediation of the existing uncommitted B2-D candidate. The first independent review returned **FAIL, Critical 0, Major 2**. The implementer reports that M1 and M2 are corrected and all authorized local QA gates pass. Treat that as a claim to verify, not an independent verdict. Do not implement changes, merge, start CP3-C2-C, or declare CP3-C2-B/Phase 2 closed.

## Read first

1. `00_USER_IMPLEMENTATION_REQUEST.txt`, then `01_USER_REMEDIATION_REQUEST.txt`, then `CANDIDATE/AGENTS.md`: exact authorization, STOP rules and status ceiling.
2. `REVIEW_MANIFEST.json`, `DIFF_FROM_BASE.patch` and `QA_RESULTS.txt`: base/candidate identities, complete changed-path classification, exact QA commands/results and package limits.
3. `CANDIDATE/qa/PHASE_02_CP3_C2_B2_D_SELF_QA.md`, `CANDIDATE/STATUS.md`, `CANDIDATE/KNOWN_ISSUES.md`, and the frozen-source/migration/scanner/Windows OWNER proof files under `CANDIDATE/qa/`.
4. Compare `BASE_SNAPSHOT/` with `CANDIDATE/` for the B2-B engine, B2-D service, tests, strict QA controls and unchanged frozen R1/security/migration source. The complete repository source snapshot, not dependencies or production data, is included.

## Authorized scope and independent checks

Base is `48d4201281db2fabdb58f09ba6860bd184e722c8`. B2-D is a local unrouted reviewer backend using existing R1 WebAuthn and OWNER/counter primitives and frozen 0005–0007 schema. It may execute authenticated APPROVED, REJECTED, REVOKED and two-authentication SUPERSEDED; canonical Issuer insert-or-verify; append-only approval, observation, link and head history; same-writer `BEGIN IMMEDIATE` B2-B revalidation; and REVIEW_REQUIRED safety projection. No migration 0008, R1 security meaning change, Security creation, VERIFIED provider mapping, provider rekey, source-policy change, frontend reviewer UI, live API, public exposure or trading is authorized.

Check the **actual code and persisted SQLite assertions** against these issues:

- **M1:** `raw_challenge` is exactly 32 OS-CSPRNG bytes; `challenge_digest = canonical.digest(raw)`; `challenge_binding_hash` uses the unchanged `canonical.ISSUER_CHALLENGE_FIELDS`. Check direct production `_new_challenge` against the repository's original ADR-017 GV-09 expected digest/binding. Independently test disposition, decision, bundle, provider, predecessor and successor binding mutations; no golden value should have been rewritten.
- **M2:** B2-B freshness/latest and B2-D approval observation membership share one selector. For O1 historical and O2 current, only O2 is bound. Check O3 revalidation, immutable event audit coverage of exact canonical membership, and fail-closed same semantic event ID with conflicting audit provenance.
- **Concurrency/idempotency:** Inspect real separate-connection SQLite races for two head successors, duplicate APPROVED, APPROVED versus REJECTED, reused successful authentication ID across disposition/decision/bundle, REVOKED versus another successor, and SUPERSEDED A/B versus a head mutation. Verify no fork, duplicate semantic history, partial mixed pair or cross-bound authorization.
- **Late conflict:** Check the production-callable two-provider path, B2-B affected-provider source, same transaction, old history preservation, new REVIEW_REQUIRED decisions/links and both current heads. Verify there is no arbitrary winner or reverse B2-B dependency on the WebAuthn layer.
- **Controls:** Verify the mypy population proof shows exactly one authorized new metadata file and that only fixed counts were synchronized; scanner detection, exceptions and coverage remain strict. Check the byte-identical Windows-local B2-D→R1 OWNER/TOKEN_USER Win32 `EqualSid` evidence and the 1,121-test Windows backend run. Confirm frozen 0001–0007 and six R1 security core files are byte-identical and 0008 absent.

Distinguish direct observations, passing tests and inference. Recompute the diff/scope and report any unsupported claim with file/line and the minimum missing evidence. The reported QA is: focused B2-D **41 passed**, relevant regression **544 passed**, Windows-native standard backend **1,121 passed**, frontend unit **43 passed**, E2E **2 passed**, migration/fixture/build/API contract/lint/typecheck/secret/policy gates exit 0, and bounded OWNER probe plus direct R1 test **2 passed**. Verify exact commands and zero required skip/xfail/deselection in `QA_RESULTS.txt` and the source test inventory.

## Limits and verdict ceiling

This ZIP contains full base and candidate source snapshots and safe summarized local QA evidence, but no `.git` history, installed dependencies, production DB, credentials, raw security logs, live authority/Toss requests or independent execution record. A reviewer who requires rerunning tests or verifying the remote ref directly needs the candidate commit SHA from `REVIEW_MANIFEST.json` plus a checkout with the pinned runtimes. Live integrations, production effects, public deployment, trading, wider R1/Phase 2 approval and independent final acceptance remain **NOT VERIFIED**. Until this review is complete, the implementer status ceiling is **IMPLEMENTED — GPT FINAL INDEPENDENT VERIFICATION REQUIRED**, never a self-declared PASS/CLOSED. Do not treat this local correction as CP3-C2-B or CP3-C2-C approval.
