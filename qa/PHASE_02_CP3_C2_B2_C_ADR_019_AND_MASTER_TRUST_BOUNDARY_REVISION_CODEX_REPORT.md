# Phase 02 CP3-C2-B2-C ADR-019 and Master Trust-Boundary Revision Codex Report

- QA date: `2026-08-29` (`Asia/Seoul`)
- Scope: documentation / architecture / control plane only
- Result: `PASS — DOCUMENTATION REVISION COMPLETE; ADR-019 REMAINS PROPOSED; R1 REMAINS BLOCKED`

## Required report

1. **Authoritative starting SHA**

   `002d844625f6a36154afb76e048113f15fb11aff` on
   `feature/phase-02-toss` was the authoritative starting point. The initial
   worktree was clean.

2. **Exact user requirement changes**

   The authorized change was to revise ADR-019 from a strict Microsoft Windows
   Hello vendor-provenance boundary to a vendor-neutral WebAuthn human-authority
   proposal, while preserving its unaccepted state and every unaffected
   accepted control. The master documents were also aligned to distinguish the
   current local Windows-first read-only system from two independent future
   checkpoints: anonymous public read-only deployment and automated trading.
   No implementation or checkpoint progression was authorized.

3. **Old strict Windows-Hello-only product property**

   Accepted B1/ADR-014 historically stated
   `Windows Hello-backed platform credential only`. That exact history remains
   recorded. Platform attachment, UV, resident discoverability and
   `attestation=none` did not cryptographically prove a credential vendor or
   product was specifically Microsoft Windows Hello.

4. **New proposed vendor-neutral WebAuthn human-authority property**

   A privileged human action requires a fresh, cryptographically verified
   WebAuthn assertion from a previously registered trusted human credential
   satisfying the exact RP, origin, challenge, user-verification, credential,
   signature-counter and audit controls. Vendor/product identity is not itself
   authority. ADR-019 is exactly
   `PROPOSED — AWAITING GPT REVIEW / USER ACCEPTANCE`; decision date is `NONE`.

5. **Authentication controls that remain unchanged**

   The following unaffected B1, ADR-017 and ADR-018 controls remain unchanged:

   - cryptographic assertion-signature verification;
   - exact `RP ID=localhost`, exact `origin=http://localhost:3000`,
     `crossOrigin=false` and exact assertion-type validation;
   - required UV and the accepted UP rules;
   - fresh 32-byte OS-CSPRNG challenge with exactly five-minute validity;
   - one terminal verification attempt, with failure consuming the challenge;
   - no reusable approval session and a fresh assertion for every approval;
   - exact previously registered credential binding, server-controlled trusted
     credential identity and exact non-empty `allowCredentials` where required;
   - strict supported-`signCount` advancement, with equality, rollback, gap,
     fork and clone indications failing closed;
   - accepted ADR-018 `NO_USABLE_COUNTER` handling;
   - append-only authentication and approval audit;
   - exact approval-event linkage to the successful authentication event;
   - no authority from caller-supplied principal, role, authenticated state or
     authentication-event ID;
   - the accepted first-enrollment bootstrap and no silently added recovery or
     reset mechanism; and
   - canonical local app-data OWNER SID equality with process `TOKEN_USER` SID
     wherever that local bootstrap/runtime boundary applies.

   The deliberate RG-09 distinct `(rpId,userHandle)` slots mapped server-side
   to one `LOCAL_DATA_STEWARD` principal also remain unchanged.

6. **Exact property intentionally removed**

   The proposed amendment removes only the requirement to prove that the
   authenticator vendor/product is specifically Microsoft Windows Hello. It
   does not remove fresh cryptographic human proof or amend another accepted
   control. The historical B1 wording is not rewritten.

7. **Threat-model consequence of removing vendor provenance**

   If ADR-019 is later accepted, a separately registered and trusted
   non-Microsoft authenticator could hold human authority. Credential
   enrollment, lifecycle authorization, loss/revocation handling and exact
   registered-key audit therefore carry the trust instead of a vendor label.
   Unknown credentials are not admitted; UV, signature, replay, counter and
   audit controls are not weakened; remote admin and recovery are not added.

8. **PUBLIC / OWNER / TRADING trust-domain model**

   - `PUBLIC`: an anonymous viewer may read only approved public-safe analytical
     output.
   - `OWNER / ADMIN`: a trusted human may perform privileged administration and
     approval through the strong human-authority boundary.
   - `TRADING`: a future deterministic execution domain may act only inside a
     human-approved risk envelope.

   Authority does not flow automatically from `PUBLIC` or AI execution into
   `OWNER / ADMIN` or `TRADING`.

9. **Future anonymous public read-only requirement**

   A future public viewer requires no authentication and has `READ ONLY`
   access to approved public-safe output. The viewer has no mutation, admin,
   canonical approval, source-admission, task-control, secret, internal-storage,
   account or trading capability. The server/service boundary, not hidden UI,
   must enforce this restriction.

10. **Public-safe projection/read-model principle**

    Future publication must follow `internal data/processing -> approved
    public-safe projection/read model or snapshot -> public read-only API/UI ->
    any Internet viewer`. Privileged operational tables are not the public read
    model. Compromise of the public surface must not directly yield owner/admin
    or trading authority. No hosting or network technology was selected.

11. **Current LOCAL_ONLY rule preserved**

    The current runtime remains `LOCAL_ONLY=true`, `TRADING_ENABLED=false` and
    `DRY_RUN=true`, bound to the current local-only security rules. CORS,
    binding and Internet reachability were not changed.

12. **Future public deployment NOT authorized**

    `Public Read-only Deployment` is
    `FUTURE / NOT AUTHORIZED / NOT STARTED`. This revision neither deploys nor
    exposes the application and does not pre-authorize a provider, network or
    hosting design.

13. **Future trading NOT authorized**

    `Automated Trading` is `FUTURE / NOT AUTHORIZED / NOT STARTED`. No order
    endpoint, broker credential, executor, risk engine or account capability was
    implemented or enabled.

14. **AI/Codex is an untrusted order-intent producer**

    Future AI/Codex output may be an untrusted order intent only. AI/Codex is
    not broker authority, may not possess unrestricted brokerage credentials,
    may not bypass risk policy and may not change its own limits.

15. **Future deterministic risk-engine requirement**

    A separately authorized future design must enforce `AI/Codex -> order
    intent -> deterministic risk policy engine -> limited trade executor ->
    broker API`. Its risk envelope must cover master enable/disable, order and
    daily notional limits, allowed universe, position exposure, order count and
    rate, order type, price/slippage protection, market session, duplicate and
    idempotency controls, stale-data blocking, immutable audit, kill switch and
    broker/API fail-closed behavior. Trading enable, limit increases, universe
    expansion, restriction weakening and kill-state recovery require strong
    human authority.

16. **Exact top-level plan files changed**

    - `AGENTS.md`
    - `README_START_HERE.md`
    - `docs/00_MASTER_IMPLEMENTATION_PLAN.md`
    - `docs/01_PRODUCT_REQUIREMENTS.md`
    - `docs/02_ARCHITECTURE.md`
    - `docs/10_SECURITY_AND_OPERATIONS.md`
    - `plans/PHASE_02_EXECUTION_PLAN.md`

17. **Exact control-plane files changed**

    - `DECISIONS.md`
    - `STATUS.md`
    - `KNOWN_ISSUES.md`
    - `CHANGELOG.md`
    - `plans/PHASE_02_CP3_C2_B1_RUNTIME_CONTRACT.md`
    - `plans/PHASE_02_CP3_C2_B2_C_ADR_018_COUNTER_CAPABILITY_SCHEMA_PROPOSAL.md`
    - `plans/PHASE_02_CP3_C2_B2_C_SCHEMA_REMEDIATION.md`
    - `qa/PHASE_02_CP3_C2_B2_C_ADR_019_AND_MASTER_TRUST_BOUNDARY_REVISION_CODEX_REPORT.md`

18. **Migrations 0001–0006 frozen blob evidence**

    Git blob equality was verified against the required values:

    | Migration | Git blob | Result |
    |---|---|---|
    | `0001` | `d00355c2456021e6ffb195e50833adc32c74a4ad` | PASS |
    | `0002` | `53f40664eca2ea2466cc6154b8579c5db506e0ba` | PASS |
    | `0003` | `47d5a69009949b155211cd68209640136a7cacd9` | PASS |
    | `0004` | `91b4d96a445be23e7aa55e08b9310dc7334a026d` | PASS |
    | `0005` | `81976b8f70a1f6107526a13acadf23f369b196e3` | PASS |
    | `0006` | `f10e7f5bc21e232fc68b38144f5b8fb124f31698` | PASS |

19. **No 0007**

    No `0007*` migration file exists. Future `0007` remains
    `NOT CREATED / NOT AUTHORIZED`.

20. **Implementation change counts**

    Application `0`; runtime `0`; migration `0`; test `0`; dependency
    definition/lock `0`; fixture `0`; frontend `0`; network exposure `0`;
    trading `0`. The ignored local `.venv` was repaired from the already frozen
    `requirements.lock` solely so the unchanged repository secret scanner could
    run; this produced no tracked dependency or application change.

21. **Secret-scan exact status**

    Final status: `SECRET SCAN — PASS`.

    `pwsh -NoLogo -NoProfile -File scripts/secret-scan.ps1` printed
    `Secret scan passed.` and returned exit code `0`. The scanner was not edited
    or weakened. Before the successful final run, the existing local environment
    required restoration of the locked `detect-secrets==1.5.0` dependency and a
    temporary pause of the already-running local dev server so the scanner could
    read its SQLite fixture database. The server was restarted after the scan;
    API health returned `ok` / `FIXTURE` and the web root returned HTTP `200`.

22. **GitHub CI exact status/evidence**

    No GitHub Actions workflow is tracked under `.github` at the authoritative
    starting SHA. GitHub's public commit-status API for
    `002d844625f6a36154afb76e048113f15fb11aff` returned `state=pending` with
    `total_count=0`; the check-runs API returned `total_count=0`. Therefore
    GitHub CI execution evidence is absent, and local QA is not represented as
    GitHub CI. Per the task contract, this is non-blocking for this
    documentation-only revision. The `gh` CLI was not installed, so the public
    GitHub REST endpoints were queried directly.

23. **Unresolved design questions**

    There is no unresolved ambiguity inside the authorized documentation
    revision. Deliberately pending decisions remain: independent GPT review and
    explicit user acceptance or rejection of ADR-019; separate authorization
    for any future `0007` and R1; selection of any future public hosting/network
    architecture; and a future Trading ADR and risk-envelope design. None was
    selected, accepted, implemented or started here.

## QA command evidence

| Check | Result |
|---|---|
| `git diff --check` | PASS |
| `git diff --cached --check` | PASS |
| exact documentation-only changed-path allowlist | PASS; exactly the 15 paths in items 16 and 17 |
| exact changed-path inventory | PASS; 15 Markdown files, application/runtime paths 0 |
| frozen `0001`–`0006` Git blob equality | PASS; exact values in item 18 |
| no `0007` | PASS |
| ADR/status/master-plan/product/security/architecture consistency | PASS |
| current `LOCAL_ONLY=true`, `TRADING_ENABLED=false`, `DRY_RUN=true` safety rules | PASS |
| `PUBLIC` / `OWNER / ADMIN` / `TRADING` trust-boundary consistency | PASS |
| stale permanent-localhost/public-prohibition contradiction search | PASS; no current final-product contradiction |
| forbidden implication search: public mutation, unrestricted Codex trading, current public/trading authorization, accepted ADR-019, authorized `0007`, started R1 | PASS; none found |
| `pwsh -NoLogo -NoProfile -File scripts/policy-scan.ps1` | PASS |
| `pwsh -NoLogo -NoProfile -File scripts/secret-scan.ps1` | PASS; exit 0 |

`docs/11_ACCEPTANCE_TESTS.md` was reviewed and did not require modification.
ADR-019 was not self-accepted. R1, B2-D, CP3-C2-C and CP3-D remain not started,
and automatic checkpoint progression remains prohibited.
