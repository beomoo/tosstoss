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

- 상태: `PROPOSED`
- 제안일: `2026-08-23`

### 문제

Phase 2부터 실제 외부 HTTP 연결과 OAuth credential을 도입해야 한다. 토스증권 공식 API에는 시장 데이터뿐 아니라 계좌·자산·주문·조건주문과 WebSocket 주문 이벤트도 함께 존재하므로 단순 provider client는 읽기 전용 경계를 약화할 수 있다.

### 제안

- backend만 `https://openapi.tossinvest.com`에 연결한다.
- `plans/PHASE_02_EXECUTION_PLAN.md`의 12개 REST method/path allowlist만 호출한다.
- POST는 `/oauth2/token`만 허용한다.
- `X-Tossinvest-Account`, 계좌·자산·주문·조건주문 endpoint와 WebSocket은 runtime·config·dependency·test helper에 추가하지 않는다.
- token은 single-flight backend manager의 memory에만 두고 secret redaction과 deny-by-default policy canary를 적용한다.
- 기존 standard test는 fixture-only·offline을 유지하고 live preflight는 별도 명시적 opt-in으로 분리한다.

### 대안

- 공식 API 전체를 범용 client로 생성: 금지 surface가 넓어져 거부한다.
- WebSocket 시세까지 Phase 2에 포함: 공식 AsyncAPI는 존재하지만 범위·운영 복잡도가 커져 별도 승인으로 이연한다.
- 외부 연결을 계속 전면 금지: Phase 2 목표를 달성하지 못한다.

### 영향

Phase 1의 blanket HTTP-client/connector 금지는 CP2에서 exact Toss connector exception으로 바뀐다. 대신 금지 endpoint·header·host canary를 추가해 보안 정책을 완화하지 않는다.

### 마이그레이션·롤백

checkpoint 단위로 connector/config/dependency/policy 변경을 revert하고 fixture-only repository로 복귀한다. token은 메모리에서 폐기하며 수집한 검증 데이터는 자동 삭제하지 않는다.

### 구현 진행 메모 — 2026-08-23

- CP2-A의 dependency/config/policy 경계와 CP2-B의 OAuth token manager/exact-boundary HTTP client까지 구현·검증했다.
- CP2-B는 synthetic credential과 `httpx.MockTransport`만 사용했고 실제 provider API 호출이나 token 저장은 하지 않았다.
- CP2-C rate limiter·retry와 CP2-D live preflight가 남아 있으므로 ADR 상태는 `PROPOSED`를 유지하며 CP2 전체 구현 또는 승인으로 간주하지 않는다.

---

## ADR-011 — date-only Toss 관측을 versioned source contract로 분리

- 상태: `PROPOSED`
- 제안일: `2026-08-23`

### 문제

Phase 1 `SourceRecord`는 `observed_at`과 `published_at`을 필수 datetime으로 요구한다. Toss 수급 응답 일부는 기준 `date`만 제공하고 publication timestamp를 제공하지 않아, 자정이나 fetch 시각을 대입하면 기존 시간 의미를 위반한다.

### 제안

- 기존 Phase 1 `SourceRecord` v0.1.0과 fixture는 변경하지 않는다.
- Phase 2에 date-only와 timestamp 관측을 구분하는 versioned provider source contract를 추가한다.
- `observed_at`과 `observed_date`를 구분하고 최소 하나를 요구한다.
- 미제공 `published_at`은 null과 구조화된 `NOT_PROVIDED` 사유로 표현한다.
- 전역 contract version Literal을 무조건 넓히지 않고 새 contract에 명시적 version을 부여한다.

### 대안

- date를 자정 UTC/KST로 변환: 존재하지 않는 시각을 생성하므로 거부한다.
- `fetched_at`을 `observed_at`으로 복사: 데이터 기준시각과 수집시각을 혼동하므로 거부한다.
- 기존 SourceRecord 전체를 즉시 breaking migration: Phase 1 회귀 범위가 커서 거부한다.

### 영향

CP3에서 source contract·OpenAPI·fixture·repository test가 추가된다. 기존 Phase 1 계약 테스트와 `contract_version=0.1.0` 응답은 그대로 통과해야 한다.

### 마이그레이션·롤백

신규 provider record만 새 contract를 사용한다. rollback은 신규 publish 중지와 해당 contract 코드 revert이며 기존 Phase 1 row·fixture를 변환하거나 삭제하지 않는다.

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
