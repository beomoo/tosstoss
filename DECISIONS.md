# Architecture Decision Record

## ADR-001 — 초기 운영은 로컬 읽기 전용으로 제한

- 상태: `ACCEPTED`
- 결정일: `2026-08-16`

### 결정
초기 버전은 개인 PC에서 실행되는 로컬 웹 대시보드로 구축한다. 실제 주문과 자동매매는 구현하지 않는다.

### 이유
- 시크릿과 계좌정보 노출 위험을 줄인다.
- 무료 운영 조건을 충족한다.
- 데이터 정확성과 분석 로직을 주문 위험과 분리해 검증한다.

---

## ADR-002 — 전체 문서는 선반영하고 구현은 Phase별로 수행

- 상태: `ACCEPTED`
- 결정일: `2026-08-16`

### 결정
향후 구조를 설명하는 모든 사양서는 저장소에 두되, Codex의 `/goal`은 한 Phase만 수행한다.

### 이유
전체 확장성을 고려하면서도 오류 누적과 대규모 미검증 변경을 방지한다.

---

## ADR-003 — 자산제곱 사고모형은 후속 Phase에서 구현

- 상태: `ACCEPTED`
- 결정일: `2026-08-16`

### 결정
자산제곱 규칙 엔진과 자동 가설 판단은 데이터 계층 검증 후 구현한다. 다만 Phase 1부터 `Evidence`, `Hypothesis`, `InvalidationCondition`, 시나리오 변경 이력에 필요한 인터페이스를 고려한다.

---

## ADR-004 — 기관 수급은 단기 수급과 중기 보유 변화를 분리

- 상태: `ACCEPTED`
- 결정일: `2026-08-16`

### 결정
토스의 개인·외국인·기관 순매수는 단기 흐름으로, SEC 13F와 DART 지분공시는 기관별 중기 포지션 변화로 분리해 분석한다.

---

## ADR-005 — Phase 1 내부 계약·정밀도·추적 규칙

- 상태: ACCEPTED
- 결정일: 2026-08-16

### 결정

- 모든 독립 레코드와 API 응답에 contract_version=0.1.0을 포함한다.
- 모든 정규화 레코드에 안정 ID, 자연키, 원문 연결, 정규화 해시를 둔다.
- 금액·수량·비율은 Decimal로 다루고 JSON canonical decimal string과 SQLite TEXT로 보존한다.
- 의미 있는 null에는 구조화된 결측 사유를 연결한다.
- 원문과 정규화 해시를 분리하고, 시각은 aware UTC, 날짜는 date-only로 보존한다.

### 이유

fixture, DB, API, UI 사이의 정밀도와 재현성을 자동 검증하기 위해서다.

---

## ADR-006 — Issuer와 Security 분리

- 상태: ACCEPTED
- 결정일: 2026-08-16

### 결정

- 발행사와 거래 증권을 별도 계약·테이블로 둔다.
- corp_code와 CIK는 발행사에, ticker, exchange, share class, CUSIP, ISIN, FIGI는 증권에 둔다.
- Company API의 경로 ID는 issuer_id이고 응답에 선택된 security_id를 포함한다.

### 이유

복수 주식 클래스, ADR과 본주, 발행사 공시와 증권 가격을 혼동하지 않기 위해서다.

---

## ADR-007 — Phase 1 저장 경계

- 상태: ACCEPTED
- 결정일: 2026-08-16

### 결정

- Phase 1 SQLite에는 발행사, 증권, 원문 메타데이터, 데이터 품질, fixture import audit만 저장한다.
- 가격·수급·재무·기관 보유 등 시계열 sample은 검증된 read-only JSON fixture adapter로 제공한다.
- Analytics repository protocol을 유지하고 Parquet/DuckDB 물리 저장은 후속 Phase로 이연한다.

### 이유

Foundation의 저장 경계를 검증하면서 실제 connector와 분석 저장소 구현으로 범위가 확대되는 것을 막기 위해서다.

---

## ADR-008 — Fixture mode, 상태 축, 로컬 fail-closed

- 상태: ACCEPTED
- 결정일: 2026-08-16

### 결정

- 모든 API와 UI에 data_mode=FIXTURE를 표시하고 합성 회사·종목만 사용한다.
- availability, freshness, finality, revision 상태를 분리한다.
- 두 서버는 127.0.0.1에만 바인딩하고 정확한 로컬 origin/host만 허용한다.
- 안전 플래그가 반대 값이면 Phase 1 앱은 startup을 실패한다.
- setup 후 test에서는 localhost 외 outbound network를 차단한다.

### 이유

fixture를 실데이터로 오인하거나 잘못된 설정으로 위험 기능·네트워크 노출이 켜지는 일을 방지하기 위해서다.

---

## ADR-009 — Windows Node.js 24.16 이상으로 안전 하한 상향

- 상태: PROPOSED
- 제안일: 2026-08-22

### 문제

최초 기준인 Windows 11 build 26200과 Node.js 24.15.0 조합에서 전체 검증 중 `0xC0000409` 네이티브 TCP 충돌이 재현되었다. 이 종료는 JavaScript 예외로 복구하거나 테스트에서 안전하게 처리할 수 없다.

### 제안

- Node.js 24 계열의 최소 지원 버전을 24.16.0으로 올린다.
- 재현 검증 버전은 현재 LTS인 24.19.0으로 고정한다.
- PowerShell 진입점은 지원하지 않는 Node.js를 실제 빌드·테스트 전에 fail-closed로 거부한다.

### 영향

Node.js 24.15 이하 사용자는 setup, dev, lint, typecheck, build, test, E2E를 실행하기 전에 Node.js를 올려야 한다. 시스템 전역 Node.js를 스크립트가 자동으로 변경하지는 않는다.

### 마이그레이션·롤백

공식 Node.js 24.16 이상으로 업그레이드한다. 하한을 다시 낮추려면 Windows TCP 네이티브 충돌이 제거되었다는 독립 재현 증거가 필요하다.

---

## ADR-010 — Phase 2 Toss connector를 REST 시장 데이터 allowlist로 제한

- 상태: `ACCEPTED`
- 제안일: `2026-08-23`
- 결정일: `2026-08-24`

### 문제

Phase 2부터 실제 외부 HTTP 연결과 OAuth credential을 도입해야 한다. 토스증권 공식 API에는 시장 데이터뿐 아니라 계좌·자산·주문·조건주문과 WebSocket 주문 이벤트도 함께 존재하므로 단순 provider client는 읽기 전용 경계를 약화할 수 있다.

### 결정

- backend만 `https://openapi.tossinvest.com`에 연결한다.
- `plans/PHASE_02_EXECUTION_PLAN.md`의 12개 REST method/path allowlist만 호출한다.
- POST는 `/oauth2/token`만 허용한다.
- `X-Tossinvest-Account`, 계좌·자산·주문·조건주문 endpoint와 WebSocket은 runtime·config·dependency·test helper에 추가하지 않는다.
- token은 single-flight backend manager의 memory에만 두고 secret redaction과 deny-by-default policy canary를 적용한다.
- 기존 standard test는 fixture-only·offline을 유지하고 live preflight는 별도 명시적 opt-in으로 분리한다.
- production retry는 exact provider 429와 `500/502/503/504`의 승인 code에만 적용한다. 유효한 `Retry-After`는 jitter 없이 우선하고, missing/invalid일 때만 bounded exponential backoff와 additive jitter를 사용한다. transport error는 live evidence 없이 추측해 retry하지 않는다.

### 대안

- 공식 API 전체를 범용 client로 생성: 금지 surface가 넓어져 거부한다.
- WebSocket 시세까지 Phase 2에 포함: 공식 AsyncAPI는 존재하지만 범위·운영 복잡도가 커져 별도 승인으로 이연한다.
- 외부 연결을 계속 전면 금지: Phase 2 목표를 달성하지 못한다.

### 영향

Phase 1의 blanket HTTP-client/connector 금지는 CP2에서 exact Toss connector exception으로 바뀐다. 대신 금지 endpoint·header·host canary를 추가해 보안 정책을 완화하지 않는다.

### 마이그레이션·롤백

checkpoint 단위로 connector/config/dependency/policy 변경을 revert하고 fixture-only repository로 복귀한다. token은 메모리에서 폐기하며 수집한 검증 데이터는 자동 삭제하지 않는다.

### 구현·검증 기록 — 2026-08-23~24

- CP2-A의 dependency/config/policy 경계, CP2-B의 OAuth token manager/exact-boundary HTTP client와 P2 token hardening, CP2-C의 rate limiter·retry·error taxonomy, CP2-D1 safe live preflight tooling의 offline validation까지 구현·검증했다.
- CP2-C는 client×group shared token bucket, 7개 callable group, documented/observed/effective limit, strict allowlisted rate telemetry를 사용한다.
- retry policy는 승인 계획대로 최초 포함 최대 3회, 단일·누적 retry sleep 30초, 1초 기준 지수 backoff와 bounded additive jitter다. 유효한 `Retry-After`가 30초를 넘으면 짧게 잘라 재시도하지 않고 deferred error를 반환한다.
- 429의 exact rate-limit code와 `500/502/503/504`의 `internal-error`/`maintenance`만 자동 retry한다. 401 replay는 기존 최대 1회이며 transport error는 evidence 없이 retry 대상으로 넓히지 않았다.
- synthetic credential, `httpx.MockTransport`, fake time만 사용했고 실제 provider API 호출이나 token/rate telemetry 저장은 하지 않았다.
- 독립 검토 P2 후 429로 시작된 재시도에서는 backoff와 다음 limiter acquire의 Reset block을 하나의 operation 누적 30초 ceiling으로 계산한다. 정상 최초 요청의 선제적 local throttling은 retry budget과 분리하되, Reset이 잔여 single/cumulative budget을 넘으면 짧게 잘라 재시도하지 않고 safe deferred error로 종료한다.
- CP2-D1은 default·SelfTest network 0, three-way opt-in, runtime canonical contract drift, environment-only credential, OAuth/stocks one-shot, safe fixed summary를 internal-only 경계로 고정했다. production retry는 변경하지 않았고 D1에서는 actual credential/OAuth/market request를 사용하지 않았다.
- CP2-D2 사용자 독립 one-shot에서 provider drift `NO`, actual OAuth와 `GET /api/v1/stocks` `PASS`, allowed-IP 실행 경로와 성공 응답의 Limit/Remaining/Reset header 유효성을 확인했다. credential 값, token, body와 raw header 값은 저장하지 않았다.
- natural 429 `Retry-After`, actual 429/5xx, production retry timing과 나머지 market endpoint는 계속 `[LIVE_UNVERIFIED]`다.
- Vitest UTF-8 byte-safe exact inventory 보강 commit `411749e171a717b3060973cb7b127fb94f592bab` 이후 사용자 ASCII-only 환경의 전체 regression이 backend 357/357, frontend 43/43, E2E 2/2와 모든 build·security gate에서 exit 0이었다.
- CP2 final integrated QA 결과는 P0 0, P1 0, unresolved functional P2 0, 명시적 deferred environment P2 1이다. 따라서 ADR-010과 CP2를 `ACCEPTED`/`COMPLETE`로 닫되 Phase 2 전체 완료나 CP3 시작으로 확대하지 않는다.

---

## ADR-011 — date-only Toss 관측을 versioned source contract로 분리

- 상태: `ACCEPTED`
- 제안일: `2026-08-23`
- 수정 제안일: `2026-08-24`
- 독립검증일: `2026-08-25` — 방향상 blocker 없음; 당시에는 사용자 승인 전이어서 `PROPOSED` 유지
- 결정일: `2026-08-25`
- 결정 근거: GPT independent re-review `PASS WITH CLOSEOUT CONDITION`, P0 0/P1 0과 사용자의 명시적 승인

### 문제

Phase 1 `SourceRecord`는 `observed_at`과 `published_at`을 필수 datetime으로 요구한다. Toss 수급 응답 일부는 기준 `date`만 제공하고 publication timestamp를 제공하지 않는다. 또한 공식 `/prices` 계약은 정상 응답에서도 `timestamp=null`을 허용한다. 기존 제안의 “`observed_at`과 `observed_date` 중 최소 하나” 규칙은 이 정상적인 time-unknown 상태를 표현하지 못한다. 자정, 현재 date 또는 fetch 시각을 대입하면 기존 시간 의미를 위반한다.

### 결정

- 기존 Phase 1 `SourceRecord` v0.1.0과 fixture는 변경하지 않는다.
- Phase 2에 date-only와 timestamp 관측을 구분하는 versioned provider source contract를 추가한다.
- `observed_at`과 `observed_date`는 각각 nullable이다.
- 둘 다 null인 상태를 허용하되 각 null field에 structured missing reason을 요구한다.
- 둘 다 값이 있으면 dataset별 contract가 해당 조합을 명시적으로 허용하는지 검증한다.
- `published_at`은 nullable이고 null이면 structured missing reason이 필수다.
- `fetched_at`은 required aware UTC이며 관측 또는 발표 시각을 대신하지 않는다.
- current price의 provider timestamp가 null이면 availability `DEGRADED`, freshness `UNKNOWN`으로 두고 current/latest publish를 막는다.
- 전역 `ContractVersion = Literal["0.1.0"]`을 무조건 확장하지 않고 새 provider source contract에 독립 version을 부여한다.
- 신규 provider source version은 기존 `source_records` natural key를 timestamp suffix로 우회하지 않고 additive table에서 revision을 표현한다.

### 대안

- date를 자정 UTC/KST로 변환: 존재하지 않는 시각을 생성하므로 거부한다.
- `fetched_at`을 `observed_at`으로 복사: 데이터 기준시각과 수집시각을 혼동하므로 거부한다.
- timestamp null인 price를 0 또는 현재 date로 대체: provider 사실을 위조하므로 거부한다.
- 기존 SourceRecord 전체를 즉시 breaking migration: Phase 1 회귀 범위가 커서 거부한다.

### 영향

이 결정은 CP3-B의 source contract·additive migration·fixture·repository test 구현 기준이다. 기존 Phase 1 계약 테스트, fixture/API/OpenAPI와 `contract_version=0.1.0` 응답은 그대로 통과해야 한다. ADR 승인은 CP3-B 시작 승인이 아니며 별도 명시적 authorization 전에는 구현하지 않는다.

### 마이그레이션·롤백

신규 provider record만 새 contract를 사용한다. rollback은 신규 publish 중지, last known-good pointer 유지와 해당 additive contract/migration의 disposable-DB 검증 후 revert다. 기존 Phase 1 row·fixture와 raw/history를 변환하거나 삭제하지 않는다.

### CP3-B 구현 기록 — 2026-08-25

- 전용 `toss-source/0.1.0` contract가 nullable `observed_at`, `observed_date`, `published_at`, structured missing reason과 required aware UTC `fetched_at`을 구현한다.
- STOCK_DISCOVERY/STOCK_DETAIL, CURRENT_PRICE, future DAILY_FLOW의 observation 조합을 strict offline contract test로 고정했다. endpoint DTO/normalizer 또는 live semantics는 구현·검증하지 않았다.
- 기존 `SourceRecord`, 전역 `ContractVersion = Literal["0.1.0"]`, fixture/API/OpenAPI는 변경하지 않았다.
- additive source-version/raw-manifest schema와 deterministic normalized hash는 fetch/run/storage identity를 semantic hash에서 제외하고 revision history를 별도 보존한다.

### CP3-B 독립검증 보완 기록 — 2026-08-25

- 같은 canonical request/status/raw hash/provider contract의 later fetch는 `fetched_at`과 allowlisted telemetry가 달라도 first-seen immutable raw/source duplicate로 처리한다. dataset, parser version, normalized hash, revision/supersedes 또는 provider contract가 다르면 fail closed한다.
- repository는 `/api/v1/stocks/all → STOCK_DISCOVERY`, `/api/v1/stocks → STOCK_DETAIL`, `/api/v1/prices → CURRENT_PRICE` exact mapping과 request→raw→source→attempt/audit graph를 강제한다. `DAILY_FLOW`은 승인 endpoint가 없어 persistence를 금지한다.
- CURRENT_PRICE source freshness는 CP3-D2 승인 전 timestamp 존재 여부와 무관하게 `UNKNOWN`이고 timestamp-null source는 보존할 수 있지만 latest pointer에는 사용할 수 없다.
- `0002` mid-DDL failure는 해당 upgrade가 생성한 CP3 table만 역순 제거해 revision/Phase 1 row/pre-existing object를 보존한다. raw publish는 overwrite 가능한 rename 대신 atomic no-replace를 사용한다.

---

## ADR-012 — Toss provider security identity와 canonical issuer/security mapping 분리

- 상태: `ACCEPTED`
- 제안일: `2026-08-24`
- 독립검증 보완일: `2026-08-25`
- 결정일: `2026-08-25`
- 결정 근거: GPT independent re-review `PASS WITH CLOSEOUT CONDITION`, P0 0/P1 0, P1-01/P1-02 `CLOSED`와 사용자의 명시적 승인

### 문제

Phase 1 `Issuer`는 KR corp_code 또는 US CIK를 요구하고 `Security`는 issuer와 exchange를 요구한다. Toss stock response에는 corp_code/CIK가 없고 현재 저장소 근거만으로 exchange semantics도 확정할 수 없다. Toss symbol, ticker, 종목명 또는 synthetic regulatory identifier로 빈칸을 채우면 잘못된 issuer merge와 VERIFIED mapping을 만들 수 있다.

첫 독립검증은 두 P1을 확인했다. P1-01은 verified canonical mapping을 Current Price 저장의 필수조건으로 둬 Phase 2가 Phase 3 OpenDART/Phase 4 SEC regulatory mapping에 순환 의존한다는 점이다. P1-02는 최초 observation 뒤 ISIN/listDate가 보강될 때 anchor 우선순위를 다시 적용하면 immutable이어야 할 동일 instrument에 새 provider identity가 생길 수 있다는 점이다.

### 결정

- canonical `Issuer`/`Security` 이전에 provider-scoped `provider_security_identity` staging 계층을 둔다.
- Toss symbol은 provider-scoped identifier history로만 저장한다.
- staging row는 `mapping_status=UNRESOLVED`, nullable canonical IDs와 explicit missing reason을 사용한다.
- internal provider identity, issuer, security ID는 외부 field와 분리하고 한번 발급되면 symbol/ISIN/provider field 변경으로 교체하지 않는다.
- valid·non-collision·non-quarantine provider identity는 canonical `security_id`가 null이고 mapping이 `UNRESOLVED`여도 provider-scoped `ProviderPriceSnapshot`과 latest state를 소유할 수 있다.
- canonical current-price view와 canonical Security API/issuer/company analysis 연결은 `security_id` linkage가 `VERIFIED`일 때만 허용한다. unresolved provider price를 canonical company price로 표현하지 않는다.
- 신규 observation은 최초 anchor 선택 전에 active identity와 provider identifier history에서 continuity 후보를 검색한다. deterministic 후보가 정확히 하나면 기존 ID를 재사용하고 ISIN/listDate/symbol을 enrichment/revision history로 추가한다.
- continuity 후보가 둘 이상이거나 enrichment가 다른 active identity와 충돌하면 auto merge/new identity/winner 선택을 금지하고 `UNRESOLVED_COLLISION`/`QUARANTINE`한다.
- continuity evidence가 0일 때만 최초 anchor를 unique valid ISIN → symbol+listDate → symbol+first-seen raw evidence 순으로 선택한다. 최초 allocation 뒤 더 강한 identifier가 생겨도 anchor migration/rekey를 금지한다.
- deterministic rebuild는 raw/source history를 stable order로 replay하며 같은 continuity-first 결과, provider identity ID와 identifier history를 재현해야 한다.
- approved canonical mapping event는 linkage만 추가하고 provider identity, allocation anchor, provider price/history ID/hash를 변경하지 않는다.
- exact deterministic anchor/hash/collision/rebuild/promotion 규칙은 `plans/PHASE_02_CP3_A_CONTRACT.md` E/G절을 따른다.
- 이름 일치, symbol/ticker, 단독 ISIN으로 issuer를 자동 병합하지 않는다.
- approved OpenDART corp_code/SEC CIK와 instrument evidence가 있을 때만 canonical mapping event를 만들 수 있다.
- quarantined/collision provider identity에는 provider snapshot/latest와 canonical view 모두 publish하지 않는다.

### 대안

1. provider-scoped provisional issuer: regulatory identity가 없는 가짜 issuer와 잘못된 name merge 가능성이 커서 거부한다.
2. canonical Security 이전 provider staging identity: 사실과 mapping 상태를 분리하므로 권고한다.
3. 기존 Issuer 계약 breaking 완화: Phase 1 fixture/API/OpenAPI 회귀와 거짓 VERIFIED row 위험 때문에 기본 거부한다.

### 영향

이 결정은 CP3-B additive staging/source/mapping/provider-latest schema와 repository interface, CP3-C offline security master normalization, CP3-D current price의 구현 기준이다. Current price는 valid provider identity를 소비해 provider-scoped snapshot/latest를 만들고, verified canonical linkage가 있을 때만 canonical current-price view를 제공한다. 따라서 Phase 2 provider-scoped Security Master + Current Price 목표는 Phase 3/4 regulatory mapping 없이 완료 가능하다. 기존 Phase 1 Issuer/Security v0.1.0, fixture IDs와 public API는 변경하지 않는다. ADR 승인은 CP3-B 시작 승인이 아니다.

### 마이그레이션·롤백

후보 `0002_phase_02_cp3_foundation`은 신규 table/FK/unique constraint만 추가한다. provider latest의 key는 `provider_security_identity_id`이고 canonical linkage는 nullable mapping table에서 분리한다. `0001` 수정, 기존 table destructive rebuild, corp_code/CIK fake backfill, 기존 fixture 변환과 SQLite 가격 history 누적을 금지한다. downgrade는 disposable DB에서만 검증하며 실제 raw/history를 자동 삭제하지 않는다.

### CP3-B 구현 기록 — 2026-08-25

- `provider_security_identities`, append-only identifier history, nullable canonical mapping과 provider-scoped latest pointer의 schema/repository foundation을 구현했다.
- identity ID는 immutable allocation anchor SHA-256과 일치해야 하고 foundation row는 스스로 `VERIFIED`로 승격할 수 없다. verified mapping은 실제 canonical issuer/security linkage와 approval time을 요구한다.
- full continuity-first reconciliation, enrichment collision service, canonical promotion, Security Master DTO/normalizer는 CP3-C로 이연했다.
- latest foundation은 `(dataset, provider_security_identity_id)` unique pointer뿐이며 ProviderPriceSnapshot 또는 SQLite 가격 history를 구현하지 않았다.

### CP3-B 독립검증 보완 기록 — 2026-08-25

- VERIFIED mapping은 existing ACTIVE identity, 실제 canonical issuer/security row와 `Security.issuer_id == mapping.issuer_id`, 그리고 identity first/latest 또는 identifier-history source lineage evidence를 모두 요구한다. quarantined/collision identity와 unrelated evidence는 거부한다.
- latest pointer eligibility는 ACTIVE identity, exact dataset/source observation과 identity lineage를 검증한다. 기존 pointer 갱신은 `latest_pointer_id`와 expected `state_hash`를 WHERE에 둔 단일 SQL conditional update이며 두 independent session 중 정확히 한 writer만 old hash를 소비한다.
- first insert race는 같은 payload를 idempotent duplicate로, 다른 payload를 typed conditional conflict로 처리하며 row 하나만 유지한다. raw `OperationalError`/`IntegrityError`를 repository 경계 밖으로 노출하지 않는다.
- 이 hardening은 CP3-C identity reconciliation이나 CP3-D price payload/service를 시작하지 않으며 ADR-012의 provider/canonical 분리 결정을 바꾸지 않는다.

### CP3-C1 구현 기록 — 2026-08-26

- strict discovery/detail DTO와 비식별 offline fixture를 `toss-security-master/0.1.0`으로 분리하고, unknown enum·extra field·JSON numeric Decimal·invalid ISIN은 normalized staging 전에 fail closed한다.
- 같은 provider/market의 continuity evidence를 최초 anchor보다 먼저 평가한다. deterministic 후보가 하나면 기존 ID/anchor를 유지하고 identifier history를 추가하며, 후보가 여럿이거나 identifier/share-class/listing-market evidence가 모순되면 신규 ID·merge·임의 winner 없이 관련 identity를 격리한다.
- semantic normalized record, source-linked staging/lifecycle observation, identity-state event와 detail-batch exact audit는 CP3-B table에 사실대로 표현할 수 없어 additive `0004_phase_02_cp3_c1_security_master` 네 table로 보존한다. `0001`/`0002`/`0003`은 byte-identical이고 backfill/destructive rewrite는 없다.
- discovery disappearance는 `DISCOVERY_MISSING` observation만 추가하며 delisting/`valid_to`/canonical mapping close를 추론하지 않는다. detail inactive/delisted/contradiction/partial/empty 상태는 LKG/history를 삭제하지 않고 별도 observation으로 남긴다.
- deterministic replay는 source를 `(fetched_at, source_version_id)`로 정렬하며 clock/run/job/attempt ID를 identity allocation에 사용하지 않는다.
- CP3-C1은 `ELIGIBLE_FOR_MAPPING` candidate evidence에서 중단한다. canonical Issuer/Security 생성, fake corp_code/CIK, exchange 추정과 `VERIFIED` 승격 권한은 CP3-C2 사용자 결정 전까지 계속 금지한다. CP3-D 가격 구현과 live request도 시작하지 않았다.

### CP3-C1 독립검토 P1 보완 기록 — 2026-08-26

- GPT independent review는 P0 0/P1 2로, symbol transition 뒤 current identifier가 history hash/ID ordering에 의존할 수 있는 문제와 동일 STOCK_DETAIL source의 뒤늦은 duplicate ISIN이 앞선 observation을 eligible로 남길 수 있는 문제를 확인했다.
- current identifier는 source chronology별 의미 상태로 해석한다. closed value를 current에서 제외하고 SYMBOL_CHANGE observation의 open replacement set을 사용하며, 상충하는 open current value가 둘 이상이면 arbitrary winner 없이 `UNRESOLVED_COLLISION`/`QUARANTINED`로 fail closed한다. `identifier_history_id`는 semantic winner를 결정하지 않는다.
- provider가 symbol-change effective date를 제공하지 않으면 `listDate` 또는 `fetched_at`을 그 날짜로 대입하지 않는다. 기존 history와 immutable provider identity/allocation anchor는 보존한다.
- 한 detail source는 complete response의 duplicate non-null ISIN과 existing continuity candidates를 publish 전에 분석한다. affected observation은 모두 처음부터 non-eligible collision quarantine으로 기록하며, new candidate collision에는 identity를 할당하지 않는다.
- schema는 이 logic correction에 충분하므로 migration은 추가하지 않는다. `0001`~`0004`는 byte-identical이고 canonical promotion authority, CP3-C2, CP3-D와 live scope는 변경하지 않는다.
- CP3-C1 상태는 `REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW`다. 이 기록은 re-review `PASS` 또는 다음 checkpoint 시작 승인이 아니다.

### CP3-C1 독립 재검토 closeout 기록 — 2026-08-26

- GPT independent re-review는 implementation SHA `ac2c194de9b9b413c3a83537b84e878ba579d3e6`에 대해 `PASS WITH CLOSEOUT CONDITION`, P0 0/P1 0, P1-01/P1-02 `CLOSED`로 판정했다.
- documentation closeout 뒤 CP3-C1은 `PASS — CLOSED`다. 이 closeout은 canonical promotion, CP3-C2 implementation, CP3-D 또는 automatic checkpoint progression 권한이 아니다.
- 이전 `CHANGES REQUIRED` 기록, 보완 self-report, 실패한 회귀 이력과 nonblocking secret-scan QA infrastructure P2는 삭제하거나 소급 수정하지 않는다.

---

## ADR-013 — canonical promotion은 field-owned authority bundle과 명시적 수동 승인을 요구

- 상태: `ACCEPTED`
- 제안일: `2026-08-26`
- 결정일: `2026-08-26`
- 상세 계약: `plans/PHASE_02_CP3_C2_PROMOTION_AUTHORITY.md`

### 문제

CP3-C1 provider staging은 Toss의 name/symbol/ISIN observation을 canonical Issuer/Security와 의도적으로 분리했다. 그러나 현행 저장소에는 OpenDART corp_code/SEC CIK, KRX/SEC·primary-exchange instrument evidence, authority revision·collision과 human approval을 하나의 검증 가능한 bundle로 표현하는 승인 계약이 없다. Toss symbol/ticker/name, synthetic corp_code/CIK 또는 단독 provider identifier로 빈칸을 채우면 issuer/class/security를 잘못 합치는 P0 mapping 오류가 발생한다.

현행 `ProviderIdentityMapping(VERIFIED)`은 issuer/security/approved_at을 동시에 요구하므로 `issuer verified, security unresolved`를 표현하지 못한다. `MappingStatus`는 review/revocation/supersession을 표현하지 못하고 mapping row 한 개의 provider source만으로 cross-authority evidence를 보존할 수 없다. `ShareClass.COMMON`도 복수 common class를 안전하게 구분하지 못한다. `Jurisdiction`은 KR/US만 지원하므로 미국 또는 한국에 상장된 foreign issuer의 실제 법적 관할권을 listing market으로 강제하면 안 된다. 또한 EDGAR Next accession prefix는 registrant가 아니라 filing agent일 수 있는 login CIK를 반영하므로 별도 provenance 없이 registrant CIK로 해석하면 잘못된 issuer anchor가 된다.

### 제안

- canonical promotion의 기본 상태는 `UNRESOLVED`다.
- machine은 official evidence 수집·정규화·revision/collision 검증과 `READY_FOR_MANUAL_REVIEW` 후보까지만 만든다. canonical Issuer/Security 생성과 current `ProviderIdentityMapping(VERIFIED)`은 authenticated human data steward의 명시적 승인 event가 필수이며 자동 final promotion은 0이다.
- human approval도 모순된 authority evidence의 임의 winner를 선택할 권한은 없다. field-owning authority의 correction이나 추가 근거로 conflict가 해소되지 않으면 unresolved/quarantine을 유지한다.
- OpenDART corp_code는 DART disclosure issuer authority이고 KR instrument/listing/share-kind/ISIN authority는 KRX다. OpenDART→KRX issuer/instrument bridge와 provider observation이 모두 일치해야 하지만, KRX market과 OpenDART `corp_cls`/`stock_code`는 legal jurisdiction authority가 아니다. KRX-listed issuer의 actual jurisdiction이 독립적으로 확인되어 현행 KR/US enum으로 표현되지 않으면 `UNRESOLVED / jurisdiction-contract-required`를 유지한다.
- US issuer authority는 accepted evidence의 authoritative registrant/filer metadata에서 얻은 SEC `registrant_cik`다. accession prefix/login CIK와 filing-agent CIK는 separate audit provenance일 뿐 issuer authority가 0이며 issuer ID, authority-bundle candidate identity와 SEC registered-class anchor에 사용할 수 없다. instrument/class authority는 accepted SEC class evidence이고 current listing/ticker status는 해당 primary exchange가 소유한다. SEC company ticker file은 discovery only다.
- CGS CUSIP/US ISIN은 numbering authority지만 license와 승인된 access가 없으면 evidence가 없는 것으로 처리한다. provider-supplied CUSIP/ISIN으로 대체하지 않는다.
- provider name/symbol/ticker는 canonical/regulatory identifier나 anchor로 사용하지 않는다. synthetic/fake corp_code/CIK, name-only/symbol-only merge, inferred exchange/share class, arbitrary collision winner를 금지한다.
- promotion은 linkage만 추가한다. `provider_security_identity_id`, allocation anchor, provider/source/identifier/normalized/observation history를 rekey·rewrite하지 않는다.
- implementation은 `CP3-C2-B canonical issuer authority/mapping`과 `CP3-C2-C canonical security authority/final mapping`으로 분리한다. issuer만 승인된 상태에서 provider final mapping은 계속 `UNRESOLVED`다.
- correction/revocation은 append-only evidence/decision event로 보존하고 authority가 주지 않은 effective date를 `fetched_at`/approval time으로 만들지 않는다.
- current evidence의 24-hour approval threshold는 `REPO_POLICY / CONSERVATIVE_APPROVAL_FRESHNESS`이며 외부 authority의 universal rule로 표현하지 않는다. authority publication/effective/as-of date와 `fetched_at`을 분리한다.

### 독립검토 보완 제안 기록 — 2026-08-26

- Reviewed SHA: `0a7463cfbc93b9f19f247577edd73b993efa2766`
- GPT independent review: `CHANGES REQUIRED`, P0 `0`, P1 `2`, P2 `1`.
- P1-01: KRX는 foreign corporation listing을 허용하므로 market=KR은 legal
  jurisdiction=KR의 근거가 아니다. KOSPI/KOSDAQ/KONEX, `corp_cls`,
  `stock_code`, provider market/name와 KR trading currency를 관할권 근거에서
  제외하고, KRX-listed foreign issuer의 actual jurisdiction이 현행 enum으로
  확인·표현되지 않으면 canonical write와 review-ready state를 모두 0으로
  고정하도록 제안을 보완했다.
- P1-02: EDGAR Next accession 첫 10자리는 login CIK이며 filing agent일 수
  있다. accepted evidence의 authoritative registrant metadata만
  `registrant_cik` 권한을 갖고 login/agent CIK는 zero-authority provenance로
  분리하도록 제안을 보완했다.
- P2: 24시간 기준을 repository conservative approval policy로 명시했다.
- 이 독립검토 보완 commit 당시에도 ADR-013 상태는 `PROPOSED`였다. GPT
  re-review와 사용자 승인은 아직 없었고 CP3-C2-B/C 구현 권한도 없었다.

### 대안

1. Toss symbol/name만으로 canonical merge: regulatory/legal/instrument authority가 아니므로 거부한다.
2. OpenDART/SEC issuer identifier 하나로 Security까지 생성: issuer와 share class/instrument를 혼동하므로 거부한다.
3. 모든 official-looking source에 동일 precedence 부여: source마다 field authority scope가 달라 conflict를 숨기므로 거부한다.
4. 전 근거 일치 시 무인 automatic VERIFIED: correction, ticker reuse, share class와 access/licensing 위험이 남으므로 이 계약에서는 거부한다.
5. issuer와 security를 한 checkpoint에서 구현: `issuer verified, security unresolved`를 거짓 final mapping 없이 표현하기 어렵고 P0 blast radius가 커서 거부한다.

### 영향

CP3-C2-A는 planning 문서만 변경한다. application, migration, fixture, test, API, frontend, connector, scheduler와 live request는 0이다. ADR-013은 아래 독립 재검토와 명시적 사용자 승인에 따라 `ACCEPTED`다. 이 승인은 CP3-C2-B/C implementation 시작 권한이 아니다.

기존 Phase 1 synthetic fixture identifier는 regression history로 보존하지만 신규 promotion evidence로 사용하지 않는다. 향후 구현은 authority evidence bundle, approver identity, issuer-only decision, multi-class instrument와 revocation을 위한 versioned additive contract/schema가 필요할 수 있으며 별도 checkpoint 승인 없이는 migration을 만들지 않는다. `0001`~`0004`는 변경하지 않는다.

### 마이그레이션·롤백

CP3-C2-A migration은 0이다. 문서 제안 rollback은 documentation commit revert뿐이며 provider/canonical data 영향은 없다. 후속 migration 설계가 승인되더라도 additive evidence/decision/linkage만 허용하고 기존 provider/canonical/raw/history row의 destructive rewrite나 rekey를 금지한다.

### 승인 기록 — 2026-08-26

- Reviewed SHA: `99bac1a7dc308414172e002496cd1e57f1c709c7`
- GPT independent re-review: `PASS WITH CLOSEOUT CONDITION`.
- P0: `0`.
- P1: `0`.
- P1-01: `CLOSED`.
- P1-02: `CLOSED`.
- P2-01: `CLOSED`.
- 사용자 결정: revised CP3-C2 canonical promotion authority contract와
  ADR-013을 명시적으로 승인했다.
- 승인 범위: CP3-C2-A contract closeout만. CP3-C2-B는 별도 사용자 시작
  승인이 필요하고 CP3-C2-C/CP3-D와 automatic progression도 승인되지 않았다.

---

## ADR-014 — issuer authority는 별도 append-only ledger와 issuer-only link로 표현

- 상태: `ACCEPTED`
- 제안일: `2026-08-26`
- 결정일: `2026-08-26`
- 상세 설계: `plans/PHASE_02_CP3_C2_B1_RUNTIME_CONTRACT.md`

### 문제

Accepted ADR-013은 automatic canonical promotion을 금지하고 field-owned
authority bundle에 대한 authenticated human approval을 요구한다. 그러나 현행
`MappingStatus`는 `UNRESOLVED|VERIFIED`뿐이고,
`ProviderIdentityMapping(VERIFIED)`은 issuer와 security를 동시에 요구한다.
따라서 authority evidence/bundle, issuer-only approval, authenticated reviewer,
stale/review-required, rejection/revocation/supersession을 기존 mapping row에
넣으면 `issuer approved / security unresolved`를 거짓으로 표현하거나 기존
계약을 breaking 변경하게 된다.

또한 기존 unique constraint만으로 duplicate corp_code/CIK 후보를 막으면 두
상충 후보 중 먼저 쓴 행이 사실상 승자가 될 수 있고, approval row를 수정·삭제해
revocation을 표현하면 ADR-013의 append-only history를 잃는다.

### 제안

- 기존 `MappingStatus`, provider identity/history, `Issuer`/`Security` public
  contract와 `0001`~`0004`는 변경하지 않는다.
- `AuthorityEvidence`, `AuthorityEvidenceApplication`, `AuthoritySourcePolicy`,
  `AuthorityBundle`, `IssuerDecision`, `IssuerApprovalEvent`,
  `IssuerAuthorityLink`와 local steward authentication에 독립 version을
  부여한다.
- semantic ID/hash는 canonical UTF-8/NFC JSON과 SHA-256으로 만들고 retrieval
  time, run/job/DB row ID, insertion order와 current clock을 제외한다.
- machine은 `UNRESOLVED`, `STALE`, `REVIEW_REQUIRED`, 최대 positive state
  `READY_FOR_MANUAL_REVIEW`만 생성한다. `APPROVED`, `REJECTED`, `REVOKED`,
  `SUPERSEDED`는 server-resolved authenticated human event로만 확정한다.
- human approval trust root는 exact `RP ID=localhost`, approval origin
  `http://localhost:3000`, user verification required인 Windows Hello-backed
  WebAuthn/passkey다. server-owned principal과 registered public-key
  fingerprint를 사용하고, every disposition은 decision/bundle/content
  hash/disposition에 bound된 CSPRNG one-time five-minute challenge와 새
  assertion을 요구한다. caller-supplied principal/role/authentication status,
  expired/reused/cross-bound challenge, invalid signature와 UV 없는 assertion은
  fail closed한다.
- human approval event는 exact immutable decision/bundle/hash와 성공한
  server-side authentication event를 참조하고 conflict override field를
  제공하지 않는다.
- approved B link는 provider identity와 canonical issuer만 연결하고
  `security_resolution_state=UNRESOLVED`를 강제한다. canonical `Security`와
  `ProviderIdentityMapping(VERIFIED)` write는 0이다.
- correction/revocation/supersession은 새 evidence/relation/decision/event/link
  row를 append한다. current head는 append-only link chain에서 rebuild 가능한
  CAS projection으로만 관리한다.
- duplicate authority identifier claim은 모두 먼저 기록한 뒤 distinct
  candidate fingerprint를 전역 검사한다. unique constraint의 first-writer를
  정답으로 사용하지 않고 모든 affected candidate를
  `UNRESOLVED`/`REVIEW_REQUIRED`로 만든다.
- KR legal jurisdiction은 original verified 대한민국 대법원/인터넷등기소
  법인등기 record와 OpenDART raw `jurir_no`의 exact bridge만 decisive하다.
  OpenDART corp_code는 disclosure-filer authority로 분리하고
  KRX/provider/OpenDART listing field, screenshot, search result와 manually
  typed registration value는 관할권 authority가 아니다.
- US legal jurisdiction은 issuer의 relevant formation-state registry가
  field-owner다. Accepted SEC registrant evidence와 approved exact non-name-only
  bridge는 필수 supporting/regulatory evidence지만 CIK, SEC, LEI와 US exchange가
  state registry를 대체하지 않는다. accession/login/filing-agent CIK는 별도
  zero-authority provenance이며 foreign private issuer의 실제 관할권이 현행
  KR/US contract로 표현되지 않으면 unresolved다.
- immutable source-policy registry는 exact namespace/document kind/scope/role,
  maximum weight, ingestion mode, production eligibility, access/license와
  fixture/test taint를 고정한다. `SourceSystem.FIXTURE_*`, `DataMode.FIXTURE`,
  legacy synthetic identifiers, test adapter, synthetic/relabelled payload는
  production authority bundle에 들어갈 수 없다.
- reusable raw evidence와 candidate application을 분리하고 bundle은 exact
  evidence application을 참조한다. raw document hash는 exact
  `raw_claim_value` 저장을 대신하지 않는다.

### 독립검토 보완 기록 — 2026-08-26

- Remediation starting SHA:
  `adfb76285af7ae5884cfc60a0223591bb7e9c913`.
- GPT independent review verdict: `CHANGES REQUIRED`, P0 `0`, P1 `4`, P2 `1`.
- P1-01: Windows Hello-backed WebAuthn trust root, exact RP/origin, server-owned
  principal/public credential, five-minute one-time exact-content-bound
  challenge, fresh assertion per disposition와 replay/tamper/fail-closed
  contract를 추가했다.
- P1-02: KR Supreme Court/Internet Registry와 relevant US formation-state
  registry만 legal-jurisdiction decisive field owner로 허용하고, exact
  human-assisted verified-document ingestion과 source×scope×maximum-weight
  matrix를 추가했다.
- P1-03: exact source locator/document reference/raw claim value와 candidate
  application disposition을 분리한 immutable
  `AuthorityEvidenceApplication`을 추가하고 bundle membership을 application
  기준으로 바꿨다.
- P1-04: immutable `AuthoritySourcePolicy`, production admission/fixture-taint
  boundary와 scenario별 exact write/rekey/approval acceptance matrix를
  추가했다.
- P2-01: reviewed SHA에는 GitHub status/workflow run이 없다. local
  documentation safety gates만 Codex local evidence로 구분하며 CI evidence를
  만들거나 추정하지 않는다.
- 이 remediation 기록 당시에는 P1 closure나 PASS가 아니었다. 당시 ADR-014
  상태는 `PROPOSED — AWAITING GPT INDEPENDENT RE-REVIEW`였고
  CP3-C2-B implementation, CP3-C2-C, CP3-D는 `NOT STARTED`였다.

### 독립 재검토·사용자 승인 closeout 기록 — 2026-08-26

- Independently reviewed SHA:
  `f3a7a3c4cc99de9cd9656544c1b29e3d03df6911`.
- GPT independent re-review verdict: `PASS WITH CLOSEOUT CONDITION`.
- P0: `0`.
- P1: `0`.
- P1-01 authenticated-human trust root: `CLOSED`.
- P1-02 legal-jurisdiction authority: `CLOSED`.
- P1-03 authority provenance/application: `CLOSED`.
- P1-04 production source admission / fixture isolation: `CLOSED`.
- P2-01: `NON-BLOCKING — GitHub CI execution evidence absent`. Reviewed SHA에
  GitHub commit status/workflow run은 없으며 local diff/secret/policy 결과는
  Codex local evidence일 뿐 GitHub CI evidence가 아니다.
- User decision: revised CP3-C2-B1 runtime contract와 ADR-014를 명시적으로
  승인했다.
- Approval scope: CP3-C2-B1 documentation closeout only.
- ADR-014 acceptance는 CP3-C2-B implementation 시작 권한이 아니다.
- CP3-C2-B implementation:
  `NOT STARTED — REQUIRES SEPARATE USER START APPROVAL`.
- CP3-C2-C와 CP3-D는 `NOT STARTED`, automatic checkpoint progression은
  `PROHIBITED`다.

### 대안

1. 기존 `MappingStatus` 확장: Phase 1/CP3-B 계약 의미를 바꾸고 issuer/security
   축을 다시 합치므로 거부한다.
2. `ProviderIdentityMapping`에 nullable security와 approval fields 추가: 기존
   VERIFIED invariant와 0002/0003 무결성을 깨므로 거부한다.
3. 승인 row를 in-place update/delete: correction/revocation 감사 이력을 잃어
   거부한다.
4. corp_code/CIK global unique insert의 첫 성공을 canonical winner로 사용:
   상충 evidence를 숨기므로 거부한다.
5. 비인증 local flag/CLI 확인을 human approval로 간주: ADR-013의
   authenticated-human 조건을 충족하지 않아 거부한다.

### 영향

CP3-C2-B1은 문서 설계만 작성했고 independent re-review와 명시적 사용자
승인으로 contract documentation을 닫았다. ADR-014 acceptance 자체는 runtime
구현 권한이 아니었고, B1 closeout 시점의 CP3-C2-B implementation은
`NOT STARTED — REQUIRES SEPARATE USER START APPROVAL`이었다. 이후 별도 사용자
승인에 따른 제한된 B2-A 진입은 아래 구현 진입 기록으로 분리한다.

향후 승인된 구현은 canonical issuer insert-or-verify와 issuer-only link를 한
transaction으로 수행할 수 있지만, canonical Security 또는 VERIFIED provider
mapping을 만들 수 없다. Local authentication/reauthentication은 이 proposal의
`issuer-steward-webauthn/0.1.0`보다 약화할 수 없고 구현·독립검증은 별도
CP3-C2-B user start authorization 뒤에만 가능하다.

### 마이그레이션·롤백

후속 migration 후보로 승인된 설계는
`0005_phase_02_cp3_c2_b_issuer_authority`이며 down revision은 정확히
`0004_phase_02_cp3_c1_security_master`다. source policy, reviewer public
credential/challenge/authentication audit, evidence/application/observation/
relation, bundle/membership, identifier claim, decision, approval event,
issuer-only link와 rebuildable head table만 additive로 제안했다. B1에서는
migration file 생성·적용 모두 0이다.

`0001`~`0004` 수정, 기존 row backfill/rebuild/rekey, provider/canonical history
삭제는 금지한다. 실제 운영 rollback은 신규 write 중지와 ledger 보존이
원칙이며 destructive downgrade는 backup/restore 검증과 별도 승인 없이 하지
않는다.

### CP3-C2-B2-A 구현 진입 기록 — 2026-08-27

- 사용자가 CP3-C2-B implementation 시작을 별도로 명시 승인했다.
- 승인된 이번 terminal scope는 `CP3-C2-B2-A — Authority Ledger & Additive
  0005 Foundation`뿐이다.
- B2-A는 approved B1 semantic contract, 21-table additive `0005`, immutable
  append-only enforcement와 low-level insert-or-verify repository foundation만
  구현한다.
- `0001`~`0004`, 기존 provider/canonical row와 public `MappingStatus` 의미는
  변경하지 않는다.
- reviewer/WebAuthn/challenge/approval/link schema는 approved later-phase
  foundation으로 포함할 수 있지만 operational WebAuthn verification, approval
  execution, canonical issuer promotion과 link-head mutation은 B2-A에서 수행하지
  않는다.
- canonical Issuer write, canonical Security write,
  `ProviderIdentityMapping(VERIFIED)` write, provider identity rekey와 automatic
  promotion은 각각 `0`이다.
- CP3-C2-B implementation: `IN PROGRESS`.
- CP3-C2-B2-A initial state: `IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW`.
- CP3-C2-B2-B, CP3-C2-B2-C, CP3-C2-B2-D, CP3-C2-C와 CP3-D:
  `NOT STARTED`.
- Automatic checkpoint progression: `PROHIBITED`.

### CP3-C2-B2-A independent-review remediation 기록 — 2026-08-27

- Reviewed SHA: `05eb70d8dfe488563757107c0697f1a7708018c9`.
- GPT independent review: `CHANGES REQUIRED`, P0 `0`, P1 `3`, P2 `1`.
- P1-01: correction successor decision은 predecessor와 같은
  `provider_security_identity_id` authority subject를 유지하면서 새 immutable
  bundle과, authoritative correction이 요구하면 새 `proposed_issuer_id`를 가질
  수 있다. Predecessor existence/self-reference/exact successor bundle 검증과
  unique predecessor-child constraint는 유지해 fork를 막고 unrelated-provider
  chain graft를 거부한다. Old bundle/decision은 update/delete하지 않는다.
- P1-02: B2-A observation membership은 exact CP3-C1 bridge 증명이 아니다.
  B2-B positive source-admission/bridge/decision engine이 구현되고 독립 검토될
  때까지 low-level repository의 모든 `READY_FOR_MANUAL_REVIEW` persistence는
  typed `REVIEW_READY_ENGINE_NOT_IMPLEMENTED`로 fail closed한다.
- P1-03: `reviewer_webauthn_credentials`는 mutable current counter 대신 exact
  capability와 immutable nullable `registration_sign_count`만 저장한다.
  `reviewer_authentication_events`는 matching capability,
  `previous_sign_count`, `asserted_sign_count`, `counter_verified`를 append-only로
  저장한다. Supported VERIFIED counter는 strict advancement를 요구하고,
  equality/rollback은 REJECTED audit만 가능하다. No-counter capability는 모든
  count를 null로 유지한다. Restart 후 current counter는 registration value와
  unique linear VERIFIED event chain에서 재구성하며 credential row update는 0이다.
- P2: GitHub CI evidence status는 별도 확인 전까지 주장하지 않는다. Local gate
  결과는 LOCAL Codex evidence만이다.
- ADR-013과 ADR-014는 `ACCEPTED`, CP3-C2-B1은
  `PASS — CONTRACT APPROVED AND CLOSED`로 유지한다.
- CP3-C2-B implementation: `IN PROGRESS`.
- CP3-C2-B2-A: `REMEDIATED — AWAITING GPT INDEPENDENT RE-REVIEW`.
- CP3-C2-B2-B/B2-C/B2-D, CP3-C2-C, CP3-D: `NOT STARTED`.
- Automatic checkpoint progression: `PROHIBITED`.
- 이 기록은 B2-A PASS 또는 B2-B 시작 승인이 아니다.

### CP3-C2-B2-A independent re-review / documentation closeout 기록 — 2026-08-27

- Reviewed SHA: `57e9bbbf2a1fd117b8e31c7288f2f08475c7e4ae`.
- GPT independent re-review: `PASS WITH CLOSEOUT CONDITION`, P0 `0`, P1
  `0`, P2 `1`.
- P1-01 `CLOSED`: same provider authority subject의 corrected evidence는 새
  immutable bundle과 successor decision을 만들 수 있고 predecessor fork와
  unrelated-provider graft는 계속 거부된다.
- P1-02 `CLOSED`: separately gated B2-B positive bridge/decision engine이
  구현되고 독립 검토되기 전에는 모든 B2-A `READY_FOR_MANUAL_REVIEW`
  persistence가 typed `REVIEW_READY_ENGINE_NOT_IMPLEMENTED`로 fail closed한다.
- P1-03 `CLOSED`: immutable registration counter와 append-only
  previous/asserted authentication-event history로 current WebAuthn counter를
  재구성한다. rollback/equality/gap/fork는 fail closed하고 no-counter
  authenticator는 advancement를 만들지 않는다.
- P2-01은 `NON-BLOCKING — GitHub CI execution evidence absent`다. Local Codex
  gate 결과는 GitHub CI evidence가 아니며 이 closeout에서 CI/workflow를
  만들지 않는다.
- 사용자는 이 documentation closeout을 요청했다. 이 요청은 B2-B/B2-C/B2-D,
  CP3-C2-C, CP3-D 또는 automatic progression 시작 승인이 아니다.
- ADR-013과 ADR-014는 `ACCEPTED`, CP3-C2-B1은
  `PASS — CONTRACT APPROVED AND CLOSED`로 유지한다.
- CP3-C2-B implementation: `IN PROGRESS`.
- CP3-C2-B2-A: `PASS — CLOSED`.
- CP3-C2-B2-B: `NOT STARTED — REQUIRES SEPARATE USER START APPROVAL`.
- CP3-C2-B2-C/B2-D, CP3-C2-C, CP3-D: `NOT STARTED`.
- Additive `0005`는 current B2-A migration이며 persistent/runtime application은
  `0`; `0006` creation은 `0`, `0001`~`0004`는 unchanged다.
- Automatic checkpoint progression: `PROHIBITED`.

### CP3-C2-B2-B implementation entry record — 2026-08-27

- The user explicitly authorized only `CP3-C2-B2-B — Production Source
  Admission, Exact Issuer Bridge, Collision/Freshness Evaluation, and Machine
  Decision Engine` from starting SHA
  `dd86aeb195222fa94e9bd0ec48a5f1d942825c14`.
- Production authority policy is now an immutable server-owned exact registry.
  A caller/parser cannot register an unlisted namespace/scope/role/version,
  raise a weight, supply a jurisdiction, or use a wildcard state registry.
  Fixture/test/synthetic lineage remains permanently zero-authority.
- KR positive evaluation requires exact OpenDART corp-code authority, current
  overview `jurir_no`, a verified domestic IROS record with the same official
  registration reference, and an exact non-name CP3-C1 provider bridge. KRX,
  market, currency, language, `corp_cls`, or stock code alone owns no legal
  jurisdiction.
- US positive evaluation requires accepted SEC issuer-registrant CIK/role and
  filing evidence, a current registrant-status check, an individually admitted
  domestic formation-state registry record, exact state-entity reconciliation,
  and exact non-name CP3-C1 provider lineage. Login/agent/accession provenance
  stays structured weight-zero provenance.
- The engine reconstructs stored correction/revocation heads, distinguishes
  historical authority facts from 24-hour repository latest-status freshness,
  and scans current identifier claims, positive applications, canonical
  identifiers, and provider collision/quarantine state without choosing a
  first writer.
- `BEGIN IMMEDIATE` serializes positive evaluation and transaction-time
  revalidation. Only the server-owned engine path may persist
  `READY_FOR_MANUAL_REVIEW`; the generic repository continues to raise typed
  `REVIEW_READY_ENGINE_NOT_IMPLEMENTED` for arbitrary READY writes.
- Machine states remain exactly `UNRESOLVED`, `READY_FOR_MANUAL_REVIEW`,
  `STALE`, and `REVIEW_REQUIRED`. B2-B implements no human disposition,
  WebAuthn operation, canonical/link write, or live collection.
- Migrations `0001`–`0005` are unchanged and `0006` is not created. Local
  implementation tests use disposable databases only; persistent/runtime
  application of `0005` remains `0`.
- CP3-C2-B implementation: `IN PROGRESS`.
- CP3-C2-B2-A: `PASS — CLOSED`.
- CP3-C2-B2-B: `IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW`.
- CP3-C2-B2-C/B2-D, CP3-C2-C, CP3-D: `NOT STARTED`.
- Automatic checkpoint progression: `PROHIBITED`.
- This record is Codex self-QA and does not declare GPT PASS or authorize a
  later checkpoint.

### CP3-C2-B2-B independent-review remediation record — 2026-08-27

- GPT independent review of SHA
  `d4f84c4bfb83f2396161eea913f2c119ecb17dac` returned `CHANGES REQUIRED`,
  P0 `0`, P1 `5`, P2 `1`. P2 is the non-blocking absence of GitHub CI
  execution evidence; LOCAL Codex results are not GitHub CI evidence.
- P1-01: the generic ledger repository no longer accepts caller-selected modes
  or any new production policy/evidence/observation/relation. It returns typed
  `PRODUCTION_AUTHORITY_ADMISSION_UNAVAILABLE` until a separately authorized
  trusted ingestion mechanism exists. Decision tests use only a helper under
  `tests/` to seed an explicitly pre-admitted snapshot; production code does
  not import or expose that helper.
- P1-02: `evaluated_at` is removed from the evaluation request. The engine reads
  an aware UTC server clock after `BEGIN IMMEDIATE`; deterministic tests inject
  the clock into the engine constructor.
- P1-03: request evidence/observation memberships are seeds, not completeness
  assertions. The engine discovers all relevant current provider observations,
  candidate authority facts, current relation heads and prior exact
  applications inside the writer transaction. Incompatible co-current KR or US
  official facts and omitted unsafe provider observations block READY.
- P1-04: an existing canonical row is not a collision solely when its issuer ID
  is the deterministic proposed ID and its jurisdiction, authoritative
  identifier, immutable payload and normalized hash are all exact. Different or
  inconsistent canonical subjects remain fail-closed conflicts and read-only.
- P1-05: duplicate corp-code/registrant-CIK evaluation identifies all affected
  provider subjects and appends `REVIEW_REQUIRED` successors to any impacted
  READY leaves in the same `BEGIN IMMEDIATE` transaction. Old bundles and
  decisions remain immutable; no first-writer winner or human disposition is
  created.
- Migrations `0001`–`0005` remain byte-identical and `0006` is not created.
  Canonical Issuer/Security writes, VERIFIED mapping writes, provider rekeys,
  WebAuthn/human approval/link execution, credentials, and live requests remain
  `0`.
- CP3-C2-B implementation: `IN PROGRESS`.
- CP3-C2-B2-A: `PASS — CLOSED`.
- CP3-C2-B2-B: `REMEDIATED — AWAITING GPT INDEPENDENT RE-REVIEW`.
- CP3-C2-B2-C/B2-D, CP3-C2-C, CP3-D: `NOT STARTED`.
- Automatic checkpoint progression: `PROHIBITED`.
- This remediation record does not declare GPT PASS and does not authorize a
  later checkpoint.

---

## 새 결정 기록 양식

```md
## ADR-XXX — 제목

- 상태: PROPOSED | ACCEPTED | REJECTED | SUPERSEDED
- 제안일:
- 결정일:

### 문제

### 제안 또는 결정

### 대안

### 영향

### 마이그레이션·롤백
```
