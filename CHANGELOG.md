# Changelog

## Unreleased — Phase 2 CP3-C2-B2-A Authority Ledger Foundation — 2026-08-27

### Added

- approved ADR-013/ADR-014에 맞춘 versioned `AuthoritySourcePolicy`, raw
  `AuthorityEvidence`, retrieval observation/relation, candidate-specific
  `AuthorityEvidenceApplication`, exact application-member `AuthorityBundle`,
  identifier claim과 machine-only `IssuerDecision` contract를 추가했다.
- canonical UTF-8/NFC JSON과 SHA-256 semantic IDs는 retrieval/evaluation/record
  time, DB/run/request ID, clock와 member input order를 제외한다.
- additive `0005_phase_02_cp3_c2_b_issuer_authority`에 approved 21-table
  authority/authentication/approval/link family, 68 inline CHECK, 14 named
  index와 40 append-only UPDATE/DELETE trigger를 추가했다.
- deterministic immutable row를 same-ID/same-content이면 idempotent success,
  same-ID/different-content이면 typed conflict로 처리하는 low-level SQLite
  ledger repository를 추가했다.

### Safety and compatibility

- source-policy exact scope/role/weight matrix와 server-owned production policy
  registry boundary를 두고 unlisted scope, fixture/test namespace, copied or
  relabelled tainted lineage와 historical synthetic corp_code/CIK를 production
  bundle에서 fail closed한다.
- corp_code/CIK claim lookup은 non-unique로 유지해 contradictory claims를 모두
  보존하고 insertion-order winner나 canonical issuer를 만들지 않는다.
- `0001`~`0004` SHA-256과 기존 provider/issuer/security/source/history row를
  보존하며 기존 `MappingStatus = VERIFIED | UNRESOLVED`와 Phase 1 public
  database revision contract를 변경하지 않는다.
- reviewer/WebAuthn/challenge/approval/link table은 later-phase schema
  foundation뿐이다. WebAuthn verification, human approval execution, canonical
  Issuer/Security write, VERIFIED mapping, provider rekey와 live authority
  request는 모두 0이다.

### QA and status

- B2-A targeted offline tests `54`, full backend inventory `598`, frontend
  inventory `43`, E2E inventory `2`를 고정했다. Final staged full regression과
  migration/fixture/build/secret/policy 결과는
  `qa/PHASE_02_CP3_C2_B2_A_CODEX_REPORT.md`에 기록한다.
- `scripts/test.ps1`의 exact backend inventory와
  `scripts/policy-scan.ps1`의 exact test allowlist/control-manifest count/digest만
  새 authorized files에 맞춰 갱신했다. scanner 조건이나 network guard는
  완화하지 않았다.
- CP3-C2-B implementation은 `IN PROGRESS`, B2-A는
  `IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW`다. B2-B/B2-C/B2-D,
  CP3-C2-C와 CP3-D는 `NOT STARTED`, automatic progression은 `PROHIBITED`다.

## Unreleased — Phase 2 CP3-C1 Independent-Review P1 Remediation — 2026-08-26

### Fixed

- current identifier를 source chronology와 identifier history의 의미 상태로 해석한다. closed history는 current에서 제외하고, symbol-change observation은 provider가 제공하지 않은 변경일을 만들지 않은 채 새 open symbol을 current로 만든다. 둘 이상의 상충 current 값은 history ID/hash 순서로 winner를 고르지 않고 collision quarantine으로 fail closed한다.
- 한 STOCK_DETAIL source의 전체 response를 publish 전에 분석해 duplicate non-null ISIN을 검출한다. 모든 affected observation을 처음부터 `QUARANTINED`/`UNRESOLVED_COLLISION`으로 기록하며 기존 identity는 source-consistent하게 함께 격리하고 신규 충돌 후보에는 identity를 할당하지 않는다.
- C-M04/IR-F의 두 affected observation 검증을 강화하고 three-step rename, current lookup, discovery/detail missing, ambiguous current, new-candidate duplicate ISIN, response-order independence 회귀를 추가했다.

### QA and Scope

- GPT independent review 결과 `CHANGES REQUIRED`, P0 0/P1 2를 전사한 QA record와 Codex fix self-report를 분리해 추가했다.
- Backend exact inventory는 `540 → 544`; frontend `43`, E2E `2`를 유지한다. migration은 0이며 `0001`~`0004`는 byte-identical이다.
- actual credential, actual Toss API request, external provider network와 canonical auto-promotion은 각각 0이다.
- 상태는 CP3-B `PASS — CLOSED`, CP3-C1 `REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW`, CP3-C2 `NOT STARTED — USER DECISION REQUIRED`, CP3-D `NOT STARTED`; automatic progression은 `PROHIBITED`다.

## Unreleased — Phase 2 CP3-C1 Security Master Staging & Reconciliation — 2026-08-26

### Added

- `/api/v1/stocks/all`과 `/api/v1/stocks` 응답을 위한 `toss-security-master/0.1.0` strict DTO, checksum-valid nullable ISIN, canonical Decimal 문자열과 비식별 KR/US offline fixture를 추가했다.
- 같은 provider/market의 active symbol, unique ISIN, symbol+listDate, lifecycle/source lineage를 anchor 할당보다 먼저 평가하는 continuity-first reconciliation을 구현했다. 이름은 증거로 사용하지 않는다.
- valid ISIN → symbol+listDate → symbol+first-seen raw hash 우선순위의 immutable provider identity, append-only symbol/ISIN/listDate/market history, enrichment no-rekey와 symbol-change continuity를 구현했다.
- 다중·모순 evidence, duplicate ISIN, identifier/share-class/listing-market change를 auto merge/new identity/arbitrary winner 없이 `UNRESOLVED_COLLISION`/`QUARANTINED`로 fail closed한다.
- discovery disappearance의 `DISCOVERY_MISSING`-only 처리, inactive/delisted observation, exact partial/empty detail batch audit와 `(fetched_at, source_version_id)` clean-DB deterministic replay를 구현했다.
- semantic normalized record, source-linked staging/lifecycle observation, identity-state event와 detail-batch result를 위한 additive `0004_phase_02_cp3_c1_security_master` 네 table을 추가했다.

### QA and Scope

- C-M01~C-M09, C-U01~C-U08와 IR-D~IR-G를 포함한 offline 회귀를 추가하고 backend exact inventory를 509에서 540으로 올렸다. frontend 43와 E2E 2 exact gate는 유지한다.
- 기존 `0001`, `0002`, `0003` bytes와 Phase 1 public API/OpenAPI/fixture를 보존하고 0004 mid-DDL cleanup/retry를 검증한다.
- actual credential, actual Toss request와 external provider network는 각각 0이다. canonical Issuer/Security promotion, price/CP3-D, live collection, frontend와 scheduler는 구현하지 않았다.
- 상태는 CP3-B `PASS — CLOSED`, CP3-C1 `IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW`, CP3-C2 `NOT STARTED — USER DECISION REQUIRED`, CP3-D `NOT STARTED`이며 automatic progression은 `PROHIBITED`다.

## Unreleased — Phase 2 CP3-B Controlled Rollback + Minimal P1 Reapply — 2026-08-26

### Fixed

- canonical request별 source history를 하나의 ORIGINAL root와 하나의 current leaf를 갖는 linear chain으로 검증한다. 후속 version은 exact leaf만 supersede할 수 있고 second root, non-leaf supersession, fork, cycle과 cross-request link를 fail closed한다.
- additive `0003_phase_02_cp3_b_invariants`에 ORIGINAL root, non-null supersedes child와 open-ended VERIFIED mapping을 위한 SQLite partial unique index를 추가한다. migration은 invalid pre-existing history/overlap을 rewrite 없이 거부하고 `0001`/`0002`를 수정하지 않는다.
- VERIFIED mapping의 nullable validity boundary를 unbounded interval로, 양 끝을 inclusive로 해석해 같은 provider identity의 bounded/open-ended overlap을 repository에서 차단한다. 기존 mapping을 자동 종료·변경하지 않는다.
- source revision과 current VERIFIED promotion의 independent-session race에서 exactly one writer만 성공하고 loser는 raw SQLite exception 대신 safe typed conflict를 받는다.

### QA and Scope

- backend exact inventory gate를 493에서 509로 올렸다. source chain/root/fork/order/preservation, mapping overlap/history/concurrent promotion과 0003 upgrade/downgrade/re-upgrade/invalid-data tests를 추가했다.
- frontend 43, E2E 2 exact gate와 policy missing/lookalike canary, exact control-plane count 70 및 digest enforcement를 유지한다.
- CP2와 approved CP3-A contract, `0001`, `0002`, connector/runtime, frontend, public API/OpenAPI와 dependency는 변경하지 않았다.
- actual credential 사용과 actual Toss API request는 0이며 CP3-C는 `NOT STARTED`다.
- `a33cf6e0ff74bf7db1a373061f90785a92709696` 기준으로 기존 작업을 stash에 보존한 뒤 P1 직접 관련 변경만 선택 재구성했다.
- `scripts/secret-scan.ps1`과 `scripts/secret_scan_driver.py`는 baseline 그대로이며 audit transport ZIP은 repository에 포함하지 않는다.
- CP3-B 상태는 `IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW`; automatic progression은 `PROHIBITED`다.

## Unreleased — Phase 2 CP3-B Independent-Review Hardening — 2026-08-25

### Fixed

- same request/status/raw hash/provider contract의 later fetch에서 `fetched_at`·safe telemetry 차이를 semantic duplicate로 처리하고 first-seen raw/source manifest를 보존한다. dataset/parser/normalized hash/revision/supersedes 차이는 conflict다.
- `/stocks/all → STOCK_DISCOVERY`, `/stocks → STOCK_DETAIL`, `/prices → CURRENT_PRICE` exact mapping과 request→raw→source→attempt/audit graph를 repository에서 강제한다. `DAILY_FLOW` persistence는 승인 endpoint가 없어 금지한다.
- VERIFIED mapping은 ACTIVE identity, 실제 issuer/security 관계와 identity first/latest 또는 identifier-history source evidence를 요구한다.
- provider latest update를 DB-level one-statement conditional SQL update로 변경하고 two-session winner 1/typed loser conflict, first-insert race와 complete-row 보존을 검증한다.
- CURRENT_PRICE freshness는 CP3-D2 전 항상 `UNKNOWN`이며 timestamp-null source는 보존 가능하지만 latest pointer에는 사용할 수 없다.
- `0002` 후반 DDL sentinel failure 시 earlier CP3 tables를 제거하고 0001 revision/Phase 1 rows/pre-existing sentinel을 보존한다.
- raw final publish를 overwrite 가능한 rename에서 atomic no-replace로 변경해 competing same bytes는 dedupe, different bytes는 conflict로 처리한다.

### QA and Status

- backend exact inventory gate를 448에서 493으로 올리고 later-fetch/trace/mapping/two-session CAS/mid-migration/no-replace negative tests를 추가했다.
- test file exact allowlist, control-plane count 70과 digest gate, missing/lookalike canary와 모든 보안 gate를 유지했다.
- actual credential 사용과 actual Toss API request는 0이며 LIVE_VERIFIED 범위는 확대하지 않았다.
- CP3-B: `REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW`; CP3-C: `NOT STARTED`; automatic progression: `PROHIBITED`.
- final staged full regression의 exact 결과와 exit code는 `qa/PHASE_02_CP3_B_FIX_CODEX_REPORT.md`에 기록한다.

## Unreleased — Phase 2 CP3-B Provider Source Trace Foundation — 2026-08-25

### Added

- 독립 `toss-source/0.1.0` provider source contract와 `toss-identity/0.1.0` identity foundation contract
- deterministic secret-free canonical request, allowlisted raw manifest metadata와 exact-byte SHA-256 contract
- injected base directory, hash-addressed opaque ref, reparse/symlink/hard-link 방어, flush/fsync와 atomic rename을 사용하는 append-only raw store
- canonical request/raw/source revision/attempt/audit/identity/history/mapping/latest pointer용 additive 9-table `0002_phase_02_cp3_foundation`
- insert-or-verify conflict detection, source+audit atomic transaction, append-only identity metadata와 compare-and-set latest pointer SQLite repository
- contract/canonical request/raw store/revision/repository/migration/security 회귀 tests; backend exact inventory 357 → 448

### Compatibility and Security

- Phase 1 global `ContractVersion = Literal["0.1.0"]`, SourceRecord/Issuer/Security, fixture row/ID/hash/payload, public API/OpenAPI와 `0001` bytes 보존
- auth endpoint body, credential/token/header/account metadata, absolute raw path와 unrestricted response header 저장 surface 0
- actual credential 사용과 actual Toss API request 0; standard suite는 offline 경계를 유지
- account/order/WebSocket, connector auth/client/rate/preflight, frontend, config, dependency와 live script 변경 0

### Scope and Status

- endpoint DTO/normalizer, collection job, Security Master continuity reconciliation와 Current Price/ProviderPriceSnapshot 구현은 포함하지 않음
- ADR-010/011/012는 `ACCEPTED`, CP3-A는 `PASS — CONTRACT APPROVED AND CLOSED`
- CP3-B는 `IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW`; `PASS`, `APPROVED`, `COMPLETE`가 아님
- CP3-C는 `NOT STARTED`, automatic checkpoint progression은 `PROHIBITED`
- `/stocks/all`, `/prices`, provider enum/null/lifecycle, price timestamp-null/currency/freshness와 actual 429/5xx timing은 계속 `[LIVE_UNVERIFIED]`

### QA

- target contract/raw/repository/migration regression 100개 PASS, 전체 backend inventory 448개로 증가
- final staged full regression의 exact 결과와 exit code는 동일 commit의 `qa/PHASE_02_CP3_B_CODEX_REPORT.md`에 기록

## Unreleased — Phase 2 CP3-A Approval and Final Closeout — 2026-08-25

### Approved

- 사용자 명시적 결정으로 ADR-011 `date-only Toss 관측을 versioned source contract로 분리`를 `ACCEPTED`로 전환
- 사용자 명시적 결정으로 revised ADR-012 `Toss provider security identity와 canonical issuer/security mapping 분리`를 `ACCEPTED`로 전환
- GPT independent re-review `PASS WITH CLOSEOUT CONDITION`, P0 0/P1 0과 P1-01/P1-02 `CLOSED` 결과를 `qa/PHASE_02_CP3_A_INDEPENDENT_QA.md`에 별도 보존
- CP3-A planning/contract를 `PASS — CONTRACT APPROVED AND CLOSED`로 closeout; CP3-B는 `NOT STARTED`, automatic progression은 `PROHIBITED`

### QA Closeout

- P2 `final post-report-edit regression evidence gap`은 두 QA 보고서를 포함한 final 9-file staged documentation set을 먼저 완성·stage한 뒤 전체 `scripts/test.ps1`을 실행해 해소
- final staged set 기준 exit 0: backend inventory 357 및 357/357, frontend inventory 43 및 43/43, E2E inventory 2 및 2/2 PASS
- migration repeat/downgrade/re-upgrade, fixture second import `inserted=0`/`updated=0`/`unchanged=13`, OpenAPI, production build 2회, secret scan, initial/final policy scan PASS
- actual Toss credential usage 0, actual Toss API requests 0, offline default/SelfTest external request 0

### Scope and Limitations

- application/test/fixture/migration/dependency/runtime config/API route/connector/CP3-B implementation 변경 0
- test 삭제, skip/xfail, inventory 감소, assertion 완화, exception/scanner/network guard 우회 0
- `/stocks/all`, `/prices`, complete enum/null/lifecycle, price timestamp-null/currency/freshness, natural 429와 actual 429/5xx production timing은 계속 `[LIVE_UNVERIFIED]`
- PR/main merge/tag/release 0

## Unreleased — Phase 2 CP3-A Independent Review Fix — 2026-08-25

### Changed

- independent review `CHANGES REQUIRED`의 P1-01을 반영해 valid provider identity 기준 `ProviderPriceSnapshot`/latest storage와 verified-only canonical current-price view를 분리했다. nullable `security_id` linkage 때문에 Phase 2 provider-scoped 목표가 Phase 3 OpenDART/Phase 4 SEC regulatory mapping에 순환 의존하지 않는다.
- P1-02를 반영해 신규 anchor allocation 전에 active identity/history continuity를 검색하고, 단일 후보 재사용, identifier enrichment, collision quarantine, evidence 0일 때만 최초 anchor 선택, 후속 rekey 금지와 deterministic replay 규칙을 추가했다.
- provider price without canonical mapping, verified mapping promotion, fake regulatory ID prevention, ISIN/listDate enrichment, enrichment collision과 deterministic rebuild를 P0 문서 acceptance로 추가했다.
- ADR-011은 `PROPOSED — INDEPENDENT REVIEW P1-NOT-BLOCKING / AWAITING USER APPROVAL`, ADR-012는 `PROPOSED — REVISED AFTER INDEPENDENT REVIEW / AWAITING RE-REVIEW`로 유지했다. Codex가 어느 ADR도 새로 승인하지 않았다.
- 상태를 `CP3-A REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW / CP3-B NOT STARTED`로 갱신하고 자동 checkpoint 진행을 금지했다.

### Security and Scope

- documentation/contract-only 보완이며 application/test/fixture/migration/dependency/runtime config/API route/connector 변경 0
- actual credential 사용 0, actual Toss API 호출 0, account/order/WebSocket 변경 0
- CP3-B implementation, PR/main merge/tag/release 0

### Review

- independent review result: P0 0 / P1 2 / CP3-B not authorized
- 이 보완은 두 P1의 재검토를 요청하며 CP3-A 승인 또는 다음 checkpoint 승인을 선언하지 않는다.
- staged eight-file documentation set의 첫 full `scripts/test.ps1`은 exit 0이었다: backend 357/357, frontend 43/43, E2E 2/2, migration repeat/downgrade/re-upgrade, fixture second import `inserted=0`/`updated=0`/`unchanged=13`, OpenAPI, production build 2회, secret scan과 initial/final policy scan PASS.

## Unreleased — Phase 2 CP3-A Contract Checkpoint — 2026-08-24

### Added

- `plans/PHASE_02_CP3_A_CONTRACT.md`에 Security Master와 Current Price의 endpoint 역할, KR/US universe, provider staging identity, lifecycle, PriceSnapshot, source trace, hash/idempotency/revision, additive migration과 CP3-B/C/D acceptance 계약 추가
- ADR-012 `Toss provider security identity와 canonical issuer/security mapping 분리`를 `PROPOSED — AWAITING INDEPENDENT REVIEW`로 추가

### Changed

- Phase 2 실행계획을 현재 `CP1 PASS / CP2 COMPLETE / CP3-A IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW / CP3-B NOT STARTED` 상태로 정합화하면서 CP1 당시 조사 baseline과 현재 live verification matrix를 분리
- ADR-011을 `/prices timestamp=null`까지 표현하는 nullable observed time/date와 structured missing reason 계약으로 수정하되 `PROPOSED — REVISED FOR CP3-A / AWAITING INDEPENDENT REVIEW` 유지
- actual OAuth/stocks/success rate header만 `[LIVE_VERIFIED]`, `/stocks/all`, `/prices`, natural 429/5xx와 CP3 semantics/freshness는 `[LIVE_UNVERIFIED]`로 유지
- issuer identity, timestamp-null source semantics와 기존 source-record natural-key/revision 충돌을 Known Issues에 추가·갱신

### Security

- CP3-A는 문서·계약 checkpoint로 application/test/fixture/migration/dependency/runtime config/API route/connector 변경 0
- actual credential 조회·사용 0, actual Toss API 호출 0, account/order/WebSocket 변경 0, secret artifact 0
- CP3-B/C/D application implementation, PR/main merge/tag/release를 수행하지 않음

### QA

- current environment: PowerShell 7.6.4(최소 7.4.0 이상, previous final QA reference 7.6.5와의 accepted variance), Python 3.13.15, Node 24.19.0, npm 11.17.0, ASCII-only path
- 최종 staged documentation 기준 `scripts/test.ps1` exit code 0: backend 357/357, frontend 43/43, E2E 2/2, migration repeat/downgrade/re-upgrade, fixture 2차 import `inserted=0`/`updated=0`/`unchanged=13`, OpenAPI check, production build 2회, secret scan, initial/final policy scan PASS
- Toss preflight default와 SelfTest는 각각 external network requests 0이었고 default credential usage도 0
- 실패 이력 1: 첫 full run은 pre-existing orphaned workspace dev listeners가 3000/8000을 점유해 E2E 시작에서 exit 1이었다. 동일 repository command line을 확인한 exact process tree만 종료하고 포트 availability를 검증했다.
- 실패 이력 2: 두 번째 full run은 E2E 2/2 뒤 unstaged documentation 때문에 secret scan의 index/working-tree equality gate에서 exit 1이었다. scanner 예외를 추가하지 않고 허용 문서 7개만 stage한 뒤 전체 suite를 처음부터 재실행했다.

### Limitations

- CP3-A는 `PASS`, `APPROVED` 또는 `COMPLETE`가 아니다. ADR-011/ADR-012와 exact provider enum/identity/migration 결정은 GPT independent review와 사용자 승인을 기다린다.
- CP3-B는 `NOT STARTED`이며 자동으로 진행하지 않는다.

## Unreleased — Phase 2 CP2 Final Closeout — 2026-08-24

### Changed

- CP2-A~D final integrated QA를 완료하고 상태를 `CP2 COMPLETE / Phase 2 IMPLEMENTATION IN PROGRESS / CP3 NOT STARTED`로 갱신
- ADR-010을 `ACCEPTED`로 전환하고 exact REST allowlist, memory-only token, bounded retry, offline/live 분리 결정을 확정
- actual live 검증과 미검증 범위를 분리해 OAuth·stocks·성공 rate header만 `[LIVE_VERIFIED]`로 재분류
- Windows non-ASCII repository parent path의 setuptools editable build 실패를 `P2 DEFERRED / ENVIRONMENT CONSTRAINT`로 기록

### QA

- CP2-D2 사용자 독립 one-shot: provider drift `NO`, OpenAPI `3.1.0`, provider `1.2.14`, actual OAuth와 `GET /api/v1/stocks` PASS, allowed-IP 실행 경로와 Limit/Remaining/Reset header 유효성 PASS
- natural 429를 유도하지 않아 `Retry-After`는 `[LIVE_UNVERIFIED]` 유지; actual 429/5xx, production retry timing과 다른 market endpoint도 미검증 유지
- Vitest UTF-8 byte-safe exact 43 inventory 구현 commit `411749e171a717b3060973cb7b127fb94f592bab`
- ASCII-only 사용자 QA 환경 PowerShell 7.6.5, Python 3.13.15, Node 24.19.0, npm 11.17.0에서 backend 357/357, frontend 43/43, E2E 2/2, migration, fixture idempotency, OpenAPI, production build, secret scan, initial/final policy scan과 exit 0 확인

### Security

- closeout에서 live API를 재호출하거나 credential을 재사용·요청하지 않았고, actual credential 값·token·body·raw header 값을 문서·Git·QA evidence에 기록하지 않음
- P0 0, P1 0, unresolved functional P2 0; Windows path portability P2 1건은 workaround와 함께 명시적으로 이월

### Limitations

- CP2 완료는 Phase 2 완료가 아니다. CP3 이후 security master/current price, normalization, storage, freshness와 나머지 endpoint 구현은 시작하지 않았다.

## Unreleased — Phase 2 CP2-D1 — 2026-08-23

### Added

- `scripts/toss-live-preflight.ps1`의 safe default, offline `-SelfTest`, `-Live` + `-ConfirmReadOnly` + exact ACK three-way gate
- exact canonical OpenAPI runtime drift gate와 environment-only credential contract를 실행하는 internal Python runner/helper
- canonical OpenAPI GET 최대 1회, OAuth POST 최대 1회, `GET /api/v1/stocks` 최대 1회의 one-shot request budget
- OAuth/market 401·403·429·5xx, redirect, drift, safe output/redaction과 request count를 검증하는 MockTransport backend 테스트 36개

### Changed

- backend inventory를 321개에서 357개로 확대하고 standard `scripts/test.ps1`에 default와 offline SelfTest만 포함
- Toss connector source allowlist를 internal-only `preflight.py` exact filename까지 확대하고 control-plane manifest digest를 고정
- production retry/401 refresh 정책은 그대로 유지하면서 live preflight 전용 경로만 retry·refresh·replay 0회로 분리

### Security

- credential은 D2에서만 기존 server-only `TOSS_CLIENT_ID`/`TOSS_CLIENT_SECRET` environment에서 읽고 CLI credential/token parameter와 `.env` loading을 제공하지 않음
- exact HTTPS origin·OpenAPI path·stocks endpoint만 허용하고 redirect 거부, TLS verification, `trust_env=False`, account/order/account header 금지를 유지
- PowerShell wrapper는 child stdout을 fixed key allowlist로 다시 필터링하고 provider body/message, raw header map, Authorization, credential, token, traceback과 private path를 출력·저장하지 않음
- D1 작업과 standard test에서 실제 credential 사용 0, OAuth POST 0, market GET 0; live evidence·DB·fixture·frontend·migration 변경 없음

### QA

- provider contract drift `NO`: OpenAPI `3.1.0`, REST API `1.2.14`, canonical SHA-256 `fccf49abd11f37f557bdd349138f4a03c42b829ebd8b5c14ab4907116fb84c7a`, exact origin 일치
- CP2-D1 baseline SHA `7437d8a30a6f2081431efee815ce96da85700f9b`, final validated implementation SHA `7840eee70ea3d4d8be9057904501ba277e68c99a`
- default `EXTERNAL_NETWORK_REQUESTS=0`, SelfTest `EXTERNAL_NETWORK_REQUESTS=0` 및 gate/schema/redaction/one-shot/drift-stop PASS
- Node.js 24.19.0에서 최종 `scripts/test.ps1` exit code 0: backend 357/357, frontend 43/43, E2E 2/2, migration, fixture idempotency, OpenAPI, build 2회, secret scan, CP2-D1 policy scan PASS
- D1 시작 전 승인된 anonymous canonical OpenAPI 문서 GET 1회만 수행했고 실제 credential, OAuth와 market business request는 수행하지 않음

### Limitations

- 실제 token issuance, 허용 IP, stocks response, rate-limit headers, provider timing, natural 429 `Retry-After`, edge/IP behavior는 계속 `[LIVE_UNVERIFIED]`다.
- CP2-D2는 `NOT STARTED`이며 CP2, CP2-D 또는 Phase 2 완료로 간주하지 않는다.

## Unreleased — Phase 2 CP2-C — 2026-08-23

### Added

- 12개 callable method/path를 7개 runtime group에 exact 매핑하는 `rate_limit.py`
- client×group shared async token bucket과 documented/observed/effective limit 분리
- 네 rate header만 읽는 strict integer parser와 memory-only missing/invalid/inconsistent diagnostic
- 총 3회 시도, 단일·누적 30초 상한, 1→2→4초 backoff와 bounded additive jitter timing primitive
- bounded 429 및 exact `500/502/503/504` retry, safe exhaustion/deferred typed error
- fake monotonic/sleeper/jitter와 `httpx.MockTransport` 기반 CP2-C backend 테스트 65개
- 429 Reset acquire wait와 backoff의 통합 누적 ceiling을 검증하는 deterministic backend 회귀 4개

### Changed

- OAuth `/oauth2/token`을 shared `AUTH` limiter와 같은 bounded retry policy에 연결
- market GET의 401 generation-aware refresh/replay는 1회를 유지하면서 rate retry budget을 분리
- Toss connector source allowlist를 exact 7개 Python 파일로 고정하고 backend inventory를 252개에서 317개로 확대
- 독립 검토 P2 수정으로 429 이후 재시도의 limiter acquire wait를 같은 operation `_RetryBudget`에 포함하고 backend inventory를 321개로 확대
- missing/invalid `Retry-After`에서 유효한 Reset이 잔여 single/cumulative budget을 넘으면 대기를 자르지 않고 즉시 safe deferred error로 종료

### Security

- public token manager/lease/raw bearer surface 없이 token을 connector-private memory에 유지
- response header 전체를 저장하지 않고 `X-RateLimit-Limit`, `Remaining`, `Reset`, `Retry-After`만 숫자로 관찰
- provider body/message, Authorization, Cookie, Set-Cookie, credential과 uncontrolled URL을 rate state/error에 보존하지 않음
- 400/401 규칙 외 auth error/403/404/422/501/contract/transport/boundary error는 retry하지 않음
- actual credential, actual Toss request, account/order surface와 CP2-D live script를 추가하지 않음

### QA

- provider contract drift `NO`: OpenAPI `3.1.0`, REST API `1.2.14`, canonical SHA-256 `fccf49abd11f37f557bdd349138f4a03c42b829ebd8b5c14ab4907116fb84c7a`
- implementation commit `e0017a1891b8f7048c5dc97565224749cf287989`
- P2 cumulative-wait hardening implementation commit `fe65076021f2cc9b3c8d533c3e844b9b9699d5b9`
- Node.js 24.19.0, npm 11.17.0에서 최종 `scripts/test.ps1` exit code 0
- backend 321/321, frontend 43/43, E2E 2/2, migration, fixture idempotency, OpenAPI, build 2회, secret scan, CP2-C policy scan PASS
- standard test outbound network 0; retry constants와 무관하게 connector target 144개가 약 1초에 완료

### Limitations

- 실제 OAuth/token, 허용 IP, runtime rate header·Retry-After, provider response/error와 timing은 계속 `[LIVE_UNVERIFIED]`다.
- CP2-D live preflight는 `NOT STARTED`이며 `scripts/toss-live-preflight.ps1`을 만들지 않았다.
- CP2-C PASS는 CP2 또는 Phase 2 완료를 의미하지 않는다.

## Phase 2 CP2-B — 2026-08-23

### Added

- strict OAuth token/error 모델과 backend application-owned single token manager
- memory-only token lease, monotonic expiry, bounded safety margin, explicit·generation-aware invalidation
- exact Toss origin과 enum 기반 11개 market GET path만 노출하는 `httpx.AsyncClient` transport
- streaming response ceiling(OAuth 64 KiB, market JSON 32 MiB), content-type/JSON/redirect 안전 검사
- CP2-B auth·boundary·integration·concurrency 테스트 75개

### Changed

- Toss connector source allowlist를 CP2-B의 exact 6개 Python 파일로 발전
- backend inventory를 176개에서 251개로 확대하고 통합 gate 기대값을 갱신
- ADR-010은 `PROPOSED`를 유지하면서 CP2-A/CP2-B 구현 진행 메모를 추가

### Security

- `trust_env=False`, `follow_redirects=False`, TLS verification 고정과 connect/read/write/pool timeout을 적용
- 외부 arbitrary URL/method/header API 없이 POST는 내부 `/oauth2/token` 하나로 제한
- symbol traversal/scheme injection과 raw query string, unknown query key/value를 fail closed
- market GET Authorization을 transport 내부에서만 구성하고 token POST·query·Cookie에 전달하지 않음
- 401 `expired-token`/`invalid-token`만 generation-aware invalidate 후 최대 한 번 재발급·replay
- provider body/message, credential, token을 exception/log/raw/DB/QA evidence에 저장하지 않음

### QA

- provider contract drift `NO`: REST API `1.2.14`, canonical SHA-256 `fccf49abd11f37f557bdd349138f4a03c42b829ebd8b5c14ab4907116fb84c7a`
- implementation commit `6a823edc6b3e02cf1c06778f26045f7c535066ed`
- Node.js 24.19.0, npm 11.17.0에서 최종 `scripts/test.ps1` exit code 0
- backend 251/251, frontend 43/43, E2E 2/2, migration, fixture idempotency, OpenAPI, build 2회, secret scan, CP2-B policy scan PASS
- standard test outbound network 0; 모든 Toss connector test는 합성 credential과 `httpx.MockTransport` 사용

### Limitations

- 실제 credential, token endpoint, market endpoint는 호출하지 않아 live OAuth·허용 IP·response/rate header는 계속 `[LIVE_UNVERIFIED]`다.
- CP2-C rate limiter·429/5xx retry와 CP2-D live preflight는 시작하지 않았다.

## Phase 2 CP2-A — 2026-08-23

### Added

- 실제 transport 없이 `services/api/src/toss_dashboard_api/connectors/toss` 전용 namespace scaffold
- optional server-only `TOSS_CLIENT_ID`, `TOSS_CLIENT_SECRET` secret-aware 설정과 빈 `.env.example` 항목
- exact Toss origin·12개 callable endpoint/rate metadata·connector 경로 정책 데이터
- HTTP import, frontend direct Toss, 계좌·주문 endpoint, account header, generic connector와 공개 credential 환경변수 negative canary

### Changed

- `httpx==0.28.1`을 exact runtime dependency로 승격하고 source/runtime 위치·version·lock hash 검증을 강화
- backend test inventory를 172개에서 176개로 확대
- CP2의 범위를 바꾸지 않고 CP2-A부터 CP2-D까지의 실행 순서를 계획에 명시

### Security

- `httpx` import 허용 가능 위치를 Toss backend connector namespace 하나로 제한
- `Authorization`, Bearer, client ID/secret, access token, cookie, set-cookie redaction 보강
- Toss/client secret assignment와 Authorization Bearer 합성 카나리를 secret scan에서 거부
- `.env`, `.env.local`, `.env.*.local`과 동등한 ignore 규칙을 검증하고 실제 credential·`.env` 파일을 추가하지 않음
- 계좌·보유·주문·구매가능금액·매도가능수량·수수료·조건주문 surface와 `X-Tossinvest-Account`를 runtime에서 계속 금지

### QA

- provider contract drift `NO`: REST API `1.2.14`, canonical SHA-256 `fccf49abd11f37f557bdd349138f4a03c42b829ebd8b5c14ab4907116fb84c7a`
- Node.js 24.19.0, npm 11.17.0에서 통합 `scripts/test.ps1` exit code 0
- backend 176/176, frontend 43/43, E2E 2/2, migration, fixture idempotency, OpenAPI drift, build 2회, secret scan, policy scan PASS
- validated implementation commit: `e1bca561998d745bb357dc8c92f835926886e770`

### Limitations

- CP2-A는 CP2 전체 완료가 아니다. OAuth/token manager, HTTP request, rate limit/retry, live preflight는 CP2-B 이후 범위이며 시작하지 않았다.
- `requirements.in`과 `requirements.lock`은 baseline부터 `httpx==0.28.1`과 승인 hash를 포함해 파일 내용 변경이 필요하지 않았다.

## 0.1.0 — 2026-08-22

### Added

- FastAPI/Pydantic 기반 Phase 1 로컬 fixture API와 안전한 오류 envelope
- SQLite metadata migration, 읽기 전용 fixture repository와 멱등 import audit
- 합성 KR/US issuer·security, 가격·수급·재무·기관 보유·공시 diff·가치평가·데이터 품질·analysis packet fixture
- Next.js/TypeScript Company 및 Data Quality 읽기 전용 화면과 loading/empty/error/not-found 상태
- OpenAPI snapshot과 `openapi-typescript` 생성 타입 drift 검사
- Windows PowerShell setup/dev/build/test/migrate/import/E2E/secret/policy 스크립트
- localhost·외부 네트워크·프로세스 소유권·브라우저 transport·테스트 inventory fail-closed gate
- Phase 1 샘플 API JSON, 실행 로그와 Playwright 화면 증거

### Changed

- ADR-005부터 ADR-008까지 Phase 1 계약·식별자·저장 경계·로컬 fail-closed 결정을 `ACCEPTED`로 기록
- Windows Node.js 지원 하한을 24.16.0으로 올리고 `.node-version`을 24.19.0으로 고정하는 ADR-009를 `PROPOSED`로 추가
- 모든 주요 PowerShell 진입점이 정확한 Node/npm 실행 파일과 상속 `NODE_OPTIONS`를 작업 전에 검증하도록 강화
- 최종 테스트 inventory를 backend 172개, frontend 43개, E2E 2개로 확대·고정
- 프로젝트 상태를 Phase 1 완료·독립 QA PASS로 갱신

### Fixed

- Node.js 24.15.0의 Windows TCP 네이티브 충돌을 지원 버전 사전검사로 회피
- E2E frontend 기동을 검증된 정확한 `npm.cmd` 경로로 고정
- Node engine 변경 뒤 이전 값에 남아 있던 비밀정보 스캐너의 `package-lock.json` 승인 digest를 현재 추적 잠금 파일과 동기화

### Security

- FastAPI와 Next.js를 127.0.0.1 전용으로 제한하고 정확한 host/CORS allowlist 적용
- 실제 키·계좌·주문·OpenAI·외부 데이터 connector를 구현하지 않음
- source, 브라우저 bundle, QA artifact와 로그를 비밀정보 검사 범위에 포함
- destructive migration downgrade를 명시적 disposable DB 경로와 확인 플래그로 제한
- Python/Node의 non-loopback 연결과 브라우저의 비허용 요청을 테스트에서 차단·수집

### QA

- 구현 기준 commit: `f358fa3f0d1af44d0348bc5ba5c48be7866d7b21`
- 최종 독립 검증 commit: `57b2a63ead06d03191d8094e1689b8d2ab3d7764`
- PR #1을 merge commit `b1829a7375704271a21267e1fcf62808147be593`으로 `main`에 병합
- Phase 1 release baseline annotated tag: `v0.1.0`
- Node.js 24.19.0, npm 11.17.0에서 setup 2회와 개발 서버 smoke 통과
- backend pytest 172개, frontend Vitest 43개(10 files), Playwright 2개 통과
- Ruff/ESLint, mypy 40 files, TypeScript, process cleanup canary 20회 통과
- migration 왕복, fixture 멱등성, OpenAPI drift, Next build, secret scan, policy scan 통과
- 최종 통합 실행은 secret scan 직전까지 기존 로그를 회수하고, stale lock digest 수정 후 실패한 보안·정책 게이트만 별도로 재검증해 중복 실행을 피함

### Limitations

- 모든 회사·시장·공시·기관 데이터는 합성 fixture이며 실제 투자 데이터가 아님
- 실제 Toss/OpenDART/SEC/news/macro 연결, 계좌, 주문, 자동매매, OpenAI API는 비범위
- ADR-009는 계속 `PROPOSED`이며, Phase 2 전용 상세 실행계획은 아직 작성되지 않음

## 0.1.0-docs — 2026-08-16

### Added

- 전체 단계별 구현계획
- 제품 요구사항
- 아키텍처와 데이터 계약
- SEC 13F·DART 지분공시 기반 기관 포지션 사양
- 가치평가, 공시 문장 비교, 매크로 영향 사양
- 자산제곱 후속 인터페이스
- 보안·운영 원칙
- Phase별 승인 기준
- Codex `/plan`, `/goal`, 독립 리뷰 프롬프트
- QA 템플릿

### Security

- 실제 주문 기능 비범위
- OpenAI API 비사용
- 시크릿 서버 전용
- 로컬 읽기 전용 우선
