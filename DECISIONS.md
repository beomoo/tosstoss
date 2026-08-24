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

- 상태: `PROPOSED — INDEPENDENT REVIEW P1-NOT-BLOCKING / AWAITING USER APPROVAL`
- 제안일: `2026-08-23`
- 수정 제안일: `2026-08-24`
- 독립검증일: `2026-08-25` — 방향상 blocker 없음; Codex가 `ACCEPTED`로 전환하지 않음

### 문제

Phase 1 `SourceRecord`는 `observed_at`과 `published_at`을 필수 datetime으로 요구한다. Toss 수급 응답 일부는 기준 `date`만 제공하고 publication timestamp를 제공하지 않는다. 또한 공식 `/prices` 계약은 정상 응답에서도 `timestamp=null`을 허용한다. 기존 제안의 “`observed_at`과 `observed_date` 중 최소 하나” 규칙은 이 정상적인 time-unknown 상태를 표현하지 못한다. 자정, 현재 date 또는 fetch 시각을 대입하면 기존 시간 의미를 위반한다.

### 제안

- 기존 Phase 1 `SourceRecord` v0.1.0과 fixture는 변경하지 않는다.
- Phase 2에 date-only와 timestamp 관측을 구분하는 versioned provider source contract를 추가한다.
- `observed_at`과 `observed_date`는 각각 nullable이다.
- 둘 다 null인 상태를 허용하되 각 null field에 structured missing reason을 요구한다.
- 둘 다 값이 있으면 dataset별 contract가 해당 조합을 명시적으로 허용하는지 검증한다.
- `published_at`은 nullable이고 null이면 structured missing reason이 필수다.
- `fetched_at`은 required aware UTC이며 관측 또는 발표 시각을 대신하지 않는다.
- current price의 provider timestamp가 null이면 availability `DEGRADED`, freshness `UNKNOWN`으로 두고 current/latest publish를 막는 보수적 default를 제안한다.
- 전역 `ContractVersion = Literal["0.1.0"]`을 무조건 확장하지 않고 새 provider source contract에 독립 version을 부여한다.
- 신규 provider source version은 기존 `source_records` natural key를 timestamp suffix로 우회하지 않고 additive table에서 revision을 표현한다.

### 대안

- date를 자정 UTC/KST로 변환: 존재하지 않는 시각을 생성하므로 거부한다.
- `fetched_at`을 `observed_at`으로 복사: 데이터 기준시각과 수집시각을 혼동하므로 거부한다.
- timestamp null인 price를 0 또는 현재 date로 대체: provider 사실을 위조하므로 거부한다.
- 기존 SourceRecord 전체를 즉시 breaking migration: Phase 1 회귀 범위가 커서 거부한다.

### 영향

독립 검토와 사용자 승인 뒤 CP3-B에서 source contract·additive migration·fixture·repository test가 추가될 수 있다. 기존 Phase 1 계약 테스트, fixture/API/OpenAPI와 `contract_version=0.1.0` 응답은 그대로 통과해야 한다. CP3-A에서는 문서 외 구현을 하지 않는다.

### 마이그레이션·롤백

신규 provider record만 새 contract를 사용한다. rollback은 신규 publish 중지, last known-good pointer 유지와 해당 additive contract/migration의 disposable-DB 검증 후 revert다. 기존 Phase 1 row·fixture와 raw/history를 변환하거나 삭제하지 않는다.

---

## ADR-012 — Toss provider security identity와 canonical issuer/security mapping 분리

- 상태: `PROPOSED — REVISED AFTER INDEPENDENT REVIEW / AWAITING RE-REVIEW`
- 제안일: `2026-08-24`
- 독립검증 보완일: `2026-08-25`

### 문제

Phase 1 `Issuer`는 KR corp_code 또는 US CIK를 요구하고 `Security`는 issuer와 exchange를 요구한다. Toss stock response에는 corp_code/CIK가 없고 현재 저장소 근거만으로 exchange semantics도 확정할 수 없다. Toss symbol, ticker, 종목명 또는 synthetic regulatory identifier로 빈칸을 채우면 잘못된 issuer merge와 VERIFIED mapping을 만들 수 있다.

첫 독립검증은 두 P1을 확인했다. P1-01은 verified canonical mapping을 Current Price 저장의 필수조건으로 둬 Phase 2가 Phase 3 OpenDART/Phase 4 SEC regulatory mapping에 순환 의존한다는 점이다. P1-02는 최초 observation 뒤 ISIN/listDate가 보강될 때 anchor 우선순위를 다시 적용하면 immutable이어야 할 동일 instrument에 새 provider identity가 생길 수 있다는 점이다.

### 제안

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

승인되면 CP3-B에 additive staging/source/mapping/provider-latest schema와 repository interface가, CP3-C에 offline security master normalization이 필요하다. CP3-D current price는 valid provider identity를 소비해 provider-scoped snapshot/latest를 만들고, verified canonical linkage가 있을 때만 canonical current-price view를 제공한다. 따라서 Phase 2 provider-scoped Security Master + Current Price 목표는 Phase 3/4 regulatory mapping 없이 완료 가능하다. 기존 Phase 1 Issuer/Security v0.1.0, fixture IDs와 public API는 변경하지 않는다.

### 마이그레이션·롤백

후보 `0002_phase_02_cp3_foundation`은 신규 table/FK/unique constraint만 추가한다. provider latest의 key는 `provider_security_identity_id`이고 canonical linkage는 nullable mapping table에서 분리한다. `0001` 수정, 기존 table destructive rebuild, corp_code/CIK fake backfill, 기존 fixture 변환과 SQLite 가격 history 누적을 금지한다. downgrade는 disposable DB에서만 검증하며 실제 raw/history를 자동 삭제하지 않는다.

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
