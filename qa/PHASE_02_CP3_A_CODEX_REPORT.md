# Phase 2 CP3-A Codex Self Report

Checkpoint Status:
CP3-A IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW

CP3-B:
NOT STARTED

Independent QA:
NOT YET PERFORMED

This report is a Codex self-report and is not an independent QA result.

## Report identity and persistence

Implementation commit:
`3e09ba4163625a193f953379ebc868f560501568`

Report storage:
Separate metadata-only follow-up commit

Reason:
The QA-report persistence rule was introduced only after the implementation
commit had already been pushed. History was preserved instead of amend /
force-push.

Report follow-up commit SHA:
See the Git commit containing this report.

This follow-up persists the self-report only. It is not a new CP3-A implementation and does not modify the implementation commit.

## A. 검증 대상

| 항목 | 값 |
|---|---|
| repository | `beomoo/tosstoss` |
| local repository | `C:\Users\beomoo\Documents\ChatGPT\tosstoss` |
| branch | `feature/phase-02-toss` |
| checkpoint | `Phase 2 CP3-A — Security Master + Current Price planning/contract` |
| CP3-A starting SHA | `6bd5d2ae9c26f02f2cd4bd75a474633a9082fa16` |
| starting origin feature SHA | `6bd5d2ae9c26f02f2cd4bd75a474633a9082fa16` |
| CP3-A implementation SHA | `3e09ba4163625a193f953379ebc868f560501568` |
| remote main SHA | `353159da45cfbe3a7f444bf476ce86fa9aece17c` |
| starting merge-base | `353159da45cfbe3a7f444bf476ce86fa9aece17c` |
| starting main/feature count | main `0`, feature `18` |
| implementation main/feature count | main `0`, feature `19` |

Corrected preflight에서 working tree clean, required branch, local/origin feature SHA, explicitly fetched remote main, merge-base와 ancestry가 모두 기대값과 일치했다. 로컬 `main` branch를 만들거나 전환하지 않았고 `remote.origin.fetch`를 영구 변경하지 않았다.

## B. 환경

| 항목 | 값 | disposition |
|---|---|---|
| PowerShell | `7.6.4` | repository minimum `7.4.0` 이상 |
| previous final QA reference | `7.6.5` | exact requirement가 아니므로 accepted environment variance |
| Python | `3.13.15` | 기준 일치 |
| Node.js | `24.19.0` | 기준 일치 |
| npm | `11.17.0` | 기준 일치 |
| repository path | ASCII-only | 기준 일치 |

PowerShell을 설치, 업데이트 또는 변경하지 않았다.

## C. 변경 파일

### CP3-A implementation commit 변경 파일

| 파일 | 변경 목적 |
|---|---|
| `plans/PHASE_02_EXECUTION_PLAN.md` | CP1 역사적 baseline, 현재 live verification matrix와 CP3-A~D checkpoint 상태 정합화 |
| `plans/PHASE_02_CP3_A_CONTRACT.md` | Security Master와 Current Price 계획·계약 및 acceptance matrix 신규 작성 |
| `DECISIONS.md` | ADR-011 revised proposal과 ADR-012 proposal 기록 |
| `KNOWN_ISSUES.md` | identity, timestamp-null, source revision/natural-key 문제 갱신 |
| `STATUS.md` | CP3-A review 대기와 CP3-B 미착수 상태 반영 |
| `CHANGELOG.md` | CP3-A 문서 checkpoint와 QA 결과 기록 |
| `PROGRESS_LOG.md` | preflight, 계약, 검증과 fail-closed 재실행 이력 기록 |

Implementation commit의 허용 범위 밖 변경은 `0`이었다. `services`, `apps`, `tests`, `fixtures`, `scripts`, migration, dependency와 runtime config diff는 `0`이었다.

### Report-only follow-up 변경 파일

- `qa/PHASE_02_CP3_A_CODEX_REPORT.md` 하나만 추가한다.
- implementation/contract 문서와 application 파일은 이 follow-up에서 수정하지 않는다.

## D. 구현·제안한 계약

### Execution plan 상태

- `CP1 PASS`
- `CP2 COMPLETE`
- `CP3-A IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW`
- `CP3-B NOT STARTED`
- `Phase 2 IMPLEMENTATION IN PROGRESS`
- CP1 당시 live 검증이 없었던 역사적 사실과 CP2-D2 이후 현재 live matrix를 분리했다.

### Endpoint 역할

- `GET /api/v1/stocks/all`: KR/US 별도 universe discovery 전용이다. ACTIVE common-share stock 후보만 다루고 상세 Security Master의 단독 최종 source로 쓰지 않는다. 목록 부재를 delisting으로 추론하지 않는다. 실제 endpoint는 `LIVE_UNVERIFIED`다.
- `GET /api/v1/stocks`: discovery 후보를 최대 200 symbols 단위로 상세 보강한다. actual 호출과 성공 outer response 구조만 `LIVE_VERIFIED`이며 전체 market/enum/null/identifier/lifecycle semantics로 확대하지 않는다.
- `GET /api/v1/prices`: verified canonical security로 mapping된 eligible security에만 사용한다. unresolved/quarantined/collision security에는 normalized price와 latest pointer를 publish하지 않는다. 실제 endpoint는 `LIVE_UNVERIFIED`다.
- fallback endpoint와 기존 exact callable allowlist 확대를 금지했다.

### KR/US universe와 lifecycle

- initial universe는 KR/US, ACTIVE, common-share, canonical provider evidence로 확인된 supported stock security type만 허용하는 보수적 proposal이다.
- market/currency는 KR/KRW와 US/USD exact match를 요구한다.
- ETF, ETN, preferred, warrant, fund, bond, unknown 또는 미확인 enum은 제외하거나 quarantine한다.
- unknown enum은 default mapping하지 않고 raw/source만 보존한 뒤 normalized publish를 막는다.
- ACTIVE에서 INACTIVE/DELISTED로 바뀐 observation은 history로 보존하며 이전 verified row를 삭제하지 않는다.
- discovery에서 일시 누락된 경우 `DISCOVERY_MISSING` observation만 만들고 delisting/valid-to를 자동 생성하지 않는다.
- `listDate=null`, `delistDate=null`, status/date contradiction, exchange 미확인, common flag/type contradiction에 explicit missing reason 또는 quarantine을 사용한다.
- 신규 schema 오류가 생겨도 last known-good를 유지한다.

### Issuer/security/provider identifier

- Phase 1 `Issuer`가 요구하는 KR corp_code/US CIK가 Toss stock response에 없다는 충돌을 명시했다.
- Toss symbol/ticker를 corp_code 또는 CIK로 저장하거나 synthetic regulatory identifier를 만들지 않는다.
- name match 또는 ISIN 하나만으로 issuer를 자동 병합하지 않는다.
- canonical `Issuer`/`Security` 앞에 provider-scoped staging identity를 두는 방안을 권고했다.
- staging mapping은 `UNRESOLVED`와 explicit missing reason을 사용하며 canonical mapping 전 price publish를 금지한다.
- provider symbol과 ISIN의 validity history, symbol change/reuse, ISIN missing/change/collision, market/share-class change, delisting/relisting을 별도 case로 정의했다.
- internal provider identity, issuer ID와 security ID의 deterministic SHA-256 anchor/allocation, collision fail-closed와 rebuild 규칙을 proposal로 문서화했다. 기존 Phase 1 ID는 그대로 보존한다.

### Current Price

- `PriceSnapshot` 후보 field로 ID, canonical security, provider symbol, last price, currency, nullable provider timestamp, fetched time, source record, raw/normalized hash, contract/freshness/availability/revision status를 정의했다.
- `lastPrice`는 canonical non-exponent Decimal string이며 JSON number, binary float, NaN, Infinity와 exponent를 금지했다.
- positive price만 current publish 후보로 삼는다. zero는 missing으로 바꾸지 않지만 `DEGRADED` quarantine하고 latest pointer를 갱신하지 않는다. negative와 negative zero는 reject한다.
- provider currency를 보존하고 Security Master currency와 불일치하면 publish하지 않는다.
- provider timestamp가 null이면 `observed_at` 또는 임의 date에 `fetched_at`을 복사하지 않는다. availability는 `DEGRADED`, freshness는 `UNKNOWN`, current/latest pointer update는 금지한다.
- duplicate same payload와 same-key changed-payload revision을 분리하고 이전 정상 snapshot을 보존한다.
- SQLite에는 current/latest row 또는 pointer만 허용하고 가격 history 누적은 CP4 Parquet/DuckDB 범위로 유지했다.

### Raw → normalized → storage와 hash

- collection attempt, canonical request, raw response payload, source version record, normalized record, latest-state pointer와 audit event를 별도 identity로 정의했다.
- raw manifest에는 source, method, allowlisted path, secret-free canonical query, fetched time, HTTP status, allowlisted response metadata, raw bytes SHA-256, opaque storage ref와 parser/contract version만 허용했다.
- 같은 request/same hash는 audit 외 duplicate를 만들지 않고, different hash는 새 source version과 supersession으로 보존한다.
- schema validation 실패는 raw만 보존하고 normalized/latest publish를 막는다. crash/partial write는 manifest를 publish하지 않는다.
- normalized hash의 semantic include set과 attempt/run/fetched time 등 nondeterministic exclude set을 명시했다.
- 기존 `source_records(source_system, source_type, external_id)` unique를 timestamp suffix로 우회하지 않고 additive provider source-version table로 분리하는 proposal을 작성했다.

### Migration/rollback과 checkpoint split

- `0002_phase_02_cp3_foundation` additive migration 후보만 문서화했고 실제 migration은 만들지 않았다.
- provider identity/history/mapping, collection/request/source/audit와 current latest metadata 후보를 검토했다.
- 기존 `0001`, Phase 1 rows/fixtures/API, FK와 contract v0.1.0의 destructive 변경과 fake regulatory backfill을 금지했다.
- disposable DB에서만 upgrade/downgrade/re-upgrade를 허용하고 raw/history 자동 삭제와 production destructive downgrade를 금지했다.
- CP3-B Contract Foundation, CP3-C Security Master, CP3-D1 Current Price Offline, CP3-D2 separately approved minimal live verification, CP3-D3 integrated QA로 분리했다.
- 각 checkpoint는 이전 checkpoint의 independent review와 사용자 승인 후에만 시작한다.

### Acceptance와 false-green 계획

- contract negative, mapping, universe, price, storage와 false-green 범주에 총 55개 구체적 case를 정의했다.
- 각 case에 목적, 입력, 기대 결과, severity와 false-green 방지 방식을 기록했다.
- extra field, Decimal representation, naive/null timestamp, missing reason, unknown enum, mapping collision/reuse, partial batch, revision, latest pointer, atomic failure와 migration roundtrip을 포함했다.

## E. ADR 상태

| ADR | 상태 | 비고 |
|---|---|---|
| ADR-010 | `ACCEPTED` | CP2 REST allowlist/auth/rate/offline-live boundary 유지 |
| ADR-011 | `PROPOSED — REVISED FOR CP3-A / AWAITING INDEPENDENT REVIEW` | observed time/date 둘 다 null과 structured missing reason proposal |
| ADR-012 | `PROPOSED — AWAITING INDEPENDENT REVIEW` | provider staging identity와 canonical mapping 분리 proposal |

ADR-011과 ADR-012를 Codex가 승인 상태로 전환하지 않았다. Exact provider security-type enum, canonical promotion authority/ID proposal, exchange mapping, freshness thresholds와 SQLite latest representation도 사용자 및 GPT independent review를 기다린다.

## F. 구현하지 않은 범위

| 범위 | 변경/실행 수 |
|---|---:|
| application source implementation | 0 |
| test code 변경 | 0 |
| fixture 변경 | 0 |
| migration 생성/수정 | 0 |
| dependency 변경 | 0 |
| runtime config/API route/connector 구현 | 0 |
| live scheduler/polling | 0 |
| actual Toss API 호출 | 0 |
| credential 사용 | 0 |
| account/order/WebSocket | 0 |
| CP3-B 구현 | 0 |

OpenDART, SEC/13F, news, macro, OpenAI API와 UI도 구현하지 않았다.

## G. 실행한 QA와 실제 결과

### CP3-A implementation commit full regression

Full regression:
Performed for CP3-A implementation commit `3e09ba4163625a193f953379ebc868f560501568`.

| command/check | actual result |
|---|---|
| `git diff --check` | exit `0` |
| `git diff --cached --check` | exit `0` |
| `pwsh -NoProfile -File .\scripts\test.ps1` | final exit `0` |
| backend inventory/result | exactly `357`; `357/357` passed |
| frontend inventory/result | exactly `43`; `43/43` passed |
| E2E inventory/result | exactly `2`; `2/2` passed |
| backend format/lint/typecheck | 79 files formatted; checks passed; mypy 48 source files |
| frontend lint/typecheck | exit path completed successfully |
| migration | repeat, downgrade, re-upgrade passed |
| fixture idempotency | second import `inserted=0`, `updated=0`, `unchanged=13` |
| OpenAPI | generated-type drift check passed |
| production build | two runs passed |
| secret scan | passed |
| initial/final policy scan | passed |
| default preflight network/credential | external requests `0`; credentials used `0` |
| SelfTest network | external requests `0` |

실패 이력도 보존한다.

1. 첫 full run은 기존 orphaned workspace listener가 port 8000을 점유해 E2E 시작에서 exit `1`이었다. 같은 repository command line의 Next/Uvicorn process만 종료하고 ports 3000/8000 availability를 확인했다.
2. 두 번째 full run은 E2E `2/2` 뒤 unstaged documentation을 secret scan의 index/working-tree equality gate가 거부해 exit `1`이었다. scanner 예외를 추가하지 않고 허용 문서만 stage한 뒤 전체 suite를 처음부터 재실행했다.
3. Staged implementation content와 마지막 문서 표기 정정 후 full suite를 다시 실행해 최종 exit `0`을 확인했다.

이번 report-only follow-up은 runtime/application 변경이 아니므로 implementation full regression을 다시 실행하지 않았다.

### Report-only follow-up validation

Report-only follow-up validation:
`git diff --check` + staged secret scan + staged policy scan

| command/check | actual result |
|---|---|
| pre-write `git status --short` | exit `0`, output empty |
| pre-write `git rev-parse HEAD` | exit `0`, implementation SHA와 일치 |
| pre-write `git rev-parse origin/feature/phase-02-toss` | exit `0`, implementation SHA와 일치 |
| `git diff --check` | exit `0` |
| `git diff --name-only` | exit `0`, report path 하나 |
| `git status --short` | exit `0`, report path 하나 |
| `git diff --cached --check` | exit `0` |
| `git diff --cached --name-only` | exit `0`, report path 하나 |
| `pwsh -NoProfile -File .\scripts\secret-scan.ps1` | exit `0`, secret scan passed |
| `pwsh -NoProfile -File .\scripts\policy-scan.ps1` | exit `0`, Phase 2 CP2-D1 scope policy scan passed |

Scan result를 보고서에 기록한 뒤 동일 report 파일만 다시 stage하고 secret/policy scan을 재실행한 최종 staged snapshot만 commit 대상으로 사용한다.

## H. 보안 확인

| 항목 | 결과 |
|---|---|
| actual credential 사용 | 0 |
| actual Toss API 호출 | 0 |
| token 저장 | 0 |
| account/order endpoint 변경 | 0 |
| account header 추가 | 0 |
| WebSocket 변경 | 0 |
| secret artifact | 0 |
| browser/provider direct call 변경 | 0 |

CP3-A에서는 GitHub fetch/push 외 외부 네트워크를 사용하지 않았다. 실제 API body, unrestricted raw headers 또는 account identifier를 QA evidence에 보존하지 않았다.

## I. false-green 확인

| 항목 | 결과 |
|---|---:|
| test 삭제 | 0 |
| skip 추가 | 0 |
| xfail 추가 | 0 |
| inventory 감소 | 0 |
| assertion 완화 | 0 |
| expected exception swallow | 0 |
| empty fixture/collection 우회 | 0 |
| network guard 우회 | 0 |

Test/fixture/application files를 변경하지 않았고 exact inventory가 backend 357, frontend 43, E2E 2로 유지됐다. 중간 실패를 삭제, skip, scanner 예외 또는 조건부 early return으로 숨기지 않았다.

## J. 알려진 제한사항

### LIVE_VERIFIED

- canonical provider contract origin/hash match와 drift 없음
- OpenAPI `3.1.0`, provider REST version `1.2.14`
- actual OAuth token issuance와 credential acceptance
- allowed-IP execution path
- actual `GET /api/v1/stocks` 호출과 성공 outer response 구조
- 해당 성공 응답의 Limit/Remaining/Reset rate header 유효성

### LIVE_UNVERIFIED

- natural 429의 retry timing header
- actual 429/5xx behavior와 production retry timing
- `GET /api/v1/stocks/all`
- `GET /api/v1/prices`
- 나머지 market endpoint
- 전체 stock market/enum/null/identifier/lifecycle semantics
- current price timestamp-null/currency/freshness semantics

Fixture/offline evidence만으로 위 항목을 live verified로 승격하지 않았다.

### Deferred/unresolved

- Windows non-ASCII parent path의 editable install 실패는 `P2 DEFERRED — ENVIRONMENT CONSTRAINT`다. 현재 QA는 ASCII-only path에서 수행했다.
- corp_code/CIK 부재와 provider/canonical identity 분리는 ADR-012 independent review가 필요하다.
- nullable provider source time은 ADR-011 independent review가 필요하다.
- exact provider security-type enum, exchange, canonical mapping authority와 freshness threshold는 unresolved다.
- `/stocks/all`과 `/prices`의 최소 live 대조는 CP3-D2 별도 승인 전 실행할 수 없다.

## K. Codex 자체 P0/P1/P2 판정

Self-assessed P0:
`0`

Self-assessed P1:
`0`

Self-assessed P2:
`0 unresolved functional`; `1 deferred environment constraint` for Windows non-ASCII repository path portability.

This is a Codex self-assessment and is not an independent QA result.

ADR-011, ADR-012와 unresolved contract decisions는 defect 0 판정으로 승인되는 것이 아니며 별도 review 대상이다.

## L. 다음 단계 상태

CP3-A:
IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW

CP3-B:
NOT STARTED

Automatic checkpoint progression:
PROHIBITED

Main merge:
NOT PERFORMED

PR:
NOT CREATED

Tag/Release:
NOT CREATED

Independent QA:
NOT YET PERFORMED

This report is a Codex self-report and is not an independent QA result.
