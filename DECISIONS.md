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

### CP3-C2-B2-B second independent-review remediation record — 2026-08-27

- GPT independent re-review of SHA
  `722a5036d7d05ad6b8de0314ff6ac5ee8dafacc2` returned `CHANGES REQUIRED`,
  P0 `0`, P1 `2` new findings, P2 `1`. P1-01 through P1-05 remain independently
  verified `CLOSED`; P2 remains the non-blocking absence of GitHub CI execution
  evidence.
- P1-06: `LEGAL_NAME` is now a required positive bundle scope. KR requires a
  current admitted OpenDART company-overview name and decisive verified IROS
  name for the same exact registry/provider path. US requires accepted-filing
  SEC name evidence and the decisive exact formation-state registry name for
  the same filing/entity path. Only exact NFC equality or an immutable,
  conflict-free, linear `CORRECTS`/`SUPERSEDES` history owned by the decisive
  legal-name registry reconciles a difference. Provider names, symbols,
  tickers, fuzzy matching, case folding, punctuation/suffix removal, and
  whitespace heuristics have zero reconciliation authority.
- P1-07: accepted SEC filing accession/document identity remains exact
  provenance but is excluded from the stable issuer/entity compatibility key.
  Every filing independently requires same-document registrant CIK, issuer
  role, state/entity bridge and legal-name facts. Compatible filings with the
  same CIK/formation state/state entity number can coexist across accessions;
  incompatible state/entity facts remain conflicts. A former provider symbol
  is accepted only when authority-supplied acceptance chronology produces one
  deterministic latest bridge matching current CP3-C1 provider lineage.
  Historical filing age remains separate from the current latest-status
  freshness check.
- Generic production admission, generic READY persistence, the server UTC
  clock, complete current-state discovery, same-canonical-subject semantics,
  impacted READY invalidation and `BEGIN IMMEDIATE` remain unchanged and
  fail-closed.
- Migrations `0001`–`0005` remain byte-identical; `0006` creation is `0`.
  Canonical Issuer/Security writes, VERIFIED mapping writes, provider rekeys,
  WebAuthn/human approval/link execution, credentials, and live requests remain
  `0`.
- CP3-C2-B implementation: `IN PROGRESS`.
- CP3-C2-B2-A: `PASS — CLOSED`.
- CP3-C2-B2-B: `REMEDIATED — AWAITING GPT INDEPENDENT RE-REVIEW`.
- CP3-C2-B2-C/B2-D, CP3-C2-C, CP3-D: `NOT STARTED`.
- Automatic checkpoint progression: `PROHIBITED`.
- This second remediation record is LOCAL Codex self-QA and does not declare
  GPT PASS or authorize a later checkpoint.

### CP3-C2-B2-B third independent-review remediation record — 2026-08-27

- GPT second independent re-review of SHA
  `8093ee9389d4f7ae716482a87de5eae252e08eff` returned `CHANGES REQUIRED`,
  P0 `0`, P1 `2` new findings, P2 `1`. P1-01 through P1-07 remain independently
  verified `CLOSED`; P2 remains the non-blocking absence of GitHub CI execution
  evidence.
- P1-08: a decisive registry legal-name history member is usable only after its
  own exact official source document independently proves the same legal-entity
  subject as the current decisive registry name. KR binds every IROS history
  document to the same exact `corporate_registration_reference`/`jurir_no`
  through its decisive registry bridge and domestic-jurisdiction companion
  facts. US binds every field-owner history document to the same exact state
  registry namespace, formation state, and `state_entity_number` through its
  domestic-formation jurisdiction fact. A `CORRECTS`/`SUPERSEDES` edge by
  itself, another entity in the same namespace, source/name/role similarity,
  provider fields, and insertion order cannot establish subject sameness.
- P1-09: reconciliation now evaluates every relevant current supporting
  OpenDART or accepted SEC legal-name fact. Each fact retains its exact
  document/candidate/bridge provenance and must be NFC-exact to the current
  decisive name or appear in the same-subject decisive registry's immutable
  conflict-free `CORRECTS`/`SUPERSEDES` history. Multiple explained former and
  current names may coexist; one unexplained or cross-entity name makes the
  scope `CONFLICT`. No case folding, fuzzy matching, punctuation/suffix removal,
  whitespace heuristics, provider name, or ticker authority was added.
- Historical SEC filing age remains separate from the current latest-status
  freshness gate. Every accepted filing still independently requires exact
  same-document CIK, issuer role, stable state/entity bridge, and legal name.
- Generic production admission, tests-only snapshot isolation, generic READY
  rejection, the engine-owned UTC clock, complete current-state discovery,
  same-canonical-subject handling, impacted READY invalidation, and the
  `BEGIN IMMEDIATE` writer boundary remain unchanged and fail closed.
- Migrations `0001`–`0005` remain byte-identical; `0006` creation is `0`.
  Canonical Issuer/Security writes, VERIFIED mapping writes, provider rekeys,
  WebAuthn/human approval/link execution, credentials, and live requests remain
  `0`.
- LOCAL Codex self-QA: B2-B targeted `89`, B2-A authority `69`, full backend
  `702`, frontend `43`, E2E `2`, with migration/idempotency/lint/typecheck/
  OpenAPI/build/safety gates passing. These results are not GitHub CI evidence.
- CP3-C2-B implementation: `IN PROGRESS`.
- CP3-C2-B2-A: `PASS — CLOSED`.
- CP3-C2-B2-B: `REMEDIATED — AWAITING GPT INDEPENDENT RE-REVIEW`.
- CP3-C2-B2-C/B2-D, CP3-C2-C, CP3-D: `NOT STARTED`.
- Automatic checkpoint progression: `PROHIBITED`.
- This third remediation record does not declare GPT PASS or authorize a later
  checkpoint.

### CP3-C2-B2-B independent-review closeout record — 2026-08-27

- GPT independently reviewed SHA
  `d81148636c237ac8ab6b85e930d3926fae19c855` and returned `PASS WITH
  CLOSEOUT CONDITION`, P0 `0`, P1 `0`, P2 `1`.
- P1-01 through P1-09 are `CLOSED`. Production authority admission and generic
  repository READY persistence remain fail closed. The machine maximum positive
  state remains `READY_FOR_MANUAL_REVIEW`.
- The server-owned aware UTC clock, complete current-state discovery, exact KR/
  US provider-to-issuer bridges, exact same-subject legal-name history,
  all-supporting-name reconciliation, collision detection and transaction-wide
  impacted-READY invalidation remain enforced.
- P2-01 is `NON-BLOCKING — GitHub CI execution evidence absent`. LOCAL Codex
  test and documentation-gate results are not GitHub CI evidence.
- ADR-013 and ADR-014 remain `ACCEPTED`; CP3-C2-B1 remains `PASS — CONTRACT
  APPROVED AND CLOSED`.
- CP3-C2-B implementation remains `IN PROGRESS`; CP3-C2-B2-A and CP3-C2-B2-B
  are `PASS — CLOSED`.
- CP3-C2-B2-C, CP3-C2-B2-D, CP3-C2-C and CP3-D remain `NOT STARTED`.
  B2-C requires independent verification of this closeout commit and a new,
  separate explicit user start approval.
- Canonical Issuer writes, canonical Security writes,
  `ProviderIdentityMapping(VERIFIED)` writes, provider rekeys, automatic final
  promotion, human approval/WebAuthn operational execution, issuer-authority
  link execution, link-head mutation, credentials, live authority requests and
  Toss live requests remain `0`.
- Migrations `0001`–`0005` remain byte-identical to the reviewed SHA; migration
  changes, persistent/runtime application of `0005`, and `0006` creation remain
  `0`.
- Automatic checkpoint progression remains `PROHIBITED`. This documentation
  closeout does not authorize or start any later checkpoint.

---

## ADR-015 — WebAuthn Enrollment and Credential-Operation Ledger Amendment

- 상태: `ACCEPTED`
- 제안일: `2026-08-28`
- 결정일: `2026-08-28`
- 상세 설계:
  `plans/PHASE_02_CP3_C2_B2_C_SCHEMA_REMEDIATION.md`

### 문제

사용자가 CP3-C2-B2-C 시작을 별도로 승인했지만, authoritative starting SHA
`60f2805d2390c91a026b3381877006be9000dedb`의 frozen `0005`를 B1 runtime
contract와 대조한 결과 구현 전에 두 schema blocker가 확인됐다.

- SG-01: `reviewer_principals`와 credential/event table은 존재하지만, 유효한
  credential이 생기기 전 server-created Windows-owner-SID-bound first-enrollment
  bootstrap, WebAuthn create challenge, expiry와 실패를 포함한 exactly-one
  terminal consumption을 관계형으로 기록할 수 없다.
- SG-02: 기존 `reviewer_authentication_events`는 issuer approval challenge,
  decision, bundle과 issuer disposition에 필수 결합되어 있다. 따라서 active
  credential의 fresh assertion이 `ADD_CREDENTIAL`/`REPLACE_CREDENTIAL`을
  승인했다는 사실과 그 assertion의 signature-counter advancement를 issuer
  disposition을 위조하지 않고 기록할 수 없다.

`payload_json`, process memory, browser storage, fake issuer decision/challenge,
synthetic credential row 또는 caller SID는 이 공백을 메우는 권한 근거가
아니다.

독립 2차 검증은 issuer `SUPERSEDED`를 schema blocker에서 제외했다. 기존
`0005`는 old `APPROVED -> SUPERSEDED -> successor APPROVED` link sequence를
두 개의 별도 authenticated disposition과 하나의 `BEGIN IMMEDIATE` transaction/
최종 head CAS로 표현할 수 있다.

첫 제안 SHA `fd0535fdd022f0171a63a83cb2861e924a92da64`에 대한 GPT 독립 검토는
SG-01/SG-02 진단과 additive 옵션 A를 원칙적으로 수용했으나 `CHANGES
REQUIRED`, P0 `0`, P1 `2`, P2 `1` non-blocking을 반환했다. P1-SR-01은 최종
active credential의 authenticated revoke를 거부한 점, P1-SR-02는 state-hash
계약과 server/SQLite 검증 경계가 불완전했던 점이다. 당시 revision은 두
finding을 remediate했지만 자체적으로 close하지 않고 GPT independent
re-review를 기다렸다.

GPT independent re-review of SHA
`e016fc59973e5c81181e7cf20c1ebe3d7aada043` returned `CHANGES REQUIRED`, P0
`0`, P1 `1`, P2 `1` non-blocking. It verified P1-SR-01 and P1-SR-02 `CLOSED`
and identified P1-SR-03: a failed/expired terminal challenge consumption could
be committed without the operation's unique terminal outcome, wedging the
predecessor/successor chain. The final revision below remediates but does not
self-close P1-SR-03 and awaits independent re-review.

GPT independently reviewed the resulting SHA
`f73115ea1182e27259787460307a01b4c3874312` and returned `PASS WITH CLOSEOUT
CONDITION`, P0 `0`, P1 `0`, P2 `1` non-blocking because GitHub CI execution
evidence is absent. SG-01, SG-02, P1-SR-01, P1-SR-02 and P1-SR-03 were closed.
The user then explicitly accepted ADR-015 on `2026-08-28`. This acceptance
approves the six-table schema architecture in
`plans/PHASE_02_CP3_C2_B2_C_SCHEMA_REMEDIATION.md`; it does not declare an
implementation PASS or authorize B2-C runtime.

### 제안

- 옵션 A를 선택한다: 기존 `0005` table을 rebuild/alter하지 않고 future
  `0006_phase_02_cp3_c2_b2_c_reviewer_operations`가 여섯 개의 append-only
  table을 additive로 제안한다.
  - `reviewer_credential_operations`
  - `reviewer_credential_operation_challenges`
  - `reviewer_credential_operation_challenge_consumptions`
  - `reviewer_credential_operation_authentication_events`
  - `reviewer_webauthn_credential_event_authorizations`
  - `reviewer_credential_operation_outcomes`
- Operation은 `FIRST_ENROLLMENT|ADD_CREDENTIAL|REPLACE_CREDENTIAL|
  REVOKE_CREDENTIAL`만 허용한다. Recovery/reset/force/override는 없다.
- 현재 active credential은 자기 자신을 포함해 최종 credential을 인증된
  `REVOKE_CREDENTIAL`로 폐기할 수 있다. 최종 폐기 결과는 정확한 empty active
  set이다. 그 뒤 issuer approval/add/replace/further revoke는 fail closed하고,
  successful registration history 때문에 first enrollment가 재개되지 않으며
  recovery/reset은 계속 없다. 운영 지속이 필요하면 최종 폐기 전에 backup
  credential을 추가해야 한다.
- Challenge purpose는 `REGISTRATION_CREATE`와
  `AUTHORIZATION_ASSERTION`으로 issuer approval과 별도 type/FK namespace를
  사용한다. Fresh 32-byte OS-CSPRNG challenge digest/binding, exact
  principal/role/SID/state/RP/origin/policy와 5분 이하 expiry를 저장한다.
- Challenge consumption FK를 unique로 두어 성공/실패 모두 정확히 한 번
  terminal consumption한다.
- Operation과 최초 required challenge는 같은 `BEGIN IMMEDIATE` issuance
  transaction에서 만들고 circular deferred exact FK로 서로 결합한다. 따라서
  challenge/outcome/safe continuation이 없는 orphan operation은 commit할 수 없다.
- 모든 failure와 모든 final-step success는 operation-terminal이다. Consumption은
  preallocated exact outcome/result/state tuple을 deferred FK로 가리키고 outcome은
  exact consumption ID/content/result를 역으로 가리킨다. 실패 시 consumption,
  attributable rejected audit, unchanged-state outcome을 commit한 뒤에만 typed
  failure를 반환한다. `EXPIRED -> EXPIRED`, invalid signature/UP/UV/registration
  `-> REJECTED`, binding/origin-RP/counter/replay/other closed failure
  `-> FAILED_CLOSED`의 closed mapping을 사용한다.
- 유일한 nonterminal consumption은 ADD/REPLACE의 successful
  `AUTHORIZATION_ASSERTION`이다. 그 consumption, immutable `VERIFIED` counter
  event와 하나의 `REGISTRATION_CREATE` challenge가 같은 transaction에서 exact
  deferred FK로 결합된다. Assertion은 재사용 가능한 session이 아니고 그
  registration challenge의 5분 expiry를 넘겨 권한을 유지하지 않는다.
- ADD/REPLACE authorization이 성공한 뒤 registration이 실패하면 verified
  counter event는 보존되고 lifecycle event/authorization은 0이며 failed outcome은
  unchanged credential state를 기록한다. Fresh retry는 그 failed outcome을
  predecessor로 하는 새 operation/challenge이고 advanced counter history를
  포함해 재구성한다.
- Credential-operation authentication event는 same-principal active public
  credential, exact signature/RP/origin/UP/UV와 nullable prior/asserted counter를
  관계형 열로 보존한다. Current counter column은 만들지 않는다.
- Counter reconstruction은 immutable registration count에서 시작해 issuer
  approval authentication과 credential-operation authentication의 relational
  `VERIFIED` rows를 합친 one linear chain으로 수행한다. Additive insert guards가
  equality/rollback/gap/fork와 동시 writer를 fail closed한다.
- 기존 `reviewer_webauthn_credentials` 및 credential lifecycle event의 future
  insert는 deferred exact proof row와 insert guard를 요구한다.
  `REGISTERED|REVOKED|SUPERSEDED` event마다 성공한 bootstrap/operation
  authorization이 정확히 하나 연결되고, authorization은 exact successful
  operation outcome/pre-state/post-state tuple에도 deferred FK로 결합된다.
- One active steward, exact principal/SID composite FK, one operation root,
  unique predecessor child, exact credential-event root/subject와 operation
  outcome binding을 additive unique index/check/FK/trigger로 검증한다.
- Credential ownership/lifecycle state는
  `reviewer-credential-state/0.1.0`으로 versioning한다. Exact principal ID,
  principal content hash, server-resolved SID hash, role과 정렬된 active
  credential/lifecycle-leaf semantic fields를 canonical UTF-8/NFC JSON으로
  직렬화해 SHA-256을 계산한다. Empty state는 동일 principal binding과 빈
  `active_credentials` 배열을 갖는 정확한 preimage다. Counter 값과 audit
  timestamp/row identity는 제외되며 counter advancement만으로 state hash가
  바뀌지 않는다.
- Trusted server가 같은 SQLite `BEGIN IMMEDIATE` 안에서 모든 lifecycle row를
  다시 읽어 pre/post state hash를 계산하고 challenge/consumption/outcome을
  revalidate한다. SQLite는 relational membership, exact copy, chain,
  predecessor, event pattern과 authorization/outcome 결합만 검증한다. 승인된
  SHA-256 UDF가 없으므로 trigger가 aggregate SHA-256을 계산한다고 가정하지
  않는다. Existing issuer-authentication path에도 current authorized
  `REGISTERED` lifecycle leaf의 server revalidation과 additive insert guard를
  요구해 final revoke 뒤 남아 있는 immutable public credential row가 approval
  authority로 재사용되지 못하게 한다.
- 모든 새 table은 append-only다. Private key, PIN, biometric, password,
  cookie, bearer token, raw challenge nonce와 reusable Windows credential은
  저장하지 않는다.

### 대안

- `0005` reviewer/authentication table rebuild: 거부. 이미 승인된 issuer
  disposition 의미와 credential administration 의미를 섞고 migration 위험을
  늘린다.
- Existing table rebuild와 new table 조합: 거부. Deferred companion FK와
  additive insert guard로 mandatory authorization을 검증할 수 있어 rebuild가
  불필요하다.
- JSON/in-memory-only bootstrap 또는 issuer challenge 재사용: 거부. Terminal
  consumption, FK purpose separation, restart/concurrency audit와 counter chain을
  증명하지 못한다.

### 영향

- ADR-013과 ADR-014의 역사적 의미와 `0001`–`0005` byte content는 바뀌지
  않는다.
- ADR-015는 `ACCEPTED`지만 migration/runtime 권한이 아니다. Separately
  authorized implementation work later discovered IG-01/IG-02 and stopped
  without changing files or creating `0006`.
- 이 ADR-015 closeout 시점의 CP3-C2-B2-C는 implementation gap에서
  blocked였다. ADR-016 acceptance와 separate `0006` authorization 이후의
  current state는 ADR-016에 기록한다.
- CP3-C2-B2-D, CP3-C2-C와 CP3-D는 `NOT STARTED`이고 automatic progression은
  `PROHIBITED`다.
- GitHub CI execution evidence 부재는 non-blocking P2이며 LOCAL 문서 검사는
  GitHub CI evidence가 아니다.

### 마이그레이션·롤백

- 이 문서 작업에서 `0006` 파일 생성/적용은 `0`이다.
- Future `0006`은 exact down revision
  `0005_phase_02_cp3_c2_b_issuer_authority`를 사용하고 table rebuild 없이 새
  table/index/trigger만 추가한다.
- Upgrade는 `0001`–`0005` hash, object collision, unexpected pre-existing
  reviewer lineage를 fail closed로 검사하며 synthetic backfill을 금지한다.
- Downgrade는 disposable empty ledger에서만 새 object를 역순 제거한다.
  Non-empty audit ledger의 destructive downgrade는 별도 승인 없이 거부한다.

---

## ADR-016 — Reviewer Operation Exact SQLite Binding Amendment

- 상태: `ACCEPTED`
- 제안일: `2026-08-28`
- 결정일: `2026-08-28`
- 선행 결정: ADR-015 `ACCEPTED`
- 상세 계약:
  `plans/PHASE_02_CP3_C2_B2_C_SCHEMA_REMEDIATION.md`

### 문제

ADR-015를 충실히 구현하려던 separately authorized `0006` 작업은 SQLite DDL을
작성하기 전에 두 implementation-discovered gap에서 fail closed했다. 파일은
변경되지 않았고 `0006`은 생성·적용되지 않았다. GPT가 두 gap을 독립 확인했다.

1. IG-01: closed enum `authorization_kind`가
   `BOOTSTRAP_REGISTRATION|AUTHORIZED_REGISTRATION`만 명시해 approved
   `REPLACE_CREDENTIAL + SUPERSEDED`와 `REVOKE_CREDENTIAL + REVOKED` row에 쓸
   exact token이 없었다.
2. IG-02: approved parent key
   `uq_reviewer_credential_operations_exact_binding`은 operation ID/hash,
   principal ID, role, principal content hash, OS-owner SID hash, operation
   type와 expected state hash의 exact 8열인데 authorization/outcome child
   schema에는 role/principal hash/SID hash 열이 없어 그 FK를 구현할 수 없었다.

ADR-015의 승인 자체와 SG-01, SG-02, P1-SR-01, P1-SR-02, P1-SR-03 closure는
유지한다. 이 문제는 approved architecture를 폐기하거나 과거 결정을
미승인으로 되돌리는 이유가 아니라 exact SQLite binding의 좁은 additive
amendment가 필요한 이유다.

### 제안

ADR-016의 범위는 다음 세 항목뿐이다.

1. `reviewer_webauthn_credential_event_authorizations.authorization_kind`를
   다음 exact closed enum으로 고정한다.
   - `BOOTSTRAP_REGISTRATION`
   - `AUTHORIZED_REGISTRATION`
   - `AUTHORIZED_SUPERSESSION`
   - `AUTHORIZED_REVOCATION`
2. `reviewer_webauthn_credential_event_authorizations`와
   `reviewer_credential_operation_outcomes` 양쪽에 다음 copied immutable
   server-owned trust columns를 추가 제안한다.
   - `reviewer_role VARCHAR(32) NOT NULL`
   - `principal_content_hash VARCHAR(71) NOT NULL`
   - `os_owner_sid_hash VARCHAR(71) NOT NULL`
3. 두 row의 immutable content-hash preimage가 위 세 semantic relational
   column을 모두 포함하도록 exact hash contract를 갱신한다. Audit timestamp와
   `payload_json`은 기존처럼 제외하며 content-hash cycle을 만들지 않는다.

허용되는 operation/event/authorization 조합은 정확히 다음 다섯 개다.

| `operation_type` | `event_type` | `authorization_kind` |
|---|---|---|
| `FIRST_ENROLLMENT` | `REGISTERED` | `BOOTSTRAP_REGISTRATION` |
| `ADD_CREDENTIAL` | `REGISTERED` | `AUTHORIZED_REGISTRATION` |
| `REPLACE_CREDENTIAL` | `REGISTERED` | `AUTHORIZED_REGISTRATION` |
| `REPLACE_CREDENTIAL` | `SUPERSEDED` | `AUTHORIZED_SUPERSESSION` |
| `REVOKE_CREDENTIAL` | `REVOKED` | `AUTHORIZED_REVOCATION` |

모든 다른 조합은 CHECK/insert guard로 거부한다. Generic
`AUTHORIZED_LIFECYCLE`, free-form token과 `payload_json` authority는 없다.

두 child table은 exact ordered tuple

```text
reviewer_credential_operation_id,
operation_content_hash,
reviewer_principal_id,
reviewer_role,
principal_content_hash,
os_owner_sid_hash,
operation_type,
expected_credential_state_hash
```

을 approved parent key
`uq_reviewer_credential_operations_exact_binding`의 동일 순서에
`DEFERRABLE INITIALLY DEFERRED` FK로 결합한다. `reviewer_role`은
`LOCAL_DATA_STEWARD`로 고정하고 두 hash는 exact `sha256:<64 lowercase hex>`
형식으로 검사한다. 값은 trusted server가 operation에서 복사하며 caller
authority가 아니다. 편의를 위한 weaker subset UNIQUE/FK는 만들지 않는다.

Authorization이 successful outcome을 참조하는 exact deferred tuple도 outcome
ID/hash, operation ID/content hash, principal ID, 위 세 trust column,
`SUCCEEDED`, expected state와 resulting state를 모두 포함한다. 따라서
operation/outcome/authorization 사이에 role/principal hash/SID hash가 다르면
commit할 수 없다.

### 대안

- Parent operation key를 subset으로 약화: 거부. Exact principal/SID/role trust
  binding을 잃는다.
- Convenience subset UNIQUE identity 추가: 거부. 승인된 exact 8열 key와 다른
  권한 identity를 만든다.
- Generic authorization token 또는 free-form string: 거부. Closed lifecycle
  authorization matrix를 증명하지 못한다.
- `payload_json`/application assumption으로 copied equality를 대체: 거부.
  SQLite commit-time relational integrity가 사라진다.

### 영향

- ADR-015는 `ACCEPTED` 상태와 `2026-08-28` 결정일을 유지한다.
- GPT independent review of SHA
  `4104973d84307b80a236d9b737b2d29339b27153` returned `PASS WITH CLOSEOUT
  CONDITION`, P0 `0`, P1 `0`, P2 `1` non-blocking, and verified IG-01/IG-02
  `CLOSED`. The user explicitly accepted ADR-016 on `2026-08-28`.
- GPT independently reviewed the implemented additive schema at SHA
  `1be18a622006a6b6a46e251350e2d861d596823d` and returned `PASS WITH CLOSEOUT
  CONDITION`, P0 `0`, P1 `0`, P2 `1` non-blocking because GitHub CI execution
  evidence is absent. The user explicitly approved the implementation closeout
  on `2026-08-28`.
- Six-table additive Option A, `reviewer-credential-state/0.1.0`, trusted-server
  SHA boundary, nullable composite-FK safeguards, union counter chain, terminal
  outcome contract와 issuer/credential-operation assertion separation은
  변경하지 않는다.
- CP3-C2-B2-C `0006` schema implementation: `PASS — CLOSED`. This closes only
  the additive schema substep and does not close CP3-C2-B implementation or
  authorize B2-C runtime.
- B2-C runtime, B2-D, CP3-C2-C와 CP3-D는 `NOT STARTED`; automatic progression은
  `PROHIBITED`다.

### 마이그레이션·롤백

- ADR-016 acceptance 기록 시점의 migration change와 `0006`
  creation/application은 `0`이다.
- `0001`–`0005`는 byte-identical하게 유지한다.
- 사용자는 ADR-016 acceptance와 별도로 approved contract에 한정한 `0006`
  schema implementation을 명시 승인했다. B2-C runtime은 승인하지 않았다.
- 현재 additive `0006`은 exact six-table surface, approved indexes/triggers,
  ADR-016 trust binding과 cross-ledger counter guards를 구현했다. `0001`–`0005`
  blob은 고정됐고 persistent canonical/runtime write는 없다.
- 이 closeout task의 migration changes는 `0`이며 `0001`–`0006`은 reviewed SHA
  `1be18a622006a6b6a46e251350e2d861d596823d`와 byte-identical하다.
- B2-C WebAuthn/reviewer/human-approval runtime, B2-D, CP3-C2-C와 CP3-D는
  계속 별도 승인 전이며 automatic progression은 `PROHIBITED`다.

---

## ADR-017 — WebAuthn Runtime Canonicalization and Hash Preimage Amendment

- 상태: `ACCEPTED`
- 제안일: `2026-08-28`
- 결정일: `2026-08-29`
- 선행 결정: ADR-015 `ACCEPTED`, ADR-016 `ACCEPTED`
- 적용 gate: `CP3-C2-B2-C R1`
- 독립 검토: authoritative SHA
  `c34d8ca5a25bbea8c4ff410b7d62dc451f357528`의 전체 R1 설계에 대해
  `CHANGES REQUIRED`, P0 `0`, P1 `3`, P2 `2`
- 최종 schema/trust-boundary 검토: authoritative SHA
  `09ced6c0d0000f911075154c97a0e1cf54656f86`에 대해 `CHANGES REQUIRED`,
  P0 `0`, P1 `3`, P2 `1`; RG-08/RG-09/RG-10 canonical SID bytes/RG-11은
  `CLOSED IN PRINCIPLE`, P1-FR-01/P1-FR-02/P1-FR-03과 Windows Hello
  provenance가 새 blocker
- 최종 보완: authoritative SHA
  `dbf913d5654b3a1095d359ac34e1edcde2f63c1e`에서 P1-FR-01 frozen-outcome
  parent key, P1-FR-02 executable immediate-trigger insertion order,
  P1-FR-03 app-data OWNER SID / process `TOKEN_USER` equality와 ADR-019
  provenance proposal을 문서화
- 최종 독립 검토: GPT가
  `dbf913d5654b3a1095d359ac34e1edcde2f63c1e`를 독립 검토해
  `PASS WITH CLOSEOUT CONDITION`, P0 `0`, unresolved ADR-017/ADR-018 P1 `0`,
  P2 `1` — GitHub CI execution evidence absent / non-blocking으로 판정하고
  P1-FR-01/P1-FR-02/P1-FR-03을 closed로 확인
- 사용자 결정: `2026-08-29` explicit acceptance로 ADR-017과 ADR-018을
  `ACCEPTED`로 결정. 이 결정 권한은 Codex self-review가 아니라 위 GPT 독립
  검토 결과와 사용자의 명시적 수락에서 발생한다.
- 재현 벡터:
  `qa/PHASE_02_CP3_C2_B2_C_RUNTIME_CANONICALIZATION_GAP_CODEX_REPORT.md`

### 문제

Separately authorized R1 runtime implementation was audited before code changes
and stopped with `BLOCKED — APPROVED RUNTIME CONTRACT GAP`. ADR-017 previously
closed the five original byte-preimage questions and ADR-018 selected the
correct zero-counter continuation principle. Full independent review then found
four further implementation gaps:

1. P1-RG-08: zero-counter bootstrap must cover first, add, and replace;
2. P1-RG-09: exact WebAuthn user entity and per-credential-slot handle;
3. P1-RG-10: exact Windows token SID source and hash bytes; and
4. P2-RG-11: implementation-exact registration request/proof derivation.

RG-01 through RG-07, including Option C and CTAP2 canonical terminology, remain
valid. The new findings require an all-operation relational projection,
deterministic credential-slot user handles, exact SID bytes, and exact
registration proof flags. These findings do not reopen `0006`; it remains
`PASS — CLOSED`.

Implementing any one reasonable interpretation would create incompatible
persisted identities. Therefore R1 stays `NOT STARTED / BLOCKED` pending
`ADR-019` user decision, even after ADR-017/ADR-018 acceptance. Future schema and
runtime work remain separately authorized. ADR-015/ADR-016 acceptance and the
`0006 PASS — CLOSED` schema result are unchanged.

### 제안 — common canonicalization

Every JSON-backed hash added by this ADR uses this exact procedure:

1. The preimage is the one exact object listed below. Unlisted keys are
   forbidden. Nullable listed keys are present as JSON `null`; they are never
   omitted, an empty string or zero.
2. All keys and string values are Unicode NFC. A duplicate key created by NFC
   normalization fails closed.
3. Object keys are recursively ordered by unsigned lexicographic UTF-8 bytes.
   Array order is semantic and must already satisfy the field-specific sort
   rule.
4. Serialize UTF-8 JSON with no BOM, indentation, insignificant whitespace or
   trailing newline. The only literals are lowercase `true`, `false`, `null`.
   Integers use their shortest base-10 JSON form. Binary floating point,
   decimal-to-float conversion, NaN and infinity are forbidden.
5. UTC timestamps use `YYYY-MM-DDTHH:MM:SSZ` when microseconds are zero and
   `YYYY-MM-DDTHH:MM:SS.ffffffZ` with exactly six digits otherwise. Offsets,
   local time and trailing-zero trimming are forbidden.
6. Enums use the exact stored uppercase/lowercase token. Opaque IDs use the
   exact NFC-normalized stored text and are not decoded or re-derived unless a
   field rule explicitly says base64url.
7. The stored digest is
   `sha256:` plus 64 lowercase hexadecimal characters from SHA-256 of the exact
   bytes. Hash text is never hashed in place of raw bytes where the rule says
   raw bytes.

`payload_json`, log/process/run/request/session/transaction identity, insertion
order and retrieval clocks never enter these preimages. Audit timestamps enter
only the challenge bindings that explicitly list `issued_at` and `expires_at`;
`registered_at`, `authenticated_at`, `consumed_at`, `recorded_at` and
`completed_at` remain excluded. The trusted server supplies every field and
insert-verifies it against relational columns. A caller cannot supply an ID,
policy value, Boolean, content hash, counter classification or timestamp as
authority.

For R1 the exact server-owned enrollment, registration and authentication
policy token is `issuer-steward-webauthn/0.1.0`. Changing it requires a new
policy/versioned contract; it is not a request option.

### RG-09 — exact WebAuthn user entity and credential-slot handle

R1 permits multiple active credentials and requires discoverable platform
credentials. A discoverable credential is keyed by `(rpId, userHandle)` on an
authenticator; reusing one stable principal handle can replace the earlier
credential on the same Windows Hello authenticator. Each credential-creating
operation therefore owns one deterministic credential-slot handle while every
slot maps server-side to the same `LOCAL_DATA_STEWARD` principal.

```text
webauthn_user_handle_bytes = SHA256(
    ASCII("issuer-steward-webauthn-user-handle/0.1.0")
    || 0x00
    || UTF8_NFC(reviewer_principal_id)
    || 0x00
    || UTF8_NFC(reviewer_credential_operation_id)
)
```

The result is exactly 32 raw bytes. No `sha256:` text is part of `user.id`.
The handle is non-empty, no more than 64 bytes, non-PII, server-derived, fixed
for that credential-creating operation, never caller-supplied, not the
principal ID, and not a session or authority token. Exact display-only creation
values are:

```text
rp.name          = "localhost"
user.name        = "local-data-steward"
user.displayName = "Local Data Steward"
```

These strings provide zero security authority, identify no natural person, do
not replace `user.id`, and never enter issuer authority identity.

Every R1 assertion request has a non-empty `allowCredentials` list.
Counter-capability assertion permits exactly the pending credential ID.
ADD/REPLACE/REVOKE authorization permits only the exact currently active
credential IDs allowed for that operation. Later issuer approval, still
contract-only, permits only exact currently active credential IDs. An empty
discoverable-account assertion is forbidden in R1.

If `response.userHandle` is present, the server follows the exact credential to
its immutable registering operation, recomputes the expected 32 bytes, and
requires byte equality. With non-empty `allowCredentials`, absence is permitted;
credential ID, principal, challenge, RP/origin, UP/UV, and signature checks
remain mandatory. A present mismatch maps to terminal
`BINDING_MISMATCH`/safe result `USER_HANDLE_MISMATCH` and cannot produce a
verified authentication.

No database user-handle value column is required. Pending rows carry the exact
operation ID; an admitted credential has one unique root `REGISTERED` event and
exact authorization pointing to its registering operation. Principal plus that
operation deterministically reconstruct the handle after restart. Returned raw
handles are transient and never persisted or logged.

### RG-10 / P1-FR-03 — exact Windows app-data owner binding and SID preimage

The exact production application-data root for the SQLite authority/reviewer
ledger is the existing repository runtime root, not a new profile directory:

```text
canonical_app_data_root = resolve(PROJECT_ROOT / "var")
canonical_authority_database = canonical_app_data_root / "dashboard.db"
```

`PROJECT_ROOT` is derived server-side from the installed API module location as
`Path(__file__).resolve().parents[4]`, matching the repository scripts'
`Get-RepoRoot` plus `var` contract. It is never derived from the current working
directory, `USERNAME`, a browser, or caller data. In production authority mode,
the effective `DASHBOARD_DATABASE_URL` must resolve byte-for-byte, under Windows
ordinal case-insensitive path comparison, to the canonical database above.
In-memory, temporary, fixture-hash, test and externally overridden SQLite paths
cannot host production reviewer/authority state and fail closed for R1.

Before reading or writing any R1 principal/credential/approval row, the server
performs this owner check:

1. Require Windows and a local volume that reports persistent ACL support. A
   remote, non-filesystem, reparse-point, or object for which owner information
   cannot be queried is rejected.
2. If `canonical_app_data_root` does not exist, resolve and open the canonical
   repository root, create exactly its `var` child with `CreateDirectoryW`, and
   immediately continue with the same handle-based verification below. The
   directory is not trusted merely because creation succeeded. Failure or a
   race/swap is fail-closed; R1 does not change ownership with `SetSecurityInfo`.
3. Open the directory with `CreateFileW(OPEN_EXISTING)` using `READ_CONTROL`,
   `FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE`, and
   `FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT`. Query
   `FileAttributeTagInfo` and reject any reparse point. Resolve the opened
   object with `GetFinalPathNameByHandleW(FILE_NAME_NORMALIZED |
   VOLUME_NAME_DOS)` and require it to equal the expected canonical root.
4. Call `GetVolumeInformationW` for the handle-resolved volume. Reject a
   remote volume or filesystem flags that omit `FILE_PERSISTENT_ACLS`.
5. Call `GetSecurityInfo(handle, SE_FILE_OBJECT,
   OWNER_SECURITY_INFORMATION, ...)`, require a non-null owner SID, and require
   `IsValidSid(app_data_owner_sid)`.
6. Independently call `OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, ...)`,
   `GetTokenInformation(..., TokenUser, ...)`, and
   `IsValidSid(token_user_sid)`. Require
   `EqualSid(app_data_owner_sid, token_user_sid)` to return nonzero. Group
   membership, administrator/elevation status, profile-folder name, and path
   access are not substitutes for owner equality.

Only after equality succeeds does production derive the immutable owner hash
from the independently obtained process-token SID:

1. `OpenProcessToken` on the current process;
2. `GetTokenInformation(..., TokenUser, ...)`;
3. take the exact `TOKEN_USER.User.Sid` and require `IsValidSid` success;
4. call `ConvertSidToStringSidW` and use exactly its canonical standard
   `S-R-I-S-S...` result; free the returned buffer with `LocalFree`.

```text
os_owner_sid_hash =
  "sha256:" + lowercase_hex(
    SHA256(UTF8(canonical_windows_sid_text))
  )
```

The preimage has no UTF-16 code units, terminating NUL, case conversion,
whitespace, domain/user name, environment username, caller value, SID alias,
binary SID bytes, or textual hash prefix. The canonical text is transient only;
the raw app-data owner SID, process-token SID, and canonical SID text are never
persisted or logged. Failure of root resolution/creation, handle opening, final-
path or reparse validation, owner-security query, token opening, TokenUser
query, either SID validation, `EqualSid`, or string conversion fails closed.
Non-Windows production execution fails closed.

### RG-11 — exact registration request and proof derivation

The registration request sets exactly:

```text
authenticatorSelection.authenticatorAttachment = "platform"
authenticatorSelection.residentKey              = "required"
authenticatorSelection.requireResidentKey       = true
authenticatorSelection.userVerification         = "required"
attestation                                      = "none"
extensions.credProps                             = true
```

No FIDO Metadata Service, vendor attestation trust, or new hardware trust root
is introduced. `platform_authenticator_verified=1` only when cryptographic
registration verification succeeds and returned
`PublicKeyCredential.authenticatorAttachment` is exactly `platform`; null,
cross-platform, or unknown rejects registration.

`resident_key_verified=1` only when the exact server option required
`residentKey`, `requireResidentKey=true`, and creation completed successfully.
If `clientExtensionResults.credProps.rk` is present it must be true; false
rejects. Missing `credProps`/`rk` does not override successful creation under
the required resident-key option.

`public_key_material_verified=1` only after cryptographic registration success,
canonical credential-ID validation, ADR-017 CTAP2-canonical COSE validation,
and exact `ES256`/`RS256` allowlist validation. Attachment and `credProps` are
client/WebAuthn ceremony outputs and consistency evidence, not hardware-
attestation authority.

Normative references for RG-09/RG-11 are W3C WebAuthn Level 3 user entities,
discoverable credentials, authenticator selection, assertion options, and
credential-properties extension (`https://www.w3.org/TR/webauthn-3/`). RG-10
uses the Microsoft Win32 contracts for `OpenProcessToken`,
`GetSecurityInfo`, `CreateFileW`, `GetFinalPathNameByHandleW`, `EqualSid`,
`GetTokenInformation`, `TOKEN_USER`, `IsValidSid`, and
`ConvertSidToStringSidW`:
`https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-getsecurityinfo`,
`https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew`,
`https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfinalpathnamebyhandlew`,
`https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-equalsid`,
`https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openprocesstoken`,
`https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-gettokeninformation`,
`https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-token_user`,
`https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-isvalidsid`,
and
`https://learn.microsoft.com/en-us/windows/win32/api/sddl/nf-sddl-convertsidtostringsidw`.

### RG-01 — exact principal content

`principal_content_hash` is SHA-256 of the common canonical JSON serialization
of exactly these keys and no others:

```json
{
  "contract_version": "issuer-steward-webauthn/0.1.0",
  "enrollment_policy_version": "issuer-steward-webauthn/0.1.0",
  "os_owner_sid_hash": "sha256:<64-lowerhex>",
  "principal_state": "ACTIVE",
  "reviewer_principal_id": "<server-owned-opaque-id>",
  "reviewer_role": "LOCAL_DATA_STEWARD"
}
```

`principal_content_hash`, `registered_at`, `payload_json` and all process/audit
identity are excluded. The server creates the R1 principal directly in
`ACTIVE`; R1 defines no later principal state transition, recovery or reset
path. `os_owner_sid_hash` is already a one-way server-derived digest; raw SID
text is neither stored in this object nor logged.

### RG-02/RG-03 — exact credential content and COSE_Key

`credential_content_hash` covers exactly these keys and no others:

```text
authenticator_aaguid
authenticator_attachment
authenticator_transports
contract_version
cose_public_key_canonical
counter_capability
credential_id_fingerprint
principal_content_hash
public_key_algorithm
public_key_fingerprint
registration_policy_version
registration_sign_count
resident_key_required
reviewer_principal_id
reviewer_role
rp_id
user_verification_required
webauthn_credential_id
```

The fixed values are `authenticator_attachment="platform"`,
`resident_key_required=true`, `user_verification_required=true`,
`reviewer_role="LOCAL_DATA_STEWARD"`, `rp_id="localhost"` and the R1 policy
token above. `credential_content_hash`, `registered_at`, `payload_json` and
process/audit IDs are excluded.

- `webauthn_credential_id` is unpadded RFC 4648 section 5 base64url of the raw
  credential-ID bytes. Decode then re-encode must equal the received text;
  padded, standard-base64 and alternate forms fail closed.
- `credential_id_fingerprint` is SHA-256 of those raw credential-ID bytes.
- `authenticator_aaguid` is JSON `null` when absent, otherwise the exact
  lowercase hyphenated UUID produced from 16 verified bytes.
- `authenticator_transports` is a deduplicated unsigned-UTF-8-sorted array from
  the closed set `ble`, `hybrid`, `internal`, `nfc`, `smart-card`, `usb`.
  Absence is `[]`; an unknown/non-text value fails closed. The DB TEXT value is
  the same compact JSON array bytes.
- `counter_capability` is exactly `SIGN_COUNT_SUPPORTED` or
  `NO_USABLE_COUNTER`. The latter requires `registration_sign_count:null`,
  never zero. A positive registration counter is sufficient to select
  `SIGN_COUNT_SUPPORTED`. A registration value of zero is
  `COUNTER_CAPABILITY_UNRESOLVED`: it selects neither immutable database value,
  cannot create a public credential row, and requires the separately proposed
  ADR-018 bootstrap continuation. Under that proposal, a fully verified fresh
  assertion `0 -> positive` selects `SIGN_COUNT_SUPPORTED` while preserving
  the truthful registration value `0`; `0 -> 0` selects the repository mode
  `NO_USABLE_COUNTER` and preserves both observed zeros in the bootstrap audit
  while the frozen credential column remains null. Browser claims, AAGUID,
  attachment, username, backup flags, caller input and payload JSON are never
  classification authority.

Only this exact COSE algorithm mapping is approved:

| COSE `alg` | stored `public_key_algorithm` |
|---:|---|
| `-7` | `ES256` |
| `-257` | `RS256` |

The server parses a top-level CBOR map, rejects duplicate labels, validates the
algorithm-specific COSE_Key structure, and rejects unknown/extra labels and all
other algorithms. ES256 is exactly EC2/P-256 with labels
`{1:2,3:-7,-1:1,-2:x,-3:y}` and 32-byte coordinates. RS256 is exactly RSA with
labels `{1:3,3:-257,-1:n,-2:e}`, an unsigned at-least-2048-bit odd modulus and
valid odd exponent. Indefinite-length items, CBOR floats, tags and unsupported
simple values are forbidden.

After validation the map is encoded in the **CTAP2 canonical CBOR encoding
form** required by WebAuthn for `credentialPublicKey`, then decoded again;
semantic equality is mandatory. RFC 8949 remains the underlying CBOR
reference, not the WebAuthn canonical-form authority. The original COSE_Key
bytes must equal the CTAP2 canonical encoding, so duplicate-label,
non-canonical and alternate encodings are rejected rather than silently
normalized. Generic `cbor2.dumps(value, canonical=True)` is not sufficient as
a general CTAP2 encoder; it is usable for these two restricted, validated key
maps only because the frozen ES256/RS256 vectors independently prove the same
bytes. `cose_public_key_canonical` is unpadded base64url of the CTAP2 canonical
CBOR bytes. `public_key_fingerprint` is SHA-256 of those raw bytes, not of the
base64url TEXT.

Normative references: W3C WebAuthn Level 3 sections 5.8.1 and 6.5.6
(`https://www.w3.org/TR/webauthn-3/`) and FIDO CTAP 2.2 section 6.5.4.1
(`https://fidoalliance.org/specs/fido-v2.2-ps-20250714/fido-client-to-authenticator-protocol-v2.2-ps-20250714.html`).

### RG-04 — challenge digest and exact binding

For both operation and issuer approval ceremonies, the WebAuthn challenge is
exactly 32 bytes from the OS CSPRNG. The stored digest is exactly SHA-256 of
those raw 32 bytes. No UTF-8/base64 conversion, contract prefix, JSON wrapper
or binding bytes enter `challenge_digest`; the raw bytes are transient and are
not persisted. The client-visible challenge is their canonical unpadded
base64url encoding. Decode/re-encode equality is required on return.

This proposal supersedes only the ambiguous B1 section 9.1.3 formula that
derived challenge bytes from `contract|nonce|binding`. Exact server-side
binding is instead provided by the separately hashed immutable binding object
below and its relational insert verification.

`reviewer_credential_operation_challenges.challenge_binding_hash` covers every
immutable relational column in section 7.2 except
`challenge_binding_hash` and `payload_json`, using exactly these keys:

```text
allowed_origin
authentication_policy_version
challenge_digest
challenge_nonce_length
challenge_purpose
client_data_type
contract_version
expected_credential_state_hash
expires_at
issued_at
operation_content_hash
operation_type
os_owner_sid_hash
platform_attachment_required
prerequisite_authentication_content_hash
prerequisite_authentication_event_id
prerequisite_authentication_result
principal_content_hash
resident_key_required
reviewer_credential_operation_challenge_id
reviewer_credential_operation_id
reviewer_principal_id
reviewer_role
rp_id
target_credential_id_fingerprint
target_webauthn_credential_id
user_verification_required
```

`challenge_nonce_length` is integer `32`. SQLite `0/1` policy columns are JSON
Booleans; nullable policy/reference fields are explicit JSON `null`. The
challenge ID is a preallocated opaque CSPRNG ID, not a digest-derived ID.
Therefore including it does not create a cycle. The operation hash never
contains this binding hash.

`issuer_approval_challenges.challenge_binding_hash` covers every immutable
server-owned relational column except `challenge_binding_hash` and
`payload_json`, using exactly these keys:

```text
allowed_origin
authentication_policy_version
authority_bundle_id
challenge_digest
contract_version
expected_bundle_content_hash
expected_decision_content_hash
expires_at
issued_at
issuer_approval_challenge_id
issuer_decision_id
predecessor_approval_event_id
predecessor_link_id
principal_content_hash
proposed_issuer_id
provider_security_identity_id
requested_disposition
reviewer_principal_id
reviewer_role
rp_id
successor_decision_id
user_verification_required
```

The issuer ceremony also requires a raw 32-byte challenge even though `0005`
does not persist a nonce-length column. All predecessor/successor fields are
present as strings or JSON `null`; decision, bundle, provider identity,
proposed issuer and requested disposition are exact relational copies. This is
a contract amendment only and does not authorize issuer-approval runtime.

### RG-05 — exact authentication content

`reviewer_credential_operation_authentication_events.authentication_content_hash`
covers every relational section 7.4 column from `contract_version` through
`safe_result_code`, except the event ID, and uses exactly these keys:

```text
asserted_sign_count
authentication_policy_version
authentication_result
authorizing_webauthn_credential_id
challenge_binding_hash
challenge_consumption_content_hash
challenge_consumption_id
challenge_purpose
challenge_terminal_result
contract_version
counter_capability
counter_verified
credential_id_fingerprint
exact_origin
expected_credential_state_hash
operation_content_hash
operation_type
origin_verified
os_owner_sid_hash
previous_sign_count
principal_content_hash
public_key_fingerprint
replay_rejected
reviewer_credential_operation_challenge_id
reviewer_credential_operation_id
reviewer_principal_id
reviewer_role
rp_id
rp_id_hash_verified
safe_result_code
signature_verified
user_presence_verified
user_verification_verified
```

The event ID, `authentication_content_hash`, `authenticated_at` and
`payload_json` are excluded. Counter values are integers or explicit JSON
`null`; every SQLite verification integer is a JSON Boolean.

`reviewer_authentication_events.authentication_content_hash` covers every
immutable semantic relational authentication field from the `0005` table
except event ID, hash, authentication time and payload, using exactly:

```text
asserted_sign_count
authentication_policy_version
authentication_result
authority_bundle_id
challenge_consumption_id
contract_version
counter_capability
counter_verified
credential_id_fingerprint
exact_origin
expected_bundle_content_hash
expected_decision_content_hash
issuer_approval_challenge_id
issuer_decision_id
origin_verified
previous_sign_count
public_key_fingerprint
replay_rejected
requested_disposition
reviewer_principal_id
reviewer_role
rp_id
rp_id_hash_verified
safe_result_code
signature_verified
user_presence_verified
user_verification_verified
webauthn_credential_id
```

This issuer authentication rule is contract-only. It does not implement or
authorize an actual assertion or approval.

### Hash dependency DAG and cycle proof

The cryptographic dependency order is:

```text
current process TOKEN_USER -> canonical Windows SID UTF-8 -> os_owner_sid_hash -> principal_content_hash
principal ID + credential-creating operation ID -> raw 32-byte WebAuthn user handle
raw credential ID -> canonical credential ID + credential_id_fingerprint --+
raw COSE_Key -> CTAP2 canonical COSE bytes -> public_key_fingerprint --------+-> credential_content_hash
principal/credential event leaves -> credential_state_hash
principal + expected state + preallocated initial challenge ID -> operation_content_hash
raw operation challenge -> challenge_digest
operation_content_hash + challenge_digest + preallocated challenge ID -> operation challenge_binding_hash
operation challenge_binding_hash -> consumption_content_hash
operation/content + binding + consumption + active credential -> operation authentication_content_hash
operation authentication + consumption -> outcome_content_hash -> authorization_content_hash

decision + bundle + principal + raw issuer challenge digest + preallocated ID
  -> issuer challenge_binding_hash -> issuer consumption_content_hash
  -> issuer authentication_content_hash -> approval-event hashes -> link hashes
```

No arrow returns to an ancestor. Preallocated opaque row IDs are independent
random identifiers, not hashes of their child rows. In particular, the
operation hash may contain `initial_challenge_id`, but never the challenge
binding hash; consumption may contain a preallocated outcome/continuation ID,
but never that child's content hash. The existing exact
credential-event, operation, consumption, authorization, outcome and state
hash contracts are unchanged.

### Feasibility evidence, alternatives and status effect

An isolated Python 3.13 audit of pinned `webauthn==3.0.0` with
`cbor2==6.1.4` exposed the expected registration/authentication generate and
verify APIs, but no authoritative signature-counter-capability result. Both
ADR-017 ES256 and RS256 vectors decoded and converted to cryptography public-
key objects. A separate standard-library encoder implementing the CTAP2 map-key
ordering and shortest-form rules reproduced both exact frozen hex strings,
base64url strings and fingerprints. `cbor2` canonical encoding is usable for
these restricted maps only behind that proved boundary. This task changes no
dependency or lock file and performs no actual Windows Hello ceremony.

Rejected alternatives are hashing library object representations, storing
arbitrary incoming COSE bytes, accepting padded/alternate base64, mapping
unknown algorithms/transports, omitting null keys, treating a missing counter
as zero, or letting callers supply policy/hash fields. Each would make the
persisted identity non-portable or weaken fail-closed verification.

ADR-017 is `ACCEPTED` (`2026-08-29`); ADR-018 below is separately
`ACCEPTED`; Codex does not self-implement. `RG-08/RG-09/RG-10` are closed as
contract/design-level matters from GPT independent review and explicit user
acceptance; `RG-11` and all requested FR findings are accepted.
R1 remains `BLOCKED / NOT STARTED` pending `ADR-019`, with application, schema,
migration, test, fixture and dependency changes all `0`. Future `0007` is
necessary under the selected proposal but is `NOT CREATED / NOT AUTHORIZED`.
ADR-015 and ADR-016 remain `ACCEPTED`; `0006` remains `PASS — CLOSED`. B2-D,
CP3-C2-C and CP3-D remain `NOT STARTED`, and automatic progression remains
`PROHIBITED`.

### 마이그레이션·롤백

This is a documentation/control-plane proposal. Migrations `0001`–`0006` stay
byte-identical; migration count and application count are `0`. Before ADR-017
and ADR-018 acceptance, rollback is removal/reversion of these documentation-
only changes. R1 cannot start from ADR-017 alone. Even after both proposals are
accepted, a future `0007` and runtime implementation each require separate
explicit authority.

---

## ADR-018 — WebAuthn Counter Capability Bootstrap Amendment

- 상태: `ACCEPTED`
- 제안일: `2026-08-28`
- 결정일: `2026-08-29`
- 선행 결정: ADR-015 `ACCEPTED`, ADR-016 `ACCEPTED`, ADR-017 `ACCEPTED`
- 적용 gate: `CP3-C2-B2-C R1`
- 결정 provenance: GPT가 authoritative SHA
  `dbf913d5654b3a1095d359ac34e1edcde2f63c1e`의 FR-01/FR-02/FR-03 보완을
  독립 검토해 `PASS WITH CLOSEOUT CONDITION`, P0 `0`, unresolved
  ADR-017/ADR-018 P1 `0`, P2 `1` — GitHub CI execution evidence absent /
  non-blocking으로 판정한 뒤, 사용자가 `2026-08-29` ADR-018을 명시적으로
  `ACCEPTED`했다. Codex self-review는 결정 권한이 아니다.
- proposed future migration:
  `0007_phase_02_cp3_c2_b2_c_counter_capability_bootstrap` — `NOT CREATED / NOT
  AUTHORIZED`

### 문제와 선택

WebAuthn permits both a counter-supporting authenticator's initial registration
counter and a no-counter authenticator's counter to be zero. R1 therefore
cannot truthfully derive the frozen `0005` classification from a zero
registration result. Three alternatives were audited:

| Option | Result | Rationale |
|---|---|---|
| A — permanently map registration zero to `NO_USABLE_COUNTER` | rejected | It is a possible repository policy, but it permanently discards clone-detection history for every supported counter that begins at zero. The stored token would describe policy, not demonstrated authenticator behavior. |
| B — reject every registration zero as `COUNTER_CAPABILITY_UNRESOLVED` | rejected as the product policy | It is fail-closed and truthful, but it rejects a standards-valid authenticator class. Without an authorized real Windows Hello ceremony, compatibility cannot be proved; a Windows Hello-only product would be unacceptably brittle and may be unusable. |
| C — one fresh post-registration assertion | selected proposal | It preserves truth and compatibility: a verified `0 -> positive` proves usable advancement, and verified `0 -> 0` establishes the repository no-usable-counter admission mode without guessing from registration alone. |

Option C does not weaken challenge, RP ID, exact origin, type, UP, UV,
signature, credential-ID, public-key or replay verification. The assertion is
bound to exactly the just-registered pending public key and a new 32-byte one-
time challenge. It grants no issuer approval, reusable login, recovery, reset
or general credential-operation authority.

### 제안 상태 기계

1. Every `FIRST_ENROLLMENT`, `ADD_CREDENTIAL`, or `REPLACE_CREDENTIAL` uses its
   exact existing `0006` `REGISTRATION_CREATE` challenge. Revoke is excluded.
2. A fully verified positive registration `signCount` is immediately
   `ACCEPTED` through the unchanged frozen terminal path as
   `SIGN_COUNT_SUPPORTED`; the positive value is immutable.
3. A fully verified registration zero is `REQUIRES CONTINUATION`. No public
   credential or frozen registration consumption exists yet. In one transaction
   the server records the verified pending public material and observed zero and
   issues exactly one fresh assertion challenge whose expiry is no later than
   the still-live parent registration challenge.
4. The continuation verifies `webauthn.get`, exact challenge/RP/origin,
   cross-origin false, UP, UV, exactly the pending credential ID, optional
   returned user-handle equality, and the signature under the pending public
   key. A result greater than zero is `ACCEPTED` as
   `SIGN_COUNT_SUPPORTED`, with frozen `registration_sign_count=0` and an
   audited first counter edge `0 -> asserted`. A result equal to zero is
   `ACCEPTED` as `NO_USABLE_COUNTER`, with frozen
   `registration_sign_count=null` and immutable observed `0 -> 0` evidence.
5. Successful FIRST and ADD project exactly one new `REGISTERED` credential.
   Successful REPLACE atomically projects the new `REGISTERED` plus old-target
   `SUPERSEDED` lifecycle authorizations under the same operation, principal,
   and successful outcome.
6. Expiry, replay, malformed data, binding/user-handle mismatch, wrong
   credential, failed RP/origin/UP/UV/signature checks, or an impossible count
   terminalizes the original operation without a public credential or lifecycle
   authorization. Expected and resulting credential-state hashes are equal.
   The exact frozen outcome is a valid predecessor for a wholly fresh successor
   operation; it is not recovery or reusable authentication state.

For ADD/REPLACE, entering step 3 never rolls back the earlier successful
`AUTHORIZATION_ASSERTION` consumption, `VERIFIED` authentication event, its
supported-counter advancement, or the already-issued registration challenge.
Failure therefore leaves ownership state unchanged but preserves that immutable
authentication history. REPLACE failure leaves the old target ACTIVE.

The repository meaning of `counter_capability` is thus an immutable **admitted
counter-evidence mode**, not a vendor/hardware capability claim. Neither
AAGUID nor attachment, Windows username, backup flags, browser/caller input,
payload JSON, undocumented Windows Hello behavior, FIDO Metadata Service or
vendor attestation trust participates in the decision.

### 기존 schema sufficiency audit

Frozen `0005`/`0006` cannot represent Option C faithfully or atomically:

- `reviewer_webauthn_credentials` must choose the immutable union before insert;
  a temporary unresolved row or later update is forbidden.
- A successful frozen registration consumption requires the already classified
  credential and a terminal operation outcome. It cannot consume registration
  zero and wait for another assertion.
- `FIRST_ENROLLMENT` permits only `REGISTRATION_CREATE`; the frozen
  authentication event table permits assertion rows only for add/replace/revoke.
- The frozen continuation slot goes in the opposite direction—successful
  add/replace assertion to registration—and cannot represent registration to
  capability assertion.
- For ADD/REPLACE, the authorizing assertion and supported counter advancement
  are already immutable before the new registration. Treating the later
  bootstrap as a new operation would lose the single-operation lifecycle and
  replace atomicity; rolling back the prior event would falsify history.
- Frozen `REGISTRATION_CREATE` is terminal and every successor requires an exact
  predecessor outcome. A pending-only terminal marker would make restart and
  successor insertion inconsistent with `0006`.
- Frozen credential insertion requires exact successful registration proof;
  REPLACE success additionally requires one `REGISTERED` plus one `SUPERSEDED`
  authorization under the same successful outcome. A side-table classification
  without an exact frozen projection cannot satisfy those guards.
- The frozen counter-union guards see only issuer and credential-operation
  authentication events. A separately stored `0 -> positive` bootstrap edge
  would otherwise be an unaudited/unreconstructed counter advancement.
- Reusing issuer approval or caller/payload fields would falsely authorize the
  assertion; pretending the assertion was registration would falsify
  `registration_sign_count`.

This is a new runtime-to-schema requirement, not a retroactive failure of
`0006`; `0006` remains `PASS — CLOSED`.

### Exact future schema amendment

The implementation-ready normative design is
`plans/PHASE_02_CP3_C2_B2_C_ADR_018_COUNTER_CAPABILITY_SCHEMA_PROPOSAL.md`.
If accepted and separately authorized, the minimum future `0007` remains three
append-only tables, but their exact roles are now:

1. `reviewer_webauthn_counter_capability_registrations`: one fully verified
   zero registration against the existing frozen challenge, including exact
   public material, request/proof flags, operation/principal/SID/state tuple,
   prerequisite authorizing event for add/replace, observed zero, and the one
   preallocated child challenge;
2. `reviewer_webauthn_counter_capability_challenges`: the raw-32-byte-digest,
   exact pending-credential assertion challenge with one non-empty allow-list
   member, handle-policy version, exact binding, and child expiry no later than
   the parent registration expiry;
3. `reviewer_webauthn_counter_capability_assertions`: the single terminal child
   consumption, verification facts, optional-user-handle result, observed
   counter edge, immutable classification, and exact IDs/hashes/results of the
   frozen consumption/outcome/credential/lifecycle projection.

The companion specifies every column, type, nullability, key, UNIQUE, composite
deferred FK, CHECK family, index, append-only trigger, insert guard, exact
content-hash field inventory, timestamp, and payload authority rule. It also
defines exact FIRST/ADD/REPLACE success and failure transactions, replay and
restart reconstruction, user-handle reconstruction, and the hash DAG.

P1-FR-01 is resolved in the proposal by choosing additive-index design A.
Future `0007` must create exactly
`uq_0007_reviewer_credential_operation_outcomes_bootstrap_projection` on the
frozen outcome table with ordered columns
`(credential_operation_outcome_id, outcome_content_hash,
reviewer_credential_operation_id, operation_content_hash,
reviewer_principal_id, reviewer_role, principal_content_hash,
os_owner_sid_hash, operation_type, terminal_result, terminal_consumption_id,
terminal_consumption_content_hash, expected_credential_state_hash,
resulting_credential_state_hash)`. Neither frozen outcome UNIQUE is an eligible
parent for that complete tuple. The assertion also now copies exact
`projected_registration_challenge_purpose='REGISTRATION_CREATE'` so its frozen
consumption FK has all six child columns; no constant is silently substituted
for a missing child column.

P1-FR-02 is resolved by the exact executable order proven against frozen
immediate triggers. First/add success is assertion -> frozen registration
consumption -> registration lifecycle authorization -> public credential ->
`REGISTERED` event -> frozen outcome. Replace success is assertion ->
consumption -> new registration authorization -> old supersession authorization
-> new credential -> new `REGISTERED` -> old `SUPERSEDED` -> outcome. Every
failure/expiry is assertion -> frozen consumption -> frozen outcome with zero
credential/lifecycle writes. The authorization rows are intentional deferred-
FK forward references; their own new additive projection guard runs before the
credential/event insert. A disposable uncommitted SQLite proof applied the
actual `0001`–`0006`, materialized the proposal, committed all nine required
first/add/replace positive/zero/failure transactions, and returned zero rows
from `PRAGMA foreign_key_check`. No proof file or database is retained.

Only the two frozen counter-union definitions are version-replaced, under their
same names, to add the supported bootstrap edge:
`trg_reviewer_authentication_events_counter_union_guard` and
`trg_reviewer_credential_operation_authentication_counter_union_guard`.
All predecessor, challenge, consumption, active-credential, registration-proof,
lifecycle, outcome, and append-only triggers remain intact and receive only
additional cross-ledger guards. No existing row or migration is rewritten.

### 상태 효과

ADR-018 is `ACCEPTED` (`2026-08-29`) and not self-implemented; it is fully
frozen as control-plane/runtime-contract design only. Future `0007` is necessary
for full Option C and is `NOT CREATED / NOT AUTHORIZED`. ADR-017 is `ACCEPTED`;
R1 remains `BLOCKED / NOT STARTED` pending `ADR-019` acceptance. RG-08~RG-11 and
FR-01~FR-03 are treated as contractually closed. ADR-015 and ADR-016 remain
`ACCEPTED`; `0006` remains `PASS — CLOSED`; B2-D, CP3-C2-C and CP3-D remain
`NOT STARTED`; automatic progression remains `PROHIBITED`.

---

## ADR-019 — Windows Hello Provenance Trust Boundary

- 상태: `PROPOSED — ON HOLD / AWAITING SEPARATE USER DECISION`
- 제안일: `2026-08-29`
- 결정일: `NONE`
- 선행 결정: accepted B1/ADR-014 requires a Windows Hello-backed platform
  credential; ADR-017/ADR-018 are accepted
- 적용 gate: `CP3-C2-B2-C R1`

### 문제와 standards result

The current ceremony requires Windows, `authenticatorAttachment=platform`,
UV, resident discoverability, and `attestation=none`; it uses no Metadata
Service, AAGUID allowlist, enterprise/direct attestation trust path, hardware
attestation CA, or native broker. WebAuthn Level 3 defines none attestation as
providing no attestation information and an empty trust path. Attachment
modality and UV prove ceremony properties, not the authenticator vendor or
implementation. Microsoft documents that current Windows WebAuthn routes to
Windows Hello, external security keys, and plugin authenticators, and Windows
11 24H2 supports plugin passkey managers.

Therefore the current exact design proves only:

```text
a user-verifying platform WebAuthn credential on Windows
```

It does **not** uniquely establish strict Windows Hello provenance. This is a
new trust-boundary blocker, not permission to weaken accepted B1.

### Options — no option selected or accepted

| Option | Property and consequence | Decision state |
|---|---|---|
| 1. Retain strict Windows Hello-only and add independently verifiable provenance | Preserves accepted B1, but requires an exact Microsoft/Windows-Hello-specific attestation or other provenance signal plus an approved trust path, failure policy, privacy model, and rotation/revocation contract. `attestation=none` cannot supply it. MDS, direct/enterprise attestation, AAGUID allowlists, and new roots remain forbidden unless separately accepted. | candidate; technically strongest product-property match, mechanism not yet approved |
| 2. Redefine the property as “user-verifying Windows platform WebAuthn credential” | Matches what the present browser ceremony actually proves. Threat model must explicitly accept Windows platform/plugin authenticators that satisfy exact RP/origin/UV/signature rules and acknowledge that no Windows Hello provenance is established. This changes the accepted B1 security property. | candidate only; not selected for ease and requires explicit user amendment |
| 3. Adopt a stronger Windows-native architecture | A native broker or Windows credential/key API might expose a narrower system trust boundary, but it adds a native component, protocol, packaging/update surface, and new authority root. Its ability to exclude plugin authenticators must be independently proved before selection. | research candidate; no broker or root authorized |

Fail-closed default retains the strict B1 words and blocks R1. No provenance
option, weaker property, Metadata Service, attestation mode, AAGUID policy,
native broker, or trust root is introduced by this proposal. ADR-019 needs
independent review and explicit user acceptance before R1 can begin, even if
ADR-017/ADR-018 later pass review.

The deliberate RG-09 handle model remains unchanged: each credential slot is
a distinct authenticator-layer WebAuthn user-account namespace so a second
discoverable credential does not replace the first `(rpId,userHandle)` entry;
all slots map server-side to the one `LOCAL_DATA_STEWARD` authorization
principal. Every assertion keeps a non-empty exact `allowCredentials` list.

Normative/primary references:
W3C WebAuthn Level 3 none attestation, user handle, and discoverable credential
rules (`https://www.w3.org/TR/webauthn-3/`) and Microsoft WebAuthn APIs for
Windows/plugin passkey managers
(`https://learn.microsoft.com/en-us/windows/security/identity-protection/hello-for-business/webauthn-apis`).

### 상태 효과

ADR-019 is `PROPOSED — ON HOLD / AWAITING SEPARATE USER DECISION`; it is not
accepted. ADR-017 and ADR-018 are `ACCEPTED`; `0006` is `PASS — CLOSED`; future
`0007` is
`NOT CREATED / NOT AUTHORIZED`; R1 is `BLOCKED / NOT STARTED`; B2-D, CP3-C2-C
and CP3-D are `NOT STARTED`; automatic progression is `PROHIBITED`.

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
