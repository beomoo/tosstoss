# R1 WebAuthn backend core — Codex report

- Date: 2026-09-13. Branch: `feature/phase-02-b2c-r1-webauthn-core`.
- Exact starting SHA: `87748c8311242e0bd45bac86e8d60da24ac8ba8a`.
- Current verdict: `R1 NOT VERIFIED — FINAL QA BLOCKED`.
- This is not a GPT independent review, PASS, or checkpoint closeout.

## Latest — fixed provenance URL policy focused verified; full QA entry — 2026-09-13

The user's explicit URL policy authorization supersedes only the earlier
proposal's no-implementation gate. Both 2026-09-09 CSV257 review/proposal files
remain mandatory scope and judgment boundaries. The current scanner's single
fixed cache-tag provenance literal is non-network metadata, not a general
external URL allowance. Exact path/raw-byte SHA/Content equality/top-level
function/Mypy explanatory assignment/literal hashes/one occurrence are all
required. Only its 28-character inspection span is removed before the unchanged
raw/normalized URL rules; source and tag bytes remain unchanged.

Scanner raw SHA-256, directly calculated with Get-FileHash:
`5af0c8b095f35ff91c8714b9c81df5e1747c8b78621bfa0926f2ac9c7fa201d9`.
Final focused policy SHA-256:
`595fa62d462c4df201379986a5d71eef04b82fb0ca1ae6d845099f72e5e17557`.
Only policy code and minimal decision/current-state/report records changed.
The existing 85-file control inventory/digest needs no synchronization: policy
is excluded and every input is unchanged. No source regex/threshold/URL scope,
Toss/issuer rule, scanner, runtime, migration, dependency, frontend, process
canary behavior, CSV or OBS-04 change accompanies this correction.

| Actual focused execution | Result |
|---|---|
| External `FOCUSED_URL_POLICY.ps1`, through metadata-only `RUN_CAPTURE.ps1 -Mode FOCUSED -RunId url-focused-001` | child exit 0 / wrapper exit 0 / capture error null / source hashes unchanged |
| New policy canaries | four positive validation checks; 35 named negative cases, including 19 pure AST negatives also checked at the production boundary; approved source span count 1 |
| Existing URL regression source | byte-identical original segment; raw6/normalized3/Toss5/issuer4 negatives and two permitted-origin calls pass |

The focused harness loads exact production definitions and existing URL canary
statements, not the whole policy/secret scanner. One-byte mutation uses the
production snapshot helper's byte-array input; immutable disk scanner is not
edited. 35 is the number of named cases, not the total assertion count; four
positives are validation checks, not four distinct URL fixture inputs.
The safe log retains 33 negative-ID lines and the exact 35-case completion
summary; two emitted metadata lines were conservatively withheld by the outer
capture. No raw lines were reconstructed or saved. Actual child exit 0 and
the unchanged harness's exact-count/completion assertions are preserved.

Windows execution environment: PowerShell 7.6.5, Python 3.13.15, SQLite 3.50.4,
Node 24.19.0. These version reads and focused checks are not full backend QA.
An external capture draft assembly error was caught by static AST parsing
before any execution, then corrected; it consumed no full QA attempt.
A pre-execution code review corrected the URL length from25 to its actual28.

The preceding external v1 STOP preserved 29/0/4 and found a live user-started
dev server. The user then explicitly allowed its shutdown. The existing exact
PID/start helper stopped only its owned web launcher; the controller's existing
unexpected-exit finally removed its Job and two launch specs/own UUID directory.
All eight captured processes exited and ports3000/8000 were released. No manual
directory cleanup, log deletion or fixture DB deletion occurred. This is not
Ctrl+C graceful shutdown and its exit codes are not QA outcomes.
Fresh RESUME gate: 341 raw index equality/345 source files, 29/0/4, frozen7,
no0008, operational DB absent, both temp roots empty and873 prior artifacts
unchanged. Prior CSV259 independent rehash/OBS-04 results and historical full
exit1 records remain preserved; first actual failed policy file stays NOT VERIFIED.

At this document freeze, the newly authorized standard full QA has not yet run.
After reviewing/staging every commit target and proving exact index/worktree,
both diff checks and final preservation, run `pwsh -NoProfile -File scripts/test.ps1`
exactly once. No document edits during execution. Any failed gate stops without
rerun/extra cleanup/new exceptions. Only full exit0 permits final result documents,
staging and standalone secret/policy scans. No commit/push in this task. General
DB/process-crash replay, actual ceremony, KI-017/KI-018 and other outstanding
independent-review requirements are not waived; R1 is not PASS/CLOSED.

## Historical — CSV257 exact exception focused verified; full QA entry — 2026-09-09

The two mandatory R1_CSV257 scope/validation and implementation/QA instructions
dated 2026-09-08 authorize only the fixed historical CSV exception, its focused
tests, exact policy digest/current-document synchronization, explicit staging,
and one conditional standard full QA followed by final scans on full exit 0.
Commit/push/merge/tag/release remain prohibited. R1 is not accepted or closed.

Before scanner edits, all 259 source rows were directly rehashed from original
bytes: 258 current originals and historical scanner Git blob
`7d4546d281b47a086b2b181bd50727f276aa8d72`. Both digest columns match in every row.
Git stdout BaseStream preserved exact bytes without decoding/EOL conversion.
The external ZIP includes all 259 originals and per-row safe provenance so a
reviewer can repeat this check. Local verification is not a claim of completed
GPT independent rehashing. All four CSVs remain byte-identical and untracked.

### Bounded implementation and actual final focused evidence

Only `scripts/secret-scan.ps1` implements/tests the new exception. Eight new
CSV-specific functions provide fixed path/49504-byte/code-pinned SHA-256 proof,
strict physical UTF-8/LF parsing, exact raw JSON/object and completion binding,
Hex-only path/physical-line/fingerprint matching, detached publication and
self-canaries. The default scanner calls the same production registration path.
The existing matcher dispatches this CSV after its unchanged generic early
checks; existing generated helper bodies, driver, filters, thresholds and
other family semantics remain unchanged. Historical source files are not
compared to their current bytes on each scan. Clean initial CSV absence yields
zero new exceptions; disappearance of this task's evidence fails preservation.

Final scanner SHA-256:
`5af0c8b095f35ff91c8714b9c81df5e1747c8b78621bfa0926f2ac9c7fa201d9`.

| Actual final command | Exit and result |
|---|---|
| `pwsh -NoProfile -File scripts/secret-scan.ps1 -FrozenDiagnosticSelfTest` | 0; 8 positive / 100 negative groups; two unchanged-driver outside-exception synthetic files; actual four-CSV completion; P=259, D=E=applied=257, proof-only lines 214/257 unregistered; other three CSV findings/new exceptions=0 |
| `pwsh -NoProfile -File scripts/secret-scan.ps1 -GeneratedArtifactSelfTest` | 0; unchanged 79 negative groups and 31-file detector batch; metadata=854, tags=2, TS sources=704; P=2406, D=E=applied=2401, proof-only unregistered=5 |

The two known families total 2658 findings; this is not the whole scanner's
finding count or a whole-repository security PASS. The reason the two original
CSV proof-only values were not retained by the detector remains NOT VERIFIED;
filters were not changed to force retention. OBS-04 local PASS is preserved;
its external observer, tests and 257-row replay were not modified or rerun.

New tests cover byte/version/header/row/column mutations, forbidden-field copies,
other-path/type/line noninheritance, scalar/Int32/Int64 and malformed fields,
completion/raw-JSON mismatch and duplicates, missing/unexplained findings,
late atomic rejection, pre/post-proof/publication/final coverage drift,
absence versus disappearance and current-source independence. The final
coverage negative first proves the same coverage invocation succeeds.
Ordinal comparisons reject BOM and culture-ignorable format characters in
exact headers, types, filenames, result/proof/completion identities. No
candidate values/fingerprints or raw security output are exported.

### Development and observation history — not retroactive PASS

- Initial external capture/provenance script exit 1: its observation fixture
  expected a quoted header; the mandatory/actual header is unquoted. Baseline
  snapshot succeeded. Corrected source-only observation exit 0; no CSV rewrite.
- Capture `csv-focused-001` failed before child launch, with child exit/PID
  unavailable. Command discovery returned two pwsh paths; the launcher now
  selects the first normal command resolution. No execution-policy change.
  Original native failure detail was not retained; that limit is preserved.
- `csv-focused-002` scanner exit 1 at the parser BOM negative. Culture-based
  equality ignored the format character. CSV-only ordinal comparison fixed it;
  the original failure and exact executed scanner are preserved.
- `csv-focused-003` and `csv-final-004`, and generated runs 001/002, exited 0
  on their own earlier byte snapshots. Subsequent in-scope review preserved
  generic rejection order and added strict format-character path regressions.
  They are not the final-code gates. Final CSV run 005 and generated run 003
  above use the same final scanner bytes.
- One external safe-summary construction command had a PowerShell parse error
  before execution; the file-backed summary builder succeeded. It was not a
  scanner/QA run. Prior R1/SCAN02/OBS-04 evidence remains untouched.

### Full QA entry snapshot (results pending at this document freeze)

The existing 85-file phase-control inventory is unchanged; only its exact
approved digest is synchronized after both final focused exits 0. Existing
27 staged changes, all nine additional document diffs, the approved AGENTS
30 lines and the scanner are reviewed for exact explicit staging. The four
CSV evidence files are not commit targets. Before the one standard runner:
all index/raw-working entries, both diff checks, frozen 0001–0007, no 0008,
operational DB absence, original runtime/test/dependency bytes, and stale
cleanup/process inventory must pass the external gate. No repository document
is edited during the run. Its actual result will be appended after termination.

### Remaining review boundaries

R1 remains `NOT VERIFIED — FINAL QA BLOCKED` until the authorized remaining
gates are actually complete, with a maximum of `IMPLEMENTED — AWAITING GPT
INDEPENDENT REVIEW`, never PASS/CLOSED. Historical canary cause and general
DB/process-failure replay safety remain NOT VERIFIED; neither a new canary
success nor the local R1-REPLAY-01 correction waives the latter requirement.
A pre-existing generated-validator scalar-type observation was not patched:
the pinned driver emits scalar strings, and no exploitable input path was
established. Broader behavior is outside this CSV change and NOT VERIFIED.
KI-017/KI-018 remain open. Actual ceremony, routes/frontend, issuer approval,
public/trading and later checkpoints remain outside scope. Historical results
below, including 1064/43/2 and 1080/43/2 with full exit 1, are preserved.

## Historical — SCAN02-01/02 implemented and focused verified; NV-CSV blocks final QA — 2026-09-08

The user supplied `R1_SCAN02_CODEX_REMEDIATION_20260907.md` and its independent
review, authorizing only generated exact-byte empty-input handling, actual
finding/proof intersection registration, their tests and conditional later gates.
This does not change any WebAuthn/runtime policy or existing ADR. The two scanner
fixes are locally implemented and focused verified; **R1 remains NOT VERIFIED —
FINAL QA BLOCKED**, because the separate CSV preflight did not produce a verified
result. No policy digest synchronization, staging, full QA or commit/push followed.

### Exact implementation

Only `scripts/secret-scan.ps1` changed during implementation and execution:

- Added `Get-GeneratedSha256HexFromBytes`: explicit null rejection, non-null
  empty-collection acceptance and .NET SHA-256 over the exact byte array.
  Updated only `Get-GeneratedArtifactSnapshot` and generated negative pre/post
  hashing in `Assert-GeneratedCanaryRejected`. The common `Get-Sha256HexFromBytes`
  remains unchanged, including its original caller contract.
- Added `Get-GeneratedArtifactRegistrationPlan`: retain every strict proof,
  inspect raw result JSON for duplicate/malformed structure, compare its parsed
  content to the actual scan object, bind proof/scan completion size and SHA-256,
  and match exact path/line/type/candidate fingerprint. A finding outside proof
  cannot contribute an exception. Other families retain existing handling.
- Reworked `Add-ValidatedGeneratedArtifactExceptions` and added
  `Publish-GeneratedArtifactRegistrationPlan`: check the complete approved
  population before building a detached map, add **only actual matching findings**,
  verify proof-only absence and drift, then publish the map once. Existing other
  exception families are copied unchanged; counts describe the new generated
  delta, not the size of the whole map. No persistence/baseline is added.
- Added `Invoke-GeneratedEmptyInputSelfCanaries` and
  `Invoke-GeneratedRegistrationSelfCanaries`; hooked them into
  `Invoke-GeneratedArtifactSelfCanaries` after the original checks. Existing
  41 negative checks and the 31-file detector batch remain intact.

The executed final scanner SHA-256 is
`e49ff329f2914e03f16e8ae1ddd45d3b6005958faa0204a7c120cb5e4d501b8d`.
No scanner change followed its final execution. Environment: Windows,
PowerShell 7.6.5, Python 3.13.15, SQLite 3.50.4, Node 24.19.0; unchanged pinned
detect-secrets 1.5.0, mypy 1.17.1, Ruff 0.12.11 and TypeScript 5.9.3.

### Actual development/final executions — preserve each result

All three use `pwsh -NoProfile -File scripts/secret-scan.ps1 -GeneratedArtifactSelfTest`:

| Execution | Result and interpretation |
|---|---|
| Development 1 | exit 1: empty hash and four .py/.pyi proof positives passed, then own synthetic directory name `nul` hit the Windows reserved device-name rule. This was test setup failure, not NUL-input rejection evidence. |
| Development 2 | exit 0 after renaming only the new case to `nul-bytes`; expectations unchanged. Production P/D/E counts below passed. This is not the final scanner snapshot. |
| Final 3 | exit 0 after explicitly grouping paired integer-type predicates and adding three malformed integer-representation cases. This is the final scanner byte snapshot. |

The final type grouping prevents PowerShell's left-to-right logical evaluation
from masking an earlier malformed-field condition when an integer is Int32.
This is a scoped new registration-guard correction, not a detector-policy change.
The added cases cover wrong finding type with an Int32 line, malformed completion
digest with an Int32 size, and a string-valued completion size. Earlier PASS/FAIL
outputs and exact per-run scanner hashes are preserved in the ZIP; no prior
exit 1 is relabeled PASS. The earlier R1-SCAN-01 and R1-SCAN-02 failures below
remain historical as well.

Final synthetic checks: **41 existing + 17 empty-input + 21 registration = 79
negative check groups**, plus the unchanged **31-file** actual detector batch.
The new empty suite has five positive groups (.py/.pyi with empty/nonempty exact
companions, exact empty SHA-1/SHA-256 and preserved nonempty results); registration
has a P=4/D=2/E=2 positive including a nonempty preexisting-family sentinel map.
Tests cover null/missing, size/hash mismatch, UTF-8/NUL, empty structured artifacts,
empty/nonempty bidirectional source and companion drift, actual validator entry
after prehash, path/line/candidate noninheritance, type/schema/duplicate/raw-result
rejection, last-artifact forbidden-copy failure and pre-publication drift with
new generated delta 0. Existing actual hard-link/junction negatives are preserved.
F.3 A/B stays favorable retained=true / adverse retained=false; both deny admission.

### Final focused production counts — measured, not prospective

| Quantity | Mypy | Tags | TypeScript | Total |
|---|---:|---:|---:|---:|
| Strict proof artifacts | 854 metadata | 2 files | 1 build-info / 704 source versions | 857 artifacts |
| P: proved exact path/line/value keys | 1708 | 2 | 696 | **2406** |
| D: actual matching findings | 1703 | 2 | 696 | **2401** |
| E: newly registered generated keys | 1703 | 2 | 696 | **2401** |
| Applied generated findings | 1703 | 2 | 696 | **2401** |
| Proved but unregistered (P minus D) | 5 | 0 | 0 | **5** |

Every generated finding is explained: **unexplained generated findings 0**.
P need not equal D; all proofs remain verified, while E=D is enforced. These are
in-memory scanner registrations, not newly saved allowlist entries. This focused
scope excludes the four diagnostic CSVs and does **not** establish whole-repository
finding zero, a repository secret-scan PASS, full QA or R1 acceptance.

### NV-CSV — result observer failure, not a CSV finding count

The authorized CSV-only diagnostic used unchanged `secret_scan_driver.py` through
the existing guarded Python invocation, with the four exact files and unchanged
settings. One observer invocation returned **exit 1**. Its safe failure capture
retained only the exception type, so actual driver exit, completion and candidate
path/line/type/count are **NOT VERIFIED**. Raw stdout/stderr were never persisted
and the process ended; there is no recoverable raw result. No rerun was performed.

Read-only source inspection found a defect in Codex's external observer: it
compares Windows backslash result keys to forward-slash request paths before
projecting safe metadata. A synthetic path-only check proves that comparison
rejects a normal Windows key. The exact executed throw line was not retained, so
this source defect is not claimed to be the sole proven execution cause. This is
our evidence-collection defect, not an observed failure of the unchanged detector.
Neither zero findings nor the review's 518 lexical / 259 distinct estimate is
substituted for actual results. No CSV exception, deletion, move or rewrite is made.

The ZIP's `csv-preflight/REPORT.md`, executed observer, safe request and failure/
preservation JSON provide the exact command, environment and seven unchanged input
hashes. Minimal next diagnostic design: canonical full-path comparison against
exact requested identities, and safe stage/line/driver-exit/completion retention
before projection. Validate that observer with synthetic metadata, then obtain
direction for a separately identified diagnostic attempt. No corrected observer
or new actual CSV scan is implemented by this submission. NV-CSV remains blocking;
the long standard QA was not started to discover the same unresolved input risk.

### Final preservation and remaining gates

The starting 345-file snapshot exactly matched the prior STOP; all 341 index
entries, original 27 staged changes and four untracked CSVs remain preserved.
After final focused execution, only nine current-state/report documents changed;
they are not security-scanned. Compared with task start the only ten changes are
the scanner and these nine documents; 335 other files remain byte-identical,
including runtime/tests/dependencies, driver, policy/test/process canary scripts
and all four CSVs. Both diff checks return exit 0; the ten intentional unstaged
paths mean raw index/worktree equality is not reached or claimed.

Frozen 0001–0007 match base/index/raw working blobs; 0008 is absent and operational
`var/dashboard.db` remains absent. Existing resources were not deleted or moved;
only each standard scanner invocation's own disposable resources were normally
cleaned, and both managed temporary roots are empty. HEAD remains
`87748c8311242e0bd45bac86e8d60da24ac8ba8a` on the approved R1 branch. No new commit,
push or remote-ref query was made; remote HEAD/equality remain NOT VERIFIED.

New full QA invocations **0**; backend/frontend/E2E **NOT RUN**; repository secret
and policy scans **NOT RUN**; process canary **NOT RUN**. Historical 1080/43/2 and
1064/43/2 with their whole-run exit 1 are not replaced. KI-017/KI-018 stay open;
actual ceremony, prior process-canary cause, general DB/process-failure replay
safety and full R1 independent verification remain NOT VERIFIED, not silently
declared nonblocking. Public/trading and subsequent checkpoints remain unauthorized.

The ZIP supports independent review of these two scanner fixes, final focused
evidence and the unresolved CSV observer issue. It is a STOP package, not a full
R1 runtime/execution acceptance package; full independent R1 verification still
needs the complete checkout or exact submitted remote SHA and final QA evidence.

## Historical STOP — R1-SCAN-02; zero-byte proof input binding — 2026-09-07

The user's independent review accepted the prior STOP and diagnosis, not R1.
F.3/F.4 were explicitly revised: strict generated-artifact rejection, zero proof
and exception, unchanged input and fail-closed admission are mandatory; an
individual adverse-order detector finding / JSON-occurrence-specific finding is
not. No supplementary detector, filter, threshold, transformer, scope, baseline
or ignore change was authorized or made. The original R1-SCAN-01 witness and both
exit-1 executions remain historical evidence below.

Only the unstaged scanner self-canaries were minimally amended. They now require
no partial proof output, no exception-map entry for a rejected artifact, exact
input-byte preservation, and no hypothetical path/line/value exception for a
forbidden candidate. A separate favorable-order case was added; the original
adverse-order case was not reordered. Candidate retention is observational only
for the three explicit mypy unknown-field cases, including a nested unknown field;
all other negative candidate checks remain. Same-line copy cases retain their
existing candidate check and add the candidate-wide no-exception assertion.

### Actual execution and new blocker

One new execution of `pwsh -NoProfile -File scripts/secret-scan.ps1
-GeneratedArtifactSelfTest` returned **exit 1**. On its final scanner bytes:

- Synthetic positive mypy source/interface verification passed.
- **41 negative checks**, including post-validation drift, passed; the unchanged
  detector completed its **31-file** synthetic negative batch.
- A: same unknown hex **before** `version_id`: strict rejection, proof 0,
  artifact/candidate exception 0, unchanged bytes; candidate retained **true**.
- B: same unknown hex **after** `version_id`: the same admission protections;
  candidate retained **false**. This observation is not the PASS condition.
- Nested unknown field: rejected with the same protections, candidate retained
  true. TypeScript, tag, link, mutation and synthetic high-confidence negatives
  were not skipped or weakened.
- The self-canary substage passed, **not the integrated focused command**.
  Production proof collection then failed at `scripts/secret-scan.ps1:1072`,
  `Get-ValidatedMypyCacheHashProof` calling `Get-GeneratedArtifactSnapshot`.
  Exact safe error: `Cannot bind argument to parameter 'Bytes' because it is an empty array.`
- The 2401 production detector population, 1703/2/696 acceptance, exact exception
  registration and unexplained-finding zero were **NOT REACHED / NOT VERIFIED**
  in this execution. The collection throws before returning proofs and before
  registration; new generated exceptions registered in this execution: **0**.

Environment checked locally: Windows, PowerShell **7.6.5**, Python **3.13.15**,
SQLite **3.50.4**, Node **24.19.0**. Dependencies and pinned detector remain
unchanged. The ZIP records the exact executed scanner SHA-256, safe output,
starting/final file hashes and Git index identities. No scanner edit followed
the failed execution; subsequent repository edits are these nine status/report
documents only. The amended documents have **not** been security-scanned.

### Confirmed cause and bounded read-only evidence

`Get-Sha256HexFromBytes` at line 96 declares mandatory `[byte[]] $Bytes` without
`AllowEmptyCollection`. Its signature/body are unchanged from the base SHA.
The new `Get-GeneratedArtifactSnapshot` reads exact source bytes at lines 457–458
and passes them to that helper. A legitimate zero-byte source therefore fails
PowerShell argument binding before hashing, UTF-8 validation or digest comparison.
This is a newly exercised input-contract incompatibility, not the ID heuristic,
new secret population, a schema bypass or evidence of a secret leak.

A read-only inventory of the current 854 mypy metadata files found **16** sources
of size 0. Every one has exact stored-size and recomputed source-SHA1 equality.
Safe metadata/source paths, sizes, SHA-256 and Boolean equality results are in
`evidence/EMPTY_SOURCE_INPUTS.json` in the ZIP; no metadata contents or candidate
values are included. The first currently enumerated example is
`.venv/Lib/site-packages/anyio/streams/__init__.py`. The failure log did not name
its input path, so the exact file reached in the failed invocation is **NOT
VERIFIED**; current enumeration is not substituted for execution evidence.
This inventory is not a complete strict proof or a rerun of the scanner. Earlier
helper-level 854/854 claims are preserved below, not promoted to a PASS of these
final scanner bytes or reused to contradict this integrated failure.

Additional static-review distinction: the current registration loop checks
**2401 detector findings**, then registers every validated proof value. Current
mypy metadata has 1708 distinct per-artifact hash/value pairs, versus 1703
expected findings; together with tags/TypeScript this would yield **2406 proven
exact exception entries**, not 2401 entries. The extra five are proof-derived
values, not unexplained findings; static review found no invalid-artifact
inheritance route. Neither count was reached in this failed run. Whether the
approved phrase "exact exception registration" permits these five non-finding
entries needs explicit review; no registration-policy change or acceptance is
inferred. The distinction must not be hidden in a future population PASS claim.

### Minimum next proposal — not implemented

Resolve only zero-length, non-null byte hashing in the generated-proof path;
prefer a scoped exact-byte digest implementation rather than silently changing
all callers of the shared helper. Alternatively, explicitly review authorizing
`AllowEmptyCollection` on the shared helper and every affected caller. Neither
option is implemented. Missing/null inputs, path/link guards, strict UTF-8/NUL,
schemas, source/interface equality and post-proof drift must remain fail closed.
No generated file may be rewritten, normalized, deleted or replaced to avoid it.

Proposed regressions: empty-source SHA-256 and SHA1; positive mypy empty Python
source with exact size 0 and companion proof; transition from empty to nonempty
after proof; stored size/hash mismatch; missing/null, link/reparse and invalid
UTF-8/NUL rejection; all existing 41 negatives and 31-file detector batch;
complete 854 metadata / two tags / 704 TypeScript source proofs and current
1703/2/696 findings with unexplained zero. Further focused/full-QA execution
requires renewed direction after this STOP; no retry or implementation is implied.

### Snapshot, execution limits and submission suitability

HEAD/base remain `87748c8311242e0bd45bac86e8d60da24ac8ba8a`; branch unchanged.
The 345-file starting snapshot and all 341 index entries matched the prior STOP
package. Original **27 staged** changes remain intact; **10 unstaged** paths are
the scanner plus nine documents. Four diagnostic CSVs remain local/untracked,
not staged. All other 335 starting files are unchanged, including runtime, tests,
dependencies, policy/test/process-canary scripts and the four CSVs. No policy
digest or inventory synchronization was performed. Frozen 0001–0007 match base,
index and raw working blobs; no 0008 exists and operational DB remains absent.
The scanner's own newly created temporary resources were normally cleaned;
no previous cache/evidence or user files were deleted. Both managed temporary
roots are empty. Both diff checks return exit 0; index/worktree equality is
intentionally **not** claimed while the ten unstaged paths remain.

This attempt: full QA **0 invocations**, new backend/frontend/E2E **NOT RUN**,
repository secret/policy scans **NOT RUN**, process canary **NOT RUN**, commit/push
**NOT PERFORMED**. No remote HEAD equality was checked or established. Historical
1080/43/2, 1064/43/2 and their full exit-1 records remain unchanged. Process-canary
root cause, general DB/process-crash ambiguous-commit replay safety and real
browser/device ceremony remain **NOT VERIFIED**; KI-017/KI-018 stay open.

The single ZIP contains the latest report/current documents, safe evidence,
before/after inventories, exact draft scanner/guard sources and historical
witness. It is suitable for reviewing this **STOP and proposed fix**, not full
independent reproduction or R1 acceptance: the full runtime checkout and all
generated-source bytes are not bundled. No raw security logs, DB/journal,
credential values, signatures or challenge material are included. The ZIP
manifest verifies transfer integrity, not security/QA acceptance. R1 remains
`NOT VERIFIED — FINAL QA BLOCKED`; public/trading and all later checkpoints remain
unauthorized. No further action follows this submission.

## Historical STOP — R1-SCAN-01; focused F.3 candidate preservation failed — 2026-09-05

The approved exact-exception implementation is retained as an **unstaged draft**.
It is not ready for the one full-QA attempt or commit/push. Current R1 remains
`NOT VERIFIED — FINAL QA BLOCKED`. The original 27 staged files were not staged
again, reset, moved or replaced. The four local diagnostic CSVs remain untracked.

### Confirmed cause, not a generated-hash false-positive reclassification

New strict mypy schema validation correctly refuses an added unknown field and
registers no exception. However, the **unchanged detect-secrets 1.5.0 detector
pipeline omits that field's synthetic high-entropy hex candidate** when it occurs
after `version_id` on the same minified JSON line. This fails attachment F.3's
candidate-detection requirement. Overall schema rejection is not evidence that
the individual candidate remains in the detector results.

The installed `detect_secrets/filters/heuristic.py:64` function
`is_likely_id_string` searches all text preceding the candidate. Its helper at
line 75 recognizes `_id` followed by a non-alphanumeric character; `version_id`
therefore affects a later, unrelated field. The current scanner intentionally
retains this existing filter: it is not one of the five prohibited filters in
the unchanged `scripts/secret_scan_driver.py`. This is an existing heuristic
behavior exposed by the newly required negative test, not proof of an actual
secret leak or permission to change detector policy.

A read-only in-memory diagnostic used the **actual unchanged driver**
`_scan_snapshot` and the same settings/filter configuration. It changed only
the ordering of two synthetic JSON fields; it wrote no input/output files and
printed no candidate values, fingerprints or source lines:

| Placement of the same synthetic hex field | Entropy above unchanged threshold | ID heuristic excludes it | Actual driver reports candidate |
|---|---|---|---|
| Before version_id | true | false | true |
| After version_id | true | true | false |

The adverse field ordering and candidate-preservation assertion remain in the
new self-canary. No field was moved to make it pass. No detector/filter/threshold,
baseline, scope, skip/xfail or existing functional test expectation was changed.

### Commands, results and execution boundaries

Environment: Windows; PowerShell **7.6.5**; Python **3.13.15**; SQLite **3.50.4**;
Node **24.19.0**; detect-secrets **1.5.0**; mypy **1.17.1**; Ruff **0.12.11**;
TypeScript **5.9.3**. Versions were read locally; no dependency was installed or
changed and Ruff was not executed.

| Execution | Actual result |
|---|---|
| `pwsh -NoProfile -File scripts/secret-scan.ps1 -GeneratedArtifactSelfTest`, development attempt 1 | exit **1** at the negative candidate-preservation assertion; generic diagnostic message. |
| Same focused command, development attempt 2 | exit **1**; exact label `unknown-hex/probe.meta.json`, two other findings present but the added candidate absent. |
| In-memory actual-driver ordering diagnostic, isolated Python `-I -X utf8 -B -c` | exit **0**, two rows above; diagnostic success, not scanner PASS. |
| Packaged `REPRODUCE_R1_SCAN_01.ps1 -RepositoryRoot ...` witness | exit **0**, same two Boolean rows; source snapshot/version checked, no file inputs or results written by the witness. |
| Final PowerShell parser and existing Node preload-guard smoke | exit **0**; syntax valid and nonempty NODE_OPTIONS rejected before invoking Node. |
| Standard full `scripts/test.ps1` | **NOT RUN (0 invocations)**: focused prerequisite did not pass. |
| New full repository secret scan / standalone policy scan / process canary | **NOT RUN**. No final scan or canary PASS. |
| New backend / frontend / E2E suites | **NOT RUN / NOT RUN / NOT RUN**. Historical 1080/43/2 and their full exit 1 are unchanged below. |
| Commit / push | **NOT PERFORMED**. No new commit or remote-head equality claim. |

Each focused execution completed a 30-file synthetic negative detector batch
through the unchanged serial driver and its completion checks, but the candidate
assertion loop failed at the unknown-field case. Do not call those 30 cases PASS.
Before that failure, the validators rejected the source/data/hash mutations,
unknown/same-line/nested/case/duplicate/malformed fields, missing/external sources,
actual disposable hard-link/junction sources, tag mutations, TypeScript
version/shape/cardinality mutations and six synthetic credential-shaped artifact
cases. Their high-confidence rejection checks also passed. These partial checks
do not satisfy the failing candidate assertion or the remaining full self-canary
suite. The post-validation drift self-canary occurs later and was **not reached**.

Separate helper-level read-only development checks observed 854/854 current mypy
metadata proofs, two complete tag proofs, and TypeScript 704/704 source-version
equality / 696 distinct values. These are not a final integrated focused run or
new 2401-finding exception acceptance result. Both focused executions stopped
before production-population validation/registration; new exception registration
in those executions was **0**. The accepted historical diagnostic population is
still distinct from a successful run of this new scanner implementation.

Between the two development attempts, result-path handling was corrected for
rooted versus relative detector paths and the failure message gained a safe
relative case label. A subsequent code review changed the new TypeScript node
invocation to use existing `Assert-PhaseNodeRuntime` instead of merely resolving
node.exe, so inherited NODE_OPTIONS cannot preload code. The final scanner bytes
have syntax/guard checks only; **no final-source focused PASS is claimed**.
The existing 85-file policy digest was deliberately not synchronized to this
unfinished draft; `scripts/policy-scan.ps1` is unchanged from this turn's starting
working snapshot. Do not run full QA against this partial snapshot.

Only the standard focused scanner's newly created disposable self-canary files
were normally created/cleaned, including exactly its own link entries before
safe final cleanup. No prior cache, stale failure evidence, diagnostic CSV,
operational DB or other user resource was deleted.

### Minimal next decision — PROPOSED, neither option implemented

1. Explicitly amend F.3 to permit strict-schema rejection in place of retaining
   the exact candidate in the unchanged detector. Keep the heuristic loss
   documented and the adverse-order witness; this is an acceptance decision,
   not something the implementation may silently choose.
2. Separately authorize a narrowly scoped schema-aware supplementary detection
   design for these exact generated artifacts. Preserve the existing detector,
   adverse ordering, same-line/case/duplicate negatives and unrelated-secret
   checks; demonstrate both candidate retention and fail-closed behavior before
   any new full-QA attempt. This additional detection path is not authorized by
   the present per-finding exception approval.

No change to installed `is_likely_id_string`, scanner filter configuration or
test assertion is made. Both options need explicit independent review/user
direction. General DB/process-crash ambiguous-commit replay safety, actual
device/browser ceremony and the prior process-canary failure cause remain
`NOT VERIFIED`. KI-017 and KI-018 remain open/nonblocking. No PASS/CLOSED or
next-checkpoint progression is declared.

### STOP snapshot and preservation audit

HEAD and base remain `87748c8311242e0bd45bac86e8d60da24ac8ba8a` on
`feature/phase-02-b2c-r1-webauthn-core`. There is **no new commit**. A read-only
`git ls-remote --exit-code --heads origin refs/heads/feature/phase-02-b2c-r1-webauthn-core`
returned exit 1 without a usable ref; remote branch HEAD/equality are therefore
**NOT VERIFIED**, not reported as absence or equality. No push was attempted.

All 341 original index entries are unchanged, including the 27 preserved staged
R1 changes. Current working state is 27 staged, ten unstaged paths (nine documents
plus the scanner), and four preserved untracked diagnostic CSVs. The 345-file
starting working snapshot comparison changes only the following ten files;
the other 335 files, including R1 runtime/tests/dependencies, policy/test runners,
process canary and all four CSVs, are byte-identical:

- CHANGELOG.md
- DECISIONS.md
- KNOWN_ISSUES.md
- STATUS.md
- plans/PHASE_02_CP3_C2_B1_RUNTIME_CONTRACT.md
- plans/PHASE_02_CP3_C2_B2_C_ADR_018_COUNTER_CAPABILITY_SCHEMA_PROPOSAL.md
- plans/PHASE_02_CP3_C2_B2_C_SCHEMA_REMEDIATION.md
- plans/PHASE_02_EXECUTION_PLAN.md
- qa/PHASE_02_CP3_C2_B2_C_R1_WEBAUTHN_CORE_CODEX_REPORT.md
- scripts/secret-scan.ps1

Frozen 0001–0007 each match base, index and raw working Git blobs. No 0008 exists;
operational var/dashboard.db remains absent. Both managed temporary roots are
empty after normal self-canary cleanup. `git diff --check` and
`git diff --cached --check` each return exit 0. These are preservation/format
checks, **not a final repository scan, current index/worktree equality, or QA
PASS**. The ten intentional unstaged paths mean exact commit-snapshot equality
has not been reached. No existing evidence is removed to make a gate pass.

The ZIP submission supplies the latest report, safe local diagnostic CSVs, final
snapshot/inventory, the draft scanner and primary detector/guard sources, and an
in-memory synthetic witness. It contains no raw security logs, candidate values,
DB/journal files, keys, signatures or challenge material. Its manifest proves
transfer integrity only. It is a **STOP review package**, not a runnable complete
R1 checkout or independent reproduction of the full 2401-source population.

## Approved exact secret-exception remediation — 2026-09-05; pre-run plan

The user independently reviewed the **diagnosis** as `PASS WITH ISSUES`; that
decision is not acceptance of R1. The new diagnostic population alone receives
`PROVEN_NOT_SECRET=2401` (mypy source/interface 1703, complete mypy/Ruff public
tags 1 each, TypeScript source-version hashes 696). Historical 2401 identities
remain `NOT VERIFIED`: 2392 recovered metadata records plus nine NOT_RECOVERED
records. Nothing in this remediation reconstructs those missing historical
identities. Earlier exit-1 runs and the diagnostic execution are preserved below.

Current work is limited to exact generated-artifact exception implementation,
fail-closed focused/self-canary validation, necessary exact policy digest
synchronization, and the prescribed documentation/index/QA submission procedure.
This was the plan before the focused attempts. **This planning section makes no
scanner, negative-test, canary, full-QA, final-snapshot, commit or push claim**;
the failed executions and current STOP are recorded immediately above.
No new runtime/semantic policy, dependency, migration or frontend change is
authorized. The original 27 staged R1 files are preserved for review/inclusion.

### Required implementation and verification boundaries

| Validator | Exact prerequisite before registering any exception |
|---|---|
| Mypy metadata | Verify pinned/installed mypy version; strict expected complete schema; reject duplicate/unknown authority or entropy fields; resolve sources only inside approved repository/installed venv roots; reject missing/external/reparse/junction/symlink/hard-linked paths; recompute source hash from exact bytes and interface hash from exact companion data; require exact stored equality without rewriting inputs. Only proven source/interface fields qualify. |
| TypeScript build-info | Verify pinned/installed version and generator contract; validate the entire structure and duplicate/extra keys; enforce expected source/version cardinality; regenerate all 704/704 source versions using the actual generator; require exact equality, the current distinct value/finding-universe correspondence and no unexplained quoted hex. Unknown fields, versions, signatures or new hex do not inherit permission. |
| Public cache tags | Only the two current approved complete fixed public files may qualify. Require exact whole-file bytes, not prefix/substring matching. One changed or appended byte denies an exception. |
| Same-line field binding | Existing key remains path + line + candidate value, not a JSON pointer. Inspect all occurrences: every occurrence must belong to a validated allowed field. A copied value in one unknown/forbidden field denies the candidate's exception entirely; strict schemas and duplicate/extra-field rejection are mandatory. |
| Existing safeguards | Preserve all detector thresholds, exact exception mechanism, self-canaries, UTF-8/binary rejection, path/scope coverage and completion checks. No directory, extension, Git-ignore, baseline or cleanup bypass. Input drift must fail closed. |

Required synthetic negative validation covers all of the following; results are
pending, not inferred from the preceding diagnosis:

1. Mutated mypy source hash and companion data; unknown high-entropy fields;
   copied allowed values in same-line forbidden fields; malformed/duplicate JSON.
2. External, missing, reparse and hard-linked sources: no exception.
3. Changed complete tag bytes and appended high-entropy values: still detected.
4. Mutated TypeScript source/version, unknown hex fields, copied allowed hashes
   in same-line forbidden fields, unknown version/signature/cardinality: reject.
5. Unrelated synthetic Bearer/API-key/private-key-shaped values added to the same
   artifact remain detected, including when an otherwise valid generated value
   is present. No real credential material is used.
6. All unchanged secret-scan self-canaries and encoding/binary/scope/completion
   guards continue to pass. No skip, xfail or weaker functional expectations.

### Snapshot and one-run execution plan

After focused/self-canary PASS only: finish authorized documents, review all 27
existing staged R1 targets plus the newly changed scanner, stage every commit
target, verify raw index/worktree equality and both diff checks, then freeze
documents throughout exactly one standard `pwsh -NoProfile -File scripts/test.ps1`
run. Keep initial policy, existing stale cleanup, complete checks/tests, final
secret and final policy in their original order. Do not rerun an unsuccessful
full suite or mix its counts with historical 1080/43/2 results.

The process canary remains unchanged: 20 iterations, 10-second waits, ownership
and retry rules. A new canary failure requires STOP and separate consideration
of safe diagnostic metadata only. Even a new pass would not establish the past
failure's root cause. A new secret or other gate failure likewise ends this
attempt without expanded exceptions, deletion or weakened checks.

Only after full exit 0 may final frozen 0001–0007/no-0008/operational-DB and
execution-file preservation checks support submission. If only report/status
documents then change, stage those exact documents and repeat final standalone
secret/policy scans plus both diff checks and raw index/worktree equality before
commit/push. No final result or commit is claimed yet. Maximum eventual R1 state
is `IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW`, never PASS/CLOSED.

### Preserved local diagnostic evidence

The following four files are **local diagnostic evidence — not part of R1
commit**. Preserve them until independent verification finishes; do not delete,
stage or treat their absence from Git as loss of their local evidence. Links in
the historical diagnosis below are local evidence references, not promises that
these CSVs are present in a checkout of the R1 commit.

- `PHASE_02_CP3_C2_B2_C_R1_DIAGNOSTIC_FINDINGS.csv`
- `PHASE_02_CP3_C2_B2_C_R1_HISTORICAL_FINDINGS.csv`
- `PHASE_02_CP3_C2_B2_C_R1_DIAGNOSTIC_FILE_COUNTS.csv`
- `PHASE_02_CP3_C2_B2_C_R1_DIAGNOSTIC_SNAPSHOT.csv`

Their aggregate classification/distribution and evidence limits remain in this
report. The localized R1-REPLAY-01 profile fix is not proof of general DB/process-
crash ambiguous-commit replay safety; the latter and actual browser/device
ceremony remain `NOT VERIFIED`. KI-017/KI-018 stay open/nonblocking. No routes,
issuer approval, public/trading, merge/tag/release or next checkpoint is added.

## Historical diagnostic execution — scope note

The diagnosis-only authorization and proposals immediately below describe that
earlier execution. The dated approval above supersedes only its prohibition on
the specifically authorized scanner remediation and conditional QA/submission;
it does not rewrite the old execution's actions, evidence or failure results.

## Read-only diagnosis — 2026-09-05; STOP retained

Authorization for this follow-up is diagnosis and safe reporting only. No R1
runtime, semantic policy, tests, dependencies, migrations, scanner, canary,
baseline or ignore rule was changed. No cache/old evidence was deleted, and no
full QA, canary rerun, commit, push or staging was performed. The unchanged
standard scanner used its own normal temporary-resource creation/finally cleanup
once, as explicitly allowed. Implementation proposals below are **not applied**.

### Three distinct failures

| Failure | Established cause / boundary | Still NOT VERIFIED |
|---|---|---|
| First full-run document/index mismatch | Nine preserved Markdown working files differed from their staged raw Git blobs. Unchanged Assert-GitIndexMatchesWorkingTree rejects this at secret-scan.ps1:547. This was the assistant's sequencing error, not a runtime failure. | The exception did not name the first rejected path; do not claim a logged per-file throw. |
| Second full-run canary timeout | Unchanged Wait-ForCanaryManifest reached its 10-second deadline at process-cleanup-canary.ps1:24 with the manifest absent at its last existence check and no earlier observed launcher-wrapper exit. | Which call/iteration, actual root/controller state, port stage and underlying cause. |
| 2,401 potential-secret findings | The scanner includes ignored generated files. These mypy/TypeScript hash fields and cache-tag constants have no registered exact exception, so their entropy findings remain blocking. The new diagnostic population is exhaustively explained below. | Historical individual candidate identity/input hashes were not retained; the old result cannot be retroactively replaced. |

The first full run's actual backend **1080**, frontend **43**, E2E **2** passes
remain recorded, with its own full-script **exit 1**. The second full run's
**exit 1 before backend** also remains. This diagnostic does not execute or pass
any of those test suites and does not close R1-REPLAY-01 independently. Its local
precision-profile evidence is separate from general DB/process-failure replay
safety, which remains NOT VERIFIED.

### Execution snapshots and document/index chronology

Repository, exact R1 branch and HEAD
87748c8311242e0bd45bac86e8d60da24ac8ba8a were verified. Diagnosis began with
27 staged files, zero unstaged and zero nonignored untracked files. All **341**
working-file SHA-256 values matched the preceding STOP snapshot. Both before and
after the diagnostic scan, those same 341 files were byte-identical. In particular
the original **259 non-Markdown** execution/test/dependency/checking inputs did
not change. Per-file before/after hashes are in
[the protected-file snapshot](PHASE_02_CP3_C2_B2_C_R1_DIAGNOSTIC_SNAPSHOT.csv).

The first full run's mismatch set was exactly:

- CHANGELOG.md
- DECISIONS.md
- KNOWN_ISSUES.md
- STATUS.md
- plans/PHASE_02_CP3_C2_B1_RUNTIME_CONTRACT.md
- plans/PHASE_02_CP3_C2_B2_C_ADR_018_COUNTER_CAPABILITY_SCHEMA_PROPOSAL.md
- plans/PHASE_02_CP3_C2_B2_C_SCHEMA_REMEDIATION.md
- plans/PHASE_02_EXECUTION_PLAN.md
- qa/PHASE_02_CP3_C2_B2_C_R1_WEBAUTHN_CORE_CODEX_REPORT.md

The approved preserved changes were staged before the second full run; all 341
raw index/worktree blobs matched then, so that mismatch was resolved for that
execution. The second run failed earlier at the canary, not at the index gate.
Afterward the STOP/status documents were updated and staged before the standalone
scans. Following those scans, only CHANGELOG, DECISIONS, STATUS and this report
were updated to record the failures and staged. That was the 27-staged/zero-
unstaged state delivered at the previous STOP; it was not a rescanned snapshot.

This follow-up leaves that index unchanged. Only this report and four safe CSV
attachments are added/updated **after** the one diagnostic scan. They are not
represented as a rescanned or commit-ready snapshot. No raw candidate value,
fingerprint, matched source line, security log, environment dump, private key,
signature or raw challenge is included in these attachments.

Actual executed script identity is not inferred from HEAD alone:

| File | Base blob | Index blob | Raw working vs index |
|---|---|---|---|
| scripts/secret-scan.ps1 | 7d4546d281b47a086b2b181bd50727f276aa8d72 | 7d4546d281b47a086b2b181bd50727f276aa8d72 | MATCH |
| scripts/secret_scan_driver.py | 3e3632a7b6c3ba6fb5182fb4ed696d48cbda9dc3 | 3e3632a7b6c3ba6fb5182fb4ed696d48cbda9dc3 | MATCH |
| scripts/process-cleanup-canary.ps1 | 6ba9ec07e14c8172896555efc172f9387d7b3552 | 6ba9ec07e14c8172896555efc172f9387d7b3552 | MATCH |
| scripts/process-cleanup-canary-root.ps1 | 97bd59bf28190a781f1dc386305160e8bd674cd5 | 97bd59bf28190a781f1dc386305160e8bd674cd5 | MATCH |
| scripts/process-job-close-canary-controller.ps1 | d97e0f275170ead21254687291d4bab5e7fa8d92 | d97e0f275170ead21254687291d4bab5e7fa8d92 | MATCH |
| scripts/process-ownership.ps1 | 05b6385ca30c9a890f5904b33dddd62e15fd8bc3 | 05b6385ca30c9a890f5904b33dddd62e15fd8bc3 | MATCH |
| scripts/owned-process-launcher.ps1 | e904e5510acac926d44501f5dceceb4314f6880e | e904e5510acac926d44501f5dceceb4314f6880e | MATCH |
| scripts/common.ps1 | f1fc284e72c56dfe9144c05af08122fef5abc650 | f1fc284e72c56dfe9144c05af08122fef5abc650 | MATCH |
| scripts/test.ps1 | f5cc119b68c84628c0e5b3bf606e10f1f0f36090 | ba15c7931a315b742e68a7d61c1a3f105ed1bc6e | MATCH |
| scripts/policy-scan.ps1 | bbee7a65161e51e411d1d1218d08d762c5d32c3e | 9f0209e739d11f69fe93bd3c726e173ac22185bb | MATCH |

The full current SHA-256 values are also in the protected-file snapshot.
test.ps1 differs from base only in three approved inventory lines, 851→1080;
its cleanup and canary invocation are unchanged. policy-scan.ps1 has the
preserved, earlier approved R1 dependency/test inventory, digest and exact OWNER
native-boundary admission changes; it is not base-identical and was not altered
by this diagnosis. All other listed scanner/canary/control files are base=index=
raw-working. Frozen 0001–0007 are likewise base=index=raw-working; 0008 and
operational var/dashboard.db remain absent.

### Secret evidence acquisition and its limitations

The previous model-facing scan output was truncated. Reading the existing local
session record's unabridged command-output field recovered **2,392 complete
path/line/type occurrences**, not 2,401. The recorded exception still says 2,401.
All recovered rows are Hex High Entropy String, line 1: mypy metadata 1,703,
mypy cache tag 1, Ruff cache tag 1, TypeScript build-info 687. The missing nine
rows' original metadata/fingerprints cannot be recovered from that output. Why
the persisted output lost these rows is NOT VERIFIED.

Because the original structured scan result had been removed by standard
finally cleanup, one evidence-only run was necessary:

- Exact command: pwsh -NoProfile -File scripts/secret-scan.ps1
- UTC start: 2026-09-05T06:29:37.4525936Z
- UTC finish: 2026-09-05T06:35:33.6860362Z
- Standard scanner PID: 2336; command exit **1**, reported **2,401**.
- Observer captured the standard scan.json in memory at
  2026-09-05T06:35:27.2985497Z, with zero partial-read failures.
- Entire standard stdout was drained in memory, yielding exactly 2,401 safe
  path/line/type rows; stderr was drained separately. Raw streams were not added
  to the repository or shared as attachments.
- Observation ran from an external temporary PowerShell file, with unchanged
  pwsh arguments, environment, scanner input/logic, result and process control.
  It used short read-sharing/delete-sharing handles and did not delay or replace
  normal finally cleanup. No inspection source/function was patched or replaced.
- The observer's own process exit 0 only means evidence collection finished; the
  scanner's actual exit is **1**, never PASS.
- The standard temp root was empty afterward. No preexisting file was deleted,
  moved or renamed. No second scan is performed.

Read directly in this diagnosis: Python 3.13.15, SQLite 3.50.4, PowerShell 7.6.5,
Node v24.19.0, detect-secrets 1.5.0, mypy 1.17.1, Ruff 0.12.11 and TypeScript
5.9.3. No dependency was installed or updated. The external observer source
remains at C:/Users/beomoo/AppData/Local/Temp/r1-diagnosis-observer-d34dd9acfb89478b9437ddb4975d3485/observe-secret.ps1;
it contains no raw candidate values, was not added to Git, and was not deleted.

Transport retention capped the observer's large structured result. All 2,401
safe table rows were recovered, and all 1,705 failed mypy/tag fingerprints were
retained and mapped exactly. The TypeScript fingerprint portion was not retained;
its complete finite candidate population was instead proved by the exhaustive
generation/lexical-set argument below, not by claiming a retained fingerprint list.
The original truncated tool output also retained the exact TypeScript scan-input
size/SHA-256 completion record, which matches the independently checked file.

All 857 checked generated files (854 mypy metadata files, two tags, one build-info)
were hash-identical across proof and post-scan checks. Their latest observed
LastWriteTimeUtc is 2026-09-05T04:50:11.9470311Z, before the earlier scan.
This supports continuity, but timestamps alone are not a cryptographic historical
snapshot. The new 2,401 result agrees with every recovered historical per-file
count except TypeScript, where 687 retained old rows compare to 696 new rows.
Do not silently fill the nine missing historical rows using the later execution.

### Exhaustive classification — populations kept separate

Classification labels in the safe CSVs:
ACTUAL_SECRET; PROVEN_NOT_SECRET; INTENDED_SYNTHETIC_TEST_VALUE; NOT_VERIFIED.

| Population | Actual secret | Proven not secret | Intended synthetic test value | NOT VERIFIED | Total |
|---|---:|---:|---:|---:|---:|
| Original reported run, historical identity standard | 0 confirmed | 0 retroactively proven | 0 confirmed | 2401 | 2401 |
| New single diagnostic run, exact current snapshot | 0 | 2401 | 0 | 0 | 2401 |

Historical NOT VERIFIED means the individual historical value/input snapshot is
not retained, **not** that current generated values are suspected credentials.
[Historical occurrence inventory](PHASE_02_CP3_C2_B2_C_R1_HISTORICAL_FINDINGS.csv)
contains the 2,392 recovered metadata rows plus nine explicit NOT_RECOVERED
placeholders; missing paths/lines/types are not invented.
[New diagnostic occurrence inventory](PHASE_02_CP3_C2_B2_C_R1_DIAGNOSTIC_FINDINGS.csv)
contains all 2,401 real path/line/type/classification/basis rows.

| New diagnostic family | Files | Occurrences | Exact proof |
|---|---:|---:|---|
| .mypy_cache/3.13/**/*.meta.json | 852 finding-bearing files | 1703 | M1: 852 source hash + 851 interface hash findings |
| .mypy_cache/CACHEDIR.TAG | 1 | 1 | C1: complete 193-byte public generator output |
| .ruff_cache/CACHEDIR.TAG | 1 | 1 | C2: complete 43-byte fixed generator marker |
| apps/web/.next/cache/tsconfig.tsbuildinfo | 1 | 696 | T1: full 696-value generation/lexical universe |
| Total | 855 | 2401 | Every occurrence assigned once |

All 2,401 detections have type **Hex High Entropy String**, line **1**.
By ownership category: current R1 changed files **0**, existing unchanged Git
files **0**, generated artifacts **2401**, logs **0**. Classification is based on
generation proof, not these locations or their ignored/untracked status.
[Every file's distribution](PHASE_02_CP3_C2_B2_C_R1_DIAGNOSTIC_FILE_COUNTS.csv)
is included; counts reconcile to 2,401.

Duplicate accounting is explicit:

- 855 distinct path/line/type triples; 1,546 additional rows share a triple.
  These are not automatically duplicate candidate values.
- 2,401 distinct path/type/value-fingerprint identities in the diagnostic.
- 2,380 distinct candidate values across files; 21 repeated-value occurrences.
  Candidate fingerprints are used only in memory, never in the attachments.
- The TypeScript source entries number 704, with 696 distinct version values;
  its eight repeated entries are already deduplicated by the scanner.
- Historical unique candidate count and exact duplicate-value count are
  NOT VERIFIED because only path/line/type output survives.

Proof details, covering every current candidate:

**M1.** All **854** current mypy metadata files, not just the 852 finding-bearing
files, were checked. Every hash equals SHA-1 of the exact referenced source bytes,
and every interface_hash equals SHA-1 of its companion .data.json bytes:
**854/854 + 854/854**, zero mismatches. All metadata version_id values are 1.17.1.
Sources are 67 repository files and 787 installed-venv files; none is external to
those roots. Each of the 1,703 retained scanner fingerprints was matched to the
verified property's UTF-8 value fingerprint. Source generation is pinned installed
mypy/util.py:562, fscache.py:254/282, build.py write_cache:1511,
data serialization/hash:1563–1564 and metadata assignment:1622/1629.
No .data.json contents or source lines are reproduced.

**C1/C2.** The complete mypy tag equals the public string literal in installed
mypy/build.py:1211 after the actual Windows text-mode LF→CRLF conversion; no
arbitrary content normalization is used. The complete Ruff tag equals the fixed
marker embedded in installed Ruff 0.12.11 and the public marker prefix in that
same mypy source. Both scanner fingerprints match that marker. Ruff's Rust
generator function source is not installed and remains NOT VERIFIED; no guessed
MD5 preimage is used. These are fixed public cache markers, not authority tokens.

**T1.** Installed TypeScript **5.9.3** was used read-only:
ts.sys.readFile(source) → ts.getSourceFileVersionAsHashFromText(ts.sys, text).
All **704/704** stored versions match, with zero different string signatures;
659 sources are installed node_modules and 45 are repository/generated files.
All 704 quoted hexadecimal string occurrences in the **entire raw build-info
text**, and every hexadecimal string/key in its parsed structure, belong to
that verified version set. There are exactly **696 distinct values** and **zero
unproven hexadecimal strings**. The detector's installed normal quoted-hex rule
and file/type/value deduplication therefore have only these 696 possible values;
the standard run reports exactly 696 distinct findings for this one-line file.
This establishes exhaustive population equality without relying on a few examples
or merely assuming that a 64-character string is a hash. The scan's retained
input completion SHA-256 equals the checked 136,594-byte file. Generator source:
node_modules/typescript/lib/typescript.js:133838, Node SHA-256:8657,
read/BOM handling:8525, build-info serialization:131264. No custom scanner rerun
or threshold/filter alteration was used for this structured proof.

Transformer selection was also checked without rerunning a plugin: .tsbuildinfo
is FileType.OTHER (detect_secrets/util/filetype.py:27); the non-eager INI parser
rejects its sectionless JSON first line (transformers/config.py:94/103), and YAML
does not select this extension (transformers/yaml.py:28). The unchanged driver
falls back to raw lines (:117–130) and does not use eager processing after normal
findings exist (:118–120). No separate has_secret/transformer-branch runtime log
was retained. The possible raw-zero/eager-config branch was therefore also
reviewed: for this one-line JSON it can only wrap the whole non-hex value after
the first colon and escape existing quotes (config.py:42–65, :94–103). It cannot
introduce a new quoted hexadecimal value outside the verified raw set; the key
and whole wrapped JSON value are not hexadecimal strings. The population bound
thus holds in either branch, without inventing an observed branch trace.
The installed quoted regex is high_entropy_strings.py:31 and deduplication is
PotentialSecret.fields_to_compare (:54): filename, secret_hash, type.

There are no intended synthetic-test candidates in this population, so no
storage-prohibited raw challenge/assertion/private-key fixture is being excused.
No actual credential is confirmed; no candidate was sent to an external API.
No credential rotation is justified by the current findings alone. If a later
candidate is confirmed as a credential, separately assess its exact local/Git/
log exposure and seek explicit revocation/rotation authority.

### Why existing exceptions did not apply

Get-SecretScanRepositoryFiles (secret-scan.ps1:754) does not use Git ignore as an
exclusion mechanism. Exact exclusions are dependency/Git/browser-binary roots
and the current scanner's own temporary root, not mypy/Ruff/Next cache families.

Test-AllowedArtifactFinding (:945) requires entropy type plus exact canonical
path, line and candidate SHA-1 key. Existing registration functions handle
specific evidence/package manifests, frozen migration references, Next nft
fileHashes/entryHash, trace IDs, prerender keys, sentinel fixtures and encryption
manifests. They register neither mypy hash/interface_hash, either cache tag, nor
TypeScript build-info versions. Thus these findings are expected to remain
blocking under the **unchanged current scanner policy**, despite their proven
non-secret nature in this diagnostic. The diagnosis is not a policy exception.

### Canary evidence and bounded conclusion

Existing full command-output records were used; canary was **not rerun**.

| Evidence | First full run | Second full run |
|---|---|---|
| Tool session ID, not OS PID | 76877 | 80119 |
| Command end UTC | 2026-09-05T04:46:41.628Z | 2026-09-05T04:50:27.435Z |
| Entire command duration | 1823.5527946 seconds | 100.0748364 seconds |
| Entire command exit | 1, later document/index gate | 1, canary |
| Retained stdout / separate stderr | 14286 / 0 characters | 2071 / 0 characters |
| Canary evidence | standard 20 iterations passed | helper throw :24, propagation common.ps1:187 |

The first success recorded root-exited-before-cleanup, two owned descendants
removed, unrelated control survived, owner-crash kill-on-close and atomic
pre-resume probe removal. Those successes do not excuse the second failure.

The same Wait-ForCanaryManifest helper has two calls: :132 waits for
job-close-ready.json while observing the controller's launcher wrapper; :292
waits for manifest-N.json while observing the root's launcher wrapper.
Start-OwnedProcess returns owned-process-launcher.ps1, **not the actual target**.
The wrapper starts its target and waits (launcher:148). Therefore the observed
error does not establish that a healthy root/controller was running.

The complete failed output still lacks the exact call, iteration, manifest kind,
OS PID/start-time identities, child exit codes and root/controller stdout/stderr.
Port/manifest/pending existence and timestamps were not retained before cleanup.
These are NOT VERIFIED, not silently inferred from a later successful run.

Outer timeout starts after wrapper creation. General root does startup and
listener/sleeper creation before its separate port deadline (root:87); port
publication is :59/64, and manifest publication :122/127. The job-close path adds
controller startup and suspended-probe work before its own inner manifest wait
(controller:37/43/111), root-exit wait :112, and ready publication :155/160.
An outer 10-second budget can expire before an inner 10-second budget ends.
This structural overlap is real; its role in **this** failure is NOT VERIFIED.

No cleanup-warning branch appeared in the complete failed output. Previous
post-failure checks found both temporary roots empty and no repo-attributable
canary/pytest command match; they are still empty. Historical identity-specific
termination/exit codes cannot be proven without the missing PID/start metadata.
Observed other-repository Python work is not evidence of causation.

### Minimal proposals and regression plan — design only

| Problem | Exact proposed scope | Requirement / regression basis |
|---|---|---|
| Document/index mismatch | Procedural fix only: freeze authorized docs, review and stage before the scan, verify all raw blobs, prohibit edits during execution. Optional safe path-only error context in Assert-GitIndexMatchesWorkingTree. | Preserve the strict index gate. Check unstaged Markdown, same-line/CRLF raw mismatch, alternate Git index/env override and no edits during scan remain rejected. Do not weaken normalization or skip docs. |
| Canary evidence gap | process-cleanup-canary.ps1: Wait-ForCanaryManifest, both call sites, and cleanup-before-delete error reporting. Add safe stage enum JOB_CLOSE_READY/ITERATION_MANIFEST, iteration, elapsed/UTC, wrapper PID/start identity, known file existence/size/time and allowlisted child metadata. | Keep 20 iterations, all 10-second deadlines and existing ownership/finally. Exercise both call sites, early wrapper exit, timeout, success, iteration1/20, PID reuse, cleanup and unrelated-process survival. Synthetic sensitive log values must not leak. No runtime behavior fix is justified without evidence of the failing stage and cause. |
| Proven generated hash findings | Proposed new narrowly validated helpers in secret-scan.ps1 for mypy hash fields, TypeScript version fields and complete cache-tag constants; register only exact proven field/value occurrences with the existing finding key. | No directory/extension/ignore exclusion. Validate pinned generator/schema/source roots, all source/data/version hashes, complete tags, duplicate-key rejection, no external/reparse/hard-linked sources, and complete snapshot equality. Keep all current self-canaries, encoding, binary and coverage checks. |
| Lost diagnostic metadata | A separately approved metadata-only collector/output design, outside scanned inputs, that retains bounded path/line/type/classification records before finally and checks expected population counts; stream only safe metadata, not raw candidates or giant security JSON. | Verify long output/population reconciliation and both normal/failure finally paths. This follow-up's transport cap demonstrates why a huge single JSON output is insufficient. |

Suggested helper names are Add-ValidatedMypyCacheHashExceptions,
Add-ValidatedTypeScriptBuildInfoExceptions and Add-ValidatedCacheTagExceptions.
They are proposals, not existing functions. No automatic allowance for other
mypy/TypeScript versions, missing source/data, changed source content, unknown
signatures or unexplained fields is proposed.

Required negative tests before any exception approval:

- Mutate one expected hash, source/data file, version or tag byte: no exception
  or fail closed; never substitute a calculated value into the input.
- Add an unrelated high-entropy credential/Bearer/private-key-shaped value to the
  same generated file and line: detection remains. Move an otherwise allowed
  value to a forbidden field/line/file: do not inherit an exception.
- Existing keys are only path/line/value, not JSON pointers. Therefore registration
  must be refused unless **every occurrence** of that value at the registered
  line is in a proven allowed field; otherwise even a duplicate allowed value in
  another same-line field could inherit the exception. Strict schemas and
  duplicate-key/extra-field checks must enforce this, not just format matching.
- Unknown fields, duplicate JSON keys, malicious/external paths, links, missing
  companions and concurrent input changes must fail closed.
- TypeScript BOM/sourceMappingURL behavior must match the pinned generator;
  different signature values need their own proof, not blanket acceptance.
- Preserve scanner self-canaries and scope/completion checks, PID ownership,
  standard canary iterations/timeouts and all previous tests. Any separately
  approved scanner/canary change will require the corresponding exact phase-
  control digest/inventory update in policy-scan.ps1, not a relaxed policy check.

No timeout increase, repeat reduction, journal/SQLite setting change, process
termination outside ownership, execution-policy/security-software adjustment or
R1 runtime change is proposed or performed here.

### Diagnostic handoff

Safe additions are this report plus four CSVs linked above. The existing 27 staged
files, including all prior R1 work, remain in the original index; diagnostic
report additions are intentionally not staged. Both diff checks pass, with no
protected execution-file drift. No successful scan of the post-diagnosis report
is claimed and no further scan is authorized by inference.

STOP remains. Independent GPT review, general DB/process-failure replay safety,
the historical missing identities and the canary root cause remain NOT VERIFIED.
KI-017/KI-018 remain open/non-blocking. Real ceremony, routes/frontend,
issuer approval, public/trading, merge/tag/release and the next checkpoint remain
outside scope. Maximum eventual state remains IMPLEMENTED — AWAITING GPT
INDEPENDENT REVIEW; this diagnostic does not grant that promotion.


## Final handoff security checks — additional STOP

After staging all nine STOP/status documents, git diff --check,
git diff --cached --check and git diff --exit-code each exited 0; all 341 raw
working/index blobs matched. The final snapshot differs from the resumption
snapshot only in those nine Markdown files: all 259 non-Markdown execution,
test, dependency and checking-script files remain byte-identical. Frozen 0001–0007
match base/index/raw working blobs. 0008, operational var/dashboard.db, the three
approved stale directories and the two previously removed Ruff files are absent.

The requested post-document standalone commands were then actually executed:

- pwsh -NoProfile -File scripts/policy-scan.ps1: **exit 0**, scope policy passed.
- pwsh -NoProfile -File scripts/secret-scan.ps1: **exit 1**, unchanged line 2167,
  "Secret scan found 2401 potential secret(s)." The displayed findings contain
  .mypy_cache/3.13/OpenSSL/SSL.meta.json and other mypy metadata, and
  apps/web/.next/cache/tsconfig.tsbuildinfo (line 1, Hex High Entropy String).
  Tool output was truncated; this is not a complete findings-path inventory.
  No raw matched values or DB/journal/key/signature contents are reproduced here.

The findings are **not adjudicated** as actual secrets or false positives. No
additional file is deleted, moved, renamed or exempted, and no scanner/baseline/
ignore/runtime/test/dependency change or retry is made. This is an additional
blocking result, separate from the canary timeout. It does not show a recurrence
of the removed journal and does not establish that the deleted journal was safe.

Only this report and the existing status/changelog/decision records are updated
after those standalone scans to preserve their failures, then staged for STOP
handoff. They have not received a subsequent successful final scan; do not apply
the preceding policy result to a claimed fully verified final commit snapshot.
No commit/push: HEAD remains 87748c8311242e0bd45bac86e8d60da24ac8ba8a.
The exact R1 remote-ref query exited 0 with no matching branch; remote HEAD
equality is not applicable. The 27-file inventory below is retained in the index.
Full QA exit 0, successful final secret scan, complete findings adjudication,
canary root cause and independent acceptance remain NOT VERIFIED.

## Historical STOP — second standard resumption failed before backend

The nine originally unstaged document diffs were incorporated without loss into
the 27 staged R1 files. Before rerunning the standard command, all **341 raw
working/index blobs matched**, both diff checks passed, no Python/test/DB process
was running, and the complete backend-tests direct-child list was empty. No
additional stale directory was deleted in this second run. No document or code
was edited while that run was active.

The second `pwsh -NoProfile -File scripts/test.ps1` again exited **1**, this time
at `scripts/process-cleanup-canary.ps1:24`: "The cleanup canary root did not
publish its manifest." Initial policy, dependency checks, offline guards, lint
and typechecks passed. The 20-iteration canary did not complete; backend tests,
migration/fixture checks, frontend tests/build/E2E and final secret/policy were
not reached in this second attempt. The preceding attempt's actual 1080/43/2
passes remain valid recorded test results, but its own script exit 1 is unchanged.
Neither full attempt reached a full-script exit 0 or its final policy scan.
The later standalone security results are recorded separately above.

Read-only diagnosis: Wait-ForCanaryManifest has an unchanged 10-second UTC
deadline, polls at 25ms, and raises this specific error when the manifest remains
absent without an earlier observed root exit. The same helper services both
job-close readiness and per-iteration manifests; the emitted error does not
identify the precise caller/iteration. Exact producer failure, scheduling cause
and root cause are **NOT VERIFIED**. The script's finally cleanup ran without a
reported additional cleanup error; `var/tmp/phase-01` and `var/tmp/backend-tests`
both contain zero children afterwards. A scoped process check found zero
remaining repo-attributable canary/pytest command matches. Concurrent non-repo
Python/pytest work was observed after failure; it is not proven causal and was
not terminated or otherwise changed.

process-cleanup-canary.ps1, its root/controller, process-ownership.ps1,
common.ps1 and secret-scan.ps1 raw blobs still equal the original base. No timeout,
assertion, skip/xfail, SQLite setting, scanner exception, cleanup logic, runtime or
dependency was changed. The first attempt's successful canary does not excuse
this failure. STOP for separate QA-infrastructure investigation/direction rather
than repeating until green. No commit/push is performed.

The approved three-directory disposal is complete; the former journal did not
recur. Its metadata/hashes and every earlier failure remain below. Operational DB
and 0008 remain absent; frozen 0001–0007 are unchanged. Remaining NOT VERIFIED:
full successful standard QA, successful final secret scan, this canary failure's cause,
GPT independent review, real WebAuthn ceremony and general DB/process-failure
replay safety. KI-017/KI-018 remain open/non-blocking, and later scopes remain
unauthorized. The latest STOP records are staged with the preserved documents
for handoff; they do not represent independent acceptance or R1 closeout.

## Approved stale-disposable cleanup and full-QA resumption

The subsequent user approval replaces the standalone-secret-first ordering only
for verified stale disposable resources. No runtime, test, dependency, migration,
SQLite setting, scanner, baseline, ignore or detection-policy change is authorized
or made. Run the unchanged standard `pwsh -NoProfile -File scripts/test.ps1`:
initial policy, existing stale cleanup, full tests/checks, final secret, final policy.
Do not repeat cleanup to convert any new final scan failure into PASS.

At resumption: repository/branch/base matched; 27 staged files and nine additional
unstaged Markdown changes were present. Each of the nine diffs was reviewed and
retained. The baseline has 341 tracked/indexed/nonignored untracked working files.
For the 259 non-Markdown files, ordinal-sorted `path<TAB>lowercase SHA256` records
joined by LF without a final LF have SHA-256
4f9e82ddc124810d633306e9ef52c121162024816683e02c5b69661837639e50.
LF-normalized captured git diff --cached --binary has SHA-256
8ad9400ab363fbf02050edf14b989f22b6f544d6166127e5212fda830a0421c3;
the unstaged counterpart is
cb67e7683084bcf76fa82fd910f910d532ff7583f7ac5b95c4541262e40ae578.
No runtime/test edits are needed; the final 229/277 passes below remain applicable
focused/subset evidence, not the new full-suite result.

### Pre-enumerated deletion scope and provenance

Canonical parent: `C:/Users/beomoo/Documents/ChatGPT/tosstoss/var/tmp/backend-tests`.
Its complete direct-child list is exactly these three directories; there are no
other direct children or nested directories. No root/var/evidence/cache deletion
is authorized by this list.

| Directory | Confirmed test source/execution and retention assessment |
|---|---|
| 668b5718e39c4293af072b3776f22632 | `test_counter_capability_migration.bootstrap_engine` creates counter-bootstrap.sqlite3 under conftest's managed workspace_tmp_path and upgrades frozen 0007. The recorded six-file regression included this fixture and was interrupted before the successful rerun. File creation/modification at 03:15:01–03:15:03 UTC matches that interrupted execution. The exact test parameter and precise teardown interruption point are NOT VERIFIED; interruption is consistent with the residue, not a proven root cause. Only the synthetic fixture DB and its journal remain. |
| 721bac18423849ebaa9998cdcde5cc62 | Exact directory printed by the recorded manual New-Item + restart_probe seed/verify commands; seed/verify exited 0 with PIDs 20712/32800, later verify PID 27724 also exited 0. restart_probe has engine.dispose in finally and deliberately leaves its disposable DB for standard stale cleanup. |
| b47e491ba0dc4ee1a0da48b2d2212ad3 | Empty directory at 03:01:45 UTC correlates with the immediately preceding recorded New-Item staging command for the isolated restart-probe attempt. That command creates the directory before Python; module import exited 1 before seed could execute. The execution chronology and absence of any files distinguish it from the later explicitly printed successful probe directory; its identification is this execution/metadata correlation, not its UUID/ignore rule alone. |

These resources contain no user/operational work: their generators are the
recorded offline migration fixtures/manual test probe, all using disposable DB
URLs and synthetic/transient test material. They are not unique evidence requiring
binary preservation: the failure was scanner input classification, with exact
path/error, commands, source, metadata and hashes preserved here; no failed R1
assertion or production incident requires this DB state. The earlier interrupted
run and successful fresh regression remain recorded. No DB was opened through
SQLite for recovery, checkpointing or inspection of rows.

All dates in the metadata table are 2026-09-05 UTC; filenames are under the above
directory. All files below exist. No -wal/-shm or additional file exists; the third
directory is empty. No raw DB/journal/key/signature content was emitted.

| Directory / file | Bytes | Created / modified UTC | SHA-256 |
|---|---:|---|---|
| 668b… / counter-bootstrap.sqlite3 | 987136 | 03:15:01.9251340 / 03:15:03.8384806 | 0e53aa306693512801d733c64ee61e068f88e49372d58e0176fac14d7fe99115 |
| 668b… / counter-bootstrap.sqlite3-journal | 8720 | 03:15:01.9271465 / 03:15:03.8478239 | df526939c31e7d8265c9b913047e1e55e385ef99c13c6325f0c393c0bdb991f7 |
| 721b… / time-profile-restart.sqlite3 | 1159168 | 03:02:27.3909504 / 03:02:31.4514130 | 64abcc6ac92f53059c8f83b8119b42afa80b9a64cc4a170ec09ca3a52d601697 |

Directory created/modified UTC respectively: 668b… 03:15:01.9210596 /
03:15:03.8478239; 721b… 03:02:23.4247879 / 03:02:31.4544140;
b47e… 03:01:45.3063573 / 03:01:45.3063573.

Preflight traversed each ancestor through the volume root and each tree entry
before descent: zero symlinks/junctions/reparse points. Every file's fsutil
hardlink list exited 0 with exactly one link. No item is Git tracked/staged;
all are under the existing ignored test root. Read-only exclusive FileShare.None
handles succeeded for each complete file while hashing. No Python/pytest/Ruff/
SQLite/DB-browser process is running; prior test/probe processes have exited.
These checks establish present non-use without opening SQLite or modifying bytes.

PowerShell AST comparison found Clear-StaleBackendTestDirectories identical to
base HEAD after LF normalization, SHA-256
1704c77c8721fe00763227eeb69545eaad97ad8a54c2fb627b2d24ba9097bb08.
scripts/test.ps1 differs from base only in three inventory lines (851→1080).
common.ps1, conftest.py, test_counter_capability_migration.py, secret-scan.ps1 and
.gitignore raw blobs exactly match base. The helper still validates canonical
direct children, 32 lowercase hex names, reparse-free trees and hard links, then
removes whole disposable directories with literal paths; it does not remove the
root or separately discard a journal while retaining its DB.

The standard run passed initial policy and reported exactly three stale
directories removed. All three prelisted paths are absent, the test root remains,
and the operational DB and previously removed Ruff files remain absent. Comparing
the 341 working-file snapshot immediately after cleanup found only this QA report
changed; all 259 non-Markdown files are identical, including execution code,
tests, dependencies and checking scripts. No directory outside the prelist was
removed in this stale-cleanup phase. Any eventual secret PASS applies to actual
post-cleanup inputs, not the deleted journal.

### First standard resumption run — preserved exit 1

`pwsh -NoProfile -File scripts/test.ps1` completed backend **1080 passed in
1459.75s**, frontend **43 passed** (10 files, 3.61s), and E2E **2 passed in 17.6s**.
Initial policy, pip check, offline Python/Node guards, lint (118 formatted files),
backend typecheck (67 files), frontend typecheck, 20-iteration process cleanup
canary, offline Toss preflight/self-test, migration repeat/downgrade/re-upgrade,
fixture import 13 then 0 (13 unchanged), OpenAPI and both builds passed.

The overall script nevertheless exited **1** at final secret-scan line 547:
"The Git index and working tree differ during the secret scan." Final policy was
not reached. This is NOT a successful full QA run and is not retroactively relabeled.
The backend-test root was empty after backend completion and after script exit;
the old directories and Ruff files stayed absent. No journal recurred.

The cause is the assistant's sequencing omission: the nine reviewed Markdown
changes (including this QA update) were preserved in the working tree but not
staged before the exact-index secret gate. Inspection of the unchanged scanner
shows it compares every indexed raw working blob to the staged object ID. The 259
non-Markdown files already match exactly; only those nine Markdown files differ.
No runtime/test/scanner fix, deletion or exception is needed or made. Stage those
authorized documents, verify all 341 raw blobs against the index, and repeat the
entire standard command for a genuine new exit-0 result. Before that repeat the
complete stale direct-child list is empty, so no further stale deletion is needed.
Do not edit even documentation during the repeated standard run. Preserve this
failed attempt and perform post-document final staging/scans after a successful run.

## Historical operational STOP after approved cache cleanup

After the final focused 229 and specified regression 277 passes, and successful
exact two-file cache cleanup, `pwsh -NoProfile -File scripts/secret-scan.ps1`
exited **1** at unchanged scanner line 922. Its next non-UTF-8 input is:
`var/tmp/backend-tests/668b5718e39c4293af072b3776f22632/counter-bootstrap.sqlite3-journal`.
Read-only metadata: 8720 bytes; created 2026-09-05T03:15:01.9271465Z, modified
2026-09-05T03:15:03.8478239Z. It is a disposable test artifact, not the operational
DB. Its content was not printed or added to Git. No assertion is made that this
artifact contains a secret: the scan failed on its strict input classification.

The user explicitly requires STOP if another file fails. Therefore this journal
and its directory were not removed/moved/renamed; no cleanup helper, alternate
interpreter, scanner/baseline/ignore/binary exception adjustment or full-suite
cleanup was used to bypass the ordering gate. Policy scan was **NOT RUN** after
this failure. The new full standard `scripts/test.ps1` run was **NOT STARTED**;
there is no post-remediation whole-suite exit-0 or 1080/43/2 result. The historical
1064/43/2 with full-script exit 1 below remains historical only.

Both authorized cache targets remain absent and var/dashboard.db remains absent.
The implementation and local focused evidence are preserved, but final QA and
independent-review submission remain blocked. No commit or push was made.
Local HEAD remains 87748c8311242e0bd45bac86e8d60da24ac8ba8a; read-only
`git ls-remote --heads origin refs/heads/feature/phase-02-b2c-r1-webauthn-core`
exited 0 with no matching remote branch, so remote HEAD equality is not applicable.
Further handling of the exact journal requires separate user direction; no
expanded cache or disposable-directory deletion is assumed authorized.

Final STOP snapshot: git diff --check and git diff --cached --check both exited
0. All seven frozen migration blobs match base, index and raw working files;
0008 and operational DB are absent. There are 27 staged R1 files, with nine
subsequent Markdown STOP/status updates left unstaged; no nonignored untracked
file remains. The 341-file before-cleanup/final snapshot comparison differs only
in those nine Markdown files. Executable code, tests, dependencies and policy
inputs are unchanged from the final focused/regression runs. Final runtime SHA-256
is 928b83842fa5d6424352ba3306b68d401677756be77361d0b17943797d6557d8;
new time-profile test is adf9804227166a7c30dc9fb13973fc470f5a61a70b4f702bd3131889439aad52.
No commit snapshot or successful full-QA snapshot is claimed.

Exact proposed R1 changed-file inventory (includes preserved prior R1 work):

```text
CHANGELOG.md
DECISIONS.md
KNOWN_ISSUES.md
STATUS.md
plans/PHASE_02_CP3_C2_B1_RUNTIME_CONTRACT.md
plans/PHASE_02_CP3_C2_B2_C_ADR_018_COUNTER_CAPABILITY_SCHEMA_PROPOSAL.md
plans/PHASE_02_CP3_C2_B2_C_SCHEMA_REMEDIATION.md
plans/PHASE_02_EXECUTION_PLAN.md
pyproject.toml
qa/PHASE_02_CP3_C2_B2_C_R1_WEBAUTHN_CORE_CODEX_REPORT.md
requirements.in
requirements.lock
scripts/policy-scan.ps1
scripts/test.ps1
services/api/src/toss_dashboard_api/reviewer/__init__.py
services/api/src/toss_dashboard_api/reviewer/canonical.py
services/api/src/toss_dashboard_api/reviewer/ledger.py
services/api/src/toss_dashboard_api/reviewer/runtime.py
services/api/src/toss_dashboard_api/reviewer/schema.py
services/api/src/toss_dashboard_api/reviewer/webauthn_core.py
services/api/src/toss_dashboard_api/reviewer/windows_owner.py
tests/backend/reviewer_test_support.py
tests/backend/test_reviewer_runtime.py
tests/backend/test_reviewer_runtime_time.py
tests/backend/test_reviewer_time_profile.py
tests/backend/test_reviewer_webauthn_core.py
tests/backend/test_reviewer_windows_owner.py
```

Remaining NOT VERIFIED: final full QA and final successful secret/policy scans,
GPT independent review, real device/browser WebAuthn ceremony, and generic
storage-failure/process-crash replay safety. KI-017 publication eligibility and
KI-018 absent GitHub CI evidence remain open/non-blocking; no later scope starts.

## Approved R1-REPLAY-01 execution compatibility remediation

The subsequent user approval explicitly supersedes the earlier cache-only scope
for this bounded runtime admission gate. The historical STOP and failed runs below
remain evidence, not retroactively successful QA. No GPT independent acceptance
or R1 closeout is claimed.

`runtime._require_time_profile` parses the unfinished operation's authoritative
0006 challenge issued_at/expires_at and prerequisite consumed_at, 0007 pending
verified_at and child issued_at/expires_at with the unchanged canonical parser.
It requires integer microsecond % 1000 == 0. `_transaction` calls it after OWNER
and ledger binding validation inside BEGIN IMMEDIATE; complete repeats it on the
final validated snapshot before the single clock sample; `_pending` and
`_authorized_continuation` check their validated writer snapshot. No new state,
terminal enum, dependency, payload authority, normalization or attempt marker is
introduced. The execution plan records the field-by-field frozen SQL rationale.

The incompatible path now remains pending **without executing crypto**, at all
later times and entrypoints. Neither identical assertion success nor later expiry
terminalization is allowed for that path. The former "later fresh attempt"
description does not apply and authorizes no retry. Completed off-grid historical
rows retain their original hashes/times and their ACTIVE credentials remain usable
in new aligned operations. Actual crypto and terminal consumption on invalid
aligned requests remain unchanged.

### New local checks (not a full-suite result)

Environment: Windows; Python 3.13.15 / SQLite 3.50.4 / Ruff 0.12.11.
All test databases use actual frozen 0001–0007; no production database is opened.

| Command/check | Actual result |
|---|---|
| `.venv/Scripts/python.exe -B -m pytest tests/backend/test_reviewer_time_profile.py -q --tb=short` before runtime fix, two exact reproductions | exit 1; 2 failed in 8.69s; A conflict→SUCCEEDED, B conflict→EXPIRED |
| Same command immediately after gate | exit 0; 2 passed in 7.35s; both submissions incompatible, real assertion verifier calls 0 |
| Expanded profile + existing time suite | exit 1; 64 passed / 1 failed in 166.24s; new individual-child fixture violated frozen child-issued/pending-verified ordering during setup |
| Corrected new fixture only: child/prerequisite timestamp +1µs, pending timestamp −1µs; profile suite | exit 0; 16 passed in 49.49s; frozen guards unchanged |
| Ruff check and format check, both `--no-cache`, on runtime/profile/time files | exit 0; checks passed, 3 files already formatted |
| Backend mypy | exit 0; 67 source files |
| Backend `--collect-only -q` | exit 0; 1080 collected (1064 historical + 16 new) |
| Focused five-file suite (webauthn_core, windows_owner, runtime, runtime_time, time_profile), `python -B -m pytest ... -q --tb=short` | exit 0; 229 passed in 420.86s |

Subsequent code inspection removed a redundant bound_target call from the pure
profile predicate, so admission does not move existing target/binding errors out
of their established handling order. The existing complete/pre-projection target
checks remain. The above focused result precedes that one-line adjustment and
does not substitute for the repeated focused/final QA on the adjusted runtime.
The first specified six-file regression invocation was deliberately interrupted
(process exit 1, no pytest failure reported before interruption) to restore the
requested focused-then-regression order after this review adjustment. It is not
counted as a completed 277-test result; the sequence is restarted in full.
Adjusted-runtime repeat: the exact five-file focused command exited 0 with
229 passed in 348.78s. The same disposable DB was also reopened by a third
process (PID 27724); verify exited 0 with verifier count zero and all rows
unchanged. Ruff check/format check with --no-cache both exited 0 again.
The subsequent specified six-file regression completed: exit 0, 277 passed in
897.33s. Repeated backend mypy also exited 0 for 67 source files. PowerShell
7.6.5, Node v24.19.0 and npm 11.17.0 were read directly from this environment.

Exact repeated commands:

```powershell
.venv/Scripts/python.exe -B -m pytest tests/backend/test_reviewer_webauthn_core.py tests/backend/test_reviewer_windows_owner.py tests/backend/test_reviewer_runtime.py tests/backend/test_reviewer_runtime_time.py tests/backend/test_reviewer_time_profile.py -q --tb=short
.venv/Scripts/python.exe -B -m pytest tests/backend/test_reviewer_operation_migration.py tests/backend/test_counter_capability_migration.py tests/backend/test_authority_migration.py tests/backend/test_authority_repository.py tests/backend/test_authority_decision_engine.py tests/backend/test_migrations.py -q --tb=short
```

The 16 new cases cover the exact A/B inputs with unchanged assertion bytes,
nine FIRST/ADD/REPLACE/REVOKE authorization/registration/child paths, three
individual prerequisite/pending/child fields, and two completed off-grid histories
(positive/zero counters) followed by real-crypto final revoke. Matrix attempts
include changed payloads, None, elapsed time, new service instances and every new
operation kind. Every incompatible attempt checks verifier count zero and complete
WRITE_TABLES/counter preservation, including committed authorizer history.

Process persistence command pair:
`.venv/Scripts/python.exe -B -m tests.backend.test_reviewer_time_profile seed <dir>`
then the same command with `verify <dir>`. Both exited 0, process IDs 20712 and
32800. The same disposable directory was
`var/tmp/backend-tests/721bac18423849ebaa9998cdcde5cc62`.
Verification after expiry still blocked complete/new FIRST without verifier calls
or row changes. These are separate top-level Python invocations, not child-spawn
tests; the fixture OWNER is not a real production steward. An initial attempt to
load that module through isolated python_runtime_guard exited 1 before seeding
because isolated sys.path does not expose the tests package. The guard was not
edited; this manual probe is not claimed as guarded/full-standard QA evidence.

### Authorized existing expectation changes

Only the 12 parameter instances of
`test_historical_off_grid_deadline_preservation_and_explicit_conflict` changed
execution expectation: 6 formerly TIMESTAMP_PRECISION_CONFLICT, 4 formerly
CHALLENGE_EXPIRED, and 2 formerly successful continuation/completion now all require
R1_TIME_PROFILE_INCOMPATIBLE. Fractions 123456/123900, expiry offsets −1/0/+1µs,
parent/child variants and original historical rows remain. Full row equality is
now unconditional; committed authorizer counter 8 and original-time assertions
remain. Only historical fixture construction uses a scoped admission bypass;
every actual attempt runs the production gate. No old test was deleted/skipped/
xfail'd, no historical input aligned, and no golden or frozen test changed.

### Post-verification rollback scope audit

`complete` still has fail-closed post-crypto revalidation, raw-clock regression,
defensive raw/SQL precision checks, and writer failures which `_transaction`
rolls back. `test_terminal_write_failure_rolls_back_all_projection` deliberately
injects an OUTCOME insertion failure and proves absence of partial credential,
authorization, consumption and outcome commits; it does not prove durable replay
rejection after arbitrary storage failure. Process-crash/ambiguous-commit replay
safety is NOT VERIFIED by this remediation. No new durable retry/attempt policy
is implemented. The approved profile removes the two demonstrated precision
eligibility transitions before crypto; aligned expiry/normal-path verification
is part of the subsequent focused/full QA, not inferred from the two regressions.

### Exact cache pre-deletion checks

Read-only checks confirmed the exact repository, R1 branch and original HEAD.
Both targets are untracked/unstaged and ignored by existing `.gitignore:22`
`.ruff_cache/`. Every path component through the volume root was checked for
reparse/link attributes; none exists. `fsutil hardlink list` exited 0 and returned
one link for each regular file. No Ruff process was running; exclusive read handles
also succeeded. File last-write UTC is 2026-09-05T01:05:59.8436613Z for both.

| Exact relative file | Bytes | SHA-256 before deletion |
|---|---|---|
| .ruff_cache/0.12.11/18381342669712907287 | 300 | a0d73718e1d890feba440e5287142f7881965eac8b2c250f785595b5da52d03a |
| .ruff_cache/0.12.11/454710207606876209 | 373 | e10b63035ae5b6ff4ba8f65dad1494ee7b6b55892ee312a286e7298d790dc221 |

Provenance was checked beyond filenames/CACHEDIR.TAG: installed Ruff reports
0.12.11. Read-only in-memory decoding used its tagged
[PackageCache/FileCache definitions](https://github.com/astral-sh/ruff/blob/0.12.11/crates/ruff/src/cache.rs)
and the [bincode 2 serialization specification](https://docs.rs/crate/bincode/2.0.1/source/docs/spec.md).
Both decoded exactly to EOF as package path + source-file map + file key/last_seen
+ linted/formatted flags, with only existing repository Python source paths.
The first has five entries (one recently seen), the second seven (all recently
seen). Recent entries match the recorded Ruff invocation/file-write interval;
all older entries are inside Ruff's source-defined retention interval. Together
with the earlier recorded cache-generating Ruff runs, this identifies regenerable
Ruff cache artifacts. No binary payload or decoded source contents were emitted.
An initial overstrict diagnostic required every retained entry to have the latest
write time and exited 1; the source documents retention of old entries, so the
completed diagnostic instead checked the actual retention rule and recent-entry
evidence, exiting 0. Neither diagnostic wrote any file or changed scan policy.

After the final focused 229 and specified 277 passes, all preflight checks and
both exact hashes were revalidated. Native PowerShell Remove-Item -LiteralPath
deleted only the two absolute files above, without wildcard/recursion/force,
exit 0. Both paths were absent afterwards. Pre/post SHA-256 snapshots of all 341
tracked/indexed/nonignored untracked working files were identical (zero changes).
No parent directory or other cache/work file was removed. Subsequent Ruff check
and format check with --no-cache both exited 0; neither target was regenerated.
No scanner/baseline/ignore/runtime/test/dependency change was made for cleanup.
The two removed cache artifacts are regenerable by Ruff, not user source data.

## Historical cache-cleanup follow-up: semantic STOP before deletion

The user authorized only two exact cache deletions, unchanged-code QA completion,
and a conditional verification commit/push. Section 6 required reviewing pending
retention / "later fresh attempt" and stopping on any new contract conflict.
That review confirmed **R1-REPLAY-01**, now recorded PROPOSED/BLOCKING in
DECISIONS.md. No runtime fix or retry-policy reinterpretation is made.

### Code and existing-test evidence

- `services/api/src/toss_dashboard_api/reviewer/runtime.py:45–66`:
  `_ClockSample.take/check_sql` floors only the new sample, then rejects either
  `sql_issued != 1` or a raw/SQL expiry disagreement.
- `runtime.py:297–380`: `_Runtime.complete` checks only persisted outcome,
  consumption or bootstrap rows for replay; performs actual crypto; then calls
  `sample.check_sql` outside the verification-error-to-terminalization block.
- `runtime.py:205–220`: `_Runtime._transaction` rolls back that exception. No
  consumption/outcome/authentication/lifecycle or precision-failure marker remains.
- `runtime.py:381–415,621` distinguishes expiry and calls `_terminal` only after
  representability succeeds. A later raw-expired request can produce EXPIRED,
  without accepting its assertion. That is not proof that every resubmission
  must expire.
- `tests/backend/test_reviewer_runtime_time.py:236–288`,
  `test_historical_off_grid_deadline_preservation_and_explicit_conflict`, checks
  one attempt near expiry and complete row preservation. It does not resubmit.
- `tests/backend/test_reviewer_runtime.py:165` checks replay rejection after a
  committed terminal consumption, not after a precision-conflict rollback.

### Non-mutating diagnostic and actual results

Command: `.venv/Scripts/python.exe -B -c <in-memory two-scenario diagnostic>`;
exit **0** means the diagnostic executed, NOT that R1 passed. Python **3.13.15**,
SQLite **3.50.4**. It used `alembic_config` + `command.upgrade(..., frozen 0007)`
against two uniquely named shared-memory SQLite URIs, held open with a keeper
connection. `PRAGMA database_list` confirmed an empty disk filename. No disk DB,
probe source file, persistent row or binary payload was written.

Reproduction sequence uses existing helpers, without editing their files:

1. Instantiate `_Runtime(engine, lambda: OWNER, Clock())` and existing ephemeral
   ES256 `Authenticator`; `enroll` establishes a supported counter of 7.
2. Set the test clock to the historical issuance below. During `issue` only,
   use the same historical `_ClockSample.take` identity seam already used by
   the existing time test. This creates valid historical off-grid rows; it does
   not rewrite a row or alter the code used for either assertion attempt.
3. Issue REVOKE for that active credential. Generate one real signed assertion
   with count 8, save its canonical bytes in memory, and reuse the same response.
4. Call `complete` at the first raw time. Check all WRITE_TABLES equal the prior
   snapshot. Advance the raw clock monotonically to the second time and call
   `complete` again with the same challenge ID and same assertion object.
5. Check canonical assertion bytes are unchanged; inspect exact outcome,
   active-state projection and authorizer counter. No bytes/keys are printed.

All dates below are `2026-09-05` UTC; ordinary expiry is issuance + five minutes.

| Case | Historical issued_at | First raw time / result | Second raw time / same-assertion result | Final effect |
|---|---|---|---|---|
| Issuance comparison conflict | 00:00:01.123900Z | 00:00:01.123901Z / TIMESTAMP_PRECISION_CONFLICT; all rows unchanged | 00:00:01.124000Z / SUCCEEDED | target REVOKED, active count 0, counter 7→8, SUCCEEDED outcome |
| Expiry comparison conflict | 00:00:01.123456Z | 00:05:01.123455Z / TIMESTAMP_PRECISION_CONFLICT; all rows unchanged | 00:05:01.124000Z / CHALLENGE_EXPIRED | active count 1, counter 7, EXPIRED outcome |

Byte-identical assertion reuse was confirmed in **both** cases. The first case
is successful retry before expiry, not merely later expiry terminalization.
This conflicts with original R1 prompt section 12's no-retry requirement. The
second case supports only the narrow expiry observation in the earlier report.
The historical phrase "later fresh attempt" below is retained as prior evidence
but corrected by this addendum: a fresh clock sample is not a fresh assertion.

### STOP scope and unfinished gates

- Cache deletion: **NOT ATTEMPTED in this follow-up**. Both exact files still
  exist at 300 and 373 bytes. Full new deletion preconditions (including Ruff
  provenance, link safety and hashes) were not completed; no deletion approval
  was exercised on incomplete evidence. Previous execution-policy rejection
  remains historical, not a new rejection or successful cleanup.
- No secret/policy/full-suite rerun in this follow-up: stopped at the explicit
  semantic gate before cleanup. Previous full command exit **1** stays exit 1.
  Previous 1064/43/2 results and focused 213/regression 277 remain historical
  local results and do not cover the newly demonstrated successful retry case.
- No runtime, tests, dependencies, frozen migrations, scanner, baseline, ignore
  rule or binary exception changed. The only follow-up file edits are this
  report and the conflict entry in DECISIONS.md. Prior staged work is preserved.
- Commit/push: **NOT PERFORMED**. Local HEAD remains original base
  `87748c8311242e0bd45bac86e8d60da24ac8ba8a`; the read-only remote query returned
  no R1 branch ref, so there is no remote R1 HEAD to compare with a new commit.
- Final read-only checks: both diff checks exit 0; remote query exit 0 with zero
  matching R1 refs; all seven raw migration blobs still match the frozen table
  below; 0008 count 0; production DB still absent. The other 24 changed files
  match their original staged blobs byte-for-byte. The index remains preserved;
  only the two reporting documents have additional unstaged changes.
- NOT VERIFIED: a contract-compliant remedy; new full QA exit 0 and final scans;
  independent review; actual device/browser WebAuthn ceremony; GitHub CI.
  KI-017/KI-018 stay open. No route/frontend/issuer/public/trading work occurs.

## Current conditional authorization and timestamp inventory

The user subsequently authorized the R1-only time policy in DECISIONS.md's
R1-TIME-01 conditional addendum. Implementation now resumes; the STOP and old
164/277 test evidence below remain historical, not fresh full-suite evidence.
Actual local runtime: Python 3.13.15 (MSC v.1944 AMD64), SQLite 3.50.4.

`runtime._ClockSample.take` takes one raw UTC sample and floors microseconds
using integer division/multiplication. Raw time controls expiry (>= is expired),
while its stored floor is passed to row builders before hashes are constructed.
The final sample is after real crypto and ledger/target revalidation inside
BEGIN IMMEDIATE. Terminalization uses no separate per-row clocks.

| Generation point | Affected newly generated fields |
|---|---|
| issue | principal.registered_at, operation.created_at, initial challenge.issued_at |
| authorizer continuation | consumption.consumed_at, authentication.authenticated_at, next challenge.issued_at |
| zero registration | pending.verified_at, child.issued_at |
| terminal projection | 0007 assertion.consumed_at, parent consumption.consumed_at, new authentication.authenticated_at, outcome.completed_at, credential.registered_at, event.occurred_at, authorization.recorded_at |
| derived expiry | ordinary canonical issued_at + 5 minutes; child min(canonical issued_at + 5 minutes, immutable parent expiry) |

No read/rehash/exact copy is floored. The shared canonicalizer, old input/expected
vectors, historical evidence, existing row timestamps and external times are
unchanged. Six-digit fractions remain six digits (.123000Z), not milliseconds
text (.123Z). Raw UTC and SQL julianday predicates are compared read-only before
projection: disagreement raises TIMESTAMP_PRECISION_CONFLICT and rolls back the
transaction. It never changes an expiry, fabricates EXPIRED, adjusts an audit
time or ignores an IntegrityError. Earlier committed authorizer history remains.
New time-only test command:
`.venv/Scripts/python.exe -B -m pytest tests/backend/test_reviewer_runtime_time.py -q --tb=short`
returned **49 passed in 93.90s** on the versions above. This covers raw expiry
-1µs/exact/+1µs for parent/child; both sides of .123500 rounding; exact ordinary
five minutes; parent-cap/positive child duration/no child when expired; crypto
and final-state-check delays crossing expiry; one decision/audit sample and
same-millisecond independent event identities/exact projections; second/day/month/
year/leap-day boundaries; preserved off-grid rows and committed authorizer history.

Concrete historical conflicts (both direct registration and 0007 child):

- Deadline .123456Z, raw deadline minus 1µs: stored .123000Z; SQLite treats stored
  and deadline equally, while raw is still live. Explicit conflict, not EXPIRED.
- Deadline .123900Z, raw deadline or plus 1µs: stored .123000Z; SQLite sees stored
  below deadline, while raw is expired. Explicit conflict, not success or a fake
  adjusted audit record.

Those attempts leave all rows unchanged, including previous VERIFIED authorizer
counter 7→8; the operation remains pending. A later fresh attempt whose actual
clock sample is SQL-representable can follow ordinary expiry terminalization;
there is no scheduled retry, clock adjustment, recovery or bypass in R1.
Compatible historical cases are also exercised, with immutable parent caps copied
exactly. These legacy limits remain explicitly disclosed for independent review.
## Fresh post-remediation verification

All Python invocations use `.venv/Scripts/python.exe -B`. No database URL override
is present; test fixtures upgrade isolated DBs through actual frozen 0001–0007.

| Command / check | Fresh result |
|---|---|
| `-m pytest tests/backend/test_reviewer_runtime_time.py -q --tb=short` | 49 passed in 93.90s |
| `-m pytest tests/backend/test_reviewer_runtime.py tests/backend/test_reviewer_runtime_time.py tests/backend/test_reviewer_webauthn_core.py tests/backend/test_reviewer_windows_owner.py -q --tb=short` | 213 passed in 279.77s; all 10 unchanged golden vectors and actual local Windows checks passed |
| `-m ruff check services/api/src/toss_dashboard_api/reviewer tests/backend/test_reviewer_runtime_time.py` | PASS |
| `-m mypy services/api/src` | PASS, 67 source files |
| `-m pytest tests/backend --collect-only -q` | 1064 collected |
| `pwsh -NoProfile -File scripts/policy-scan.ps1` | PASS |
| `git diff --check`; `git diff --cached --check`; raw working/index blob equality | PASS, 26 changed files |
| Specified six-file regression | 277 passed in 582.93s |
| `pwsh -NoProfile -File scripts/test.ps1` | Exit 1 at final secret scan; detailed completed checks and exact blocker below |
| Full backend in that standard run | **1064 passed in 1215.84s** |
| Frontend / E2E in that standard run | **43 passed / 2 passed** |
| Standard lint / format / both typechecks | PASS; 117 formatted files, 67 backend source files |
| Migration repeat / downgrade / re-upgrade | PASS, disposable frozen-0007 database |
| Fixture idempotency | PASS; first insert 13, repeat insert 0 / unchanged 13 |
| OpenAPI / production builds | PASS |
| Dependency / offline guards / cleanup canary / offline preflight | PASS; canary 20 iterations; external requests and credentials used 0 |

### Final QA artifact blocker (not a runtime test failure)

`scripts/secret-scan.ps1:922` rejected this non-UTF-8 Ruff binary cache input:
`.ruff_cache/0.12.11/18381342669712907287` (300 bytes).
The same cache directory contains `454710207606876209` (373 bytes).
Both are generated cache binaries, with the standard CACHEDIR.TAG signature
`8a477f597d28d172789f06886806bc55`, excluded by Git's `.ruff_cache/` rule.
Direct local Ruff invocations created/updated them; the repository standard
lint script already uses `--no-cache`. No source, test or frozen evidence is
in these two files. The full run passed every preceding gate, including E2E,
but its secret scan did **not** pass; the final policy step was not reached.

A narrowly targeted removal of only those two regenerable files was rejected
by the execution policy before execution. **No cache file was removed.** No
scanner exclusion, baseline change, binary-format exception or alternate deletion
path was introduced. Explicit user direction for cache cleanup is needed before
the security gate/full QA closeout can be completed. No commit or push occurred.
Do not mark R1 IMPLEMENTED/AWAITING REVIEW, PASS or CLOSED while this gate remains.

Regression command: `-m pytest tests/backend/test_reviewer_operation_migration.py tests/backend/test_counter_capability_migration.py tests/backend/test_authority_migration.py tests/backend/test_authority_repository.py tests/backend/test_authority_decision_engine.py tests/backend/test_migrations.py -q --tb=short`.

The time-test addition did not alter any original R1 test assertion/input. Initial
new-code formatting findings were corrected with the existing formatter; subsequent
lint/typecheck passed. Full QA closeout and independent review remain outstanding.
The 49 new time cases comprise 11 pure flooring/canonical-preservation cases and
38 actual disposable frozen-0007 DB cases. The 213 focused and 277 regression
cases are subsets of the 1064 backend cases, not additional unique test counts.

## Historical STOP: exact expiry is not representable for all approved UTC values

`R1-TIME-01` is recorded as PROPOSED/BLOCKING in `DECISIONS.md`. This was found
during additional boundary review after the main focused/regression tests passed.
At that STOP the runtime took full-microsecond server UTC timestamps. No alternative
precision/rounding policy had been silently substituted.

Exact disposable reproduction:

```text
parent expires_at:       2026-09-05T00:05:00.123456Z
candidate issued_at:     2026-09-05T00:05:00.123455Z
approved child duration: 1 microsecond (> 0)
Python issued < parent:  true
SQLite julianday(issued) < julianday(parent): false
SQLite julianday(expiry) > julianday(issued): false
runtime_result: REVIEWER_TRANSACTION_FAILED
frozen_guard: counter capability registration exact live parent mismatch
pending / child / consumption / outcome / credential rows: 0 / 0 / 0 / 0 / 0
```

The reproduction upgraded only an isolated disposable DB to frozen 0007, issued
FIRST_ENROLLMENT at `00:00:00.123456Z`, and performed actual zero-counter
registration verification one microsecond before parent expiry. Frozen 0007's
live-parent guard (`julianday(NEW.verified_at) < julianday(challenge.expires_at)`)
rejects this case. Its child-positive-duration guard also rejects those equal
SQLite time values. Frozen 0006's consumption guard similarly bases EXPIRED on
`julianday()`, which disagrees with the approved exact timestamp ordering here.

Choosing a server precision grid/quantization or an alternate early-expiry rule
would add a time interpretation not explicitly approved. No such change was made.
Per the user's absolute STOP condition, the full standard QA run was deliberately
stopped during backend execution after its 21% progress marker. This is not a full
suite PASS, nor a hidden test failure. Partial implementation is retained locally;
no commit, push, merge, frozen migration change, or 0008 was performed.

## Authority and preserved boundaries

The user expressly authorized R1 backend implementation from the starting SHA,
then approved two exact clarifications: only counter-capability continuation
challenges use `min(issued_at + 5 minutes, parent.expires_at)`; management target
credential IDs are untrusted selection intent, never authentication authority.
The server derives principal/SID/state/fingerprint bindings and active authorizers
from the ledger. Target and authorizer may differ. Target/state/bindings are
rechecked after verification and immediately before terminal projection.

ADR-015/016/017/018/019 remain ACCEPTED. ADR-019 proposal date is 2026-08-29,
decision date 2026-08-31; the historical B1 Windows Hello wording is preserved.
Only authenticator-vendor provenance was amended. 0006 remains PASS — CLOSED;
0007 is PASS — CLOSED under the user closeout dated 2026-09-05, recorded in
`PHASE_02_CP3_C2_B2_C_0007_ACCEPTANCE_CLOSEOUT_GPT_REPORT.md`.

Routes/browser ceremonies/real WebAuthn integration and issuer human approval /
canonical promotion remain NOT STARTED and require separate authorization.
Public Read-only Deployment and Automated Trading remain FUTURE / NOT AUTHORIZED /
NOT STARTED. Automatic progression remains PROHIBITED. Flags remain
`LOCAL_ONLY=true`, `TRADING_ENABLED=false`, `DRY_RUN=true`.

## Implementation and pre-implementation audit

The frozen 0005/0006/0007 schemas and representative transaction tests were
inspected before implementation. The earlier expiry and target-selection gaps
were resolved by the user's explicit clarifications, not by changing migrations.
Existing frozen-schema probes passed: 4 expiry/blob tests and 13 representative
terminal/counter/final-revoke tests. No new schema or SQL SHA authority was added.

The exact approved library sources were audited:
[registration verifier](https://github.com/duo-labs/py_webauthn/blob/v3.0.0/webauthn/registration/verify_registration_response.py),
[assertion verifier](https://github.com/duo-labs/py_webauthn/blob/v3.0.0/webauthn/authentication/verify_authentication_response.py),
[authenticator-data parser](https://github.com/duo-labs/py_webauthn/blob/v3.0.0/webauthn/helpers/parse_authenticator_data.py).
The parser re-encodes COSE: the wrapper therefore validates original bytes before
calling the library and compares returned material. Restricted ES256/P-256 and
RS256/RSA >=2048-bit maps reject extra/duplicate labels, floats, tags, indefinite
or noncanonical encodings. Generic cbor2 canonical mode is not treated as a
general CTAP2 encoder. Attestation `none` is not vendor provenance or attestation
signature proof; the approved verifier and exact registration consistency policy
are applied. Assertion signature verification is real, not a Boolean fixture.

The library's counter baseline is zero for signature verification; the actual
ledger counter is then enforced by trusted code. This permits a cryptographically
valid rollback signature to produce a rejected audit instead of being mistaken
for a signature failure. Supported counters strictly advance from the unique
three-ledger leaf. NO_USABLE_COUNTER management rows retain NULL/NULL.

Canonicalization implements NFC, duplicate-after-NFC rejection, recursive UTF-8
key ordering, compact JSON, explicit nulls/Booleans/integers, strict UTC and
canonical base64url. All ten accepted ADR-017 vector byte/hash results passed.
Issuer hash helpers are pure only; no issuer approval runtime was added.

Every writer enables foreign keys and uses BEGIN IMMEDIATE. Reads reconstruct
credential/lifecycle/authorization and operation graphs and reject corruption.
Projection ordering follows frozen triggers; planned and transaction-visible
credential states are compared before inserting the deferred terminal outcome.
FIRST retries retain the principal after failed pre-registration attempts. Final
revoke can produce an empty active set but cannot reopen FIRST or create recovery.

The production factory accepts only the canonical installed-module-root
`var/dashboard.db`. Its real Windows check verifies opened directory identity,
reparse status, local persistent-ACL volume, OWNER SID and independent TOKEN_USER
equality before deriving the SID hash. No raw SID is returned or logged. No
production skip-owner, caller-SID or test-DB switch exists; isolated tests use the
private lower-level transaction service against disposable frozen-0007 databases.

## Changed files

- Control plane: `DECISIONS.md`, `KNOWN_ISSUES.md`, `STATUS.md`, `CHANGELOG.md`;
  `plans/PHASE_02_EXECUTION_PLAN.md`,
  `plans/PHASE_02_CP3_C2_B1_RUNTIME_CONTRACT.md`,
  `plans/PHASE_02_CP3_C2_B2_C_SCHEMA_REMEDIATION.md`,
  `plans/PHASE_02_CP3_C2_B2_C_ADR_018_COUNTER_CAPABILITY_SCHEMA_PROPOSAL.md`;
  this report.
- Runtime: `services/api/src/toss_dashboard_api/reviewer/` containing
  `__init__.py`, `canonical.py`, `webauthn_core.py`, `windows_owner.py`,
  `schema.py`, `ledger.py`, `runtime.py`.
- Tests: `tests/backend/reviewer_test_support.py`,
  `test_reviewer_webauthn_core.py`, `test_reviewer_windows_owner.py`,
  `test_reviewer_runtime.py`, `test_reviewer_runtime_time.py`,
  `test_reviewer_time_profile.py` in the same directory.
- Dependencies: `requirements.in`, `requirements.lock`, `pyproject.toml`.
- Exact inventory/policy synchronization: `scripts/test.ps1`,
  `scripts/policy-scan.ps1`. No existing test was removed, skipped or weakened.
- Newly authorized exact generated-artifact remediation: `scripts/secret-scan.ps1`;
  necessary changed-control digest synchronization only in `scripts/policy-scan.ps1`.
  The four diagnostic CSVs above remain local-only and outside this commit list.

## Dependency and policy evidence

Added exact direct dependencies: `webauthn==3.0.0`, `cbor2==6.1.4`.
Necessary new locked transitives: `cffi==2.1.1`, `cryptography==50.0.1`,
`pyasn1==0.6.4`, `pyasn1-modules==0.4.2`, `pycparser==3.0`, `pyopenssl==26.4.0`.
No previous direct or transitive version changed. Standard hashed pip-compile
workflow regenerated the lock; hash-required installation succeeded.
An initial isolated pip-tools/pip incompatibility was corrected only in the
temporary lock-generation environment (pip 25.2 / pip-tools 7.5.0 / click 8.2.1).
Those build tools were not added to project dependencies.

The policy gate retains exact lock/config/source-inventory hashes. The required
Win32 owner adapter is the sole native-API exception, pinned by both full path
and exact file SHA-256; its edits/copies are not generically exempt. Every other
runtime policy scan and the native/process/network negative canaries remain.
The prior time-policy run's approved backend inventory was 1064 (851 existing +
164 original R1 tests + 49 time-policy tests), with 84 phase control files.
That approved execution-profile remediation added 16 tests: its exact inventory
was 1080 and its phase control manifest had 85 files, with pre-scanner-remediation digest
d432dfe5a0a17e0db1d5e8fbb22c0c089c8c8e97ae279594f0bc191592eb46e4.
This preserved prior digest/inventory is not a result for the newly changed
scanner snapshot; the exact new digest and gate results must be recorded after
implementation. Existing runtime/test/dependency inventories remain frozen.

## Frozen migration evidence

No migration is edited or created; no 0008 exists. Required Git blobs:

| Revision | Blob |
|---|---|
| 0001 | `d00355c2456021e6ffb195e50833adc32c74a4ad` |
| 0002 | `53f40664eca2ea2466cc6154b8579c5db506e0ba` |
| 0003 | `47d5a69009949b155211cd68209640136a7cacd9` |
| 0004 | `91b4d96a445be23e7aa55e08b9310dc7334a026d` |
| 0005 | `81976b8f70a1f6107526a13acadf23f369b196e3` |
| 0006 | `f10e7f5bc21e232fc68b38144f5b8fb124f31698` |
| 0007 | `a83385f8ff50f4e8a54e673c6d8a3c015eb0b053` |

## Historical pre-remediation verification (not a new full QA result)

| Check | Observed result |
|---|---|
| Focused crypto/canonicalization/Windows tests | 90 passed; includes all 10 golden vectors and real ES256/RS256 signature negatives |
| Focused runtime | 60 passed, then 14 additional graph/race/rollback/security tests passed |
| FIRST / ADD / REPLACE | positive registration, 0007 0→positive, 0→0, rejection/expiry and frozen projection tested |
| REVOKE | exact target, same/different active authorizer, unrelated credential retained, final empty set/re-enrollment refusal tested |
| Challenge lifecycle | 32 bytes, uniqueness, ordinary exact five minutes, child parent cap, no expired-parent child, completion-time expiry, consumption and replay refusal tested |
| Counter/state integrity | supported advancement, equality/rollback, three-ledger unit graph, fork/duplicate/disconnected rejection; disposable corrupt-ledger rejection |
| Windows | real directory owner/TOKEN_USER check and canonical SID hash; controlled mismatch/reparse/remote/ACL negatives; non-Windows and arbitrary DB rejection |
| Existing six-file migration/authority regression suite | 277 passed in 585.91s |
| Standard lint / typecheck | PASS; 116 formatted files, backend 67 source files, frontend type generation/typecheck |
| Policy scan | PASS after exact authorized inventory/hash synchronization |
| Full standard test/build/E2E/migration/idempotency/secret gate | INCOMPLETE — deliberately interrupted at the explicit STOP gate; remaining frontend/build/E2E/secret steps were not reached |
| Staged diff / frozen blob checks | Pre-STOP staged diff check passed; all 7 working-file raw Git blobs match; no 0008; final successful implementation snapshot does not exist |

Initial local checks found and corrected a test-helper argument collision, strict
type/format findings, and stale policy hashes. No failure was hidden or bypassed.
The three-ledger model test injects a unit-level issuer edge; frozen migration
tests separately exercise persisted union constraints. It does not execute issuer
approval runtime. Full QA completion and final reviewed snapshot are blocked by
R1-TIME-01. The interrupted standard run had already passed policy, pip check,
offline guards, lint, both typechecks, 20-iteration process-cleanup canary, offline
Toss preflight/self-test and exact 1015/43/2 test collection. Its backend execution
did not finish. No frontend test/build/E2E/secret PASS is claimed for this R1 run.

## Safety counts and remaining review

Safety counts below concern R1 production/authority execution, not the pre-existing
synthetic fixture imports into disposable QA databases.
Persistent production DB mutation/migration: 0; `var/dashboard.db` is absent in
this workspace (checked before standard QA and at STOP). Real steward enrollment: 0.
Real credential registrations: 0. Real WebAuthn/Windows Hello prompts: 0.
HTTP routes added: 0. Frontend WebAuthn additions: 0. Issuer human approval
executions: 0. Canonical Issuer/link/Security/VERIFIED mapping writes: 0.
No live provider/brokerage/OpenAI call was made. Test keys/challenges/signatures
are transient; tests check that raw challenge, returned handle, signature,
private key and raw SID do not enter reviewer rows or logs. No real ceremony
payload or screenshot is produced by this backend-only checkpoint.

KI-017 source redistribution/publication eligibility remains OPEN/NONBLOCKING
for a future public checkpoint. KI-018 GitHub CI execution evidence remains
absent, OPEN/NONBLOCKING; local QA is not GitHub CI. Real browser/device ceremony
behavior is NOT VERIFIED and outside R1 authority. GPT independent review and
user closeout are not claimed. No next checkpoint starts automatically.
